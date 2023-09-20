INSERT INTO routes (
            route_name VARCHAR(255),
            direction VARCHAR(255), 
            start_naptanId VARCHAR(255),
            start_commonName VARCHAR(255), 
            end_naptanId VARCHAR(255), 
            end_commonName VARCHAR(255),
            min_lat FLOAT, 
            max_lat FLOAT,
            min_lon FLOAT, 
            max_lon FLOAT
        )
        WITH route_end_points AS (
            SELECT 
                route, 
                direction, 
                naptanId, 
                commonName, 
                stop_order 
            FROM (
                SELECT 
                    route, 
                    direction, 
                    naptanId, 
                    commonName, 
                    stop_order,  
                    row_number() over (partition by route, direction order by stop_order desc) as rn
                FROM bus_routes.stops
            ) ta
            WHERE stop_order = 0 OR rn = 1   
        )
        SELECT 
			start.route, 
            start.direction, 
            start.naptanId, 
            start.commonName, 
            end.naptanId, 
            end.commonName, 
            min(lat) as min_lat,
            max(lat) as max_lat,
            min(lon) as min_lon, 
            max(lon) as max_lon
        FROM route_end_points start
        JOIN route_end_points end ON start.route = end.route AND start.direction = end.direction AND start.naptanId <> end.naptanId AND start.stop_order = 0
        JOIN stops s ON s.route = start.route AND s.direction = start.direction 
        GROUP BY start.route, start.direction, start.naptanId, start.commonName, end.naptanId, end.commonName