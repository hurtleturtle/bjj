#!/bin/bash

WEBAPP_HOME=$(dirname $(dirname $(readlink -f "$0")))
LOG_FILE="$WEBAPP_HOME/instance/logs/webapp.log"
source $WEBAPP_HOME/venv/bin/activate
pkill uwsgi
nohup uwsgi --socket 0.0.0.0:5000 --wsgi-file "$WEBAPP_HOME/wsgi.py" --logto $LOG_FILE
