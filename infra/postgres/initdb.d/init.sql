-- Создание баз данных
CREATE DATABASE app_auth OWNER dba;
CREATE DATABASE app_user OWNER dba;

\c app_auth
GRANT ALL PRIVILEGES ON SCHEMA public TO dba;

\c app_user
GRANT ALL PRIVILEGES ON SCHEMA public TO dba;

