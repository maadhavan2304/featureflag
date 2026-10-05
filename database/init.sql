-- Only needed if you are NOT using docker-compose. Run as a MySQL admin (e.g. in MySQL Workbench).
-- Tables are then created by Alembic: `alembic upgrade head`.
CREATE DATABASE IF NOT EXISTS featureflags CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'ffuser'@'%' IDENTIFIED BY 'ffpass';
GRANT ALL PRIVILEGES ON featureflags.* TO 'ffuser'@'%';
FLUSH PRIVILEGES;
