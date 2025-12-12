from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid

class GentleInteraction(models.Model):
    """Advanced therapeutic social interaction system"""
    
    class InteractionType(models.TextChoices):
        ENCOURAGEMENT = 'encouragement', 'Words of Encouragement'
        ACHIEVEMENT = 'achievement', 'Achievement Share'
        QUESTION = 'question', 'Gentle Question'
        RESOURCE = 'resource', 'Resource Share'
        GRATITUDE = 'gratitude', 'Expression of Gratitude'
        REFLECTION = 'reflection', 'Learning Reflection'
        SUPPORT = 'support', 'Request Support'
    
    class VisibilityLevel(models.TextChoices):
        PUBLIC = 'public', 'Public (Visible to all)'
        COMMUNITY = 'community', 'Community Only'
        ANONYMOUS = 'anonymous', 'Anonymous'
        PRIVATE = 'private', 'Private to Recipient'
    
    # Core fields
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    interaction_type = models.CharField(
        max_length=20,
        choices=InteractionType.choices,
        default=InteractionType.ENCOURAGEMENT,
        db_index=True
    )
    
    # Participants
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_interactions',
        null=True,
        blank=True  # Allow anonymous interactions
    )
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_interactions',
        null=True,
        blank=True  # Allow general posts
    )
    
    # Content
    title = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    
    # Metadata
    visibility = models.CharField(
        max_length=20,
        choices=VisibilityLevel.choices,
        default=VisibilityLevel.ANONYMOUS
    )
    
    is_pinned = models.BooleanField(default=False)
    allow_replies = models.BooleanField(default=True)
    
    # Therapeutic features
    therapeutic_intent = models.TextField(blank=True, help_text="Intent behind the interaction")
    expected_response_time = models.CharField(
        max_length=20,
        choices=[
            ('no_response', 'No response needed'),
            ('whenever', 'Whenever convenient'),
            ('within_day', 'Within a day'),
            ('urgent', 'Needs attention'),
        ],
        default='whenever'
    )
    
    # Engagement tracking
    likes_count = models.PositiveIntegerField(default=0)
    replies_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    
    # Content moderation
    is_moderated = models.BooleanField(default=False)
    moderator_notes = models.TextField(blank=True)
    
    # Technical
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name_plural = 'Gentle Interactions'
        indexes = [
            models.Index(fields=['interaction_type', 'created_at']),
            models.Index(fields=['sender', 'recipient', 'created_at']),
        ]
    
    def __str__(self):
        if self.sender:
            sender_name = self.sender.username if not self.is_anonymous else 'Anonymous'
        else:
            sender_name = 'System'
        
        recipient_name = self.recipient.username if self.recipient else 'Community'
        return f"{sender_name} → {recipient_name}: {self.interaction_type}"
    
    def save(self, *args, **kwargs):
        # Set expiration for certain types
        if not self.expires_at and self.interaction_type in ['encouragement', 'question']:
            self.expires_at = timezone.now() + timezone.timedelta(days=30)
        
        # Auto-moderation for new posts
        if not self.pk and not self.is_moderated:
            self._auto_moderate()
        
        super().save(*args, **kwargs)
    
    def _auto_moderate(self):
        """Simple auto-moderation based on content"""
        import re
        
        # List of concerning patterns (simplified)
        concerning_patterns = [
            r'\b(hate|stupid|idiot|worthless)\b',
            r'\b(kill|hurt|harm)\b',
            # Add more patterns as needed
        ]
        
        content = f"{self.title} {self.message}".lower()
        for pattern in concerning_patterns:
            if re.search(pattern, content):
                self.is_moderated = True
                self.moderator_notes = "Flagged for review by auto-moderation"
                break
    
    @property
    def is_anonymous(self):
        """Check if this is an anonymous interaction"""
        return (self.visibility == self.VisibilityLevel.ANONYMOUS or 
                self.sender is None)
    
    @property
    def display_name(self):
        """Get display name based on visibility"""
        if self.is_anonymous:
            return 'Anonymous Friend'
        elif self.sender:
            return self.sender.username
        return 'Community Member'
    
    @property
    def therapeutic_impact_score(self):
        """Calculate therapeutic impact score"""
        base_score = self.likes_count * 2 + self.replies_count * 3
        
        # Adjust based on interaction type
        type_multipliers = {
            'encouragement': 1.5,
            'gratitude': 1.3,
            'achievement': 1.2,
            'support': 1.1,
            'question': 1.0,
            'reflection': 1.0,
            'resource': 0.8,
        }
        
        multiplier = type_multipliers.get(self.interaction_type, 1.0)
        return int(base_score * multiplier)
    
    def can_user_see(self, user):
        """Check if a user can see this interaction"""
        if self.visibility == self.VisibilityLevel.PUBLIC:
            return True
        elif self.visibility == self.VisibilityLevel.ANONYMOUS:
            return True
        elif self.visibility == self.VisibilityLevel.COMMUNITY:
            return user.is_authenticated
        elif self.visibility == self.VisibilityLevel.PRIVATE:
            return user == self.recipient or user == self.sender
        return False
    
    def create_reply(self, user, message, anonymous=False):
        """Create a reply to this interaction"""
        if not self.allow_replies:
            raise ValidationError("Replies are not allowed for this interaction")
        
        reply = GentleInteraction.objects.create(
            interaction_type=self.InteractionType.REFLECTION,
            sender=user,
            recipient=self.sender,
            message=message,
            visibility=self.VisibilityLevel.ANONYMOUS if anonymous else self.VisibilityLevel.COMMUNITY
        )
        
        self.replies_count += 1
        self.save(update_fields=['replies_count'])
        
        return reply


