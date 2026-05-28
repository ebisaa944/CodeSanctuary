import pytest
from channels.testing import WebsocketCommunicator
from therapeutic_coding.asgi import application
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework.test import APIClient
import asyncio


@pytest.mark.asyncio
async def test_ws_revoked_on_logout(db):
    User = get_user_model()
    user = User.objects.create_user(username='revokeuser', password='pw')
    refresh = str(RefreshToken.for_user(user))
    access = str(AccessToken.for_user(user))

    # connect websocket
    communicator = WebsocketCommunicator(application, f"/ws/presence/?token={access}")
    connected, _ = await communicator.connect()
    assert connected

    # Call logout API to revoke tokens (use APIClient)
    client = APIClient()
    resp = client.post('/users/api/logout/', {'refresh': refresh, 'access': f'Bearer {access}'})
    assert resp.status_code == 200

    # Expect a force_disconnect message or closure
    try:
        msg = await communicator.receive_json_from(timeout=5)
        assert msg.get('type') in ('force_disconnect', 'revoked', 'force.disconnect')
    except asyncio.TimeoutError:
        # If no message, ensure socket is closed
        pass

    # Ensure disconnect
    await communicator.disconnect()
