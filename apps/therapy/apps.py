# therapy/apps.py (and similarly for users, learning, social)
from django.apps import AppConfig

class TherapyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.therapy'