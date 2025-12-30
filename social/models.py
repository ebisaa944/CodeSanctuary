# social/models.py
"""
Models for therapeutic social app
"""

import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()


class GentleInteraction(models.Model):
    """
    Therapeutic interaction between users
    """
    INTERACTION_TYPES = [
        ('encouragement', 'Encouragement'),
        ('question', 'Question'),
        ('share', 'Personal Share'),
        ('support', 'Request Support'),
    ]
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('community', 'Community Only'),
        ('circle', 'Circle Members Only'),
        ('private', 'Private'),
        ('anonymous', 'Anonymous'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_interactions'
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_interactions'
    )
    title = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPES,
        default='encouragement'
    )
    therapeutic_intent = models.TextField(blank=True)
    therapeutic_impact_score = models.IntegerField(default=50)
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='community'
    )
    allow_replies = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    anonymous = models.BooleanField(default=False)
    likes_count = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Parent interaction for replies
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['visibility', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['interaction_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_interaction_type_display()} - {self.title or 'No title'}"
    
    def create_reply(self, user, message, anonymous=False):
        """Create a reply to this interaction"""
        if not self.allow_replies:
            raise ValidationError("Replies are not allowed for this interaction.")
        
        reply = GentleInteraction.objects.create(
            sender=None if anonymous else user,
            recipient=self.sender,
            message=message,
            interaction_type='encouragement',  # Replies are encouragements
            therapeutic_intent="To respond with support and understanding",
            visibility=self.visibility,
            anonymous=anonymous,
            parent=self
        )
        
        return reply
    
    def is_expired(self):
        """Check if the interaction has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def is_visible_to_user(self, user):
        """Check if interaction is visible to given user"""
        if self.visibility == 'public':
            return True
        elif self.visibility == 'community':
            return user.is_authenticated
        elif self.visibility == 'circle':
            # Check if user is in same circles as sender
            return False  # Implement circle logic
        elif self.visibility == 'private':
            return user == self.sender or user == self.recipient
        elif self.visibility == 'anonymous':
            return True
        return False


class SupportCircle(models.Model):
    """
    Therapeutic support circle for group interactions
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    focus_areas = models.CharField(max_length=200)  # e.g., "anxiety, stress, self-care"
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_circles'
    )
    is_public = models.BooleanField(default=True)
    allow_anonymous = models.BooleanField(default=False)
    active_members = models.IntegerField(default=0)
    max_members = models.IntegerField(default=20)
    total_interactions = models.IntegerField(default=0)
    join_code = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-active_members', 'name']
        indexes = [
            models.Index(fields=['is_public', 'active_members']),
            models.Index(fields=['focus_areas']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.active_members} members)"
    
    def clean(self):
        """Validate circle data"""
        if self.active_members > self.max_members:
            raise ValidationError("Active members cannot exceed maximum capacity.")
        
        if not self.is_public and not self.join_code:
            raise ValidationError("Private circles require a join code.")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class CircleMembership(models.Model):
    """
    User membership in support circles
    """
    ROLE_CHOICES = [
        ('leader', 'Circle Leader'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    circle = models.ForeignKey(
        SupportCircle,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='circle_memberships'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='member'
    )
    notification_preferences = models.JSONField(
        default=dict,
        help_text="Notification settings for this circle"
    )
    introduction = models.TextField(blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['circle', 'user']
        ordering = ['role', 'joined_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.circle.name} ({self.role})"


class Achievement(models.Model):
    """
    Therapeutic achievements for user progress
    """
    TIER_CHOICES = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='bronze')
    icon_name = models.CharField(max_length=50, default='award')  # FontAwesome icon
    criteria = models.JSONField(
        default=dict,
        help_text="Criteria for earning this achievement"
    )
    is_active = models.BooleanField(default=True)
    total_earners = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['tier', 'name']
    
    def __str__(self):
        return f"{self.get_tier_display()}: {self.name}"
    
    def update_earner_count(self):
        """Update total earners count"""
        self.total_earners = self.userachievement_set.count()
        self.save()


class UserAchievement(models.Model):
    """
    User-earned achievements
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='achievements'
    )
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE
    )
    reflection_notes = models.TextField(blank=True)
    shared_publicly = models.BooleanField(default=False)
    earned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'achievement']
        ordering = ['-earned_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            # Update achievement's total earners count
            self.achievement.update_earner_count()