class Achievement(models.Model):
    """Therapeutic achievement and milestone system"""
    
    class AchievementTier(models.TextChoices):
        GENTLE = 'gentle', '🌱 Gentle Start'
        CONFIDENT = 'confident', '🌿 Building Confidence'
        RESILIENT = 'resilient', '🌳 Becoming Resilient'
        MASTER = 'master', '🏔️ Master of Self'
        THERAPEUTIC = 'therapeutic', '🌟 Therapeutic Breakthrough'
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    tier = models.CharField(max_length=20, choices=AchievementTier.choices)
    
    # Visual representation
    icon_name = models.CharField(max_length=50, default='star')
    color = models.CharField(max_length=7, default='#FFD700')  # Gold
    
    # Requirements
    requirement_type = models.CharField(
        max_length=20,
        choices=[
            ('activities_completed', 'Complete Activities'),
            ('streak_days', 'Consecutive Days'),
            ('stress_reduction', 'Reduce Stress'),
            ('help_others', 'Help Others'),
            ('breakthrough', 'Therapeutic Breakthrough'),
            ('custom', 'Custom Criteria'),
        ]
    )
    
    requirement_value = models.IntegerField(default=1)
    requirement_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional requirement data"
    )
    
    # Therapeutic value
    therapeutic_message = models.TextField(blank=True)
    reflection_prompt = models.TextField(blank=True)
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['tier', 'name']
    
    def __str__(self):
        return f"{self.get_tier_display()} - {self.name}"
    
    def check_achievement(self, user):
        """Check if a user has earned this achievement"""
        from apps.learning.models import UserProgress
        
        if self.requirement_type == 'activities_completed':
            completed = UserProgress.objects.filter(
                user=user,
                status='completed'
            ).count()
            return completed >= self.requirement_value
        
        elif self.requirement_type == 'streak_days':
            return user.consecutive_days >= self.requirement_value
        
        elif self.requirement_type == 'stress_reduction':
            # Simplified check - would need historical data
            return user.current_stress_level <= 5
        
        elif self.requirement_type == 'breakthrough':
            progress_with_breakthrough = UserProgress.objects.filter(
                user=user,
                breakthrough_notes__isnull=False
            ).exists()
            return progress_with_breakthrough
        
        return False


