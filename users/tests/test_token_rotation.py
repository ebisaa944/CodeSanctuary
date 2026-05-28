import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django_redis import get_redis_connection
import time


@pytest.mark.django_db
def test_refresh_rotation_and_replay_protection(settings):
    User = get_user_model()
    user = User.objects.create_user(username='rotuser', password='pw')
    refresh = str(RefreshToken.for_user(user))

    client = APIClient()

    url = '/users/api/token/refresh/'
    # First refresh should succeed
    resp1 = client.post(url, {'refresh': refresh}, format='json')
    assert resp1.status_code == 200
    new_refresh = resp1.data.get('refresh') or resp1.data.get('refresh_token') or None
    # Second refresh with same token should fail due to replay protection
    resp2 = client.post(url, {'refresh': refresh}, format='json')
    assert resp2.status_code in (401, 400)

    # Using new refresh should succeed
    if new_refresh:
        resp3 = client.post(url, {'refresh': new_refresh}, format='json')
        assert resp3.status_code == 200

