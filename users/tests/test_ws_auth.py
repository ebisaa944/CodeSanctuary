import pytest
import asyncio
from channels.testing import WebsocketCommunicator
from therapeutic_coding.asgi import application
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken


@pytest.mark.asyncio
async def test_ws_auth_success(db, django_user_model):
    User = get_user_model()
    user = User.objects.create_user(username='wsuser', password='testpass')
    token = str(AccessToken.for_user(user))

    communicator = WebsocketCommunicator(application, f"/ws/presence/?token={token}")
    connected, subprot = await communicator.connect()
    assert connected is True
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_ws_auth_invalid_token(db):
    token = 'invalid.token.value'
    communicator = WebsocketCommunicator(application, f"/ws/presence/?token={token}")
    connected, _ = await communicator.connect()
    assert connected is False


@pytest.mark.asyncio
async def test_ws_auth_expired_token(db, monkeypatch):
    # Create a token and mutate its lifetime to simulate expiry by setting 'exp' in the past
    User = get_user_model()
    user = User.objects.create_user(username='wsuser2', password='testpass')
    token_obj = AccessToken.for_user(user)
    token_obj.set_exp(lifetime=-1)
    token = str(token_obj)

    communicator = WebsocketCommunicator(application, f"/ws/presence/?token={token}")
    connected, _ = await communicator.connect()
    assert connected is False
