import requests
import json
import pandas as pd
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.sql import text


def get_arrivals_data(route, retrieval_time, inbound=True):
    # arrivals dataprep 
    r = requests.get(f"https://api.tfl.gov.uk/Line/{route}/Arrivals")
    content = json.loads(r.content.decode('utf-8'))
    arrivals = pd.DataFrame(content)
    if inbound:
        arrivals = arrivals[arrivals['direction'] == 'inbound']
        arrivals['direction'] = 'inbound'
    else:
        arrivals = arrivals[arrivals['direction'] == 'outbound']
        arrivals['direction'] = 'outbound'
    
    arrivals['route'] = route
    arrivals['retrievalTime'] = retrieval_time

    required_columns = ['route', 'direction', 'vehicleId', 'naptanId', \
                        'stationName', 'timeToStation', 'retrievalTime']

    return arrivals[required_columns].sort_values(by=['vehicleId', 'timeToStation'])


def get_db_conn():
    conn_str = f"mysql+mysqlconnector://{os.environ['MYSQL_ETL_USER']}:{os.environ['MYSQL_ETL_PASSWORD']}@db:3306/bus_routes"
    return create_engine(conn_str, echo=True)


def extract_and_load_data():

    aldwych_bus_routes = ['1', '9', '15', '23', '26', '59', '68', '76', '87', 
                          '91', '168', '172', '188', '243', '341']
    
    retrieval_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for route in aldwych_bus_routes:
        inbound_data = get_arrivals_data(route,retrieval_time,inbound=True)
        inbound_data.to_sql('arrivals', con=get_db_conn(), if_exists='append', index=False)

        outbound_data = get_arrivals_data(route,retrieval_time,inbound=False)
        outbound_data.to_sql('arrivals', con=get_db_conn(), if_exists='append', index=False)

def transform_data():

    q = """
        INSERT INTO edge_estimates (
            route, 
            direction,
            start_naptanId, 
            end_naptanId, 
            estimate_seconds, 
            estimate_time
        )
        WITH time_to_next_stations AS (
            SELECT 
                vehicleId, 
                MIN(timeToStation) AS time_to_next_station 
            FROM arrivals
            WHERE retrievalTime = (SELECT MAX(retrievalTime) FROM arrivals)
            GROUP BY vehicleId
        ), 
        edges AS (
            SELECT
                s1.naptanId as edge_start, 
                s2.naptanId as edge_end
            FROM stops s1
            JOIN stops s2 ON s1.stop_order + 1 = s2.stop_order
            AND s1.route = s2.route
	        AND s1.direction = s2.direction
        ),
        latest_previous_estimates AS (
            SELECT 
                naptanId, 
                direction, 
                vehicleId, 
                timeToStation, 
                retrievalTime 
            FROM (
                SELECT 
                    *, 
                    ROW_NUMBER() OVER (PARTITION BY vehicleId, naptanId ORDER BY retrievalTime DESC) AS rn
                FROM arrivals
            ) ta where rn = 1
        )
        SELECT
            a.route, 
            a.direction,
            edges.edge_start AS start_naptanId, 
            edges.edge_end AS end_naptanId,
            TIME_TO_SEC(TIMEDIFF(ADDTIME(a.retrievalTime, SEC_TO_TIME(ttns.time_to_next_station)), ADDTIME(latest_previous_estimates.retrievalTime, SEC_TO_TIME(latest_previous_estimates.timeToStation)))) AS estimate_seconds,
            a.retrievalTime AS estimate_time
        FROM arrivals a 
        JOIN time_to_next_stations ttns 
        ON a.vehicleId = ttns.vehicleId 
        AND a.timeToStation = ttns.time_to_next_station
        AND a.retrievalTime = (SELECT MAX(retrievalTime) FROM arrivals)
        JOIN edges ON a.naptanId = edges.edge_end
        JOIN latest_previous_estimates ON edges.edge_start = latest_previous_estimates.naptanId and a.vehicleId = latest_previous_estimates.vehicleId;
        """
    engine = get_db_conn()
    with engine.connect() as connection:
        connection.execute(text(q))
        connection.commit()


if __name__=="__main__":
    extract_and_load_data()
    transform_data()
