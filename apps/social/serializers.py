from rest_framework import serializers
from .models import GentleInteraction, Achievement, UserAchievement, SupportCircle, CircleMembership
from django.utils import timezone
from django.core.exceptions import ValidationError

class GentleInteractionSerializer(serializers.ModelSerializer):
    """Serializer for gentle interactions"""
    
    display_name = serializers.CharField(source='display_name', read_only=True)
    therapeutic_impact_score = serializers.IntegerField(read_only=True)
    can_user_see = serializers.SerializerMethodField()
    reply_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = GentleInteraction
        fields = [
            'id', 'uuid', 'interaction_type', 'sender', 'recipient',
            'title', 'message', 'display_name', 'visibility',
            'is_pinned', 'allow_replies', 'therapeutic_intent',
            'expected_response_time', 'likes_count', 'replies_count',
            'shares_count', 'is_moderated', 'therapeutic_impact_score',
            'can_user_see', 'reply_preview', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uuid', 'likes_count', 'replies_count', 'shares_count',
            'is_moderated', 'created_at', 'updated_at'
        ]
    
    def get_can_user_see(self, obj):
        """Check if current user can see this interaction"""
        request = self.context.get('request')
        if request:
            return obj.can_user_see(request.user)
        return False
    
    def get_reply_preview(self, obj):
        """Get preview of recent replies"""
        replies = GentleInteraction.objects.filter(
            interaction_type='reflection',
            created_at__gt=obj.created_at
        )[:3]
        return [
            {
                'display_name': reply.display_name,
                'message_preview': reply.message[:50] + '...' if len(reply.message) > 50 else reply.message,
                'created_at': reply.created_at
            }
            for reply in replies
        ]
    
    def validate(self, data):
        """Apply therapeutic validation"""
        request = self.context.get('request')
        
        # Check for excessive posting
        if request and request.user.is_authenticated:
            today = timezone.now().date()
            today_posts = GentleInteraction.objects.filter(
                sender=request.user,
                created_at__date=today
            ).count()
            
            if today_posts >= 10:
                raise ValidationError(
                    "Gentle reminder: You've posted 10 times today. Consider taking a break."
                )
        
        # Validate visibility rules
        visibility = data.get('visibility', 'anonymous')
        sender = data.get('sender') or (request.user if request else None)
        
        if visibility == 'anonymous' and sender:
            data['sender'] = None  # Anonymous posts have no sender
        
        return data
    
    def create(self, validated_data):
        """Create interaction with therapeutic defaults"""
        request = self.context.get('request')
        
        if request and request.user.is_authenticated:
            # Set sender if not anonymous
            if validated_data.get('visibility') != 'anonymous':
                validated_data['sender'] = request.user
        
        return super().create(validated_data)


