from django.core.management.base import BaseCommand
from django_redis import get_redis_connection
from django.conf import settings
import socket


class Command(BaseCommand):
    help = 'Check Redis connectivity and basic operations'

    def handle(self, *args, **options):
        try:
            conn = get_redis_connection('default')
            pong = conn.ping()
            self.stdout.write(self.style.SUCCESS(f'Redis ping: {pong}'))
            # Try a small set/get
            key = f"{getattr(settings, 'REDIS_KEY_PREFIX', 'cs:')}healthcheck"
            conn.set(key, 'ok', ex=5)
            val = conn.get(key)
            self.stdout.write(self.style.SUCCESS(f'Redis set/get OK: {val}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Redis healthcheck failed: {e}'))
            raise
