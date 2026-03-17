#!/bin/ash

until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
	echo "Waiting for PostgreSQL..."
	sleep 2
done

# Install PostGIS extension if not exists
psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS postgis;"

echo "Apply database migrations"
python manage.py migrate_schemas --shared
python manage.py migrate

echo "Starting server"
gunicorn --worker-class gevent --bind 0.0.0.0:80 --access-logfile - device_service.wsgi & celery -A device_service worker -l info -c 1
