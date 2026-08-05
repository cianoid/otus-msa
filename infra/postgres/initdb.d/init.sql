-- Создание баз данных
CREATE DATABASE app_auth OWNER dba;
CREATE DATABASE app_user OWNER dba;
CREATE DATABASE app_billing OWNER dba;
CREATE DATABASE app_order OWNER dba;
CREATE DATABASE app_notification OWNER dba;

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
