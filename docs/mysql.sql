-- Run with a database-administrator account on your local server.
CREATE DATABASE IF NOT EXISTS clipview CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- Replace the password before running the following statements.
CREATE USER IF NOT EXISTS 'clipview'@'localhost' IDENTIFIED BY 'REPLACE_WITH_YOUR_OWN_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE ON clipview.* TO 'clipview'@'localhost';
