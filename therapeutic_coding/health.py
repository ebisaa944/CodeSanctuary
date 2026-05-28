from django.http import JsonResponse
from django.db import connections
from django.core.cache import cache
from django.conf import settings
import time

def health(request):
    """Simple health endpoint checking DB and Redis/cache connectivity."""
    status = {
        'ok': True,
        'services': {},
        'timestamp': int(time.time())
    }

    # Database check
    try:
        conn = connections['default']
        with conn.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        status['services']['database'] = 'ok'
    except Exception as e:
        status['services']['database'] = f'error: {str(e)}'
        status['ok'] = False

    # Cache/Redis check
    try:
        # Try a cache set/get to exercise underlying backend
        cache.set('healthcheck', '1', timeout=5)
        v = cache.get('healthcheck')
        if v != '1':
            raise RuntimeError('cache mismatch')
        status['services']['cache'] = 'ok'
    except Exception as e:
        status['services']['cache'] = f'error: {str(e)}'
        status['ok'] = False

    code = 200 if status['ok'] else 503
    return JsonResponse(status, status=code)
