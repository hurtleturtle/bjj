#!/bin/bash

apt-get update
apt-get install mysql-server

echo 'Preparing config...'
read -s -p 'Database password: ' PASSWORD
sed -E 's/<password>/'$PASSWORD'/' init_template.sql > init.sql

echo 'Initialising database...'
mysql < init.sql

echo 'Finished setting up database.'