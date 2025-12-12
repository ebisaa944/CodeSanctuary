from rest_framework import serializers
from .models import EmotionalCheckIn, CopingStrategy
from django.utils import timezone

class EmotionalCheckInSerializer(serializers.ModelSerializer):
    """Serializer for emotional checkins with therapeutic validation"""
    
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    emotional_summary = serializers.ReadOnlyField()
    suggested_strategies = serializers.SerializerMethodField()
    
    class Meta:
        model = EmotionalCheckIn
        fields = [
            'id', 'user', 'primary_emotion', 'secondary_emotions',
            'intensity', 'physical_symptoms', 'trigger_description',
            'context_tags', 'coping_strategies_used', 'coping_effectiveness',
            'notes', 'key_insight', 'created_at', 'emotional_summary',
            'suggested_strategies'
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'intensity': {'min_value': 1, 'max_value': 10},
            'coping_effectiveness': {'min_value': 1, 'max_value': 10}
        }
    
    def validate(self, data):
        """Apply therapeutic validation rules"""
        # Check for duplicate recent checkins
        user = data.get('user') or self.context['request'].user
        recent_checkins = EmotionalCheckIn.objects.filter(
            user=user,
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        ).count()
        
        if recent_checkins >= 3:
            raise serializers.ValidationError(
                "Take a gentle break between checkins. You've checked in 3 times in the last hour."
            )
        
        # Validate coping effectiveness if strategies used
        if data.get('coping_strategies_used') and 'coping_effectiveness' not in data:
            raise serializers.ValidationError(
                "Please rate the effectiveness of your coping strategies"
            )
        
        return data
    
    def get_suggested_strategies(self, obj):
        """Get coping strategies suggested for this emotional state"""
        return obj.suggest_coping_strategies()


class CopingStrategySerializer(serializers.ModelSerializer):
    """Serializer for coping strategies"""
    
    is_recommended = serializers.SerializerMethodField()
    estimated_duration_display = serializers.SerializerMethodField()
    
    class Meta:
        model = CopingStrategy
        fields = [
            'id', 'name', 'description', 'strategy_type',
            'target_emotions', 'estimated_minutes', 'estimated_duration_display',
            'difficulty_level', 'coding_integration', 'coding_language',
            'coding_template', 'instructions', 'tips_for_success',
            'common_challenges', 'is_recommended', 'created_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_is_recommended(self, obj):
        """Check if strategy is recommended for current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_recommended_for_user(request.user)
        return True
    
    def get_estimated_duration_display(self, obj):
        """Get human-readable duration"""
        if obj.estimated_minutes < 2:
            return "Less than 2 minutes"
        elif obj.estimated_minutes < 5:
            return "2-5 minutes"
        elif obj.estimated_minutes < 10:
            return "5-10 minutes"
        else:
            return f"{obj.estimated_minutes} minutes"


class EmotionalPatternSerializer(serializers.Serializer):
    """Serializer for emotional pattern analysis"""
    
    dominant_emotion = serializers.CharField()
    average_intensity = serializers.FloatField()
    volatility = serializers.FloatField()
    common_triggers = serializers.DictField()
    pattern_trend = serializers.CharField()
    recommendation = serializers.CharField()
    
    class Meta:
        fields = [
            'dominant_emotion', 'average_intensity', 'volatility',
            'common_triggers', 'pattern_trend', 'recommendation'
        ]


class QuickCheckInSerializer(serializers.Serializer):
    """Serializer for quick emotional checkins"""
    
    emotion = serializers.ChoiceField(choices=EmotionalCheckIn.PrimaryEmotion.choices)
    intensity = serializers.IntegerField(min_value=1, max_value=5)
    
    def create(self, validated_data):
        """Create a quick checkin"""
        request = self.context['request']
        return EmotionalCheckIn.objects.create(
            user=request.user,
            primary_emotion=validated_data['emotion'],
            intensity=validated_data['intensity'],
            created_at=timezone.now()
        )


class CopingStrategyRecommendationSerializer(serializers.Serializer):
    """Serializer for coping strategy recommendations"""
    
    emotion = serializers.CharField()
    strategies = CopingStrategySerializer(many=True)
    best_fit = CopingStrategySerializer()
    why_recommended = serializers.CharField()


class EmotionalHistorySerializer(serializers.ModelSerializer):
    """Serializer for emotional history with trends"""
    
    day_of_week = serializers.SerializerMethodField()
    time_of_day = serializers.SerializerMethodField()
    
    class Meta:
        model = EmotionalCheckIn
        fields = [
            'id', 'primary_emotion', 'intensity',
            'created_at', 'day_of_week', 'time_of_day'
        ]
    
    def get_day_of_week(self, obj):
        return obj.created_at.strftime('%A')
    
    def get_time_of_day(self, obj):
        hour = obj.created_at.hour
        if hour < 12:
            return 'Morning'
        elif hour < 17:
            return 'Afternoon'
        elif hour < 21:
            return 'Evening'
        else:
            return 'Night'