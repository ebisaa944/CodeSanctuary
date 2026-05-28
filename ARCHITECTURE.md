# Architecture Notes

This document summarizes the key architectural decisions, Redis key structures, and production recommendations for Code Sanctuary.

## Redis Key Structure

- `cs:presence:active` (sorted set)
  - Members: user ids (integers)
  - Score: last_seen (unix epoch seconds)

- `cs:presence:connections:<user_id>` (string/integer)
  - Tracks the number of active websocket connections for the user
  - `INCR` on connect, `DECR` on disconnect; `EXPIRE` set to `PRESENCE_TTL`

- `cs:presence:uid:<user_id>` (cache fallback)
  - Used when Redis unavailable; simple boolean with TTL

## WebSocket Authentication Flow

1. Client opens WebSocket to `/ws/presence/?token=<JWT>` or sends token in `Sec-WebSocket-Protocol` header.
2. `JwtAuthMiddleware` decodes and validates token using `rest_framework_simplejwt.backends.TokenBackend`.
3. Middleware checks for `jti` against the blacklist (if available).
4. Middleware attaches `scope['user']` and allows connection; otherwise connection is closed immediately.

## Presence Lifecycle

- On login or token refresh: `PresenceService.add(user_id)` (ZADD + trim old entries).
- On websocket connect: `add()` + `increment_connections()`.
- On websocket disconnect: `decrement_connections()` (may remove from active set if count ≤ 0).
- Periodic cleanup: call `PresenceService.cleanup()` via scheduled job (optional).

## Token blacklist & revocation

- Refresh rotation protection: refresh token `jti`s are marked in Redis when used to prevent replay attacks. A subsequent attempt to reuse the same refresh token will be rejected.
- Blacklisting: refresh tokens are blacklisted in the DB (`OutstandingToken` / `BlacklistedToken`) and added to a Redis revoked-jti store for immediate enforcement on access tokens and websockets.
- WebSocket session registry: each websocket channel registers itself in Redis under `cs:ws:sessions:<user_id>` and stores per-channel jti mapping in `cs:ws:channel:<channel_name>` so revocation can target and force-disconnect active sockets.

## Token revocation workflow

1. When a refresh is used, the middleware/view marks its `jti` in Redis (setnx) to prevent replay.
2. The refresh request is validated; on success previous refresh tokens are blacklisted by SimpleJWT rotation logic and the Redis mark remains to prevent reuse.
3. On logout or explicit revocation, the refresh token is blacklisted and the access token's `jti` is added to Redis revoked set.
4. `revoke_user_sessions()` uses the websocket registry to send `force.disconnect` messages to active channels for the affected user, causing clean disconnect and presence cleanup.


## Scaling Considerations

- Use Redis cluster or Sentinel for high-availability and failover.
- Ensure Channel layer and cache use same Redis instance or well-provisioned cluster.
- Use horizontal scaling for ASGI workers; ensure channel layer supports cross-instance communication.
- Add connection sharding and autoscaling thresholds for WebSocket-heavy workloads.

## Observability and Monitoring

- Export Redis metrics (usage, latency, key eviction rates).
- Monitor presence churn (adds/removes per minute), unauthorized websocket attempts, and blacklist events.
- Centralize logs (structured JSON) into ELK/Datadog and add alerting for anomalies.

## Deployment Topology

- Nginx (edge): TLS termination, rate limiting, static file serving, websocket proxying.
- Application layer: multiple replicas of the ASGI app (Gunicorn + UvicornWorkers) behind Nginx. Run at least 2 replicas for zero-downtime deploys.
- Channel layer: Redis configured with AOF persistence and replication (Sentinel or Cluster) for high availability.
- DB: Postgres with persistent volumes and regular backups; use connection pooling (PgBouncer) for scale.

## Production Hardening Checklist

- Ensure Redis persistence (AOF) and memory policy `volatile-lru` or appropriate policy for your use case.
- Protect Redis with ACLs and bind/requirepass where appropriate; place in VPC/private network.
- Rotate signing keys and manage via KMS/Vault; stage key rollover carefully.
- Add CI pipelines that run full integration tests with Redis and Postgres using Docker Compose.

## Render.com Deployment Notes

- Render provides TLS termination and a managed HTTP load balancer; you do not need a separate Nginx for TLS in Render deployments.
- Use the provided `start-render.sh` and `render.yaml` to configure the Web Service. Set `healthCheckPath` to `/health/`.
- Static files: serve via WhiteNoise for small-to-medium apps, or push static and media to an object storage (S3/Cloudinary/Backblaze) for production media.
- WebSockets: Render supports WebSockets. Use Uvicorn/Daphne via the `start-render.sh` command. Prefer horizontal scaling (multiple instances) rather than many worker processes for long-lived websocket connections.
- Redis: Use the Render Redis managed service; set `REDIS_URL` and prefer TLS (`rediss://`) if provided. Ensure `channels_redis` is configured to use the given URL.
- Postgres: Use Render Postgres; set `DATABASE_URL`. Use PgBouncer or database pooling to avoid connection limits when scaling web instances.

## WebSocket scaling guidance on Render

- Long-lived connections consume file descriptors and Redis channel connections. Scale by adding more Render instances rather than increasing worker counts per instance.
- Recommended instance sizes: start with `Starter` (1GB) for low traffic; move to at least 2GB RAM instances for production websocket loads.
- Tune `WEB_CONCURRENCY` to a low number (1-3) when running Uvicorn/Daphne to avoid context switching for long-lived connections; rely on horizontal instance scaling.
- Use Redis plan that supports connection count > (expected concurrent sockets * instances).


