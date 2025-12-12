from django_filters import rest_framework as filters
from .models import MicroActivity, LearningPath, UserProgress
from django.utils import timezone

class MicroActivityFilter(filters.FilterSet):
    """Filters for micro activities with therapeutic considerations"""
    
    difficulty = filters.ChoiceFilter(
        field_name='difficulty_level',
        choices=[(i, f"Level {i}") for i in range(1, 6)],
        label='Difficulty Level'
    )
    
    duration = filters.RangeFilter(
        field_name='estimated_minutes',
        label='Duration (minutes)'
    )
    
    therapeutic_focus = filters.ChoiceFilter(
        field_name='therapeutic_focus',
        choices=MicroActivity.TherapeuticFocus.choices
    )
    
    activity_type = filters.ChoiceFilter(
        field_name='activity_type',
        choices=MicroActivity.ActivityType.choices
    )
    
    language = filters.ChoiceFilter(
        field_name='primary_language',
        label='Programming Language'
    )
    
    has_video = filters.BooleanFilter(
        field_name='video_url',
        method='filter_has_video',
        label='Has video tutorial'
    )
    
    has_starter_code = filters.BooleanFilter(
        field_name='starter_code',
        method='filter_has_starter',
        label='Has starter code'
    )
    
    class Meta:
        model = MicroActivity
        fields = {
            'difficulty_level': ['exact', 'lt', 'gt'],
            'estimated_minutes': ['lt', 'gt'],
            'therapeutic_focus': ['exact'],
            'activity_type': ['exact'],
            'primary_language': ['exact'],
            'learning_path': ['exact']
        }
    
    def filter_has_video(self, queryset, name, value):
        """Filter by presence of video"""
        if value:
            return queryset.exclude(video_url='')
        return queryset.filter(video_url='')
    
    def filter_has_starter(self, queryset, name, value):
        """Filter by presence of starter code"""
        if value:
            return queryset.exclude(starter_code='')
        return queryset.filter(starter_code='')
    
    @property
    def qs(self):
        """Apply therapeutic filtering"""
        queryset = super().qs
        
        # Only show published activities
        queryset = queryset.filter(is_published=True)
        
        # Apply user's therapeutic restrictions
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'get_safe_learning_plan'):
            plan = user.get_safe_learning_plan()
            max_difficulty = plan.get('max_difficulty', 3)
            queryset = queryset.filter(difficulty_level__lte=max_difficulty)
        
        return queryset


class LearningPathFilter(filters.FilterSet):
    """Filters for learning paths"""
    
    difficulty = filters.ChoiceFilter(
        field_name='difficulty_level',
        choices=LearningPath.PathDifficulty.choices,
        label='Path Difficulty'
    )
    
    target_language = filters.ChoiceFilter(
        field_name='target_language',
        choices=LearningPath._meta.get_field('target_language').choices
    )
    
    recommended_for = filters.CharFilter(
        field_name='recommended_for_profiles',
        lookup_expr='contains',
        label='Recommended for profile'
    )
    
    estimated_time = filters.RangeFilter(
        field_name='estimated_total_hours',
        label='Estimated Time (hours)'
    )
    
    is_active = filters.BooleanFilter(field_name='is_active')
    
    class Meta:
        model = LearningPath
        fields = {
            'difficulty_level': ['exact'],
            'target_language': ['exact'],
            'estimated_total_hours': ['lt', 'gt'],
            'max_daily_minutes': ['lt', 'gt']
        }
    
    @property
    def qs(self):
        """Apply therapeutic filtering"""
        queryset = super().qs
        
        # Only show active paths
        queryset = queryset.filter(is_active=True)
        
        # Filter by user's emotional profile
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'emotional_profile'):
            profile = user.emotional_profile
            queryset = queryset.filter(
                recommended_for_profiles__contains=[profile]
            )
        
        return queryset


class UserProgressFilter(filters.FilterSet):
    """Filters for user progress"""
    
    status = filters.ChoiceFilter(
        field_name='status',
        choices=UserProgress.ProgressStatus.choices
    )
    
    date_range = filters.DateFromToRangeFilter(
        field_name='completion_time',
        label='Completion Date Range'
    )
    
    activity_difficulty = filters.RangeFilter(
        field_name='activity__difficulty_level',
        label='Activity Difficulty'
    )
    
    time_spent = filters.RangeFilter(
        field_name='time_spent_seconds',
        label='Time Spent (seconds)'
    )
    
    has_breakthrough = filters.BooleanFilter(
        field_name='breakthrough_notes',
        method='filter_has_breakthrough',
        label='Has breakthrough notes'
    )
    
    emotional_impact = filters.ChoiceFilter(
        method='filter_emotional_impact',
        choices=[
            ('positive', 'Positive Impact'),
            ('neutral', 'Neutral Impact'),
            ('challenging', 'Challenging')
        ],
        label='Emotional Impact'
    )
    
    class Meta:
        model = UserProgress
        fields = {
            'status': ['exact'],
            'completion_time': ['date__gte', 'date__lte'],
            'activity__difficulty_level': ['lt', 'gt'],
            'time_spent_seconds': ['lt', 'gt'],
            'self_assessment': ['lt', 'gt']
        }
    
    def filter_has_breakthrough(self, queryset, name, value):
        """Filter by presence of breakthrough notes"""
        if value:
            return queryset.exclude(breakthrough_notes='')
        return queryset.filter(breakthrough_notes='')
    
    def filter_emotional_impact(self, queryset, name, value):
        """Filter by emotional impact"""
        # This is a simplified implementation
        # In production, you'd calculate actual impact
        if value == 'positive':
            return queryset.filter(
                stress_level_after__lt=models.F('stress_level_before')
            )
        elif value == 'challenging':
            return queryset.filter(
                stress_level_after__gt=models.F('stress_level_before') + 1
            )
        return queryset
    
    @property
    def qs(self):
        """Apply user-specific filtering"""
        queryset = super().qs
        
        # Filter by current user if not staff
        user = self.request.user
        if user.is_authenticated and not user.is_staff:
            queryset = queryset.filter(user=user)
        
        return queryset