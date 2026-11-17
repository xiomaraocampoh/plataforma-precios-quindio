#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py cargar_demo --con-vencidos
exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --access-logfile -
