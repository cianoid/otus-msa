-- Создание баз данных
CREATE DATABASE app_auth OWNER dba;
CREATE DATABASE app_user OWNER dba;
CREATE DATABASE app_billing OWNER dba;
CREATE DATABASE app_order OWNER dba;
CREATE DATABASE app_notification OWNER dba;
CREATE DATABASE app_warehouse OWNER dba;
CREATE DATABASE app_delivery OWNER dba;

\c app_auth
GRANT ALL PRIVILEGES ON SCHEMA public TO dba;

\c app_user
GRANT ALL PRIVILEGES ON SCHEMA public TO dba;

\c app_billing
GRANT ALL PRIVILEGES ON SCHEMA public TO dba;

\c app_order
GRANT ALL PRIVILEGES ON SCHEMA public TO dba;

\c app_notification
GRANT ALL PRIVILEGES ON SCHEMA public TO dba;

\c app_warehouse
GRANT ALL PRIVILEGES ON SCHEMA public TO dba;

\c app_delivery
GRANT ALL PRIVILEGES ON SCHEMA public TO dba;
