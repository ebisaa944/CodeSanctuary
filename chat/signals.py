# chat/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.models import Count
from .models import ChatMessage, RoomMembership, ChatSessionAnalytics, ChatNotification
from users.models import TherapeuticUser

@receiver(post_save, sender=ChatMessage)
def handle_therapeutic_message(sender, instance, created, **kwargs):
    """Handle therapeutic aspects of new messages"""
    if created:
        # Update user's last activity
        instance.user.last_activity_date = timezone.now().date()
        instance.user.update_streak()
        
        # Check for breakthrough moments
        if instance.message_type == 'breakthrough':
            instance.user.add_breakthrough_moment(
                f"Breakthrough in chat: {instance.content[:100]}"
            )
        
        # Create gentle notification for vulnerable shares
        if instance.is_vulnerable_share and instance.user.receive_gentle_reminders:
            ChatNotification.objects.create(
                user=instance.user,
                notification_type='therapeutic_insight',
                title="Thank you for sharing",
                message="Sharing vulnerable thoughts is brave. Remember to practice self-care.",
                is_gentle=True
            )

@receiver(pre_save, sender=RoomMembership)
def validate_membership(sender, instance, **kwargs):
    """Validate room membership based on therapeutic settings"""
    if not instance.pk:  # New membership
        # Check stress level
        if instance.user.current_stress_level > instance.room.max_stress_level:
            raise ValueError(
                f"Cannot join room: User stress level {instance.user.current_stress_level} "
                f"exceeds room maximum {instance.room.max_stress_level}"
            )
        
        # Check if room is at capacity
        current_count = instance.room.memberships.filter(is_active=True).count()
        if current_count >= instance.room.max_participants:
            raise ValueError("Room is at maximum capacity")

@receiver(post_save, sender=TherapeuticUser)
def create_chat_settings(sender, instance, created, **kwargs):
    """Create default chat settings for new users"""
    if created:
        from chat.models import TherapeuticChatSettings
        TherapeuticChatSettings.objects.create(user=instance)