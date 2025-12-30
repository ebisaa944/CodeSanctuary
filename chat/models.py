# chat/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import uuid
import json

# Import your custom user model
User = settings.AUTH_USER_MODEL


class ChatRoom(models.Model):
    """
    Therapeutic chat room with integration to other CODE_SANCTUARY apps
    """
    class RoomType(models.TextChoices):
        THERAPY_SESSION = 'therapy_session', 'Therapy Session'
        PEER_SUPPORT = 'peer_support', 'Peer Support Group'
        LEARNING_GROUP = 'learning_group', 'Learning Group'
        PROJECT_TEAM = 'project_team', 'Project Collaboration'
        GENERAL = 'general', 'General Discussion'
        MODERATED = 'moderated', 'Moderated Support'
        THERAPEUTIC_CODING = 'therapeutic_coding', 'Therapeutic Coding'
        SOCIAL = 'social', 'Social Connection'
    
    class SafetyLevel(models.TextChoices):
        SAFE_SPACE = 'safe_space', 'Safe Space (Heavy Moderation)'
        SUPPORTIVE = 'supportive', 'Supportive Environment'
        CHALLENGING = 'challenging', 'Growth-Focused'
        OPEN = 'open', 'Open Discussion'
    
    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    room_type = models.CharField(max_length=30, choices=RoomType.choices, default=RoomType.GENERAL)
    description = models.TextField(blank=True, null=True)
    
    # Therapeutic features
    safety_level = models.CharField(max_length=20, choices=SafetyLevel.choices, default=SafetyLevel.SUPPORTIVE)
    is_gated = models.BooleanField(default=False, help_text="Requires emotional readiness assessment")
    requires_consent = models.BooleanField(default=True)
    mood_tracking_enabled = models.BooleanField(default=True)
    trigger_warnings_required = models.BooleanField(default=True)
    max_stress_level = models.IntegerField(
        default=7,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Maximum stress level allowed to join"
    )
    
    # Integration with other apps
    # Link to therapy sessions
    # TODO: Uncomment when therapy app is created
    # therapy_session = models.ForeignKey(
    #     'therapy.TherapySession', 
    #     on_delete=models.SET_NULL, 
    #     null=True, 
    #     blank=True,
    #     related_name='chat_rooms'
    # )
    
    # Link to learning modules
    # TODO: Uncomment when learning app is created
    # learning_module = models.ForeignKey(
    #     'learning.LearningModule', 
    #     on_delete=models.SET_NULL, 
    #     null=True, 
    #     blank=True,
    #     related_name='discussion_rooms'
    # )
    
    # Link to therapeutic coding exercises
    # TODO: Uncomment when therapeutic_coding app is created
    # coding_exercise = models.ForeignKey(
    #     'therapeutic_coding.CodingExercise', 
    #     on_delete=models.SET_NULL, 
    #     null=True, 
    #     blank=True,
    #     related_name='collaboration_rooms'
    # )
    
    # Link to social events
    # TODO: Uncomment when social app is created
    # social_event = models.ForeignKey(
    #     'social.SocialEvent', 
    #     on_delete=models.SET_NULL, 
    #     null=True, 
    #     blank=True,
    #     related_name='chat_rooms'
    # )
    
    # Room management
    is_private = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    max_participants = models.IntegerField(default=20, validators=[MinValueValidator(1), MaxValueValidator(100)])
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_chat_rooms')
    moderators = models.ManyToManyField(User, related_name='moderated_chat_rooms', blank=True)
    therapists = models.ManyToManyField(User, related_name='therapist_chat_rooms', blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_open = models.DateTimeField(null=True, blank=True)
    scheduled_close = models.DateTimeField(null=True, blank=True)
    
    # Therapeutic goals
    therapeutic_goal = models.TextField(blank=True, null=True)
    conversation_guidelines = models.JSONField(
        default=list,
        blank=True,
        help_text="List of conversation guidelines for this room"
    )
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Therapeutic Chat Room'
        verbose_name_plural = 'Therapeutic Chat Rooms'
        indexes = [
            models.Index(fields=['room_type', 'safety_level']),
            models.Index(fields=['is_private', 'is_archived']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_room_type_display()})"
    
    def clean(self):
        """Validate room settings"""
        if self.max_stress_level < 1 or self.max_stress_level > 10:
            raise ValidationError({'max_stress_level': 'Must be between 1 and 10'})
        
        if self.scheduled_open and self.scheduled_close:
            if self.scheduled_close <= self.scheduled_open:
                raise ValidationError({
                    'scheduled_close': 'Close time must be after open time'
                })
    
    @property
    def is_active(self):
        """Check if room is currently active based on schedule"""
        now = timezone.now()
        if self.scheduled_open and self.scheduled_close:
            return self.scheduled_open <= now <= self.scheduled_close
        return not self.is_archived
    
    @property
    def participant_count(self):
        return self.participants.filter(membership__is_active=True).count()
    
    def can_user_join(self, user):
        """Check if user meets criteria to join this room"""
        if user.current_stress_level > self.max_stress_level:
            return False, "Your current stress level is too high for this room"
        
        if self.is_gated and user.emotional_profile in ['ANXIOUS', 'OVERWHELMED']:
            return False, "This room requires emotional readiness preparation"
        
        if self.participant_count >= self.max_participants:
            return False, "Room is at maximum capacity"
        
        return True, ""


class RoomMembership(models.Model):
    """
    Therapeutic membership tracking with emotional state monitoring
    """
    class MemberRole(models.TextChoices):
        PARTICIPANT = 'participant', 'Participant'
        MODERATOR = 'moderator', 'Moderator'
        THERAPIST = 'therapist', 'Therapist'
        FACILITATOR = 'facilitator', 'Facilitator'
        OBSERVER = 'observer', 'Observer'
        SUPPORT_BOT = 'support_bot', 'Support Bot'
    
    class ComfortLevel(models.TextChoices):
        VERY_UNCOMFORTABLE = '1', 'Very Uncomfortable'  # CORRECT - '1' is a string
        UNCOMFORTABLE = '2', 'Uncomfortable'  # CORRECT - '2' is a string
        NEUTRAL = '3', 'Neutral'  # CORRECT - '3' is a string
        COMFORTABLE = '4', 'Comfortable'  # CORRECT - '4' is a string
        SAFE = '5', 'Feeling Safe'  # CORRECT - '5' is a string
    
    # Core membership
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_memberships')
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='memberships')
    
    # Role and status
    role = models.CharField(max_length=20, choices=MemberRole.choices, default=MemberRole.PARTICIPANT)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_muted = models.BooleanField(default=False)
    is_anonymous = models.BooleanField(default=False, help_text="Participate without revealing identity")
    
    # Therapeutic tracking
    consent_given = models.BooleanField(default=False)
    comfort_level = models.IntegerField(
        choices=ComfortLevel.choices,
        default=ComfortLevel.NEUTRAL,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    entry_stress_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        null=True,
        blank=True,
        help_text="Stress level when joining"
    )
    exit_stress_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        null=True,
        blank=True,
        help_text="Stress level when leaving"
    )
    
    # Therapeutic metadata
    therapeutic_goals = models.JSONField(
        default=list,
        blank=True,
        help_text="Personal goals for this chat experience"
    )
    triggers_disclosed = models.JSONField(
        default=list,
        blank=True,
        help_text="List of disclosed triggers for this user"
    )
    
    # Notification preferences
    notification_preference = models.CharField(
        max_length=20,
        choices=[
            ('all', 'All Messages'),
            ('mentions', 'Only @mentions'),
            ('none', 'No Notifications'),
            ('gentle', 'Gentle Reminders Only')
        ],
        default='gentle'
    )
    
    # Safety features
    has_safety_plan = models.BooleanField(default=False)
    emergency_contact_notified = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['user', 'room']
        verbose_name = 'Room Membership'
        verbose_name_plural = 'Room Memberships'
    
    def __str__(self):
        return f"{self.user.username} - {self.room.name} ({self.get_role_display()})"
    
    def save(self, *args, **kwargs):
        """Record stress level when joining"""
        if not self.pk and not self.entry_stress_level:
            self.entry_stress_level = self.user.current_stress_level
        super().save(*args, **kwargs)
    
    def update_comfort_level(self, level):
        """Update comfort level with validation"""
        if 1 <= level <= 5:
            self.comfort_level = level
            self.save(update_fields=['comfort_level'])
            return True
        return False
    
    def mark_exit(self, stress_level=None):
        """Mark user as leaving the room"""
        self.is_active = False
        if stress_level:
            self.exit_stress_level = stress_level
        self.save()


