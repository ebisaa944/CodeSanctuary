#!/usr/bin/env bash
set -euo pipefail

echo "Render start: running migrations and collectstatic"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

WEB_CONCURRENCY=${WEB_CONCURRENCY:-2}
PORT=${PORT:-8000}

echo "Starting Gunicorn (Uvicorn workers): workers=$WEB_CONCURRENCY port=$PORT"
exec gunicorn therapeutic_coding.asgi:application \
  -k uvicorn.workers.UvicornWorker \
  -w $WEB_CONCURRENCY \
  --bind 0.0.0.0:$PORT \
  --log-level ${GUNICORN_LOG_LEVEL:-info} \
  --timeout ${GUNICORN_TIMEOUT:-120}
