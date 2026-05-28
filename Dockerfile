# Multi-stage Dockerfile for production
FROM python:3.11-slim as builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev git curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel
RUN pip wheel --no-cache-dir --no-deps -r requirements.txt -w /wheels

FROM python:3.11-slim as runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 POETRY_VIRTUALENVS_CREATE=false
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY --from=builder /wheels /wheels
COPY requirements.txt /app/
RUN pip install --no-cache /wheels/* && rm -rf /wheels
COPY . /app/
RUN chown -R app:app /app
USER app
ENV PATH="/app:$PATH"

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python manage.py redis_healthcheck || exit 1

CMD ["/app/start-render.sh"]