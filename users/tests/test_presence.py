import time
import unittest

from users.presence import PresenceService


class FakeRedis:
    def __init__(self):
        self._z = {}

    def pipeline(self):
        return self

    def zadd(self, key, mapping):
        for member, score in mapping.items():
            self._z[int(member)] = int(score)

    def zremrangebyscore(self, key, min_s, max_s):
        to_del = [m for m, s in self._z.items() if s >= min_s and s <= max_s]
        for m in to_del:
            del self._z[m]

    def execute(self):
        return True

    def zrem(self, key, member):
        self._z.pop(int(member), None)

    def zrangebyscore(self, key, min_s, max_s):
        return [str(m).encode() for m, s in self._z.items() if s >= min_s and s <= max_s]

    def incr(self, key):
        v = getattr(self, key, 0) + 1
        setattr(self, key, v)
        return v

    def decr(self, key):
        v = max(0, getattr(self, key, 0) - 1)
        setattr(self, key, v)
        return v

    def get(self, key):
        return getattr(self, key, 0)

    def expire(self, key, ttl):
        return True


class PresenceServiceTests(unittest.TestCase):
    def test_add_and_get(self):
        fake = FakeRedis()
        svc = PresenceService(redis_conn=fake, key_prefix='test:', ttl=5)
        svc.add(42)
        ids = svc.get_online_ids()
        self.assertIn(42, ids)

    def test_remove(self):
        fake = FakeRedis()
        svc = PresenceService(redis_conn=fake, key_prefix='test:', ttl=5)
        svc.add(99)
        svc.remove(99)
        ids = svc.get_online_ids()
        self.assertNotIn(99, ids)

    def test_connection_counting(self):
        fake = FakeRedis()
        svc = PresenceService(redis_conn=fake, key_prefix='test:', ttl=5)
        svc.add(1)
        svc.increment_connections(1)
        svc.increment_connections(1)
        # simulate decrement twice => removed
        svc.decrement_connections(1)
        svc.decrement_connections(1)
        ids = svc.get_online_ids()
        self.assertNotIn(1, ids)


if __name__ == '__main__':
    unittest.main()
