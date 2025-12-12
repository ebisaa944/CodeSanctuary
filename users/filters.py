from django_filters import rest_framework as filters
from .models import TherapeuticUser

class TherapeuticUserFilter(filters.FilterSet):
    """Filters for therapeutic users with gentle defaults"""
    
    emotional_profile = filters.ChoiceFilter(
        choices=TherapeuticUser.EmotionalProfile.choices,
        method='filter_by_profile'
    )
    
    gentle_mode = filters.BooleanFilter(field_name='gentle_mode')
    
    stress_level = filters.RangeFilter(
        field_name='current_stress_level',
        label='Stress Level (1-10)'
    )
    
    learning_style = filters.ChoiceFilter(
        choices=TherapeuticUser.LearningStyle.choices,
        null_label='Not specified'
    )
    
    has_custom_affirmation = filters.BooleanFilter(
        method='filter_has_affirmation',
        label='Has custom affirmation'
    )
    
    class Meta:
        model = TherapeuticUser
        fields = {
            'emotional_profile': ['exact'],
            'gentle_mode': ['exact'],
            'current_stress_level': ['lt', 'gt', 'exact'],
            'daily_time_limit': ['lt', 'gt'],
            'consecutive_days': ['gt']
        }
    
    def filter_by_profile(self, queryset, name, value):
        """Filter by emotional profile with therapeutic considerations"""
        if value == 'anxious':
            # For anxious users, only show if gentle mode is on
            return queryset.filter(
                emotional_profile=value,
                gentle_mode=True
            )
        return queryset.filter(emotional_profile=value)
    
    def filter_has_affirmation(self, queryset, name, value):
        """Filter users who have set a custom affirmation"""
        if value:
            return queryset.exclude(custom_affirmation='')
        return queryset.filter(custom_affirmation='')
    
    @property
    def qs(self):
        """Apply therapeutic safety to queryset"""
        queryset = super().qs
        
        # Always exclude superusers from public filters
        if not self.request.user.is_superuser:
            queryset = queryset.filter(is_superuser=False)
        
        # Respect privacy settings
        if not self.request.user.is_staff:
            queryset = queryset.filter(hide_progress=False)
        
        return queryset