class ChatMessage(models.Model):
    """
    Therapeutic chat message with extensive metadata and integrations
    """
    class MessageType(models.TextChoices):
        TEXT = 'text', 'Text Message'
        CODE = 'code', 'Code Snippet'
        REFLECTION = 'reflection', 'Session Reflection'
        CHECKIN = 'checkin', 'Wellness Check-in'
        BREAKTHROUGH = 'breakthrough', 'Breakthrough Moment'
        RESOURCE = 'resource', 'Helpful Resource'
        EXERCISE = 'exercise', 'Therapeutic Exercise'
        AFFIRMATION = 'affirmation', 'Positive Affirmation'
        TRIGGER_WARNING = 'trigger_warning', 'Trigger Warning'
        SYSTEM = 'system', 'System Message'
        MODERATION = 'moderation', 'Moderator Action'
    
    class Visibility(models.TextChoices):
        PUBLIC = 'public', 'Visible to all participants'
        PRIVATE = 'private', 'Direct message to recipient'
        ANONYMOUS = 'anonymous', 'Anonymous to group'
        THERAPIST_ONLY = 'therapist_only', 'Visible to therapists only'
        SELF_REFLECTION = 'self_reflection', 'Private reflection'
        MODERATORS_ONLY = 'moderators_only', 'Moderators only'
    
    # Core message
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_messages')
    
    # Content
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.TEXT)
    content = models.TextField()
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    
    # Threading for therapeutic conversations
    parent_message = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='replies'
    )
    is_thread_starter = models.BooleanField(default=False)
    thread_depth = models.IntegerField(default=0)
    
    # Therapeutic metadata
    emotional_tone = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="AI-detected emotional tone (e.g., 'hopeful', 'anxious', 'proud')"
    )
    trigger_warning = models.TextField(blank=True, null=True)
    is_vulnerable_share = models.BooleanField(default=False)
    coping_strategy_shared = models.BooleanField(default=False)
    contains_affirmation = models.BooleanField(default=False)
    therapeutic_label = models.CharField(max_length=100, blank=True, null=True)
    
    # Safety and moderation
    requires_moderation = models.BooleanField(default=False)
    moderated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='moderated_messages'
    )
    moderation_notes = models.TextField(blank=True, null=True)
    is_flagged = models.BooleanField(default=False)
    flagged_reason = models.CharField(max_length=200, blank=True, null=True)
    
    # Integration with other apps
    # Link to learning activity
    # TODO: Uncomment when learning app is created
    # learning_activity = models.ForeignKey(
    #     'learning.LearningActivity', 
    #     on_delete=models.SET_NULL, 
    #     null=True, 
    #     blank=True,
    #     related_name='discussion_messages'
    # )
    
    # Link to therapy exercise
    # TODO: Uncomment when therapy app is created
    # therapy_exercise = models.ForeignKey(
    #     'therapy.TherapyExercise', 
    #     on_delete=models.SET_NULL, 
    #     null=True, 
    #     blank=True,
    #     related_name='reflection_messages'
    # )
    
    # Link to coding exercise
    # TODO: Uncomment when therapeutic_coding app is created
    # coding_solution = models.ForeignKey(
    #     'therapeutic_coding.CodingSolution', 
    #     on_delete=models.SET_NULL, 
    #     null=True, 
    #     blank=True,
    #     related_name='discussion_messages'
    # )
    
    # Attachments
    attachment = models.FileField(
        upload_to='chat_attachments/%Y/%m/%d/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator([
                'jpg', 'jpeg', 'png', 'gif',  # Images
                'pdf', 'doc', 'docx', 'txt',  # Documents
                'mp3', 'wav',  # Audio
                'mp4', 'mov',  # Video
                'py', 'js', 'html', 'css', 'json'  # Code files
            ])
        ]
    )
    attachment_caption = models.CharField(max_length=200, blank=True, null=True)
    
    # Message lifecycle
    edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='deleted_chat_messages'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    
    # Analytics
    read_by_count = models.IntegerField(default=0)
    reaction_count = models.IntegerField(default=0)
    share_count = models.IntegerField(default=0)
    
    # Therapeutic impact tracking
    helpful_votes = models.IntegerField(default=0)
    supportive_responses = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Therapeutic Chat Message'
        verbose_name_plural = 'Therapeutic Chat Messages'
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['message_type', 'created_at']),
            models.Index(fields=['is_vulnerable_share', 'created_at']),
            models.Index(fields=['emotional_tone', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}"
    
    def clean(self):
        """Validate message based on therapeutic settings"""
        if self.is_vulnerable_share and not self.trigger_warning and self.room.trigger_warnings_required:
            raise ValidationError({
                'trigger_warning': 'Trigger warning required for vulnerable shares'
            })
        
        if self.visibility == self.Visibility.ANONYMOUS and not self.user.allow_anonymous:
            raise ValidationError({
                'visibility': 'User does not allow anonymous posting'
            })
    
    def soft_delete(self, deleted_by_user):
        """Soft delete message with therapeutic consideration"""
        self.deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by_user
        
        # Preserve therapeutic value while removing content
        if self.is_vulnerable_share or self.coping_strategy_shared:
            self.content = "[Therapeutic content removed - user requested deletion]"
        else:
            self.content = "[Message deleted]"
        
        self.save()
    
    def mark_as_helpful(self):
        """Increment helpful votes"""
        self.helpful_votes += 1
        self.save(update_fields=['helpful_votes'])
    
    @property
    def is_scheduled(self):
        """Check if message is scheduled for future"""
        if self.scheduled_for:
            return self.scheduled_for > timezone.now()
        return False
    
    @property
    def safe_content_preview(self):
        """Get content preview with trigger warning consideration"""
        if self.trigger_warning:
            return f"[Trigger: {self.trigger_warning}] {self.content[:100]}..."
        return self.content[:150]
    
    def get_therapeutic_context(self):
        """Get therapeutic context for this message"""
        context = {
            'user_stress_level': self.user.current_stress_level,
            'user_emotional_profile': self.user.get_emotional_profile_display(),
            'room_safety_level': self.room.get_safety_level_display(),
            'message_type': self.get_message_type_display(),
        }
        
        if self.emotional_tone:
            context['emotional_tone'] = self.emotional_tone
        
        if self.is_vulnerable_share:
            context['is_vulnerable'] = True
            context['needs_support'] = True
        
        return context


class MessageReaction(models.Model):
    """
    Therapeutic reactions with emotional validation support
    """
    class ReactionType(models.TextChoices):
        # Emotional support reactions
        HEART = '❤️', 'Heart (Support)'
        HUG = '🤗', 'Virtual Hug'
        SUN = '☀️', 'Light & Hope'
        LEAF = '🍃', 'Growth'
        STAR = '⭐', 'Shining Moment'
        CHECK = '✅', 'I Understand'
        
        # Therapeutic validation
        BREATH = '🌬️', 'Take a Breath'
        ANCHOR = '⚓', 'Stay Grounded'
        WAVE = '🌊', 'Riding the Wave'
        SEED = '🌱', 'New Beginning'
        
        # Learning support
        BULB = '💡', 'Great Idea'
        CLAP = '👏', 'Well Done'
        ROCKET = '🚀', 'Making Progress'
        PUZZLE = '🧩', 'Figuring It Out'
        
        # Safety signals
        WARNING = '⚠️', 'Trigger Warning'
        SHIELD = '🛡️', 'I Feel Safe'
        DOOR = '🚪', 'Need Space'
        HAND = '🤝', 'Reaching Out'
    
    # Core reaction
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_reactions')
    reaction_type = models.CharField(max_length=5, choices=ReactionType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Therapeutic context
    emotional_context = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Optional: What emotion prompted this reaction"
    )
    is_supportive = models.BooleanField(default=True)
    is_therapeutic = models.BooleanField(default=False)
    
    # Anonymous reactions for sensitive topics
    is_anonymous = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['message', 'user', 'reaction_type']
        verbose_name = 'Message Reaction'
        verbose_name_plural = 'Message Reactions'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} reacted {self.reaction_type} to message"
    
    @property
    def reaction_category(self):
        """Categorize reaction for therapeutic analysis"""
        support_reactions = ['❤️', '🤗', '✅', '🛡️', '🤝']
        growth_reactions = ['⭐', '💡', '👏', '🚀', '🌱']
        safety_reactions = ['⚠️', '🚪', '🌊', '⚓']
        
        if self.reaction_type in support_reactions:
            return 'emotional_support'
        elif self.reaction_type in growth_reactions:
            return 'growth_encouragement'
        elif self.reaction_type in safety_reactions:
            return 'safety_signal'
        else:
            return 'general_reaction'


