import requests
import json
import pandas as pd
import os
from sqlalchemy import create_engine

def get_db_conn():
    conn_str = f"mysql+mysqlconnector://{os.environ['MYSQL_ETL_USER']}:{os.environ['MYSQL_ETL_PASSWORD']}@127.0.0.1:3306/bus_routes"
    return create_engine(conn_str)

aldwych_bus_routes = ['1', '9', '15', '23', '26', '59', '68', '76', '87', 
                        '91', '168', '172', '188', '243', '341']
    
for route in aldwych_bus_routes:
    for direction in ['inbound', 'outbound']:
        if route == '9' and direction == 'inbound':
            pass
        else:
            r = requests.get(f"https://api.tfl.gov.uk/Line/{route}/StopPoints")
            content = json.loads(r.content.decode('utf-8'))
            all_stops = pd.DataFrame(content)

            r = requests.get(f"https://api.tfl.gov.uk/Line/{route}/Route/Sequence/{direction}/")
            content = json.loads(r.content.decode('utf-8'))
            ordered_stops = content['orderedLineRoutes'][0]['naptanIds']

            stops = all_stops[all_stops['naptanId'].isin(ordered_stops)]
            stops['stop_order'] = stops['naptanId'].apply(lambda x: ordered_stops.index(x))
            stops['route'] = route
            stops['direction'] = direction
            stops = stops[['route', 'direction', 'stop_order', 'commonName', 'naptanId', 'lat', 'lon']]
            stops.sort_values(by='stop_order').to_sql('stops', con=get_db_conn(), if_exists='append', index=False)
