#!/bin/bash

WEBAPP_HOME="/opt/bjj"
SCRIPTS_DIR="/opt/bjj/scripts"
INSTANCE_HOME="$WEBAPP_HOME/instance"

# Create user
APP_USER="nexusadmin"
adduser --system --group $APP_USER

# Create directory
mkdir $WEBAPP_HOME
cd $WEBAPP_HOME

# Create venv
apt-get update
apt-get install -y python3-venv
python3 -m venv venv

# Install webapp
echo 'Installing webapp...'
pip install .
mkdir instance
cd $SCRIPTS_DIR

echo 'Creating webapp service...'
sed -E 's+(ExecStart=)(.*)$+\1'"$SCRIPTS_DIR\/run.sh+" webapp.service > /lib/systemd/system/nexusbjj.service

echo 'Creating log folder...'
LOG_FOLDER="/var/log/nexusbjj"
mkdir -p $LOG_FOLDER 
ln -s $LOG_FOLDER $INSTANCE_HOME/logs

echo 'Configuring logging...'
LOG_FILE="$LOG_FOLDER/webapp.log"
cp run.sh run.sh.old
sed -E "s|<log_file>|${LOG_FILE}|" run.sh.old > run.sh
echo "The application will log to $LOG_FILE"

echo 'Creating config...'
read -p "Enter IP address of database host: " DATABASE
read -s -p "Enter database password: " PASSWORD
sed -E "s/<host>/${DATABASE}/" $SCRIPTS_DIR/config_template.py | sed -E "s/<password>/$PASSWORD/" > $INSTANCE_HOME/config.py

# Change ownership of project to APP_USER
chown -R $APP_USER:$APP_USER $WEBAPP_HOME

echo 'Installing service...'
systemctl enable nexusbjj

echo 'Starting service...'
systemctl start nexusbjj

echo 'Done.'
