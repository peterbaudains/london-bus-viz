# -*- coding: utf-8 -*-

import mysql.connector
import pandas as pd
import numpy as np
import panel as pn
import cartopy.io.img_tiles as cimgt
import cartopy.crs as ccrs
from scipy.stats import sem
import matplotlib.text as text
import datetime as dt
import matplotlib.image as mpimg

import os
import sys
sys.path.append('vizent/')
from vizent.vizent_plot import create_plot, add_lines
from vizent.background_map import get_projected_aspects

def get_db_conn():
    cnx = mysql.connector.connect(user=os.environ['MYSQL_APP_USER'], 
                                  password=os.environ['MYSQL_APP_PASSWORD'], 
                                  host='db', # change to db when running in docker-compose
                                  database='bus_routes')
    return cnx


def get_edge_estimates(route, direction):
    cnx = get_db_conn()
    cursor = cnx.cursor()
    
    q ="""
        SELECT 
            start_naptanId, 
            end_naptanId, 
            ed.distance,
            estimate_time, 
            estimate_seconds      
        FROM edge_estimates
        JOIN edge_distances ed 
        ON ed.naptanId_start = start_naptanId 
        AND ed.naptanId_end = end_naptanId
        AND ADDTIME(estimate_time, SEC_TO_TIME(1800)) > NOW()
        AND estimate_seconds < 1800
        AND estimate_seconds > 10
        AND edge_estimates.route = %s
        AND edge_estimates.direction = %s
        """

    cursor.execute(q, (route, direction))
    columns = ['start_naptanId', 'end_naptanId', 'distance', 'estimate_time', 
               'estimate_seconds']
    edge_estimates = pd.DataFrame(cursor.fetchall(), columns=columns)
    cnx.close()
    return edge_estimates


def get_stops(transform_crs, route, direction):
    cnx = get_db_conn()
    cursor = cnx.cursor()
    q = "SELECT * FROM stops WHERE route=%s and direction=%s ORDER BY stop_order ASC"
    cursor.execute(q, (route, direction))
    stops = pd.DataFrame(cursor.fetchall(), columns=['stop_key', 'route', 'direction', 'stop_order', 'commonName', 'naptanId', 'lat', 'lon'])
    
    transformed = transform_crs.transform_points(src_crs=ccrs.PlateCarree(), x=stops['lon'], y=stops['lat'])
    stops['transformed_x'] = [i[0] for i in transformed]
    stops['transformed_y'] = [i[1] for i in transformed]

    return stops


def add_location_data(stops, edge_estimates):

    edge_estimates = edge_estimates.merge(stops[['naptanId','transformed_x','transformed_y']].rename(
                                            {'transformed_x': 'x_start', 
                                            'transformed_y': 'y_start', 
                                            'naptanId': 'start_naptanId'
                                            }, axis=1), 
                                        how='inner', 
                                        on='start_naptanId')

    edge_estimates = edge_estimates.merge(stops[['naptanId','transformed_x','transformed_y']].rename(
                                            {'transformed_x': 'x_end', 
                                            'transformed_y': 'y_end', 
                                            'naptanId': 'end_naptanId'
                                            }, axis=1), 
                                        how='inner', 
                                        on='end_naptanId')

    return edge_estimates


