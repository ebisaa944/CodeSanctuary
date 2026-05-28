import time
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('therapeutic.presence')


class PresenceService:
    """Encapsulate Redis-backed presence operations.

    Implementation notes:
    - We maintain a sorted set `presence:active` with score = last_seen (unix seconds).
    - Adding a user does ZADD with current timestamp.
    - Cleanup removes entries older than now - TTL.
    - Getting online ids returns ZRANGEBYSCORE for recent scores.
    - All Redis ops are wrapped to gracefully fallback to Django cache/no-op when Redis unavailable.
    """

    def __init__(self, redis_conn=None, key_prefix=None, ttl=None):
        self._redis = redis_conn
        self.key_prefix = key_prefix or getattr(settings, 'REDIS_KEY_PREFIX', 'cs:')
        self.ttl = ttl or getattr(settings, 'PRESENCE_TTL', 45)
        self.zkey = f"{self.key_prefix}presence:active"

    def _now(self):
        return int(time.time())

    def add(self, user_id):
        try:
            if self._redis:
                now = self._now()
                pipe = self._redis.pipeline()
                pipe.zadd(self.zkey, {user_id: now})
                # Also trim old entries
                pipe.zremrangebyscore(self.zkey, 0, now - self.ttl)
                pipe.execute()
            else:
                # Fallback: set in Django cache (per-user mark) with TTL
                cache.set(f"{self.key_prefix}presence:uid:{user_id}", True, timeout=self.ttl)
        except Exception as e:
            logger.exception('Presence add failed')

    def remove(self, user_id):
        try:
            if self._redis:
                self._redis.zrem(self.zkey, user_id)
            else:
                cache.delete(f"{self.key_prefix}presence:uid:{user_id}")
        except Exception:
            logger.exception('Presence remove failed')

    def get_online_ids(self):
        try:
            if self._redis:
                now = self._now()
                # expand window slightly to avoid tiny clock skews between calls
                min_score = now - self.ttl - 2
                max_score = now + 2
                # Return ids added within TTL
                ids = self._redis.zrangebyscore(self.zkey, min_score, max_score)
                # Redis returns bytes; convert to int
                return [int(i) for i in ids]
            else:
                # Fallback: inspect Django cache keys is not reliable; return empty list
                return []
        except Exception:
            logger.exception('Presence get_online_ids failed')
            return []

    def cleanup(self):
        try:
            if self._redis:
                now = self._now()
                self._redis.zremrangebyscore(self.zkey, 0, now - self.ttl)
        except Exception:
            logger.exception('Presence cleanup failed')

    # Connection counting for websocket connections to avoid removing user while they still
    # have active websocket connections. Uses a per-user counter key with TTL.
    def increment_connections(self, user_id):
        try:
            if self._redis:
                conn_key = f"{self.key_prefix}presence:connections:{user_id}"
                now = self._now()
                pipe = self._redis.pipeline()
                pipe.incr(conn_key)
                pipe.expire(conn_key, self.ttl)
                # Also update last_seen score so user stays in active set
                pipe.zadd(self.zkey, {user_id: now})
                pipe.execute()
            else:
                # Not available; noop
                return
        except Exception:
            logger.exception('Presence increment_connections failed')

    def decrement_connections(self, user_id):
        try:
            if self._redis:
                conn_key = f"{self.key_prefix}presence:connections:{user_id}"
                pipe = self._redis.pipeline()
                pipe.decr(conn_key)
                pipe.get(conn_key)
                pipe.expire(conn_key, self.ttl)
                res = pipe.execute()
                # res[1] is the value after decrement (bytes)
                try:
                    current = int(res[1]) if res[1] is not None else 0
                except Exception:
                    current = 0
                if current <= 0:
                    # No more connections - remove from active set
                    self._redis.zrem(self.zkey, user_id)
        except Exception:
            logger.exception('Presence decrement_connections failed')


def get_presence_service():
    """Factory: attempts to get a django-redis connection; returns PresenceService.

    If Redis is not available, returns a PresenceService with redis_conn=None (fallback).
    """
    try:
        from django_redis import get_redis_connection
        conn = get_redis_connection('default')
        return PresenceService(redis_conn=conn)
    except Exception:
        logger.exception('Redis connection failed; falling back to cache-based presence')
        return PresenceService(redis_conn=None)
