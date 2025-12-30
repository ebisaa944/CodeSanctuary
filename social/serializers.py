# social/serializers.py
"""
Serializers for therapeutic social app
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    GentleInteraction, Achievement, UserAchievement,
    SupportCircle, CircleMembership
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model
    """
    avatar_color = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar_color']
        read_only_fields = ['id', 'username', 'avatar_color']
    
    def get_avatar_color(self, obj):
        # Generate consistent color from username
        import hashlib
        if obj.username:
            hash_obj = hashlib.md5(obj.username.encode())
            hex_dig = hash_obj.hexdigest()[:6]
            return f'#{hex_dig}'
        return '#000000'


class GentleInteractionSerializer(serializers.ModelSerializer):
    """
    Serializer for GentleInteraction model
    """
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    parent_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = GentleInteraction
        fields = [
            'id', 'sender', 'recipient', 'title', 'message',
            'interaction_type', 'therapeutic_intent', 'therapeutic_impact_score',
            'visibility', 'allow_replies', 'is_pinned', 'anonymous',
            'likes_count', 'views_count', 'expires_at', 'created_at',
            'updated_at', 'parent_id'
        ]
        read_only_fields = [
            'id', 'sender', 'therapeutic_impact_score', 'likes_count',
            'views_count', 'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        # Remove parent_id from validated_data
        validated_data.pop('parent_id', None)
        
        # Set sender to current user
        validated_data['sender'] = self.context['request'].user
        
        # Calculate therapeutic impact score
        message = validated_data.get('message', '')
        validated_data['therapeutic_impact_score'] = self._calculate_score(message)
        
        return super().create(validated_data)
    
    def _calculate_score(self, message):
        """Calculate therapeutic impact score"""
        positive_words = ['support', 'encourage', 'progress', 'growth', 'heal', 'hope']
        score = 50  # Base score
        
        message_lower = message.lower()
        for word in positive_words:
            if word in message_lower:
                score += 5
        
        return min(score, 100)


class GentleEncouragementSerializer(serializers.Serializer):
    """
    Serializer for quick encouragement
    """
    message = serializers.CharField(max_length=500)
    recipient_id = serializers.IntegerField(required=False)
    anonymous = serializers.BooleanField(default=False)
    
    def validate_message(self, value):
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Message is too short.")
        return value.strip()


class AchievementSerializer(serializers.ModelSerializer):
    """
    Serializer for Achievement model
    """
    tier_display = serializers.CharField(source='get_tier_display', read_only=True)
    
    class Meta:
        model = Achievement
        fields = [
            'id', 'name', 'description', 'tier', 'tier_display',
            'icon_name', 'criteria', 'is_active', 'total_earners',
            'created_at'
        ]
        read_only_fields = ['id', 'total_earners', 'created_at']


class UserAchievementSerializer(serializers.ModelSerializer):
    """
    Serializer for UserAchievement model
    """
    achievement = AchievementSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserAchievement
        fields = [
            'id', 'user', 'achievement', 'reflection_notes',
            'shared_publicly', 'earned_at'
        ]
        read_only_fields = ['id', 'user', 'achievement', 'earned_at']


class CircleMembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for CircleMembership model
    """
    user = UserSerializer(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = CircleMembership
        fields = [
            'id', 'circle', 'user', 'role', 'role_display',
            'notification_preferences', 'introduction', 'joined_at'
        ]
        read_only_fields = ['id', 'user', 'joined_at']


class SupportCircleSerializer(serializers.ModelSerializer):
    """
    Serializer for SupportCircle model
    """
    created_by = UserSerializer(read_only=True)
    memberships = CircleMembershipSerializer(many=True, read_only=True)
    
    class Meta:
        model = SupportCircle
        fields = [
            'id', 'name', 'description', 'focus_areas',
            'created_by', 'is_public', 'allow_anonymous',
            'active_members', 'max_members', 'total_interactions',
            'join_code', 'created_at', 'updated_at', 'memberships'
        ]
        read_only_fields = [
            'id', 'created_by', 'active_members', 'total_interactions',
            'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        # Set created_by to current user
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class CommunityStatsSerializer(serializers.Serializer):
    """
    Serializer for community statistics
    """
    total_members = serializers.IntegerField()
    active_today = serializers.IntegerField()
    total_interactions = serializers.IntegerField()
    total_encouragements = serializers.IntegerField()
    support_circles = serializers.IntegerField()
    achievements_earned = serializers.IntegerField()
    avg_therapeutic_score = serializers.FloatField()
    engagement_rate = serializers.FloatField()
    positivity_score = serializers.FloatField()
    calculated_at = serializers.DateTimeField()