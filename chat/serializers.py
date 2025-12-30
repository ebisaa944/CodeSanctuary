# chat/serializers.py - COMPLETE FIXED VERSION WITH ALL SERIALIZERS
from rest_framework import serializers
from django.db.models import Count, Avg, Q
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import (
    ChatMessage, ChatRoom, RoomMembership, 
    MessageReaction, ChatSessionAnalytics,
    ChatNotification, TherapeuticChatSettings
)

User = get_user_model()

# ===== SIMPLE COMPATIBILITY SERIALIZERS =====
class MessageSerializer(serializers.ModelSerializer):
    """Simple serializer for chat messages (for compatibility with views)"""
    user = serializers.StringRelatedField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'content', 'user', 'created_at',
            'is_vulnerable_share', 'coping_strategy_shared',
            'contains_affirmation', 'trigger_warning'
        ]
        read_only_fields = ['created_at', 'user']

class RoomSerializer(serializers.ModelSerializer):
    """Simple serializer for chat rooms (for compatibility with views)"""
    participant_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'name', 'description', 'room_type', 'safety_level',
            'participant_count', 'max_stress_level', 'is_private',
            'therapeutic_goal'
        ]

class UserSerializer(serializers.ModelSerializer):
    """Simple user serializer (for compatibility with views)"""
    class Meta:
        model = User
        fields = ['id', 'username', 'avatar_color']

# ===== MAIN SERIALIZERS =====
class ChatStatisticsSerializer(serializers.Serializer):
    """Serializer for chat room statistics"""
    total_messages = serializers.IntegerField()
    vulnerable_shares = serializers.IntegerField()
    coping_strategies = serializers.IntegerField()
    affirmations = serializers.IntegerField()
    avg_stress_level = serializers.FloatField()
    activity_data = serializers.ListField(child=serializers.IntegerField())
    active_members = serializers.IntegerField()
    new_members_today = serializers.IntegerField()
    messages_today = serializers.IntegerField()
    engagement_rate = serializers.FloatField()
    
    @classmethod
    def calculate_for_room(cls, room):
        """Calculate statistics for a specific room"""
        now = timezone.now()
        today = now.date()
        
        # Base querysets
        room_messages = ChatMessage.objects.filter(room=room)
        vulnerable_messages = room_messages.filter(is_vulnerable_share=True)
        coping_messages = room_messages.filter(coping_strategy_shared=True)
        affirmation_messages = room_messages.filter(contains_affirmation=True)
        
        # Get room memberships
        room_memberships = RoomMembership.objects.filter(room=room)
        
        # Calculate activity data (last 7 days)
        activity_data = []
        for i in range(6, -1, -1):  # Last 7 days including today
            day = today - timedelta(days=i)
            day_messages = room_messages.filter(
                created_at__date=day
            ).count()
            activity_data.append(day_messages)
        
        # Calculate engagement rate
        total_members = room_memberships.count()
        active_members = room_memberships.filter(
            last_seen__date=today
        ).count()
        engagement_rate = (active_members / total_members * 100) if total_members > 0 else 0
        
        return {
            'total_messages': room_messages.count(),
            'vulnerable_shares': vulnerable_messages.count(),
            'coping_strategies': coping_messages.count(),
            'affirmations': affirmation_messages.count(),
            'avg_stress_level': room_memberships.aggregate(
                avg_stress=Avg('entry_stress_level')
            )['avg_stress'] or 0,
            'activity_data': activity_data,
            'active_members': active_members,
            'new_members_today': room_memberships.filter(
                joined_at__date=today
            ).count(),
            'messages_today': room_messages.filter(
                created_at__date=today
            ).count(),
            'engagement_rate': round(engagement_rate, 2)
        }
    
    @classmethod
    def calculate_global(cls):
        """Calculate global chat statistics"""
        now = timezone.now()
        today = now.date()
        
        # Global statistics
        total_rooms = ChatRoom.objects.count()
        total_messages = ChatMessage.objects.count()
        total_users = RoomMembership.objects.values('user').distinct().count()
        
        # Active rooms (rooms with messages in last 24 hours)
        active_rooms = ChatRoom.objects.filter(
            messages__created_at__gte=now - timedelta(hours=24)
        ).distinct().count()
        
        # Vulnerable shares percentage
        vulnerable_messages = ChatMessage.objects.filter(is_vulnerable_share=True).count()
        vulnerable_percentage = (vulnerable_messages / total_messages * 100) if total_messages > 0 else 0
        
        return {
            'total_rooms': total_rooms,
            'total_messages': total_messages,
            'total_users': total_users,
            'active_rooms': active_rooms,
            'vulnerable_percentage': round(vulnerable_percentage, 2),
            'average_room_size': round(total_users / total_rooms, 2) if total_rooms > 0 else 0,
            'messages_today': ChatMessage.objects.filter(
                created_at__date=today
            ).count()
        }


