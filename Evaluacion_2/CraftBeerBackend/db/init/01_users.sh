#!/bin/bash
# Crea un usuario/esquema Oracle por servicio y ejecuta su script. Corre dentro del contenedor Oracle.
set -e
for pair in "clients:$DB_CLIENTS_PWD" "inventory:$DB_INVENTORY_PWD" "orders:$DB_ORDERS_PWD" "payments:$DB_PAYMENTS_PWD" "delivery:$DB_DELIVERY_PWD" "notifications:$DB_NOTIFICATIONS_PWD"; do
  u="${pair%%:*}"; p="${pair#*:}"
  sqlplus -s / as sysdba <<SQL
ALTER SESSION SET CONTAINER=XEPDB1;
CREATE USER $u IDENTIFIED BY "$p" QUOTA UNLIMITED ON USERS;
GRANT CREATE SESSION, CREATE TABLE, CREATE SEQUENCE, CREATE PROCEDURE, CREATE VIEW, CREATE JOB TO $u;
EXIT;
SQL
  sqlplus -s "$u/$p@//localhost:1521/XEPDB1" @/opt/oracle/schemas/$u.sql
done
