from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import TherapeuticUser

@receiver(post_save, sender=TherapeuticUser)
def create_integration_profiles(sender, instance, created, **kwargs):
    """Create integration profiles when a user is created"""
    if created:
        # Import here to avoid circular imports
        from .integration.therapy_integration import UserTherapyProfile
        from .integration.learning_integration import UserLearningProfile
        from .integration.social_integration import UserSocialProfile
        
        # Create therapy profile
        UserTherapyProfile.objects.create(user=instance)
        
        # Create learning profile
        UserLearningProfile.objects.create(user=instance)
        
        # Create social profile
        UserSocialProfile.objects.create(user=instance)

@receiver(post_save, sender=TherapeuticUser)
def update_therapeutic_state(sender, instance, **kwargs):
    """Update therapeutic state in integrated apps"""
    # This would trigger updates in other apps
    # For now, we'll just log it
    import logging
    logger = logging.getLogger('therapeutic.integration')
    
    logger.info(f"Therapeutic user updated: {instance.username}")