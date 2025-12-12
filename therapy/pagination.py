from django_filters import rest_framework as filters
from .models import EmotionalCheckIn, CopingStrategy
from django.utils import timezone
from django.db.models import JSONField
from rest_framework.pagination import PageNumberPagination   # ✅ added for pagination classes


# ---------------------------
# EmotionalCheckIn Filters
# ---------------------------
class EmotionalCheckInFilter(filters.FilterSet):
    """Filters for emotional checkins with therapeutic considerations"""
    
    date_range = filters.DateFromToRangeFilter(
        field_name='created_at',
        label='Date Range'
    )
    
    emotion = filters.ChoiceFilter(
        field_name='primary_emotion',
        choices=EmotionalCheckIn.PrimaryEmotion.choices
    )
    
    intensity_range = filters.RangeFilter(
        field_name='intensity',
        label='Intensity Range (1-10)'
    )
    
    has_physical_symptoms = filters.BooleanFilter(
        field_name='physical_symptoms',
        method='filter_has_symptoms',
        label='Has physical symptoms'
    )
    
    has_coping = filters.BooleanFilter(
        field_name='coping_strategies_used',
        method='filter_has_coping',
        label='Used coping strategies'
    )
    
    time_of_day = filters.ChoiceFilter(
        method='filter_time_of_day',
        choices=[
            ('morning', 'Morning (6am-12pm)'),
            ('afternoon', 'Afternoon (12pm-6pm)'),
            ('evening', 'Evening (6pm-10pm)'),
            ('night', 'Night (10pm-6am)')
        ],
        label='Time of Day'
    )
    
    class Meta:
        model = EmotionalCheckIn
        fields = {
            'primary_emotion': ['exact'],
            'intensity': ['lt', 'gt', 'exact'],
            'created_at': ['date__gte', 'date__lte'],
            'context_tags': ['contains']
        }

        # ✅ Fix for JSONField
        filter_overrides = {
            JSONField: {
                'filter_class': filters.CharFilter,
                'extra': lambda f: {
                    'lookup_expr': 'icontains',
                },
            },
        }
    
    def filter_has_symptoms(self, queryset, name, value):
        if value:
            return queryset.exclude(physical_symptoms=[])
        return queryset.filter(physical_symptoms=[])
    
    def filter_has_coping(self, queryset, name, value):
        if value:
            return queryset.exclude(coping_strategies_used=[])
        return queryset.filter(coping_strategies_used=[])
    
    def filter_time_of_day(self, queryset, name, value):
        hour_ranges = {
            'morning': (6, 12),
            'afternoon': (12, 18),
            'evening': (18, 22),
            'night': (22, 6)
        }
        
        if value in hour_ranges:
            start, end = hour_ranges[value]
            if value == 'night':
                return queryset.extra(
                    where=["EXTRACT(HOUR FROM created_at) >= %s OR EXTRACT(HOUR FROM created_at) < %s"],
                    params=[start, end]
                )
            else:
                return queryset.extra(
                    where=["EXTRACT(HOUR FROM created_at) >= %s AND EXTRACT(HOUR FROM created_at) < %s"],
                    params=[start, end]
                )
        
        return queryset
    
    @property
    def qs(self):
        queryset = super().qs
        user = self.request.user
        if user.is_authenticated and not user.is_staff:
            queryset = queryset.filter(user=user)
        if user.is_authenticated and getattr(user, "gentle_mode", False):
            queryset = queryset.filter(intensity__lte=8)
        return queryset


# ---------------------------
# CopingStrategy Filters
# ---------------------------
class CopingStrategyFilter(filters.FilterSet):
    """Filters for coping strategies"""
    
    emotion_target = filters.CharFilter(
        field_name='target_emotions',
        lookup_expr='contains',
        label='Helps with emotion'
    )
    
    strategy_type = filters.ChoiceFilter(
        field_name='strategy_type',
        choices=CopingStrategy.StrategyType.choices
    )
    
    duration = filters.ChoiceFilter(
        method='filter_by_duration',
        choices=[
            ('quick', 'Quick (<5 min)'),
            ('short', 'Short (5-15 min)'),
            ('medium', 'Medium (15-30 min)'),
            ('long', 'Long (>30 min)')
        ],
        label='Duration'
    )
    
    difficulty = filters.ChoiceFilter(
        field_name='difficulty_level',
        choices=[(i, f"Level {i}") for i in range(1, 6)]
    )
    
    coding_integration = filters.BooleanFilter(field_name='coding_integration')
    
    class Meta:
        model = CopingStrategy
        fields = {
            'strategy_type': ['exact'],
            'difficulty_level': ['exact', 'lt', 'gt'],
            'estimated_minutes': ['lt', 'gt'],
            'coding_language': ['exact']
        }
    
    def filter_by_duration(self, queryset, name, value):
        duration_ranges = {
            'quick': (1, 5),
            'short': (5, 15),
            'medium': (15, 30),
            'long': (30, 999)
        }
        
        if value in duration_ranges:
            min_min, max_min = duration_ranges[value]
            if value == 'quick':
                return queryset.filter(estimated_minutes__lt=max_min)
            elif value == 'long':
                return queryset.filter(estimated_minutes__gte=min_min)
            else:
                return queryset.filter(
                    estimated_minutes__gte=min_min,
                    estimated_minutes__lt=max_min
                )
        return queryset
    
    @property
    def qs(self):
        queryset = super().qs
        queryset = queryset.filter(is_active=True)
        user = self.request.user
        if user.is_authenticated and getattr(user, "gentle_mode", False):
            queryset = queryset.filter(difficulty_level__lte=3)
        return queryset


# ---------------------------
# Pagination Classes
# ---------------------------
class TherapeuticPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CopingStrategyPagination(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 50


class EmotionalHistoryPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 200
