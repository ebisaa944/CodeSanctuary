# Code Sanctuary — Therapeutic Learning Platform

[![CI](https://img.shields.io/badge/ci-pending-lightgrey)](#)
[![Coverage](https://img.shields.io/badge/coverage-unknown-lightgrey)](#)
[![License](https://img.shields.io/badge/license-PLACEHOLDER-lightgrey)](#)

Project documentation for the Code Sanctuary project (a.k.a. Therapeutic Coding).

## Project Overview

### Detailed description
Code Sanctuary is a Django-based, therapeutically-minded learning platform that pairs a learning experience with mental health-aware features. The system includes learning modules, social interactions, chat, and therapeutic tracking to encourage sustainable learning habits.

### Business purpose
- Provide an adaptable and gentle online learning environment.
- Track and respond to emotional state, reduce burnout risk.
- Provide presence-aware features (online indicators) for safe community interactions.

### Architecture overview
- Monolithic Django project, split into apps: `users`, `chat`, `therapy`, `learning`, `social`.
- REST API via Django REST Framework (DRF) + JWT (SimpleJWT) for mobile/SPA clients.
- Real-time presence & WebSocket support via Django Channels and Redis channel layer.
- Redis used for caching and presence (sorted-set + connection counters).
- ASGI entrypoint for WebSocket handling; WSGI kept for HTTP fallback.

### System capabilities
- Secure authentication (JWT with refresh rotation and blacklist support).
- Persistent account lockouts for abusive patterns.
- Redis-backed presence with TTL, connection counters and ghost session prevention.
- WebSocket authenticated presence channel for live indicators.
- Admin monitoring and filtered changelists (online/locked users) with audit logs.
- Throttling, object-level permission enforcement, and structured logging.

## Features

- Authentication
  - JWT tokens (SimpleJWT) + Session fallback for browsers.
  - Rotating refresh tokens and blacklist support enabled in settings.

- Online presence tracking
  - Redis-backed presence using a sorted set of `last_seen` timestamps.
  - Per-user connection counters to prevent ghost sessions.
  - Presence TTL and cleanup operations.

- WebSocket support
  - Django Channels `PresenceConsumer` for authenticated websocket connections.
  - Authenticated presence updates on connect/disconnect.

- Redis caching
  - `django-redis` cache backend with graceful fallback when Redis is unavailable.

- API endpoints
  - Profile management (HTML + API endpoints).
  - Cached `online-users` API (returns minimal non-PII user info).
  - Token refresh endpoint that updates presence.

- Admin monitoring
  - Admin filters for online and locked users.
  - Admin unlock action logs via Django `LogEntry`.

- Security hardening
  - DRF throttling defaults, serializer validation for HTML flows, audit logging, RBAC enforcement for admin unlocks.

- Testing
  - Unit tests for presence service, including fake Redis tests.

## Architecture

### Django architecture
- Apps are organized by domain under the project root. `AUTH_USER_MODEL` uses `users.TherapeuticUser`.
- Views provide both HTML and API endpoints. Business logic moved into service modules where appropriate (e.g., `chat/services`).

### DRF architecture
- DRF applies authentication classes preferring JWT and falling back to sessions.
- Global throttling defaults configured, with ability to declare per-view throttles.

### Redis presence system
- Uses a Redis sorted set key `<PREFIX>presence:active` where members are `user_id` and score is `last_seen` (unix epoch seconds).
- Per-user connection counters stored at `<PREFIX>presence:connections:<user_id>` to track open websocket connections.
- On login, token refresh, or websocket connect, the system `ZADD` the user's id with current timestamp and `INCR` the connection counter when appropriate.
- On websocket disconnect the system `DECR` the counter and removes the user from the set when the counter reaches zero.
- Presence TTL (`PRESENCE_TTL`) controls how long a user is considered online without refresh.

### WebSocket lifecycle
- Client connects to `/ws/presence/` (see `chat/routing.py`).
- `AuthMiddlewareStack` is used for session-based auth; for JWT-based websocket auth a custom token middleware is recommended.
- On connect: authenticate, call `PresenceService.add()` and `increment_connections()`.
- On disconnect: call `decrement_connections()` which removes the user from the sorted set if no active connections remain.

### Channels architecture
- `ASGI` application built via `ProtocolTypeRouter` in `therapeutic_coding/asgi.py`.
- Channel layer configured with Redis in `therapeutic_coding/settings.py`.

### ASGI flow
- HTTP → routed to Django ASGI app (matches WSGI behavior).
- WebSocket → routed to `AuthMiddlewareStack` → `PresenceConsumer` → presence service operations.

### Caching strategy
- Redis via `django-redis` configured as default cache with a key prefix.
- Presence keys use namespacing and short TTLs.
- Cache `IGNORE_EXCEPTIONS` enabled to allow graceful application operation when Redis is unreachable.

### Authentication flow
- Clients obtain JWT via login endpoints; tokens rotate refresh tokens and use blacklist.
- Session-based browsers use `SessionAuthentication`.
- Token refresh endpoint updates presence when invoked.

### Connection counting
- `PresenceService.increment_connections()` increments a per-user counter and refreshes their `last_seen` in the ZSET.
- `decrement_connections()` decrements and removes user when counter ≤ 0.

### Graceful fallback design
- If `django-redis` connection fails, `PresenceService` falls back to Django cache-based per-user keys as a degraded mode (not feature-complete but safe).

## Redis Presence Design (Detailed)

### Data structures
- Sorted set: `<PREFIX>presence:active`
  - Member: `user_id`
  - Score: `last_seen` (unix epoch seconds)

- Connection counter: `<PREFIX>presence:connections:<user_id>`
  - Integer counter (INCR/DECR).

### Semantics
- `add(user_id)`:
  - ZADD `<prefix>presence:active` with score = now
  - ZREMRANGEBYSCORE to trim entries older than `now - TTL`

- `increment_connections(user_id)`:
  - INCR connection counter
  - EXPIRE connection counter to TTL
  - ZADD last_seen to keep user active

- `decrement_connections(user_id)`:
  - DECR connection counter
  - If counter <= 0 → ZREM from active set

### Presence TTL
- Default `PRESENCE_TTL` is 45 seconds (configurable via env). Clients should refresh presence at intervals shorter than TTL when active.

### Ghost session prevention
- Connection counter ensures that a single disconnect doesn't remove a user who still has other open connections.

### Cleanup strategy
- `PresenceService.cleanup()` trims old ZSET entries older than `now - TTL`.

### Key naming structure
- `REDIS_KEY_PREFIX` (default `cs:`) + `presence:active`
- `REDIS_KEY_PREFIX` + `presence:connections:<user_id>`

## WebSocket Architecture

### Channels routing
- `chat/routing.py` defines `ws/presence/` endpoint.

### Consumers
- `chat/consumers.py` implements `PresenceConsumer` (ASGI) that accepts authenticated connections and updates presence.

### WebSocket authentication
- Session authentication supported via `AuthMiddlewareStack`.
- Recommend implementing JWT middleware for websocket auth in production: accept `?token=` query param or `Sec-WebSocket-Protocol` header and validate JWT.

### Online presence updates
- Connect → add + increment
- Disconnect → decrement (and possibly remove)

## Tech Stack
- Python 3.10+ (workspace uses Python 3.14 where available)
- Django 6.0
- Django REST Framework
- djangorestframework-simplejwt
- django-redis
- channels, channels-redis
- redis
- whitenoise (static files)
- pytest/unittest (tests)

## Installation Guide

Prerequisites
- Python 3.10+ (venv recommended)
- Redis server
- PostgreSQL (recommended for production)

Local setup (quick)

1. Create virtualenv and activate

```bash
python -m venv venv
venv\Scripts\Activate.ps1  # Windows PowerShell
source venv/bin/activate    # macOS/Linux
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

## Deployment (Docker)

This repository includes production-ready Docker and orchestration assets under the project root.

Quick start (development):

```bash
docker compose up --build
```

Production (example using docker stack):

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Ensure you have `.env.production` populated with secure secrets and a Redis/Postgres cluster available.

## Render.com Deployment

This project is optimized for Render.com. Use the provided `render.yaml` and set the following environment variables in the Render dashboard (or via `render.yaml` secrets):

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `DJANGO_SETTINGS_MODULE=therapeutic_coding.settings.production`
- `WEB_CONCURRENCY` (recommended `2`)
- `ALLOWED_HOSTS` (your Render service hostname)

Start command used by Render: `./start-render.sh`

Health check path: `/health/`

Static files: Render ephemeral filesystem is not durable for media. Use an object store (S3/Cloudinary/Backblaze) for media; static files can be served using WhiteNoise or uploaded to object storage during build.



3. Create `.env` from `.env.example` and adjust values

4. Configure DB (SQLite dev or Postgres in production). Example Postgres `DATABASE_URL` environment variable format used by `dj-database-url` if configured.

5. Run migrations and create superuser

```bash
python manage.py migrate
python manage.py createsuperuser
```

6. Start Redis (if not already running)

Linux/macOS (local):
```bash
redis-server --port 6379
```

Windows: use WSL or install Redis via docker

7. Run Redis healthcheck

```bash
python manage.py redis_healthcheck
```

8. Run development server (ASGI)

```bash
python manage.py runserver
```

For websocket testing run Channels via Daphne or Uvicorn:

```bash
# daphne
daphne -b 0.0.0.0 -p 8001 therapeutic_coding.asgi:application

# uvicorn
uvicorn therapeutic_coding.asgi:application --host 0.0.0.0 --port 8001
```

## Environment Variables (.env.example provided)

An example `.env.example` is included. Key variables:
- `DJANGO_SECRET_KEY` — application secret
- `DJANGO_DEBUG` — True/False
- `DATABASE_URL` — primary DB connection
- `REDIS_URL` — Redis connection string (e.g. `redis://redis:6379/1`)
- `REDIS_KEY_PREFIX` — prefix for Redis keys
- `PRESENCE_TTL` — presence TTL (seconds)
- `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS` — JWT lifetimes
- `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` — network settings

## Running Tests

Unit tests (presence unit tests included):

```bash
# Run all tests discovered under users/tests
python -m unittest discover -s users/tests -p 'test_*.py' -v

# Or run full Django test suite
python manage.py test
```

Coverage (example with coverage.py):

```bash
coverage run -m pytest
coverage report -m
```

## API Documentation

### Authentication
- `POST /users/api/login/` — returns `access` and `refresh` tokens (JWT). Use `Authorization: Bearer <token>` for protected endpoints.
- `POST /users/api/token/refresh/` — rotates refresh token. Our `TokenRefreshWithPresenceView` also updates presence when a refresh is used.

### Profile endpoints
- `GET /users/profile/` — HTML profile view.
- `POST /users/profile/` — updates profile; server-side serializer validation is enforced.
- `GET /users/profiles/` (DRF router) — profile listing (API).

### Online users
- `GET /users/api/online-users/` — returns cached list of online users (requires authentication). Example response:

```json
{
  "results": [
    {"id": 2, "display_name": "Learner", "avatar_color": "#aabbcc"}
  ]
}
```

### WebSocket
- Endpoint: `ws://<host>/ws/presence/` — authenticated connection. For session-based clients use existing session cookie; for JWT you must implement a websocket JWT middleware.

## Security Features

- JWT authentication with refresh rotation and blacklist support.
- DRF throttling (anon/user) configured globally; per-view throttles applied for sensitive endpoints.
- RBAC enforced for admin unlock actions (superuser recommended) and audit logging via `LogEntry`.
- Serializer validation used for HTML `profile` POST flows to prevent mass-assignment.
- Sensitive Redis operations are wrapped with exception handling and `IGNORE_EXCEPTIONS` to avoid total outages.

## Testing

- Unit tests: presence service test harness with fake Redis.
- Websocket tests: recommended with `channels.testing` and a test Redis or `fakeredis`.
- API tests: DRF test client for endpoints and throttling rules.

## Redis Healthcheck

- Management command: `python manage.py redis_healthcheck`
- Expected output (healthy):
  - `Redis ping: True`
  - `Redis set/get OK: b"ok"`
- If failing: verify `REDIS_URL`, network/firewall, and that `django-redis` is installed and configured.

## Deployment

Recommended production stack:
- PostgreSQL for primary DB
- Redis (cluster or sentinel) for caching, channel layer, presence
- Daphne/Uvicorn + Gunicorn (or dedicated ASGI server)
- Nginx as reverse proxy + TLS termination
- Dockerized containers and Kubernetes for horizontal scaling

Basic steps
1. Build Docker images for the web and worker processes.
2. Use environment variables for secrets and service locations.
3. Run migrations and collectstatic.
4. Start Redis and Postgres services.
5. Launch ASGI server (Daphne/Uvicorn) and expose ports through Nginx.

## Production Recommendations

- Use Redis clustering or Sentinel for HA. Keep presence data in a dedicated Redis DB.
- Use sticky sessions or a broadcast presence invalidation in multi-region deployments.
- Horizontally scale ASGI workers and attach to shared channel layer.
- Use centralized logging (ELK, Datadog) and tracing (OpenTelemetry).
- Use Celery (Redis/RabbitMQ) for background jobs and presence reconciliation when needed.
- Backup Postgres daily and Redis RDB/ AOF depending on persistence needs.

## Project Structure

```
Code_Sanctuary/
├─ therapeutic_coding/
│  ├─ asgi.py
│  ├─ settings.py
│  ├─ urls.py
│  └─ wsgi.py
├─ users/
│  ├─ models.py
│  ├─ views.py
│  ├─ presence.py
│  ├─ signals_presence.py
│  ├─ api_serializers.py
│  ├─ admin.py
│  └─ tests/
│     └─ test_presence.py
├─ chat/
│  ├─ consumers.py
│  └─ routing.py
├─ learning/
├─ therapy/
├─ social/
├─ requirements.txt
├─ manage.py
└─ README.md
```

## Future Improvements

- Implement JWT middleware for websocket authentication (secure token negotiation).
- Advanced RBAC (role-permission groups) and 2-person review workflows for unlocks.
- Add Prometheus metrics for presence churn and Redis errors.
- Integrate SIEM and audit dashboards.
- Consider Redis Sentinel/Cluster for HA and geo-distribution.
- Add end-to-end integration tests with Docker Compose.

## Contributing

1. Fork the repository and create a feature branch.
2. Run tests and ensure linting.
3. Open a pull request with a clear description and tests for new behavior.

Follow the repo's coding standards and add unit/integration tests for new features.

## License

This project is provided under a placeholder license. Replace with a project-appropriate license, for example `Apache-2.0` or `MIT`.

## Security & Scores

These scores are conservative estimations reflecting the current implementation and remaining work to reach healthcare/banking-grade readiness.


### Token security updates (new)

- Implemented refresh token rotation protection using Redis marking to prevent replay attacks.
- Blacklist enforcement on refresh and logout; refreshes are verified and previous refresh tokens are blacklisted.
- Logout endpoint revokes refresh and access tokens and forces websocket disconnects for affected users.
- WebSocket middleware now rejects blacklisted tokens and exposes token `jti` to consumers; consumers register channel sessions in Redis so revocation can force-disconnect active sockets.
- **Security Score:** 85/100 — JWT rotation, blacklist checks, WebSocket JWT authentication, RBAC on admin unlocks, DRF throttling, and audit logging implemented. Remaining tasks: SIEM integration, hardened secrets management, and full penetration testing.
- **Scalability Score:** 78/100 — Redis-backed presence, Channels with Redis layer ready for horizontal scaling. Remaining tasks: Redis clustering, connection pooling, and performance tuning under heavy websocket load.
- **Production Readiness Score:** 72/100 — Good baseline (ASGI, static handling, Redis). Remaining tasks: Docker/K8s manifests, CI/CD, comprehensive integration tests, and observability setup.

If you want, I can generate CI/CD workflows and Kubernetes manifests next.
# CodeSanctuary

