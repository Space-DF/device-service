#!/bin/ash

echo "Apply database migrations"
python manage.py migrate_schemas --shared

echo "Starting server"
gunicorn --worker-class gevent --bind 0.0.0.0:80 --access-logfile - device_service.wsgi & celery -A device_service worker -l info -c 1
