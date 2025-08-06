#!/bin/sh

CONTAINER_ALREADY_STARTED="./data/CONTAINER_ALREADY_STARTED_FLAG"

if [ ! -f "$CONTAINER_ALREADY_STARTED" ]; then
    touch "$CONTAINER_ALREADY_STARTED"
    echo "-- First container startup --"
    # YOUR_FIRST_TIME_SETUP_COMMANDS_HERE
    python manage.py makemigrations
    python manage.py migrate
    #python manage.py collectstatic
else
    echo "-- Not first container startup --"
    # YOUR_REGULAR_STARTUP_COMMANDS_HERE (if any)

fi
python manage.py runserver 0.0.0.0:8000
# Keep the container running (e.g., if it's a server)
exec "$@"
