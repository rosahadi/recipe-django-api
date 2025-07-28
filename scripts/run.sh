#!/bin/sh

set -e

echo "🟢 Waiting for database..."
python manage.py wait_for_db

echo "🟢 Collecting static files..."
python manage.py collectstatic --noinput

echo "🟢 Applying database migrations..."
python manage.py migrate

echo "🚀 Starting uWSGI server..."
exec uwsgi --socket :9000 --workers 4 --master --enable-threads --module app.wsgi
