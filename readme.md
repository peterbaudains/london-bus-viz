# TfL bus route estimated speed and variability real-time visualisation

Using open data from TfL, this dashboard estimates bus speeds on road segments between stops and creates a data visualisation of these estimates and their variability using the [vizent library](https://cusplondon.ac.uk/vizent).

The estimates are constructed by looking at the difference in bus arrival estimates from the [TfL unified API](https://api.tfl.gov.uk/) across consecutive stops on a given bus route. Data is collected from the API every 60 seconds. Bus locations are inferred by using the stop with the smallest time to arrival estimate. The time taken for a bus to travel along a road segment is estimated as the difference between the last arrival estimate to the previous stop and the current estimate to the next stop. The average speed along a segment is then computed as the distance of the segment divided by the estimated time taken.

In the visualisations generated, we plot the average of all estimates on the segment captured within the last 30 minutes from the moment the image is rendered, which is represented as the colour of the edges. The variability, represented by the black and white frequency segment of each line, is calculated as the standard error of the mean of each estimate.This captures variability across our estimates but also reduces as our sample size increases. The network segments and their associated variability are plotted on a static background map centred on the home of CUSP London in Bush House, Aldwych.

Our objectives in creating this dashboard are:

1) To provide real-time insights that can aid operational decision-making in a transport context (for example, to respond to congestion on London's road network).

2) To capture and visually represent uncertainty associated with our measurements, which is a key factor in determining how to respond, and which can often be neglected in data visualisations that support decision-making.

## Getting started

Prerequisites:
- Docker engine and docker-compose

The following environment variables are required to be setup for the docker images. These are: 
- `HOST_DATA_VOLUME_PATH`
- `MYSQL_ROOT_PASSWORD`
- `MYSQL_ETL_USER`
- `MYSQL_ETL_PASSWORD`
- `MYSQL_APP_USER`
- `MYSQL_APP_PASSWORD`
- `MAPBOX_API_TOKEN`

To build the images:

`docker-compose build`

To run the containers:

`docker-compose up -d`


## License

Distributed under the MIT License. See `LICENSE.txt` for more information.


## Contact

Peter Baudains - peter.baudains@kcl.ac.uk

Project link: https://github.com/peterbaudains/london-bus-viz


## Acknowlegements

Created by CUSP London at King's College London. Powered by TfL Open Data. Contains OS data © Crown copyright and database rights 2016 and Geomni UK Map data © and database rights [2019].
