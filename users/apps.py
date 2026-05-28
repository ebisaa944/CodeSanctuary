from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        # Import presence signals so they get registered
        try:
            from . import signals_presence  # noqa: F401
        except Exception:
            pass