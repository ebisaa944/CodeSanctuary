from django_filters import rest_framework as filters
from .models import GentleInteraction, SupportCircle, Achievement, UserAchievement
from django.utils import timezone

class GentleInteractionFilter(filters.FilterSet):
    """Filters for gentle interactions"""
    
    interaction_type = filters.ChoiceFilter(
        field_name='interaction_type',
        choices=GentleInteraction.InteractionType.choices
    )
    
    visibility = filters.ChoiceFilter(
        field_name='visibility',
        choices=GentleInteraction.VisibilityLevel.choices
    )
    
    date_range = filters.DateFromToRangeFilter(
        field_name='created_at',
        label='Date Range'
    )
    
    has_replies = filters.BooleanFilter(
        field_name='replies_count',
        method='filter_has_replies',
        label='Has replies'
    )
    
    is_pinned = filters.BooleanFilter(field_name='is_pinned')
    
    therapeutic_impact = filters.ChoiceFilter(
        method='filter_therapeutic_impact',
        choices=[
            ('high', 'High Impact'),
            ('medium', 'Medium Impact'),
            ('low', 'Low Impact')
        ],
        label='Therapeutic Impact'
    )
    
    class Meta:
        model = GentleInteraction
        fields = {
            'interaction_type': ['exact'],
            'visibility': ['exact'],
            'created_at': ['date__gte', 'date__lte'],
            'likes_count': ['gt'],
            'replies_count': ['gt']
        }
    
    def filter_has_replies(self, queryset, name, value):
        """Filter by presence of replies"""
        if value:
            return queryset.filter(replies_count__gt=0)
        return queryset.filter(replies_count=0)
    
    def filter_therapeutic_impact(self, queryset, name, value):
        """Filter by therapeutic impact score"""
        if value == 'high':
            return queryset.filter(likes_count__gt=5, replies_count__gt=2)
        elif value == 'medium':
            return queryset.filter(likes_count__gt=2, replies_count__gt=0)
        elif value == 'low':
            return queryset.filter(likes_count__lte=2, replies_count=0)
        return queryset
    
    @property
    def qs(self):
        """Apply community filtering"""
        queryset = super().qs
        
        # Filter by user's visibility permissions
        user = self.request.user
        if user.is_authenticated:
            # Start with interactions user can see
            visible_interactions = []
            for interaction in queryset:
                if interaction.can_user_see(user):
                    visible_interactions.append(interaction.id)
            
            queryset = queryset.filter(id__in=visible_interactions)
        else:
            # Anonymous users only see public/anonymous
            queryset = queryset.filter(
                visibility__in=['public', 'anonymous']
            )
        
        # Filter out moderated content for non-staff
        if not user.is_staff:
            queryset = queryset.filter(is_moderated=False)
        
        return queryset


class SupportCircleFilter(filters.FilterSet):
    """Filters for support circles"""
    
    is_public = filters.BooleanFilter(field_name='is_public')
    
    has_join_code = filters.BooleanFilter(
        field_name='join_code',
        method='filter_has_join_code',
        label='Requires join code'
    )
    
    member_count = filters.RangeFilter(
        field_name='active_members',
        label='Member Count'
    )
    
    focus_area = filters.CharFilter(
        field_name='focus_areas',
        lookup_expr='contains',
        label='Focus Area'
    )
    
    has_meetings = filters.BooleanFilter(
        field_name='meeting_schedule',
        method='filter_has_meetings',
        label='Has scheduled meetings'
    )
    
    class Meta:
        model = SupportCircle
        fields = {
            'is_public': ['exact'],
            'active_members': ['lt', 'gt'],
            'max_members': ['lt', 'gt']
        }
    
    def filter_has_join_code(self, queryset, name, value):
        """Filter by presence of join code"""
        if value:
            return queryset.exclude(join_code='')
        return queryset.filter(join_code='')
    
    def filter_has_meetings(self, queryset, name, value):
        """Filter by presence of meeting schedule"""
        if value:
            return queryset.exclude(meeting_schedule={})
        return queryset.filter(meeting_schedule={})
    
    @property
    def qs(self):
        """Apply circle filtering"""
        queryset = super().qs
        
        # For non-authenticated users, only show public circles
        user = self.request.user
        if not user.is_authenticated:
            queryset = queryset.filter(is_public=True)
        
        # Filter out circles user is already in (for discovery)
        if user.is_authenticated:
            user_circles = user.circle_memberships.values_list('circle_id', flat=True)
            queryset = queryset.exclude(id__in=user_circles)
        
        return queryset