def get_vizent_fig(route, direction, show_map=True):
    ''' 
    Given a bus route name and a direction, plot the vizent figure to display
    and estimate of speed on line segements and standard error of the mean to 
    indicate variability/uncertainty.

    The show_map variable is used as a switch to plot the background map
    '''

    # Use mapbox light as a background map
    mapbox_light = cimgt.MapboxTiles(access_token=os.environ['MAPBOX_API_TOKEN'], map_id='light-v11')
    
    # Get latest edge estimates from the db
    edge_estimates = get_edge_estimates(route, direction)
    if edge_estimates.shape[0] == 0:
        return None, edge_estimates

    # Get stops and add location data to estimates
    stops = get_stops(mapbox_light.crs, route, direction)
    edge_estimates = add_location_data(stops, edge_estimates)

    # Plot test
    vizent_fig = create_plot(use_glyphs=False, 
                             use_lines=True, 
                             show_legend=True, 
                             show_axes=False, 
                             use_cartopy=True, 
                             cartopy_projection=mapbox_light.crs,
                             extent=[-0.152096,-0.082229,51.4975, 51.5282],
                             scale_x=20, 
                             scale_y=11.25)
    
    # Adjust figure layout
    vizent_fig[0].subplots_adjust(left=0.001, right=1, bottom=0.001, top=1, 
                                  wspace = 0.02)

    # Background map switch
    if show_map:
        vizent_fig[1].add_image(mapbox_light, 14, zorder=0)

    # Plot stops as an angled triangle in the direction of the next edge
    for i in range(stops.shape[0]-1):
        dx = stops['transformed_x'].values[i+1] - \
                stops['transformed_x'].values[i]
        dy = stops['transformed_y'].values[i+1] - \
                stops['transformed_y'].values[i]
        theta = np.arctan2(dy, dx)
        theta_degrees = 180 * theta / np.pi
        vizent_fig[1].plot(stops['transformed_x'].values[i],
                           stops['transformed_y'].values[i],
                           marker=(3, 1, theta_degrees + 270),
                           markersize=10,
                           lw=0, 
                           color='k')
    
    # Plot the terminating stop
    vizent_fig[1].plot(stops['transformed_x'].values[stops.shape[0]-1], 
                       stops['transformed_y'].values[stops.shape[0]-1], 
                       marker='o', 
                       color='k', 
                       markersize=10
                       )
    
    # Calculate edge color and frequency for plotting the lines
    viz_df = edge_estimates.groupby(['start_naptanId', 'end_naptanId', 
                                     'distance', 'x_start', 'x_end', 
                                     'y_start', 'y_end'])['estimate_seconds']\
                                        .agg([np.mean, sem]).reset_index()
    
    # Convert to kmh
    viz_df['kmh'] = 3.6 * (viz_df['distance'] / viz_df['mean'])

    # Plot the lines on the figure
    add_lines(vizent_fig,
              x_starts=viz_df['x_start'], 
              x_ends=viz_df['x_end'], 
              y_starts=viz_df['y_start'], 
              y_ends=viz_df['y_end'], 
              color_values=viz_df['kmh'],
              freq_values=viz_df['sem'], 
              width_values=[10 for l in range(viz_df.shape[0])], 
              colormap='Purples', 
              color_min=0,
              color_max=30,
              label_fontsize=12, 
              legend_title='Legend', 
              color_label='Speed (km/h)', 
              frequency_label='Variability', 
              length_type='units',
              style='set_length',
              striped_length=150,
              scale_dp=0,
              freq_n=3)

    # Rename axis labels
    sem_scale = []
    for child in vizent_fig[0].axes[0].get_children():
        if type(child)==text.Annotation:
            try:
                number = int(child.get_text())
                sem_scale.append(number)
            except:
                pass
    for child in vizent_fig[0].axes[0].get_children():
        if type(child)==text.Annotation:
            try: 
                number = int(child.get_text())
                if number == min(sem_scale):
                    child.set_text('Low')
                elif number == max(sem_scale):
                    child.set_text('High')
                else:
                    child.set_text('Medium')
            except:
                pass

    # Add mapbox attribution
    im = mpimg.imread('mapbox-logo-black.png')
    imax = vizent_fig[1].inset_axes([0.0, 0.01, 0.1, 0.02])
    imax.imshow(im)
    imax.axis('off')
    
    return vizent_fig[0], edge_estimates


def get_route_options():
    ''' 
    Get the list options for the routes for which vizent_figs can be created.
    '''

    cnx = get_db_conn()
    cursor = cnx.cursor()
    q = "SELECT route_name, direction, start_commonName, end_commonName \
         FROM Routes"
    cursor.execute(q)
    columns = ['route', 'direction', 'start_commonName', 'end_commonName'] 
    route_options = pd.DataFrame(cursor.fetchall(), columns=columns)
    route_options['display_text'] = route_options['route'] + ': ' + \
                                    route_options['start_commonName'] + \
                                    ' to ' + route_options['end_commonName']
    
    cnx.close()
    return route_options