class TherapeuticUserLiteSerializer(serializers.ModelSerializer):
    """
    Lightweight user serializer for chat display
    Respects therapeutic settings like anonymous posting
    """
    emotional_profile_display = serializers.CharField(source='get_emotional_profile_display', read_only=True)
    comfort_level_display = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    avatar_color = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'display_name', 'avatar_color',
            'emotional_profile', 'emotional_profile_display',
            'current_stress_level', 'comfort_level_display',
            'gentle_mode', 'learning_streak_badge'
        ]
        read_only_fields = fields
    
    def get_comfort_level_display(self, obj):
        # Get comfort level from membership if available
        request = self.context.get('request')
        room_id = self.context.get('room_id')
        
        if room_id and request and request.user != obj:
            try:
                membership = RoomMembership.objects.get(user=obj, room_id=room_id)
                return membership.get_comfort_level_display()
            except RoomMembership.DoesNotExist:
                return None
        return None
    
    def get_display_name(self, obj):
        """Respect anonymous settings"""
        request = self.context.get('request')
        
        # Check if user is posting anonymously in this context
        is_anonymous = self.context.get('is_anonymous', False)
        
        if is_anonymous and obj.allow_anonymous:
            return "Anonymous User"
        
        # Check if viewing user should see stress level
        if request and request.user != obj:
            chat_settings = getattr(obj, 'chat_settings', None)
            if chat_settings and not chat_settings.show_stress_level_in_chat:
                # Return username without stress indicators
                return obj.username
        
        return obj.username


