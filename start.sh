#!/usr/bin/env bash
set -euo pipefail
export DJANGO_SETTINGS_MODULE=therapeutic_coding.settings
echo "Starting container, waiting for dependent services..."
python ./scripts/wait_for_services.py
echo "Applying database migrations..."
python manage.py migrate --noinput
echo "Collecting static files..."
python manage.py collectstatic --noinput
echo "Starting Gunicorn with Uvicorn workers..."
exec gunicorn therapeutic_coding.asgi:application \
  -k uvicorn.workers.UvicornWorker \
  -w ${GUNICORN_WORKERS:-2} \
  --bind 0.0.0.0:8000 \
  --log-level ${GUNICORN_LOG_LEVEL:-info}
