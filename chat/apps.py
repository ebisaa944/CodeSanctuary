# chat/apps.py
from django.apps import AppConfig

class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'
    verbose_name = 'Therapeutic Chat'
    
    def ready(self):
        import chat.signals  # Register signals