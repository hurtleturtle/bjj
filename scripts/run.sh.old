#!/bin/bash

WEBAPP_HOME=$(dirname $(dirname $(readlink -f "$0")))
LOG_FILE="<log_file>"
source $WEBAPP_HOME/venv/bin/activate
pkill uwsgi
nohup uwsgi --socket 0.0.0.0:5000 --wsgi-file "$WEBAPP_HOME/wsgi.py" --logto $LOG_FILE
