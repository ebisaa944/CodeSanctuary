from rest_framework import serializers
from .models import LearningPath, MicroActivity, UserProgress
from django.utils import timezone
from django.core.exceptions import ValidationError

class LearningPathSerializer(serializers.ModelSerializer):
    """Serializer for learning paths"""
    
    progress = serializers.SerializerMethodField()
    is_suitable = serializers.SerializerMethodField()
    estimated_completion = serializers.SerializerMethodField()
    
    class Meta:
        model = LearningPath
        fields = [
            'id', 'name', 'slug', 'description', 'difficulty_level',
            'target_language', 'recommended_for_profiles',
            'estimated_total_hours', 'max_daily_minutes',
            'modules', 'is_active', 'progress', 'is_suitable',
            'estimated_completion', 'created_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']
    
    def get_progress(self, obj):
        """Get user's progress through this path"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.get_progress_for_user(request.user)
        return None
    
    def get_is_suitable(self, obj):
        """Check if path is suitable for current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user_profile = request.user.emotional_profile
            return user_profile in obj.recommended_for_profiles
        return True
    
    def get_estimated_completion(self, obj):
        """Estimate completion time based on user's pace"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user_limit = request.user.daily_time_limit
            total_minutes = obj.estimated_total_hours * 60
            return total_minutes / user_limit if user_limit > 0 else None
        return None


class MicroActivitySerializer(serializers.ModelSerializer):
    """Serializer for micro activities"""
    
    therapeutic_context = serializers.SerializerMethodField()
    is_suitable = serializers.SerializerMethodField()
    user_progress = serializers.SerializerMethodField()
    
    class Meta:
        model = MicroActivity
        fields = [
            'id', 'title', 'slug', 'short_description', 'full_description',
            'activity_type', 'therapeutic_focus', 'difficulty_level',
            'primary_language', 'tech_stack', 'estimated_minutes',
            'no_time_limit', 'infinite_retries', 'skip_allowed',
            'gentle_feedback', 'learning_objectives', 'prerequisites',
            'starter_code', 'solution_code', 'test_cases', 'validation_type',
            'video_url', 'documentation_url', 'additional_resources',
            'therapeutic_instructions', 'coping_suggestions',
            'success_affirmations', 'learning_path', 'order_position',
            'therapeutic_context', 'is_suitable', 'user_progress',
            'is_published', 'created_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']
    
    def get_therapeutic_context(self, obj):
        """Get therapeutic context for this activity"""
        return obj.get_therapeutic_context()
    
    def get_is_suitable(self, obj):
        """Check if activity is suitable for current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            suitable, message = obj.is_suitable_for_user(request.user)
            return {
                'suitable': suitable,
                'message': message
            }
        return {'suitable': True, 'message': ''}
    
    def get_user_progress(self, obj):
        """Get user's progress on this activity"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                progress = UserProgress.objects.get(
                    user=request.user,
                    activity=obj
                )
                return UserProgressSerializer(progress).data
            except UserProgress.DoesNotExist:
                return None
        return None
    
    def validate_difficulty_level(self, value):
        """Validate difficulty level"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Difficulty must be between 1 and 5")
        return value
    
    def validate_estimated_minutes(self, value):
        """Validate estimated minutes"""
        if value < 1:
            raise serializers.ValidationError("Minimum 1 minute")
        if value > 60:
            raise serializers.ValidationError("Maximum 60 minutes")
        return value


class ActivitySubmissionSerializer(serializers.Serializer):
    """Serializer for submitting activity solutions"""
    
    code = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Your solution code"
    )
    
    emotional_state_before = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="How you felt before starting"
    )
    
    emotional_state_after = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="How you feel now"
    )
    
    stress_level_before = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=10,
        help_text="Stress level before (1-10)"
    )
    
    stress_level_after = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=10,
        help_text="Stress level after (1-10)"
    )
    
    confidence_before = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=5,
        help_text="Confidence before (1-5)"
    )
    
    confidence_after = serializers.IntegerField(
        required=False,
        min_value=1,
        max_value=5,
        help_text="Confidence after (1-5)"
    )
    
    reflection_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Any reflections on the experience"
    )
    
    what_went_well = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="What went well during the activity"
    )
    
    challenges_faced = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Challenges you faced"
    )
    
    coping_strategies_used = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Coping strategies you used"
    )
    
    def validate(self, data):
        """Validate submission data"""
        # Check emotional consistency
        if 'stress_level_before' in data and 'stress_level_after' in data:
            if data['stress_level_after'] > 10 or data['stress_level_before'] > 10:
                raise serializers.ValidationError("Stress levels must be 1-10")
        
        return data


class UserProgressSerializer(serializers.ModelSerializer):
    """Serializer for user progress"""
    
    activity_title = serializers.CharField(source='activity.title', read_only=True)
    activity_difficulty = serializers.IntegerField(source='activity.difficulty_level', read_only=True)
    emotional_impact = serializers.SerializerMethodField()
    is_breakthrough = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = UserProgress
        fields = [
            'id', 'user', 'activity', 'activity_title', 'activity_difficulty',
            'status', 'start_time', 'completion_time', 'time_spent_seconds',
            'attempts', 'successful_attempts', 'submitted_code', 'code_output',
            'errors', 'emotional_state_before', 'emotional_state_after',
            'stress_level_before', 'stress_level_after',
            'confidence_before', 'confidence_after', 'self_assessment',
            'reflection_notes', 'what_went_well', 'challenges_faced',
            'coping_strategies_used', 'code_quality_score', 'efficiency_score',
            'breakthrough_notes', 'therapist_feedback', 'emotional_impact',
            'is_breakthrough', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_emotional_impact(self, obj):
        """Calculate emotional impact"""
        return obj.calculate_emotional_impact()
    
    def validate_self_assessment(self, value):
        """Validate self assessment"""
        if value and (value < 1 or value > 5):
            raise serializers.ValidationError("Self assessment must be 1-5")
        return value


class GentleRecommendationSerializer(serializers.Serializer):
    """Serializer for gentle activity recommendations"""
    
    activity = MicroActivitySerializer()
    reason = serializers.CharField()
    therapeutic_benefit = serializers.CharField()
    estimated_time = serializers.IntegerField()
    preparation_tip = serializers.CharField()
    
    class Meta:
        fields = [
            'activity', 'reason', 'therapeutic_benefit',
            'estimated_time', 'preparation_tip'
        ]


class LearningStatsSerializer(serializers.Serializer):
    """Serializer for learning statistics"""
    
    total_activities_completed = serializers.IntegerField()
    total_time_spent = serializers.IntegerField()
    average_difficulty = serializers.FloatField()
    favorite_language = serializers.CharField()
    emotional_trend = serializers.CharField()
    breakthrough_count = serializers.IntegerField()
    current_streak = serializers.IntegerField()
    
    class Meta:
        fields = [
            'total_activities_completed', 'total_time_spent',
            'average_difficulty', 'favorite_language',
            'emotional_trend', 'breakthrough_count',
            'current_streak'
        ]