class AchievementFilter(filters.FilterSet):
    """Filters for achievements"""
    
    tier = filters.ChoiceFilter(
        field_name='tier',
        choices=Achievement.AchievementTier.choices
    )
    
    requirement_type = filters.ChoiceFilter(
        field_name='requirement_type',
        choices=Achievement._meta.get_field('requirement_type').choices
    )
    
    difficulty = filters.ChoiceFilter(
        method='filter_by_difficulty',
        choices=[
            ('easy', 'Easy to earn'),
            ('medium', 'Moderate'),
            ('hard', 'Challenging')
        ],
        label='Difficulty'
    )
    
    recently_added = filters.BooleanFilter(
        method='filter_recently_added',
        label='Recently added'
    )
    
    class Meta:
        model = Achievement
        fields = {
            'tier': ['exact'],
            'requirement_type': ['exact'],
            'requirement_value': ['lt', 'gt'],
            'is_active': ['exact']
        }
    
    def filter_by_difficulty(self, queryset, name, value):
        """Filter by achievement difficulty"""
        if value == 'easy':
            return queryset.filter(requirement_value__lte=3)
        elif value == 'medium':
            return queryset.filter(
                requirement_value__gt=3,
                requirement_value__lte=10
            )
        elif value == 'hard':
            return queryset.filter(requirement_value__gt=10)
        return queryset
    
    def filter_recently_added(self, queryset, name, value):
        """Filter achievements added in last 30 days"""
        if value:
            month_ago = timezone.now() - timezone.timedelta(days=30)
            return queryset.filter(created_at__gte=month_ago)
        return queryset
    
    @property
    def qs(self):
        """Apply achievement filtering"""
        queryset = super().qs
        
        # Only show active achievements
        queryset = queryset.filter(is_active=True)
        
        # Filter by user's earned status if requested
        user = self.request.user
        earned_only = self.request.query_params.get('earned_only')
        
        if earned_only and user.is_authenticated:
            earned_achievements = user.earned_achievements.values_list('achievement_id', flat=True)
            queryset = queryset.filter(id__in=earned_achievements)
        
        return queryset


class UserAchievementFilter(filters.FilterSet):
    """Filters for user achievements"""
    
    tier = filters.ChoiceFilter(
        field_name='achievement__tier',
        choices=Achievement.AchievementTier.choices,
        label='Achievement Tier'
    )
    
    date_earned = filters.DateFromToRangeFilter(
        field_name='earned_at',
        label='Earned Date Range'
    )
    
    shared_publicly = filters.BooleanFilter(field_name='shared_publicly')
    
    has_reflection = filters.BooleanFilter(
        field_name='reflection_notes',
        method='filter_has_reflection',
        label='Has reflection notes'
    )
    
    class Meta:
        model = UserAchievement
        fields = {
            'achievement__tier': ['exact'],
            'earned_at': ['date__gte', 'date__lte'],
            'shared_publicly': ['exact']
        }
    
    def filter_has_reflection(self, queryset, name, value):
        """Filter by presence of reflection notes"""
        if value:
            return queryset.exclude(reflection_notes='')
        return queryset.filter(reflection_notes='')
    
    @property
    def qs(self):
        """Apply user-specific filtering"""
        queryset = super().qs
        
        # Filter by current user if not staff
        user = self.request.user
        if user.is_authenticated and not user.is_staff:
            queryset = queryset.filter(user=user)
        
        return queryset