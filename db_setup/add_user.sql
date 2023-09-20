CREATE USER etl_user IDENTIFIED BY {add_pw};
GRANT INSERT, SELECT ON bus_routes.* TO {add_user};