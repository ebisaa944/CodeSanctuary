from channels.generic.websocket import AsyncWebsocketConsumer
import json
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from users.presence import get_presence_service
import logging
from users.token_utils import register_ws_channel, unregister_ws_channel, is_jti_revoked, get_user_channels
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import asyncio

logger = logging.getLogger('therapeutic.websocket')


class PresenceConsumer(AsyncWebsocketConsumer):
    """Simple presence websocket consumer.

    Expects session authentication (AuthMiddlewareStack). For JWT-based websocket auth,
    a custom middleware should be introduced (not implemented here).
    """

    async def connect(self):
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            await self.close()
            return

        self.user_id = user.id
        self.service = get_presence_service()
        # Mark presence and increment connection count
        await database_sync_to_async(self.service.add)(self.user_id)
        await database_sync_to_async(self.service.increment_connections)(self.user_id)

        # Register websocket channel for revocation handling
        channel_name = self.channel_name
        token_jti = self.scope.get('token_jti')
        token_exp = self.scope.get('token_exp')
        await database_sync_to_async(register_ws_channel)(self.user_id, channel_name, token_jti, token_exp)

        # Start revocation monitor task
        self._revocation_task = asyncio.create_task(self._monitor_revocation())

        await self.accept()

    async def disconnect(self, code):
        try:
            # Decrement; service will remove from active set if no more connections
            await database_sync_to_async(self.service.decrement_connections)(self.user_id)
            # Unregister channel
            await database_sync_to_async(unregister_ws_channel)(self.user_id, self.channel_name)
            # Cancel revocation task
            try:
                self._revocation_task.cancel()
            except Exception:
                pass
        except Exception:
            logger.exception('Error in disconnect presence cleanup')

    async def receive(self, text_data=None, bytes_data=None):
        # For presence, no payload expected; echo minimal ack
        await self.send(json.dumps({'status': 'ok'}))

    async def _monitor_revocation(self):
        # Periodically check whether our token jti has been revoked
        try:
            while True:
                token_jti = self.scope.get('token_jti')
                if token_jti and await database_sync_to_async(is_jti_revoked)(token_jti):
                    # Initiate graceful disconnect
                    await self.send(json.dumps({'type': 'revoked', 'reason': 'token_revoked'}))
                    await self.close()
                    return
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception('Error in revocation monitor')

    async def force_disconnect(self, event):
        # Handler for 'force.disconnect' messages sent via channel layer
        reason = event.get('reason')
        try:
            await self.send(json.dumps({'type': 'force_disconnect', 'reason': reason}))
        except Exception:
            pass
        await self.close()
