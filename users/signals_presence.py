from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from .presence import get_presence_service
import logging

logger = logging.getLogger('therapeutic.presence')


@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    try:
        service = get_presence_service()
        service.add(user.id)
        logger.debug('User logged in presence updated', extra={'user_id': user.id})
    except Exception:
        logger.exception('Failed to update presence on login')


@receiver(user_logged_out)
def handle_user_logged_out(sender, request, user, **kwargs):
    try:
        service = get_presence_service()
        service.remove(user.id)
        logger.debug('User logged out presence removed', extra={'user_id': user.id})
    except Exception:
        logger.exception('Failed to remove presence on logout')