class ChatSessionAnalytics(models.Model):
    """
    Track therapeutic outcomes from chat sessions
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_analytics')
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='session_analytics')
    session_start = models.DateTimeField()
    session_end = models.DateTimeField(null=True, blank=True)
    
    # Emotional metrics
    starting_stress_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    ending_stress_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        null=True,
        blank=True
    )
    
    # Participation metrics
    messages_sent = models.IntegerField(default=0)
    messages_received = models.IntegerField(default=0)
    reactions_given = models.IntegerField(default=0)
    reactions_received = models.IntegerField(default=0)
    
    # Therapeutic engagement
    vulnerable_shares = models.IntegerField(default=0)
    coping_strategies_shared = models.IntegerField(default=0)
    affirmations_given = models.IntegerField(default=0)
    affirmations_received = models.IntegerField(default=0)
    
    # Safety metrics
    trigger_warnings_used = models.IntegerField(default=0)
    safety_plan_activated = models.BooleanField(default=False)
    moderation_interventions = models.IntegerField(default=0)
    
    # Therapeutic outcomes
    breakthrough_moments = models.JSONField(default=list, blank=True)
    insights_gained = models.JSONField(default=list, blank=True)
    follow_up_actions = models.JSONField(default=list, blank=True)
    
    # Session feedback
    session_rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        null=True,
        blank=True
    )
    feedback_notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Chat Session Analytics'
        verbose_name_plural = 'Chat Session Analytics'
        indexes = [
            models.Index(fields=['user', 'session_start']),
            models.Index(fields=['room', 'session_start']),
        ]
        ordering = ['-session_start']
    
    def __str__(self):
        return f"{self.user.username} - {self.room.name} - {self.session_start.date()}"
    
    @property
    def session_duration_minutes(self):
        """Calculate session duration in minutes"""
        if self.session_end:
            duration = self.session_end - self.session_start
            return duration.total_seconds() / 60
        return None
    
    @property
    def stress_change(self):
        """Calculate change in stress level"""
        if self.ending_stress_level:
            return self.ending_stress_level - self.starting_stress_level
        return None
    
    @property
    def therapeutic_engagement_score(self):
        """Calculate therapeutic engagement score"""
        score = 0
        score += self.vulnerable_shares * 3  # Higher weight for vulnerability
        score += self.coping_strategies_shared * 2
        score += self.affirmations_given
        score += self.affirmations_received
        score += self.messages_sent * 0.5
        score -= self.moderation_interventions * 2  # Penalize for needing moderation
        
        return max(0, score)  # Ensure non-negative


class ChatNotification(models.Model):
    """
    Therapeutic notifications for chat activities
    """
    class NotificationType(models.TextChoices):
        MESSAGE = 'message', 'New Message'
        MENTION = 'mention', 'You Were Mentioned'
        REACTION = 'reaction', 'Reaction to Your Message'
        ROOM_INVITE = 'room_invite', 'Room Invitation'
        SAFETY_CHECK = 'safety_check', 'Safety Check-in'
        BREAKTHROUGH = 'breakthrough', 'Breakthrough Alert'
        GENTLE_REMINDER = 'gentle_reminder', 'Gentle Reminder'
        MODERATION = 'moderation', 'Moderation Action'
        THERAPEUTIC_INSIGHT = 'therapeutic_insight', 'Therapeutic Insight'
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_notifications')
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    
    # Content
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_urgent = models.BooleanField(default=False)
    
    # Related objects (using GenericForeignKey for flexibility)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Therapeutic settings
    is_gentle = models.BooleanField(default=True, help_text="Use gentle notification style")
    delay_until = models.DateTimeField(null=True, blank=True, help_text="Delay notification if user is stressed")
    
    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Chat Notification'
        verbose_name_plural = 'Chat Notifications'
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
            models.Index(fields=['notification_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"
    
    def should_deliver_now(self):
        """Check if notification should be delivered based on user state"""
        if not self.delay_until:
            return True
        
        now = timezone.now()
        if now >= self.delay_until:
            return True
        
        # Don't deliver if user is highly stressed and notification isn't urgent
        if self.user.current_stress_level >= 7 and not self.is_urgent:
            return False
        
        return True
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class TherapeuticChatSettings(models.Model):
    """
    User-specific therapeutic chat settings
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='chat_settings')
    
    # Safety preferences
    auto_trigger_warnings = models.BooleanField(
        default=True,
        help_text="Automatically add trigger warnings to vulnerable shares"
    )
    
    vulnerability_timeout = models.IntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(300)],
        help_text="Minutes to wait before sending vulnerable message"
    )
    
    # Notification preferences
    notify_on_mention = models.BooleanField(default=True)
    notify_on_reaction = models.BooleanField(default=True)
    notify_on_breakthrough = models.BooleanField(default=True)
    
    # Therapeutic features
    enable_emotional_tone_detection = models.BooleanField(default=True)
    enable_coping_suggestions = models.BooleanField(default=True)
    enable_affirmation_suggestions = models.BooleanField(default=True)
    
    # Privacy
    show_stress_level_in_chat = models.BooleanField(default=False)
    allow_anonymous_posting = models.BooleanField(default=True)
    archive_chats_after_days = models.IntegerField(
        default=90,
        validators=[MinValueValidator(1), MaxValueValidator(365)],
        help_text="Automatically archive chats after X days"
    )
    
    # Gentle mode integration
    gentle_notification_sounds = models.BooleanField(default=True)
    gentle_message_colors = models.BooleanField(default=True)
    hide_stressful_content = models.BooleanField(
        default=True,
        help_text="Automatically hide content when stressed"
    )
    
    # Learning integration
    link_chats_to_learning = models.BooleanField(
        default=True,
        help_text="Automatically connect chat discussions to learning modules"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Therapeutic Chat Setting'
        verbose_name_plural = 'Therapeutic Chat Settings'
    
    def __str__(self):
        return f"Chat settings for {self.user.username}"
    
    def get_safe_notification_settings(self):
        """Get notification settings adjusted for user's current state"""
        base_settings = {
            'notify_on_mention': self.notify_on_mention,
            'notify_on_reaction': self.notify_on_reaction,
            'notify_on_breakthrough': self.notify_on_breakthrough,
        }
        
        # Adjust based on stress level
        if self.user.current_stress_level >= 7:
            return {**base_settings, 'is_gentle': True, 'delay_non_urgent': True}
        elif self.user.current_stress_level >= 5:
            return {**base_settings, 'is_gentle': True, 'delay_non_urgent': False}
        else:
            return {**base_settings, 'is_gentle': self.user.gentle_mode, 'delay_non_urgent': False}