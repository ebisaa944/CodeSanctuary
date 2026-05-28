import logging
from urllib.parse import parse_qs
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenBackendError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from django.conf import settings

logger = logging.getLogger('therapeutic.websocket')


@database_sync_to_async
def get_user_for_payload(payload):
    User = get_user_model()
    user_id = payload.get('user_id') or payload.get('user')
    try:
        return User.objects.get(pk=user_id)
    except Exception:
        return AnonymousUser()


class JwtAuthMiddleware:
    """Custom Channels middleware that authenticates via JWT tokens.

    Look for `token` in query string or `sec-websocket-protocol` header.
    Validates token using SimpleJWT TokenBackend and rejects invalid/expired tokens.
    Also checks blacklist for outstanding tokens when token jti is present.
    """

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return JwtAuthMiddlewareInstance(scope, self)


class JwtAuthMiddlewareInstance:
    def __init__(self, scope, middleware):
        self.scope = dict(scope)
        self.inner = middleware.inner

    async def __call__(self, receive, send):
        headers = dict((k.decode() if isinstance(k, bytes) else k, v.decode() if isinstance(v, bytes) else v) for k, v in self.scope.get('headers', []))

        # Extract token from query string
        token = None
        qs = self.scope.get('query_string', b'').decode()
        if qs:
            params = parse_qs(qs)
            toks = params.get('token') or params.get('access_token')
            if toks:
                token = toks[0]

        # If not in query, check Sec-WebSocket-Protocol header (common pattern)
        if not token:
            proto = headers.get('sec-websocket-protocol')
            if proto:
                # clients may send 'access.token' or just the token
                token = proto.split(',')[0].strip()

        if not token:
            # No token provided — reject connection
            logger.warning('WS auth failed: no token provided', extra={'path': self.scope.get('path')})
            await send({
                'type': 'websocket.close',
                'code': 4401,
            })
            return

        try:
            tb = TokenBackend(
                algorithm=getattr(settings, 'SIMPLE_JWT', {}).get('ALGORITHM', 'HS256'),
                signing_key=getattr(settings, 'SIMPLE_JWT', {}).get('SIGNING_KEY', settings.SECRET_KEY),
            )
            payload = tb.decode(token, verify=True)

            # Optional: check blacklist for the token's jti (if present)
            jti = payload.get('jti')
            if jti:
                # If a matching OutstandingToken is blacklisted, reject
                try:
                    # This queries DB; cost is acceptable at connection time
                    blacklisted = BlacklistedToken.objects.filter(token__jti=jti).exists()
                    if blacklisted:
                        logger.warning('WS auth failed: token blacklisted', extra={'jti': jti})
                        await send({'type': 'websocket.close', 'code': 4403})
                        return
                except Exception:
                    # If blacklist model unavailable, continue but log
                    logger.exception('Failed to check token blacklist')

            user = await get_user_for_payload(payload)
            self.scope['user'] = user
            # expose token jti and exp for downstream consumers
            jti = payload.get('jti')
            exp = payload.get('exp')
            self.scope['token_jti'] = jti
            self.scope['token_exp'] = exp

        except Exception as exc:
            # Token invalid/expired or other errors — reject connection
            logger.warning('WS auth failed: token invalid or expired', extra={'error': str(exc)})
            await send({
                'type': 'websocket.close',
                'code': 4401,
            })
            return

        inner = self.inner(dict(self.scope))
        return await inner(receive, send)


def JwtAuthMiddlewareStack(inner):
    # Compose JwtAuthMiddleware with standard AuthMiddlewareStack behavior
    from channels.auth import AuthMiddlewareStack
    return JwtAuthMiddleware(AuthMiddlewareStack(inner))
