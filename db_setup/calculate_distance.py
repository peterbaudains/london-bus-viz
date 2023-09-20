from sqlalchemy import create_engine
import geopandas as gpd
import os
import pandas as pd

def get_db_conn():
    conn_str = f"mysql+mysqlconnector://{os.environ['MYSQL_ETL_USER']}:{os.environ['MYSQL_ETL_PASSWORD']}@127.0.0.1:3306/bus_routes"
    return create_engine(conn_str)

# Calculate distances
stops = pd.read_sql("SELECT * FROM stops", con=get_db_conn())
stops = gpd.GeoDataFrame(stops, geometry=gpd.points_from_xy(stops['lon'], stops['lat']), crs=4326)
stops = stops.to_crs(27700)
edges = stops[['naptanId', 'commonName', 'geometry']].merge(stops[['naptanId', 'commonName', 'geometry']].loc[1:].reset_index(drop=True), left_index=True, right_index=True, suffixes=('_start', '_end'))
edges['distance'] = gpd.GeoSeries(edges['geometry_start']).distance(gpd.GeoSeries(edges['geometry_end']))
edges[['naptanId_start', 'naptanId_end', 'distance']].to_sql('edge_distances', con=get_db_conn(), if_exists='append', index=False)