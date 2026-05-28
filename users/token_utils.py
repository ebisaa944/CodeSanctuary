import time
import logging
from django.conf import settings
from django_redis import get_redis_connection
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger('therapeutic.tokens')

REDIS_PREFIX = getattr(settings, 'REDIS_KEY_PREFIX', 'cs:')
REVOKED_JTI_KEY = REDIS_PREFIX + 'revoked:jti:'
WS_SESSIONS_KEY = REDIS_PREFIX + 'ws:sessions:'  # set of channel_names per user
WS_CHANNEL_KEY = REDIS_PREFIX + 'ws:channel:'   # mapping channel_name -> jti


def _redis():
    try:
        return get_redis_connection('default')
    except Exception:
        return None


def revoke_refresh_token(refresh_token_str):
    """Blacklist a refresh token via OutstandingToken/BlacklistedToken if possible."""
    try:
        token = RefreshToken(refresh_token_str)
        jti = token['jti']
        user_id = token['user_id']
        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
        except Exception:
            user = None

        # Try to find OutstandingToken and create BlacklistedToken
        if user:
            outs = OutstandingToken.objects.filter(jti=jti, user=user)
            for o in outs:
                # Create blacklisted entry if not exists
                if not BlacklistedToken.objects.filter(token=o).exists():
                    BlacklistedToken.objects.create(token=o)

        # Also add to Redis revoked set for immediate access-token revocation handling
        add_revoked_jti(jti, token.get('exp', None))
        # Revoke all websocket sessions for this user
        if user:
            revoke_user_sessions(user.id, reason='refresh_revoked', revoked_jti=jti)

    except Exception:
        logger.exception('Failed to revoke refresh token')


def add_revoked_jti(jti, exp_timestamp=None):
    """Add jti to Redis revoked set with TTL until exp_timestamp."""
    try:
        conn = _redis()
        if not conn:
            return
        key = REVOKED_JTI_KEY + str(jti)
        if exp_timestamp:
            ttl = int(exp_timestamp - time.time())
            if ttl <= 0:
                ttl = 1
        else:
            ttl = int(getattr(settings, 'JWT_ACCESS_EXPIRE_SECONDS', 3600))
        conn.set(key, 1, ex=ttl)
    except Exception:
        logger.exception('Failed to add revoked jti to redis')


def is_jti_revoked(jti):
    try:
        conn = _redis()
        if not conn:
            return False
        key = REVOKED_JTI_KEY + str(jti)
        return conn.get(key) is not None
    except Exception:
        logger.exception('Failed to check revoked jti')
        return False


def register_ws_channel(user_id, channel_name, jti=None, exp_ts=None):
    try:
        conn = _redis()
        if not conn:
            return
        conn.sadd(WS_SESSIONS_KEY + str(user_id), channel_name)
        # store mapping channel->jti for targeted revocation
        key = WS_CHANNEL_KEY + channel_name
        if exp_ts:
            ttl = int(exp_ts - time.time())
            if ttl <= 0:
                ttl = 1
            conn.set(key, jti or '', ex=ttl)
        else:
            conn.set(key, jti or '', ex=getattr(settings, 'PRESENCE_TTL', 45))
    except Exception:
        logger.exception('Failed to register ws channel')


def unregister_ws_channel(user_id, channel_name):
    try:
        conn = _redis()
        if not conn:
            return
        conn.srem(WS_SESSIONS_KEY + str(user_id), channel_name)
        conn.delete(WS_CHANNEL_KEY + channel_name)
    except Exception:
        logger.exception('Failed to unregister ws channel')


def get_user_channels(user_id):
    try:
        conn = _redis()
        if not conn:
            return []
        return [c.decode() if isinstance(c, bytes) else c for c in conn.smembers(WS_SESSIONS_KEY + str(user_id))]
    except Exception:
        logger.exception('Failed to get user channels')
        return []


def revoke_user_sessions(user_id, reason='revoked', revoked_jti=None):
    """Force-disconnect all websocket channels for a user.

    Sends a `force.disconnect` message to each channel so the consumer can close cleanly.
    """
    try:
        channels = get_user_channels(user_id)
        if not channels:
            return
        layer = get_channel_layer()
        for ch in channels:
            try:
                async_to_sync(layer.send)(ch, {
                    'type': 'force.disconnect',
                    'reason': reason,
                    'revoked_jti': revoked_jti,
                })
            except Exception:
                logger.exception('Failed to send force.disconnect to channel %s', ch)
    except Exception:
        logger.exception('Failed to revoke user sessions')
