"""
ASGI config for therapeutic_coding project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os

import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from users.ws_middleware import JwtAuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'therapeutic_coding.settings')
django.setup()

from chat.routing import websocket_urlpatterns
from django.core.asgi import get_asgi_application

application = ProtocolTypeRouter({
	'http': get_asgi_application(),
	'websocket': JwtAuthMiddlewareStack(
		URLRouter(
			websocket_urlpatterns
		)
	),
})