class AchievementSerializer(serializers.ModelSerializer):
    """Serializer for achievements"""
    
    earned_by_count = serializers.SerializerMethodField()
    recently_earned = serializers.SerializerMethodField()
    
    class Meta:
        model = Achievement
        fields = [
            'id', 'name', 'description', 'tier', 'icon_name', 'color',
            'requirement_type', 'requirement_value', 'requirement_data',
            'therapeutic_message', 'reflection_prompt', 'earned_by_count',
            'recently_earned', 'is_active', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_earned_by_count(self, obj):
        """Count how many users have earned this achievement"""
        return obj.user_achievements.count()
    
    def get_recently_earned(self, obj):
        """Get recent earners"""
        recent = obj.user_achievements.order_by('-earned_at')[:3]
        return [
            {
                'user': achievement.user.username,
                'earned_at': achievement.earned_at
            }
            for achievement in recent
        ]


class UserAchievementSerializer(serializers.ModelSerializer):
    """Serializer for user achievements"""
    
    achievement_details = AchievementSerializer(source='achievement', read_only=True)
    user_display_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = UserAchievement
        fields = [
            'id', 'user', 'user_display_name', 'achievement', 'achievement_details',
            'earned_at', 'context_data', 'shared_publicly', 'reflection_notes'
        ]
        read_only_fields = ['earned_at']
    
    def validate(self, data):
        """Validate achievement earning"""
        achievement = data.get('achievement')
        user = data.get('user')
        
        if achievement and user:
            # Check if user already has this achievement
            if UserAchievement.objects.filter(
                user=user,
                achievement=achievement
            ).exists():
                raise ValidationError("User has already earned this achievement")
            
            # Check if achievement requirements are met
            if not achievement.check_achievement(user):
                raise ValidationError("Achievement requirements not met")
        
        return data


class SupportCircleSerializer(serializers.ModelSerializer):
    """Serializer for support circles"""
    
    member_count = serializers.IntegerField(source='active_members', read_only=True)
    is_member = serializers.SerializerMethodField()
    can_join = serializers.SerializerMethodField()
    recent_activity = serializers.SerializerMethodField()
    
    class Meta:
        model = SupportCircle
        fields = [
            'id', 'name', 'description', 'max_members', 'is_public',
            'join_code', 'focus_areas', 'community_guidelines',
            'meeting_schedule', 'total_interactions', 'member_count',
            'created_by', 'is_member', 'can_join', 'recent_activity',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'total_interactions', 'active_members', 'created_at', 'updated_at'
        ]
    
    def get_is_member(self, obj):
        """Check if current user is a member"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.memberships.filter(user=request.user).exists()
        return False
    
    def get_can_join(self, obj):
        """Check if current user can join"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        # Check if circle is full
        if obj.active_members >= obj.max_members:
            return False
        
        # Check if already a member
        if self.get_is_member(obj):
            return False
        
        return True
    
    def get_recent_activity(self, obj):
        """Get recent circle activity"""
        from .models import GentleInteraction
        
        recent = GentleInteraction.objects.filter(
            visibility__in=['public', 'community'],
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).order_by('-created_at')[:5]
        
        return [
            {
                'type': interaction.interaction_type,
                'preview': interaction.message[:100],
                'created_at': interaction.created_at
            }
            for interaction in recent
        ]
    
    def validate(self, data):
        """Validate circle creation"""
        max_members = data.get('max_members', 10)
        
        if max_members < 3:
            raise ValidationError("Support circles need at least 3 members")
        if max_members > 50:
            raise ValidationError("Support circles work best with 50 or fewer members")
        
        return data


class CircleMembershipSerializer(serializers.ModelSerializer):
    """Serializer for circle memberships"""
    
    user_info = serializers.SerializerMethodField()
    circle_info = serializers.SerializerMethodField()
    
    class Meta:
        model = CircleMembership
        fields = [
            'id', 'circle', 'circle_info', 'user', 'user_info', 'role',
            'joined_at', 'last_active', 'support_given', 'support_received',
            'notification_preferences'
        ]
        read_only_fields = ['joined_at', 'last_active']
    
    def get_user_info(self, obj):
        """Get user info respecting privacy"""
        if obj.user.hide_progress:
            return {
                'id': obj.user.id,
                'display_name': 'Anonymous Member',
                'avatar_color': obj.user.avatar_color
            }
        
        return {
            'id': obj.user.id,
            'username': obj.user.username,
            'avatar_color': obj.user.avatar_color,
            'emotional_profile': obj.user.emotional_profile
        }
    
    def get_circle_info(self, obj):
        """Get circle info"""
        return {
            'id': obj.circle.id,
            'name': obj.circle.name,
            'focus_areas': obj.circle.focus_areas
        }
    
    def validate(self, data):
        """Validate membership"""
        circle = data.get('circle')
        user = data.get('user')
        
        if circle and user:
            # Check if circle is full
            if circle.active_members >= circle.max_members:
                raise ValidationError("Support circle is full")
            
            # Check if already a member
            if CircleMembership.objects.filter(circle=circle, user=user).exists():
                raise ValidationError("User is already a member of this circle")
        
        return data


class GentleEncouragementSerializer(serializers.Serializer):
    """Serializer for sending gentle encouragement"""
    
    recipient_id = serializers.IntegerField(required=False)
    message = serializers.CharField(max_length=500)
    anonymous = serializers.BooleanField(default=True)
    
    def validate(self, data):
        """Validate encouragement"""
        recipient_id = data.get('recipient_id')
        
        if recipient_id:
            from apps.users.models import TherapeuticUser
            try:
                recipient = TherapeuticUser.objects.get(id=recipient_id)
                if recipient.hide_progress:
                    raise ValidationError("Cannot send to private users")
            except TherapeuticUser.DoesNotExist:
                raise ValidationError("Recipient not found")
        
        # Check message tone
        message = data.get('message', '').lower()
        negative_words = ['stupid', 'idiot', 'failure', 'worthless']
        
        for word in negative_words:
            if word in message:
                raise ValidationError(
                    "Please use gentle, encouraging language"
                )
        
        return data


class CommunityStatsSerializer(serializers.Serializer):
    """Serializer for community statistics"""
    
    total_members = serializers.IntegerField()
    active_today = serializers.IntegerField()
    total_encouragements = serializers.IntegerField()
    average_stress = serializers.FloatField()
    support_circles = serializers.IntegerField()
    achievements_earned = serializers.IntegerField()
    
    class Meta:
        fields = [
            'total_members', 'active_today', 'total_encouragements',
            'average_stress', 'support_circles', 'achievements_earned'
        ]