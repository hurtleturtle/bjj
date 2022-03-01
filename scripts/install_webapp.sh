#!/bin/bash

WEBAPP_HOME=$(dirname $(dirname $(readlink -f "$0")))
SCRIPTS_DIR=$(dirname $(readlink -f "$0"))
INSTANCE_HOME="$WEBAPP_HOME/instance"

# Install webapp
echo 'Installing webapp...'
cd $WEBAPP_HOME
pip install .
mkdir instance
cd $SCRIPTS_DIR

echo 'Creating webapp service...'
sed -E 's+(ExecStart=)(.*)$+\1'"$SCRIPTS_DIR\/run.sh+" webapp.service > /lib/systemd/system/webapp.service

echo 'Creating log folder...'
LOG_FOLDER="/var/log/webapp"
mkdir -p $LOG_FOLDER 
ln -s $LOG_FOLDER $INSTANCE_HOME/logs

echo 'Configuring logging...'
LOG_FILE="$LOG_FOLDER/webapp.log"
cp run.sh run.sh.old
sed -E 's/<log_file>/'"$LOG_FILE/" run.sh.old > run.sh
echo "The application will log to $LOG_FILE"

echo 'Creating config...'
read -p "Enter IP address of database host: " DATABASE
read -s -p "Enter database password: " PASSWORD
sed -E 's/<host>/'"$DATABASE"'/' $SCRIPTS_DIR/config_template.py | sed -E 's/<password>/'"$PASSWORD"'/' > $INSTANCE_HOME/config.py

echo 'Installing service...'
systemctl enable webapp

echo 'Starting service...'
systemctl start webapp

echo 'Done.'
