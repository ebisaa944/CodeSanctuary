from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import TherapeuticUser
from django.core.exceptions import ValidationError
from therapy.models import EmotionalCheckIn  # Fixed import

# Fix the import - change from "apps.therapy.models" to "therapy.models"
try:
    from therapy.models import EmotionalCheckIn
    THERAPY_APP_READY = True
except ImportError:
    # Therapy app not ready yet
    THERAPY_APP_READY = False
    EmotionalCheckIn = None

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration with therapeutic defaults"""
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    class Meta:
        model = TherapeuticUser
        fields = [
            'id', 'username', 'email', 'password', 'confirm_password',
            'emotional_profile', 'daily_time_limit', 'gentle_mode'
        ]
        extra_kwargs = {
            'emotional_profile': {'default': 'balanced'},
            'gentle_mode': {'default': True},
            'daily_time_limit': {'default': 30}
        }
    
    def validate(self, data):
        """Validate password match and therapeutic constraints"""
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError("Passwords do not match")
        
        # Ensure gentle mode for certain emotional profiles
        if data.get('emotional_profile') in ['anxious', 'overwhelmed']:
            data['gentle_mode'] = True
        
        return data
    
    def create(self, validated_data):
        """Create user with therapeutic defaults"""
        user = TherapeuticUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            emotional_profile=validated_data.get('emotional_profile', 'balanced'),
            gentle_mode=validated_data.get('gentle_mode', True),
            daily_time_limit=validated_data.get('daily_time_limit', 30)
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login with therapeutic consideration"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        """Validate credentials and check user's therapeutic state"""
        user = authenticate(username=data['username'], password=data['password'])
        
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled")
        
        # Add therapeutic context
        data['user'] = user
        data['therapeutic_context'] = {
            'stress_level': user.current_stress_level,
            'gentle_mode': user.gentle_mode,
            'safe_plan': user.get_safe_learning_plan()
        }
        
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile with therapeutic data"""
    learning_streak_badge = serializers.CharField(read_only=True)
    therapeutic_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = TherapeuticUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'emotional_profile', 'learning_style', 'daily_time_limit',
            'gentle_mode', 'hide_progress', 'allow_anonymous',
            'current_stress_level', 'total_learning_minutes',
            'consecutive_days', 'learning_streak_badge',
            'avatar_color', 'custom_affirmation',
            'therapy_start_date', 'therapeutic_summary'
        ]
        read_only_fields = [
            'total_learning_minutes', 'consecutive_days',
            'therapy_start_date', 'learning_streak_badge'
        ]
    
    def get_therapeutic_summary(self, obj):
        """Get therapeutic summary for user"""
        return {
            'safe_learning_plan': obj.get_safe_learning_plan(),
            'breakthrough_count': len(obj.breakthrough_moments),
            'current_streak': obj.consecutive_days,
            'avg_stress_last_week': self._calculate_avg_stress(obj)
        }
    
    def _calculate_avg_stress(self, user):
        """Calculate average stress from recent checkins"""
        # Check if therapy app is ready
        if not THERAPY_APP_READY or not EmotionalCheckIn:
            return user.current_stress_level
        
        from django.utils import timezone
        from django.db.models import Avg
        
        week_ago = timezone.now() - timezone.timedelta(days=7)
        avg_stress = EmotionalCheckIn.objects.filter(
            user=user,
            created_at__gte=week_ago
        ).aggregate(avg=Avg('intensity'))['avg']
        
        return round(avg_stress, 1) if avg_stress else user.current_stress_level


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user with therapeutic validation"""
    class Meta:
        model = TherapeuticUser
        fields = [
            'email', 'first_name', 'last_name',
            'emotional_profile', 'learning_style',
            'daily_time_limit', 'gentle_mode',
            'hide_progress', 'allow_anonymous',
            'avatar_color', 'custom_affirmation',
            'preferred_learning_hours'
        ]
    
    def validate_daily_time_limit(self, value):
        """Ensure time limit is within therapeutic bounds"""
        if value < 5:
            raise serializers.ValidationError("Minimum 5 minutes per day")
        if value > 180:
            raise serializers.ValidationError("Maximum 180 minutes per day")
        return value
    
    def validate(self, data):
        """Apply therapeutic rules"""
        # Force gentle mode for high-stress profiles
        if data.get('emotional_profile') in ['anxious', 'overwhelmed']:
            data['gentle_mode'] = True
        
        # Adjust time limits based on stress
        if 'current_stress_level' in data and data['current_stress_level'] > 7:
            if 'daily_time_limit' in data and data['daily_time_limit'] > 30:
                data['daily_time_limit'] = 30
        
        return data


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal user serializer for public/community views"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = TherapeuticUser
        fields = ['id', 'display_name', 'avatar_color']
        read_only = True
    
    def get_display_name(self, obj):
        """Get safe display name respecting privacy"""
        if obj.hide_progress and not self.context.get('is_self', False):
            return "Anonymous Learner"
        return obj.username


class TherapeuticStatsSerializer(serializers.Serializer):
    """Serializer for therapeutic statistics"""
    total_users = serializers.IntegerField()
    average_stress = serializers.FloatField()
    active_today = serializers.IntegerField()
    common_profiles = serializers.DictField()
    avg_daily_minutes = serializers.FloatField()