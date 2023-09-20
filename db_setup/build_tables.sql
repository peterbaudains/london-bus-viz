USE bus_routes;

CREATE TABLE arrivals (
    route varchar(255),
    direction varchar(255),
    vehicleId varchar(255), 
    naptanId varchar(255), 
    stationName varchar(255), 
    timeToStation int, 
    retrievalTime datetime
);

CREATE TABLE stops (
    stop_key INT NOT NULL AUTO_INCREMENT,
    route VARCHAR(255), 
    direction VARCHAR(255),
    stop_order INT, 
    commonName varchar(255), 
    naptanId varchar(255), 
    lat FLOAT, 
    lon FLOAT,
    PRIMARY KEY (stop_key)
);


CREATE TABLE edge_estimates (
	edge_estimate_key INT NOT NULL AUTO_INCREMENT, 
    start_naptanId VARCHAR(255), 
    end_naptanId VARCHAR(255), 
    estimate_seconds INT, 
    estimate_time DATETIME, 
    PRIMARY KEY (edge_estimate_key)


CREATE TABLE edge_distances (
    start_naptanId VARCHAR(255),
    end_naptanId VARCHAR(255), 
    distance FLOAT
)


CREATE TABLE routes (
    route_key INT NOT NULL AUTO_INCREMENT, 
    route_name VARCHAR(255),
    direction VARCHAR(255), 
    start_naptanId VARCHAR(255),
    start_commonName VARCHAR(255), 
    end_naptanId VARCHAR(255), 
    end_commonName VARCHAR(255),
    min_lat FLOAT, 
    max_lat FLOAT,
    min_lon FLOAT, 
    max_lon FLOAT,
    PRIMARY KEY (route_key)
)