def update(event):
    '''
    Callback function to render a new image when a selection in the drop down
    menu is selected
    '''

    # Get the route and direction selected
    route, direction\
          = route_options[route_options['display_text'] == event.new] \
                [['route', 'direction']].values[0]
    
    # Plot the map
    map_fig, edge_estimates = get_vizent_fig(route, direction, show_map=True)
    nomap_fig, edge_estimates = get_vizent_fig(route, direction, show_map=False)

    # Handle any missing data and create other panel objects.
    if edge_estimates.shape[0] == 0:
        show_map = pn.widgets.StaticText(name='show_map_no_estimates', value='No estimates found in the db.')
        no_map = pn.widgets.StaticText(name='no_map_no_estimates', value='No estimates found in the db.')
    else:
        latest_timestamp = edge_estimates['estimate_time'].max()
        estimate_count = edge_estimates.shape[0]
        next_data_timestamp = edge_estimates['estimate_time'].max() + dt.timedelta(seconds=60)
        context_row = pn.Row(
            f"Latest data: {latest_timestamp} UTC", 
            f"Estimates in last 30 minutes: {estimate_count}", 
            f"Refreshed data available at {next_data_timestamp} UTC"
        )
        show_map = pn.pane.Matplotlib(map_fig, dpi=300, name='Map')
        no_map = pn.pane.Matplotlib(nomap_fig, dpi=300, name='No map')
    layout[4] = pn.Tabs(('Map', show_map), no_map)
    layout[3] = context_row


# Dashboard definitions
pn.extension(sizing_mode="stretch_width", design='material', template="fast")
pn.state.template.param.update(title="How fast are London buses travelling?")

# Create some text describing the dashboard
dashboard_intro = pn.pane.Markdown("""
                Using open data from TfL, this dashboard estimates bus speeds \
                on road segments between stops and creates a data \
                visualisation of these estimates and their variability using \
                the [vizent library](https://cusplondon.ac.uk/vizent).
                """)

data_info = pn.pane.Markdown("""
The estimates are constructed by looking at the difference \
in bus arrival estimates from the [TfL unified \
API](https://api.tfl.gov.uk/) across consecutive stops on \
a given bus route. Data is collected from the API every 60 \
seconds. Bus locations are inferred by using the stop with \
the smallest time to arrival estimate. The time taken for a \
bus to travel along a road segment is estimated as the \
difference between the last arrival estimate to the previous \
stop and the current estimate to the next stop. The average \
speed along a segment is then computed as the distance of the \
segment divided by the estimated time taken.

In the visualisations generated, we plot the average of all \
estimates on the segment captured within the last 30 minutes \
from the moment the image is rendered, which is represented \
as the colour of the edges. The variability, represented by \
the black and white frequency segment of each line, is \
calculated as the standard error of the mean of each estimate.\
This captures variability across our estimates but also \
reduces as our sample size increases. The network segments \
and their associated variability are plotted on a static \
background map centred on the home of CUSP London in Bush \
House, Aldwych.

Our objectives in creating this dashboard are:
1) To provide real-time insights that can aid operational \
decision-making in a transport context (for example, to \
respond to congestion on London's road network).
2) To capture and visually represent uncertainty associated \
with our measurements, which is a key factor in determining \
how to respond, and which can often be neglected in data \
visualisations that support decision-making.""")

acknlgmnts = pn.pane.Markdown("""
                This dashboard is created by [CUSP \
                London](https://cusplondon.ac.uk/) at King's College London \
                and is powered by TfL Open Data. Contains OS data © Crown \
                copyright and database rights 2016 and Geomni UK Map data\
                © and database rights [2019].
                """)

# Drop down menu
route_options = get_route_options()
route_select = pn.widgets.Select(name='Route', 
                                 options=[' '] + \
                                    route_options['display_text']\
                                    .sort_values().values.tolist())

context_row = None
tabs = None

map_attribution_html = """Map Data: © <a href='https://www.mapbox.com/about/maps/'>
                        Mapbox</a> © <a href=
                        'http://www.openstreetmap.org/copyright'>
                        OpenStreetMap</a> <strong>
                        <a href='https://www.mapbox.com/map-feedback/' 
                        target='_blank'>Improve this map</a></strong>"""

layout = pn.Column(dashboard_intro,
                   pn.Accordion(('Information', data_info),
                   ('Acknowledgements', acknlgmnts)),
                   route_select,
                   context_row, 
                   tabs,
                   pn.pane.HTML(map_attribution_html))

route_select.param.watch(update, 'value')

layout.servable()