class UserAchievement(models.Model):
    """Link between users and achievements they've earned"""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='earned_achievements'
    )
    
    achievement = models.ForeignKey(
        Achievement,
        on_delete=models.CASCADE,
        related_name='user_achievements'
    )
    
    earned_at = models.DateTimeField(auto_now_add=True)
    context_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Context about how achievement was earned"
    )
    
    shared_publicly = models.BooleanField(default=False)
    reflection_notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['user', 'achievement']
        ordering = ['-earned_at']
        verbose_name_plural = 'User Achievements'
    
    def __str__(self):
        return f"{self.user.username} - {self.achievement.name}"
    
    def share_to_community(self, message=''):
        """Share this achievement with the community"""
        interaction = GentleInteraction.objects.create(
            interaction_type=GentleInteraction.InteractionType.ACHIEVEMENT,
            sender=self.user,
            title=f"Achievement Unlocked: {self.achievement.name}",
            message=message or f"I just earned {self.achievement.name}! {self.achievement.therapeutic_message}",
            visibility=GentleInteraction.VisibilityLevel.COMMUNITY
        )
        
        self.shared_publicly = True
        self.save(update_fields=['shared_publicly'])
        
        return interaction


class SupportCircle(models.Model):
    """Therapeutic support group system"""
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    
    # Circle settings
    max_members = models.PositiveIntegerField(default=10)
    is_public = models.BooleanField(default=False)
    join_code = models.CharField(max_length=20, blank=True, unique=True)
    
    # Therapeutic focus
    focus_areas = models.JSONField(
        default=list,
        blank=True,
        help_text="List of therapeutic focus areas"
    )
    
    # Rules and guidelines
    community_guidelines = models.TextField(blank=True)
    meeting_schedule = models.JSONField(
        default=dict,
        blank=True,
        help_text="Weekly meeting schedule"
    )
    
    # Statistics
    total_interactions = models.PositiveIntegerField(default=0)
    active_members = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_circles'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-active_members', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.active_members} members)"
    
    def add_member(self, user):
        """Add a member to the support circle"""
        if self.members.count() >= self.max_members:
            raise ValidationError("Support circle is full")
        
        membership, created = CircleMembership.objects.get_or_create(
            circle=self,
            user=user,
            defaults={'role': 'member'}
        )
        
        if created:
            self.active_members += 1
            self.save(update_fields=['active_members'])
        
        return membership
    
    def create_gentle_checkin(self, user, emotion_data):
        """Create a gentle group checkin"""
        if not self.members.filter(user=user).exists():
            raise ValidationError("User is not a member of this circle")
        
        # Create an interaction for the circle
        interaction = GentleInteraction.objects.create(
            interaction_type=GentleInteraction.InteractionType.REFLECTION,
            sender=user,
            title=f"Group Check-in: {user.username}",
            message=f"I'm feeling {emotion_data.get('emotion', '...')} today.",
            visibility=GentleInteraction.VisibilityLevel.COMMUNITY
        )
        
        self.total_interactions += 1
        self.save(update_fields=['total_interactions'])
        
        return interaction


class CircleMembership(models.Model):
    """Membership in a support circle"""
    
    class MemberRole(models.TextChoices):
        LEADER = 'leader', 'Circle Leader'
        SUPPORTER = 'supporter', 'Active Supporter'
        MEMBER = 'member', 'Member'
        OBSERVER = 'observer', 'Observer'
    
    circle = models.ForeignKey(
        SupportCircle,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='circle_memberships'
    )
    
    role = models.CharField(
        max_length=20,
        choices=MemberRole.choices,
        default=MemberRole.MEMBER
    )
    
    joined_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    
    # Therapeutic metrics
    support_given = models.PositiveIntegerField(default=0)
    support_received = models.PositiveIntegerField(default=0)
    
    # Preferences
    notification_preferences = models.JSONField(
        default=dict,
        blank=True,
        help_text="Notification settings for circle"
    )
    
    class Meta:
        unique_together = ['circle', 'user']
        ordering = ['role', '-joined_at']
    
    def __str__(self):
        return f"{self.user.username} in {self.circle.name}"