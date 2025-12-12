from django.apps import AppConfig

class TherapyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'therapy'
    verbose_name = 'Therapeutic Tools'
    
    def ready(self):
        # Import signals if you create them later
        pass