class ChatRoomSerializer(serializers.ModelSerializer):
    """
    Serializer for therapeutic chat rooms
    """
    room_type_display = serializers.CharField(source='get_room_type_display', read_only=True)
    safety_level_display = serializers.CharField(source='get_safety_level_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    participant_count = serializers.IntegerField(read_only=True)
    created_by = TherapeuticUserLiteSerializer(read_only=True)
    moderators = TherapeuticUserLiteSerializer(many=True, read_only=True)
    therapists = TherapeuticUserLiteSerializer(many=True, read_only=True)
    
    # Integration fields
    therapy_session = serializers.UUIDField(source='therapy_session.id', read_only=True, allow_null=True)
    learning_module = serializers.UUIDField(source='learning_module.id', read_only=True, allow_null=True)
    coding_exercise = serializers.UUIDField(source='coding_exercise.id', read_only=True, allow_null=True)
    
    # Therapeutic metrics
    current_user_membership = serializers.SerializerMethodField()
    can_join = serializers.SerializerMethodField()
    join_reason = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'name', 'room_type', 'room_type_display',
            'description', 'safety_level', 'safety_level_display',
            'is_private', 'is_active', 'is_gated', 'requires_consent',
            'max_stress_level', 'max_participants', 'participant_count',
            'created_by', 'moderators', 'therapists',
            'therapy_session', 'learning_module', 'coding_exercise',
            'therapeutic_goal', 'conversation_guidelines',
            'mood_tracking_enabled', 'trigger_warnings_required',
            'created_at', 'updated_at', 'scheduled_open', 'scheduled_close',
            'current_user_membership', 'can_join', 'join_reason'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'participant_count',
            'is_active', 'current_user_membership', 'can_join', 'join_reason'
        ]
    
    def get_current_user_membership(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                membership = RoomMembership.objects.get(user=request.user, room=obj)
                return RoomMembershipSerializer(membership, context=self.context).data
            except RoomMembership.DoesNotExist:
                return None
        return None
    
    def get_can_join(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            can_join, _ = obj.can_user_join(request.user)
            return can_join
        return False
    
    def get_join_reason(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            _, reason = obj.can_user_join(request.user)
            return reason
        return "Authentication required"
    
    def validate(self, data):
        """Validate therapeutic room settings"""
        if data.get('max_stress_level', 7) < 1 or data.get('max_stress_level', 7) > 10:
            raise serializers.ValidationError({
                'max_stress_level': 'Must be between 1 and 10'
            })
        
        if data.get('max_participants', 20) < 1:
            raise serializers.ValidationError({
                'max_participants': 'Must be at least 1'
            })
        
        return data
    
    def create(self, validated_data):
        """Create room with therapeutic defaults"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        
        # Set therapeutic conversation guidelines if not provided
        if not validated_data.get('conversation_guidelines'):
            validated_data['conversation_guidelines'] = [
                "Practice active listening",
                "Use 'I' statements when sharing",
                "Respect different emotional experiences",
                "Use trigger warnings when discussing difficult topics",
                "Take breaks when needed"
            ]
        
        room = super().create(validated_data)
        
        # Auto-add creator as moderator
        if request and request.user.is_authenticated:
            RoomMembership.objects.create(
                user=request.user,
                room=room,
                role='moderator',
                consent_given=True
            )
        
        return room


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating chat rooms
    """
    class Meta:
        model = ChatRoom
        fields = [
            'name', 'room_type', 'description', 'safety_level',
            'is_private', 'max_participants', 'max_stress_level',
            'therapeutic_goal', 'conversation_guidelines'
        ]
    
    def create(self, validated_data):
        """Create room with therapeutic defaults"""
        request = self.context.get('request')
        validated_data['created_by'] = request.user
        
        # Set therapeutic conversation guidelines if not provided
        if not validated_data.get('conversation_guidelines'):
            room_type = validated_data.get('room_type', 'general')
            
            if room_type == 'therapy_session':
                guidelines = [
                    "This is a confidential therapeutic space",
                    "Share only what feels safe",
                    "Therapist may guide the conversation",
                    "Take breaks as needed",
                    "Focus on the present experience"
                ]
            elif room_type == 'peer_support':
                guidelines = [
                    "Peer support - we're all learning together",
                    "Share experiences, not advice",
                    "Respect different healing journeys",
                    "Use 'I' statements",
                    "Take space when needed"
                ]
            else:
                guidelines = [
                    "Practice kindness and respect",
                    "Use trigger warnings for difficult topics",
                    "Take responsibility for your impact",
                    "Listen more than you speak",
                    "Celebrate small victories"
                ]
            
            validated_data['conversation_guidelines'] = guidelines
        
        return super().create(validated_data)


class RoomMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for therapeutic room memberships
    """
    user = TherapeuticUserLiteSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    comfort_level_display = serializers.CharField(source='get_comfort_level_display', read_only=True)
    room_name = serializers.CharField(source='room.name', read_only=True)
    room_type = serializers.CharField(source='room.room_type', read_only=True)
    
    # Therapeutic tracking
    session_duration = serializers.SerializerMethodField()
    stress_change = serializers.SerializerMethodField()
    
    class Meta:
        model = RoomMembership
        fields = [
            'id', 'user', 'room', 'room_name', 'room_type',
            'role', 'role_display', 'joined_at', 'last_seen',
            'is_active', 'is_muted', 'is_anonymous',
            'comfort_level', 'comfort_level_display',
            'entry_stress_level', 'exit_stress_level',
            'notification_preference', 'consent_given',
            'therapeutic_goals', 'triggers_disclosed',
            'has_safety_plan', 'emergency_contact_notified',
            'session_duration', 'stress_change'
        ]
        read_only_fields = [
            'id', 'user', 'room', 'joined_at', 'last_seen',
            'session_duration', 'stress_change'
        ]
    
    def get_session_duration(self, obj):
        """Calculate session duration in minutes"""
        if obj.last_seen and obj.joined_at:
            duration = obj.last_seen - obj.joined_at
            return duration.total_seconds() / 60
        return None
    
    def get_stress_change(self, obj):
        """Calculate stress level change"""
        if obj.exit_stress_level and obj.entry_stress_level:
            return obj.exit_stress_level - obj.entry_stress_level
        return None
    
    def validate(self, data):
        """Validate therapeutic membership"""
        # Check consent for therapeutic rooms
        if self.instance and self.instance.room.requires_consent:
            if not data.get('consent_given', self.instance.consent_given):
                raise serializers.ValidationError({
                    'consent_given': 'Consent is required for this therapeutic space'
                })
        
        # Validate comfort level
        comfort_level = data.get('comfort_level')
        if comfort_level and (comfort_level < 1 or comfort_level > 5):
            raise serializers.ValidationError({
                'comfort_level': 'Must be between 1 and 5'
            })
        
        return data
    
    def update(self, instance, validated_data):
        """Update membership with therapeutic checks"""
        # Update last_seen timestamp
        if 'last_seen' not in validated_data:
            validated_data['last_seen'] = timezone.now()
        
        return super().update(instance, validated_data)


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for therapeutic chat messages
    """
    user = TherapeuticUserLiteSerializer(read_only=True)
    message_type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    visibility_display = serializers.CharField(source='get_visibility_display', read_only=True)
    
    # Threading
    parent_message = serializers.UUIDField(source='parent_message.id', allow_null=True, required=False)
    replies_count = serializers.SerializerMethodField()
    is_editable = serializers.SerializerMethodField()
    is_deletable = serializers.SerializerMethodField()
    
    # Therapeutic context
    therapeutic_context = serializers.JSONField(read_only=True)
    safe_content = serializers.SerializerMethodField()
    requires_moderation_review = serializers.SerializerMethodField()
    
    # Reactions
    reactions_summary = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()
    
    # Integration fields
    learning_activity = serializers.UUIDField(source='learning_activity.id', read_only=True, allow_null=True)
    therapy_exercise = serializers.UUIDField(source='therapy_exercise.id', read_only=True, allow_null=True)
    coding_solution = serializers.UUIDField(source='coding_solution.id', read_only=True, allow_null=True)
    
    # Attachment
    attachment_url = serializers.FileField(source='attachment', read_only=True)
    attachment_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'room', 'user', 'content', 'message_type', 'message_type_display',
            'visibility', 'visibility_display', 'parent_message', 'thread_depth',
            'emotional_tone', 'trigger_warning', 'is_vulnerable_share',
            'coping_strategy_shared', 'contains_affirmation', 'therapeutic_label',
            'requires_moderation', 'moderated_by', 'moderation_notes',
            'is_flagged', 'flagged_reason', 'attachment', 'attachment_url',
            'attachment_name', 'attachment_caption', 'edited', 'edited_at',
            'deleted', 'deleted_at', 'deleted_by', 'created_at', 'updated_at',
            'scheduled_for', 'read_by_count', 'reaction_count', 'share_count',
            'helpful_votes', 'supportive_responses', 'learning_activity',
            'therapy_exercise', 'coding_solution', 'replies_count',
            'is_editable', 'is_deletable', 'therapeutic_context',
            'safe_content', 'requires_moderation_review', 'reactions_summary',
            'user_reaction'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'updated_at', 'edited', 'edited_at',
            'deleted', 'deleted_at', 'deleted_by', 'read_by_count',
            'reaction_count', 'share_count', 'helpful_votes', 'supportive_responses',
            'replies_count', 'is_editable', 'is_deletable', 'therapeutic_context',
            'safe_content', 'requires_moderation_review', 'reactions_summary',
            'user_reaction', 'attachment_url', 'attachment_name'
        ]
        extra_kwargs = {
            'content': {'write_only': True},  # Content is write-only, use safe_content for reading
            'room': {'write_only': True},
        }
    
    def get_replies_count(self, obj):
        return obj.replies.count()
    
    def get_is_editable(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Users can edit their own messages within 15 minutes
            if obj.user == request.user:
                time_since_creation = timezone.now() - obj.created_at
                return time_since_creation.total_seconds() < 900  # 15 minutes
            # Moderators can edit within 1 hour
            elif request.user in obj.room.moderators.all():
                time_since_creation = timezone.now() - obj.created_at
                return time_since_creation.total_seconds() < 3600  # 1 hour
        return False
    
    def get_is_deletable(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Users can always delete their own messages
            if obj.user == request.user:
                return True
            # Moderators can delete any message
            elif request.user in obj.room.moderators.all():
                return True
        return False
    
    def get_safe_content(self, obj):
        """Get content with therapeutic safety considerations"""
        request = self.context.get('request')
        
        # Handle deleted messages
        if obj.deleted:
            return "[Message deleted]"
        
        # Handle scheduled messages
        if obj.is_scheduled:
            return "[Scheduled message]"
        
        # Check if viewer should see content based on stress level
        if request and request.user.is_authenticated:
            user_settings = getattr(request.user, 'chat_settings', None)
            if user_settings and user_settings.hide_stressful_content:
                if request.user.current_stress_level >= 7 and obj.is_vulnerable_share:
                    return "[Content hidden due to high stress level. Take a break and return when ready.]"
        
        # Add trigger warning prefix if needed
        if obj.trigger_warning:
            return f"[Trigger Warning: {obj.trigger_warning}] {obj.content}"
        
        return obj.content
    
    def get_requires_moderation_review(self, obj):
        """Check if message needs moderation review"""
        if obj.requires_moderation and not obj.moderated_by:
            return True
        if obj.is_flagged:
            return True
        if obj.is_vulnerable_share and not obj.room.moderators.filter(id=obj.user.id).exists():
            # Vulnerable shares from non-moderators need review
            return True
        return False
    
    def get_reactions_summary(self, obj):
        """Get summary of reactions for this message"""
        from django.db.models import Count
        reactions = obj.reactions.values('reaction_type').annotate(count=Count('reaction_type'))
        return {r['reaction_type']: r['count'] for r in reactions}
    
    def get_user_reaction(self, obj):
        """Get current user's reaction to this message"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                reaction = MessageReaction.objects.get(
                    message=obj,
                    user=request.user
                )
                return reaction.reaction_type
            except MessageReaction.DoesNotExist:
                return None
        return None
    
    def get_attachment_name(self, obj):
        if obj.attachment:
            return obj.attachment.name.split('/')[-1]
        return None
    
    def validate(self, data):
        """Validate therapeutic message settings"""
        request = self.context.get('request')
        
        # Check if user is in the room
        if request and request.user.is_authenticated:
            room = data.get('room')
            if room:
                try:
                    membership = RoomMembership.objects.get(
                        user=request.user,
                        room=room,
                        is_active=True
                    )
                    
                    # Check if user is muted
                    if membership.is_muted:
                        raise serializers.ValidationError({
                            'room': 'You are muted in this room and cannot send messages'
                        })
                    
                    # Check stress level for vulnerable shares
                    if data.get('is_vulnerable_share', False):
                        if request.user.current_stress_level >= 8:
                            raise serializers.ValidationError({
                                'is_vulnerable_share': 'Your stress level is too high for vulnerable sharing. Please practice self-care first.'
                            })
                    
                except RoomMembership.DoesNotExist:
                    raise serializers.ValidationError({
                        'room': 'You are not a member of this room'
                    })
        
        # Validate trigger warnings for vulnerable shares
        if data.get('is_vulnerable_share', False) and not data.get('trigger_warning'):
            room = data.get('room')
            if room and room.trigger_warnings_required:
                raise serializers.ValidationError({
                    'trigger_warning': 'Trigger warning is required for vulnerable shares in this room'
                })
        
        # Validate content length for therapeutic messages
        content = data.get('content', '')
        if len(content) > 5000:
            raise serializers.ValidationError({
                'content': 'Message is too long (maximum 5000 characters)'
            })
        
        return data
    
    def create(self, validated_data):
        """Create message with therapeutic defaults"""
        request = self.context.get('request')
        
        # Set user from request
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        # Handle parent message
        parent_id = validated_data.pop('parent_message', {}).get('id', None)
        if parent_id:
            try:
                parent_message = ChatMessage.objects.get(id=parent_id)
                validated_data['parent_message'] = parent_message
                validated_data['thread_depth'] = parent_message.thread_depth + 1
                parent_message.is_thread_starter = True
                parent_message.save()
            except ChatMessage.DoesNotExist:
                pass
        
        # Check if message needs moderation
        room = validated_data.get('room')
        if room and room.safety_level == 'safe_space':
            if validated_data.get('is_vulnerable_share', False):
                validated_data['requires_moderation'] = True
        
        # Add therapeutic label based on content
        content = validated_data.get('content', '').lower()
        therapeutic_keywords = {
            'breakthrough': 'breakthrough',
            'coping': 'coping_strategy',
            'affirmation': 'affirmation',
            'trigger': 'trigger_discussion',
            'vulnerable': 'vulnerability'
        }
        
        for keyword, label in therapeutic_keywords.items():
            if keyword in content:
                validated_data['therapeutic_label'] = label
                break
        
        # Create the message
        message = super().create(validated_data)
        
        # Update room's updated_at timestamp
        message.room.updated_at = timezone.now()
        message.room.save()
        
        return message


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating chat messages
    Focused on therapeutic validation
    """
    is_anonymous = serializers.BooleanField(write_only=True, default=False)
    
    class Meta:
        model = ChatMessage
        fields = [
            'room', 'content', 'message_type', 'visibility',
            'parent_message', 'trigger_warning', 'is_vulnerable_share',
            'coping_strategy_shared', 'contains_affirmation',
            'emotional_tone', 'attachment', 'attachment_caption',
            'scheduled_for', 'is_anonymous'
        ]
    
    def validate(self, data):
        """Enhanced therapeutic validation"""
        request = self.context.get('request')
        
        # Check user's stress level
        if request and request.user.current_stress_level >= 9:
            raise serializers.ValidationError({
                'content': 'Your stress level is very high. Please practice self-care before engaging in chat.'
            })
        
        # Check vulnerability timeout
        if data.get('is_vulnerable_share', False):
            chat_settings = getattr(request.user, 'chat_settings', None)
            if chat_settings and chat_settings.vulnerability_timeout > 0:
                # In a real implementation, you might want to implement this check
                pass
        
        # Validate attachment size
        attachment = data.get('attachment')
        if attachment and attachment.size > 10 * 1024 * 1024:  # 10MB
            raise serializers.ValidationError({
                'attachment': 'File size must be less than 10MB'
            })
        
        return data
    
    def create(self, validated_data):
        """Create message with therapeutic context"""
        request = self.context.get('request')
        validated_data['user'] = request.user
        
        # Handle anonymous posting
        is_anonymous = validated_data.pop('is_anonymous', False)
        if is_anonymous and request.user.allow_anonymous:
            # Store anonymous flag in context for user serialization
            self.context['is_anonymous'] = True
        
        # Add therapeutic auto-detection
        content = validated_data.get('content', '').lower()
        
        # Auto-detect emotional tone (simplified example)
        emotional_keywords = {
            'proud': 'accomplished',
            'happy': 'joyful',
            'sad': 'sorrowful',
            'anxious': 'anxious',
            'calm': 'peaceful',
            'excited': 'enthusiastic',
            'frustrated': 'frustrated'
        }
        
        for keyword, tone in emotional_keywords.items():
            if keyword in content and not validated_data.get('emotional_tone'):
                validated_data['emotional_tone'] = tone
                break
        
        # Auto-detect if message contains affirmation
        affirmation_phrases = ['i am', 'i can', 'i will', 'i choose', 'i appreciate']
        if any(phrase in content for phrase in affirmation_phrases):
            validated_data['contains_affirmation'] = True
        
        return super().create(validated_data)


class MessageReactionSerializer(serializers.ModelSerializer):
    """
    Serializer for therapeutic message reactions
    """
    user = TherapeuticUserLiteSerializer(read_only=True)
    reaction_type_display = serializers.CharField(source='get_reaction_type_display', read_only=True)
    reaction_category = serializers.CharField(read_only=True)
    message_preview = serializers.CharField(source='message.safe_content_preview', read_only=True)
    
    class Meta:
        model = MessageReaction
        fields = [
            'id', 'message', 'user', 'reaction_type', 'reaction_type_display',
            'emotional_context', 'is_supportive', 'is_therapeutic',
            'is_anonymous', 'created_at', 'reaction_category', 'message_preview'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'reaction_category', 'message_preview']
    
    def validate(self, data):
        """Validate therapeutic reaction"""
        request = self.context.get('request')
        
        # Check if user can react to this message
        if request and request.user.is_authenticated:
            message = data.get('message')
            if message:
                # Check if user can see the message
                if message.visibility == 'therapist_only' and not request.user.is_therapist:
                    raise serializers.ValidationError({
                        'message': 'You cannot react to therapist-only messages'
                    })
                
                # Check if message is deleted
                if message.deleted:
                    raise serializers.ValidationError({
                        'message': 'Cannot react to deleted messages'
                    })
        
        # Validate emotional context
        emotional_context = data.get('emotional_context')
        if emotional_context and len(emotional_context) > 50:
            raise serializers.ValidationError({
                'emotional_context': 'Emotional context must be 50 characters or less'
            })
        
        return data
    
    def create(self, validated_data):
        """Create reaction with therapeutic context"""
        request = self.context.get('request')
        
        # Set user from request
        if request and request.user.is_authenticated:
            validated_data['user'] = request.user
        
        # Check for existing reaction of same type
        message = validated_data.get('message')
        reaction_type = validated_data.get('reaction_type')
        
        if request and message:
            existing = MessageReaction.objects.filter(
                message=message,
                user=request.user,
                reaction_type=reaction_type
            ).first()
            
            if existing:
                # Toggle reaction - remove if it exists
                existing.delete()
                message.reaction_count = max(0, message.reaction_count - 1)
                message.save()
                raise serializers.ValidationError({
                    'reaction_type': 'Reaction removed'
                })
        
        # Create reaction
        reaction = super().create(validated_data)
        
        # Update message reaction count
        message.reaction_count += 1
        message.save()
        
        # Check if reaction is supportive for therapeutic tracking
        if reaction.is_supportive:
            message.supportive_responses += 1
            message.save()
        
        return reaction


class ChatSessionAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for therapeutic chat analytics
    """
    user = TherapeuticUserLiteSerializer(read_only=True)
    room = ChatRoomSerializer(read_only=True)
    session_duration_minutes = serializers.FloatField(read_only=True)
    stress_change = serializers.IntegerField(read_only=True)
    therapeutic_engagement_score = serializers.FloatField(read_only=True)
    
    # Therapeutic metrics
    emotional_impact = serializers.SerializerMethodField()
    safety_metrics = serializers.SerializerMethodField()
    growth_indicators = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSessionAnalytics
        fields = [
            'id', 'user', 'room', 'session_start', 'session_end',
            'starting_stress_level', 'ending_stress_level', 'stress_change',
            'messages_sent', 'messages_received', 'reactions_given',
            'reactions_received', 'vulnerable_shares', 'coping_strategies_shared',
            'affirmations_given', 'affirmations_received', 'trigger_warnings_used',
            'safety_plan_activated', 'moderation_interventions',
            'breakthrough_moments', 'insights_gained', 'follow_up_actions',
            'session_rating', 'feedback_notes', 'created_at',
            'session_duration_minutes', 'therapeutic_engagement_score',
            'emotional_impact', 'safety_metrics', 'growth_indicators'
        ]
        read_only_fields = fields
    
    def get_emotional_impact(self, obj):
        """Calculate emotional impact metrics"""
        if obj.ending_stress_level:
            stress_reduction = obj.starting_stress_level - obj.ending_stress_level
            return {
                'stress_reduction': max(0, stress_reduction),
                'stress_increase': max(0, -stress_reduction),
                'net_emotional_change': -stress_reduction  # Negative = improvement
            }
        return None
    
    def get_safety_metrics(self, obj):
        """Calculate safety metrics"""
        return {
            'trigger_warnings_per_message': obj.trigger_warnings_used / max(1, obj.messages_sent),
            'needed_moderation': obj.moderation_interventions > 0,
            'safety_plan_used': obj.safety_plan_activated,
            'safe_environment_score': 5 - min(4, obj.moderation_interventions)  # 1-5 scale
        }
    
    def get_growth_indicators(self, obj):
        """Calculate growth indicators"""
        return {
            'vulnerability_ratio': obj.vulnerable_shares / max(1, obj.messages_sent),
            'support_provided': obj.affirmations_given + obj.coping_strategies_shared,
            'support_received': obj.affirmations_received + obj.reactions_received,
            'breakthroughs': len(obj.breakthrough_moments),
            'insights': len(obj.insights_gained)
        }


class ChatNotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for therapeutic chat notifications
    """
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    user = TherapeuticUserLiteSerializer(read_only=True)
    content_object_info = serializers.SerializerMethodField()
    should_deliver = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatNotification
        fields = [
            'id', 'user', 'notification_type', 'notification_type_display',
            'title', 'message', 'is_urgent', 'is_gentle', 'delay_until',
            'content_type', 'object_id', 'content_object_info',
            'is_read', 'read_at', 'created_at', 'delivered_at',
            'should_deliver'
        ]
        read_only_fields = [
            'id', 'user', 'created_at', 'delivered_at',
            'content_object_info', 'should_deliver'
        ]
    
    def get_content_object_info(self, obj):
        """Get info about related object"""
        if obj.content_object:
            if hasattr(obj.content_object, 'name'):
                return {'name': obj.content_object.name, 'type': obj.content_type.model}
            elif hasattr(obj.content_object, 'username'):
                return {'name': obj.content_object.username, 'type': obj.content_type.model}
        return None
    
    def get_should_deliver(self, obj):
        """Check if notification should be delivered now"""
        return obj.should_deliver_now()
    
    def validate(self, data):
        """Validate notification settings"""
        # Check gentle notification for high-stress users
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if request.user.current_stress_level >= 7 and not data.get('is_gentle', True):
                raise serializers.ValidationError({
                    'is_gentle': 'Gentle notifications required for high stress levels'
                })
        
        # Validate delay time
        delay_until = data.get('delay_until')
        if delay_until and delay_until < timezone.now():
            raise serializers.ValidationError({
                'delay_until': 'Delay time must be in the future'
            })
        
        return data


class TherapeuticChatSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for user's therapeutic chat settings
    """
    user = TherapeuticUserLiteSerializer(read_only=True)
    safe_notification_settings = serializers.JSONField(read_only=True)
    
    class Meta:
        model = TherapeuticChatSettings
        fields = [
            'id', 'user', 'auto_trigger_warnings', 'vulnerability_timeout',
            'notify_on_mention', 'notify_on_reaction', 'notify_on_breakthrough',
            'enable_emotional_tone_detection', 'enable_coping_suggestions',
            'enable_affirmation_suggestions', 'show_stress_level_in_chat',
            'allow_anonymous_posting', 'archive_chats_after_days',
            'gentle_notification_sounds', 'gentle_message_colors',
            'hide_stressful_content', 'link_chats_to_learning',
            'updated_at', 'safe_notification_settings'
        ]
        read_only_fields = ['id', 'user', 'updated_at', 'safe_notification_settings']
    
    def validate_vulnerability_timeout(self, value):
        """Validate vulnerability timeout"""
        if value < 5 or value > 300:
            raise serializers.ValidationError(
                'Vulnerability timeout must be between 5 and 300 minutes'
            )
        return value
    
    def validate_archive_chats_after_days(self, value):
        """Validate archive days"""
        if value < 1 or value > 365:
            raise serializers.ValidationError(
                'Archive days must be between 1 and 365'
            )
        return value


class ChatBulkActionSerializer(serializers.Serializer):
    """
    Serializer for bulk therapeutic chat actions
    """
    action = serializers.ChoiceField(choices=[
        ('mark_read', 'Mark as Read'),
        ('delete', 'Delete Messages'),
        ('archive', 'Archive Room'),
        ('mute', 'Mute Participants'),
        ('add_moderator', 'Add Moderator'),
        ('remove_moderator', 'Remove Moderator'),
        ('trigger_safety_check', 'Trigger Safety Check'),
        ('schedule_break', 'Schedule Break')
    ])
    
    target_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    
    room_id = serializers.UUIDField(required=False)
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
    
    parameters = serializers.JSONField(required=False)
    
    def validate(self, data):
        """Validate bulk action parameters"""
        action = data.get('action')
        
        # Validate required fields based on action
        if action in ['mark_read', 'delete'] and not data.get('target_ids'):
            raise serializers.ValidationError({
                'target_ids': f'This field is required for {action} action'
            })
        
        if action in ['archive', 'trigger_safety_check', 'schedule_break'] and not data.get('room_id'):
            raise serializers.ValidationError({
                'room_id': f'This field is required for {action} action'
            })
        
        if action in ['mute', 'add_moderator', 'remove_moderator'] and not data.get('user_ids'):
            raise serializers.ValidationError({
                'user_ids': f'This field is required for {action} action'
            })
        
        return data


class TherapeuticInsightSerializer(serializers.Serializer):
    """
    Serializer for therapeutic insights generated from chat analysis
    """
    insight_type = serializers.ChoiceField(choices=[
        ('emotional_pattern', 'Emotional Pattern'),
        ('growth_moment', 'Growth Moment'),
        ('support_network', 'Support Network'),
        ('coping_strategy', 'Coping Strategy'),
        ('trigger_awareness', 'Trigger Awareness'),
        ('communication_style', 'Communication Style')
    ])
    
    title = serializers.CharField(max_length=200)
    description = serializers.CharField()
    evidence = serializers.ListField(child=serializers.CharField())
    confidence = serializers.FloatField(min_value=0, max_value=1)
    suggested_actions = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    related_messages = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    timestamp = serializers.DateTimeField(default=timezone.now)
    
    def validate_confidence(self, value):
        """Validate confidence score"""
        if value < 0.3:
            raise serializers.ValidationError('Confidence too low for therapeutic insight')
        return value


class ChatExportSerializer(serializers.ModelSerializer):
    """
    Serializer for exporting therapeutic chat data
    """
    room_name = serializers.CharField(source='room.name', read_only=True)
    room_type = serializers.CharField(source='room.room_type', read_only=True)
    user_display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'content', 'message_type', 'emotional_tone',
            'trigger_warning', 'is_vulnerable_share',
            'coping_strategy_shared', 'contains_affirmation',
            'created_at', 'room_name', 'room_type', 'user_display_name'
        ]
    
    def get_user_display_name(self, obj):
        """Get display name for export (respects anonymity)"""
        if obj.visibility == 'anonymous' and obj.user.allow_anonymous:
            return "Anonymous User"
        return obj.user.username