# chat/filters.py
from django_filters import rest_framework as filters
from django.db.models import Q
from .models import ChatRoom, ChatMessage, RoomMembership, MessageReaction
from django.utils import timezone
from datetime import timedelta


class TherapeuticFilterBackend(filters.DjangoFilterBackend):
    """
    Custom filter backend with therapeutic considerations
    """
    def filter_queryset(self, request, queryset, view):
        """Apply therapeutic filters based on user state"""
        queryset = super().filter_queryset(request, queryset, view)
        
        # Apply therapeutic pre-filters based on user state
        if request.user.is_authenticated:
            user = request.user
            
            # Stress level filtering
            if hasattr(queryset.model, 'max_stress_level'):
                queryset = queryset.filter(max_stress_level__gte=user.current_stress_level)
            
            # Gentle mode filtering
            if user.gentle_mode and hasattr(queryset.model, 'safety_level'):
                queryset = queryset.filter(safety_level__in=['safe_space', 'supportive'])
            
            # Time-based filtering for high-stress users
            if user.current_stress_level >= 7 and hasattr(queryset.model, 'created_at'):
                # Don't show very old content to high-stress users
                week_ago = timezone.now() - timedelta(days=7)
                queryset = queryset.filter(created_at__gte=week_ago)
        
        return queryset


class TherapeuticChatRoomFilter(filters.FilterSet):
    """
    Therapeutic filters for chat rooms
    """
    room_type = filters.ChoiceFilter(
        choices=ChatRoom.RoomType.choices,
        help_text="Type of therapeutic room"
    )
    
    safety_level = filters.ChoiceFilter(
        choices=ChatRoom.SafetyLevel.choices,
        help_text="Safety level of the room"
    )
    
    is_active = filters.BooleanFilter(
        method='filter_is_active',
        help_text="Filter by room activity status"
    )
    
    max_stress_level = filters.NumberFilter(
        lookup_expr='lte',
        help_text="Maximum stress level allowed"
    )
    
    has_moderator = filters.BooleanFilter(
        method='filter_has_moderator',
        help_text="Rooms with active moderators"
    )
    
    mood_tracking = filters.BooleanFilter(
        field_name='mood_tracking_enabled',
        help_text="Rooms with mood tracking enabled"
    )
    
    trigger_warnings = filters.BooleanFilter(
        field_name='trigger_warnings_required',
        help_text="Rooms requiring trigger warnings"
    )
    
    therapeutic_focus = filters.CharFilter(
        method='filter_therapeutic_focus',
        help_text="Search in therapeutic goals and descriptions"
    )
    
    class Meta:
        model = ChatRoom
        fields = {
            'name': ['icontains'],
            'description': ['icontains'],
            'is_private': ['exact'],
            'is_archived': ['exact'],
            'created_at': ['gte', 'lte'],
            'max_participants': ['gte', 'lte'],
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize with user context"""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def filter_is_active(self, queryset, name, value):
        """Filter by room activity status"""
        if value:
            return queryset.filter(
                Q(scheduled_open__isnull=True) | Q(scheduled_open__lte=timezone.now()),
                Q(scheduled_close__isnull=True) | Q(scheduled_close__gte=timezone.now()),
                is_archived=False
            )
        else:
            return queryset.filter(
                Q(scheduled_open__gt=timezone.now()) |
                Q(scheduled_close__lt=timezone.now()) |
                Q(is_archived=True)
            )
    
    def filter_has_moderator(self, queryset, name, value):
        """Filter rooms with active moderators"""
        if value:
            return queryset.filter(
                moderators__isnull=False,
                moderators__roommembership__is_active=True
            ).distinct()
        else:
            return queryset.filter(
                Q(moderators__isnull=True) |
                Q(moderators__roommembership__is_active=False)
            ).distinct()
    
    def filter_therapeutic_focus(self, queryset, name, value):
        """Search in therapeutic content"""
        if value:
            return queryset.filter(
                Q(therapeutic_goal__icontains=value) |
                Q(description__icontains=value) |
                Q(name__icontains=value)
            )
        return queryset


class TherapeuticChatMessageFilter(filters.FilterSet):
    """
    Therapeutic filters for chat messages
    """
    message_type = filters.ChoiceFilter(
        choices=ChatMessage.MessageType.choices,
        help_text="Type of therapeutic message"
    )
    
    emotional_tone = filters.CharFilter(
        lookup_expr='icontains',
        help_text="Filter by emotional tone"
    )
    
    is_vulnerable_share = filters.BooleanFilter(
        help_text="Vulnerable shares only"
    )
    
    contains_affirmation = filters.BooleanFilter(
        help_text="Messages containing affirmations"
    )
    
    coping_strategy_shared = filters.BooleanFilter(
        help_text="Messages sharing coping strategies"
    )
    
    has_trigger_warning = filters.BooleanFilter(
        method='filter_has_trigger_warning',
        help_text="Messages with trigger warnings"
    )
    
    therapeutic_label = filters.CharFilter(
        lookup_expr='icontains',
        help_text="Filter by therapeutic label"
    )
    
    user_stress_level = filters.NumberFilter(
        method='filter_by_user_stress',
        help_text="Filter messages based on user's stress level when sent"
    )
    
    gentle_mode_compatible = filters.BooleanFilter(
        method='filter_gentle_mode',
        help_text="Messages suitable for gentle mode"
    )
    
    class Meta:
        model = ChatMessage
        fields = {
            'content': ['icontains'],
            'created_at': ['gte', 'lte', 'date'],
            'room': ['exact'],
            'user': ['exact'],
            'visibility': ['exact'],
        }
    
    def __init__(self, *args, **kwargs):
        """Initialize with user context"""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def filter_has_trigger_warning(self, queryset, name, value):
        """Filter messages with trigger warnings"""
        if value:
            return queryset.exclude(trigger_warning__isnull=True).exclude(trigger_warning='')
        else:
            return queryset.filter(Q(trigger_warning__isnull=True) | Q(trigger_warning=''))
    
    def filter_by_user_stress(self, queryset, name, value):
        """Filter messages based on user's stress level when sent"""
        if self.user and value:
            # This would require storing user stress level with messages
            # For now, we'll use a placeholder implementation
            return queryset
        
        # Default: show all messages
        return queryset.filter(deleted=False)
    
    def filter_gentle_mode(self, queryset, name, value):
        """Filter messages suitable for gentle mode"""
        if value and self.user and self.user.gentle_mode:
            # Gentle mode: avoid intense content
            return queryset.exclude(
                Q(emotional_tone__in=['anxious', 'angry', 'overwhelmed']) |
                Q(is_vulnerable_share=True) |
                Q(trigger_warning__isnull=False)
            )
        return queryset
    
    def filter_queryset(self, queryset):
        """Apply therapeutic filters"""
        queryset = super().filter_queryset(queryset)
        
        # Always exclude deleted messages
        queryset = queryset.filter(deleted=False)
        
        # Apply therapeutic visibility filtering
        if self.user and self.user.is_authenticated:
            # Users can see their own messages regardless of visibility
            queryset = queryset.filter(
                Q(visibility__in=['public', 'anonymous']) |
                Q(user=self.user) |
                Q(visibility='moderators_only', room__moderators=self.user) |
                Q(visibility='therapist_only', room__therapists=self.user) |
                Q(visibility='self_reflection', user=self.user)
            ).distinct()
        
        return queryset


class TherapeuticRoomMembershipFilter(filters.FilterSet):
    """
    Therapeutic filters for room memberships
    """
    role = filters.ChoiceFilter(
        choices=RoomMembership.MemberRole.choices,
        help_text="Member role in the room"
    )
    
    comfort_level = filters.NumberFilter(
        help_text="Comfort level in the room (1-5)"
    )
    
    is_active = filters.BooleanFilter(
        help_text="Active members only"
    )
    
    is_muted = filters.BooleanFilter(
        help_text="Muted members only"
    )
    
    is_anonymous = filters.BooleanFilter(
        help_text="Anonymous participants only"
    )
    
    has_safety_plan = filters.BooleanFilter(
        help_text="Members with safety plans"
    )
    
    stress_level_change = filters.NumberFilter(
        method='filter_stress_change',
        help_text="Filter by stress level change (entry vs exit)"
    )
    
    therapeutic_engagement = filters.ChoiceFilter(
        method='filter_therapeutic_engagement',
        choices=[
            ('high', 'High Engagement'),
            ('medium', 'Medium Engagement'),
            ('low', 'Low Engagement')
        ],
        help_text="Filter by therapeutic engagement level"
    )
    
    class Meta:
        model = RoomMembership
        fields = {
            'joined_at': ['gte', 'lte', 'date'],
            'last_seen': ['gte', 'lte', 'date'],
            'room': ['exact'],
            'user': ['exact'],
        }
    
    def filter_stress_change(self, queryset, name, value):
        """Filter by stress level change"""
        if value > 0:
            # Stress decreased (improvement)
            return queryset.filter(
                exit_stress_level__isnull=False,
                entry_stress_level__isnull=False
            ).filter(exit_stress_level__lt=F('entry_stress_level'))
        elif value < 0:
            # Stress increased
            return queryset.filter(
                exit_stress_level__isnull=False,
                entry_stress_level__isnull=False
            ).filter(exit_stress_level__gt=F('entry_stress_level'))
        else:
            # No change
            return queryset.filter(
                exit_stress_level__isnull=False,
                entry_stress_level__isnull=False
            ).filter(exit_stress_level=F('entry_stress_level'))
    
    def filter_therapeutic_engagement(self, queryset, name, value):
        """Filter by therapeutic engagement level"""
        from django.db.models import Count, Q
        
        # This would require joining with message data
        # For now, we'll use a simplified implementation
        if value == 'high':
            return queryset.filter(
                Q(comfort_level__gte=4) |
                Q(role__in=['moderator', 'therapist', 'facilitator'])
            )
        elif value == 'medium':
            return queryset.filter(comfort_level=3)
        elif value == 'low':
            return queryset.filter(comfort_level__lte=2)
        
        return queryset


class TherapeuticMessageReactionFilter(filters.FilterSet):
    """
    Therapeutic filters for message reactions
    """
    reaction_type = filters.ChoiceFilter(
        choices=MessageReaction.ReactionType.choices,
        help_text="Type of therapeutic reaction"
    )
    
    is_supportive = filters.BooleanFilter(
        help_text="Supportive reactions only"
    )
    
    is_therapeutic = filters.BooleanFilter(
        help_text="Therapeutically intentional reactions"
    )
    
    is_anonymous = filters.BooleanFilter(
        help_text="Anonymous reactions only"
    )
    
    emotional_context = filters.CharFilter(
        lookup_expr='icontains',
        help_text="Filter by emotional context"
    )
    
    reaction_category = filters.ChoiceFilter(
        method='filter_by_category',
        choices=[
            ('emotional_support', 'Emotional Support'),
            ('growth_encouragement', 'Growth Encouragement'),
            ('safety_signal', 'Safety Signal'),
            ('general_reaction', 'General Reaction')
        ],
        help_text="Filter by reaction category"
    )
    
    class Meta:
        model = MessageReaction
        fields = {
            'created_at': ['gte', 'lte', 'date'],
            'message': ['exact'],
            'user': ['exact'],
        }
    
    def filter_by_category(self, queryset, name, value):
        """Filter reactions by therapeutic category"""
        if value == 'emotional_support':
            return queryset.filter(
                reaction_type__in=['❤️', '🤗', '✅', '🛡️', '🤝']
            )
        elif value == 'growth_encouragement':
            return queryset.filter(
                reaction_type__in=['⭐', '💡', '👏', '🚀', '🌱']
            )
        elif value == 'safety_signal':
            return queryset.filter(
                reaction_type__in=['⚠️', '🚪', '🌊', '⚓']
            )
        elif value == 'general_reaction':
            return queryset.filter(
                reaction_type__in=['☀️', '🍃', '🌬️', '🧩']
            )
        
        return queryset


class TherapeuticSearchFilter(filters.FilterSet):
    """
    Comprehensive therapeutic search across chat entities
    """
    q = filters.CharFilter(
        method='therapeutic_search',
        help_text="Therapeutic search query"
    )
    
    search_type = filters.MultipleChoiceFilter(
        method='filter_search_type',
        choices=[
            ('rooms', 'Rooms'),
            ('messages', 'Messages'),
            ('users', 'Users'),
            ('reactions', 'Reactions')
        ],
        help_text="Types of content to search"
    )
    
    emotional_context = filters.CharFilter(
        method='filter_emotional_context',
        help_text="Search with emotional context consideration"
    )
    
    therapeutic_intent = filters.ChoiceFilter(
        method='filter_therapeutic_intent',
        choices=[
            ('support', 'Looking for Support'),
            ('share', 'Want to Share'),
            ('learn', 'Want to Learn'),
            ('connect', 'Want to Connect')
        ],
        help_text="Filter by therapeutic intent"
    )
    
    stress_safe = filters.BooleanFilter(
        method='filter_stress_safe',
        help_text="Show only stress-safe content"
    )
    
    class Meta:
        model = ChatMessage  # Base model, but searches across multiple
        fields = []
    
    def __init__(self, *args, **kwargs):
        """Initialize with user context"""
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def therapeutic_search(self, queryset, name, value):
        """Perform therapeutic search across multiple models"""
        # This is a placeholder - actual implementation would search across models
        # For now, we'll return the base queryset
        return queryset
    
    def filter_search_type(self, queryset, name, value):
        """Filter by search type"""
        # Implementation would handle different search types
        return queryset
    
    def filter_emotional_context(self, queryset, name, value):
        """Filter with emotional context"""
        if self.user and value:
            # Consider user's emotional state in search
            if self.user.current_stress_level >= 7:
                # High stress: prioritize calming content
                return queryset.filter(
                    Q(emotional_tone__in=['calm', 'supportive', 'hopeful']) |
                    Q(contains_affirmation=True)
                )
        
        return queryset
    
    def filter_therapeutic_intent(self, queryset, name, value):
        """Filter by therapeutic intent"""
        if value == 'support':
            return queryset.filter(
                Q(message_type__in=['reflection', 'checkin', 'breakthrough']) |
                Q(is_vulnerable_share=True)
            )
        elif value == 'share':
            return queryset.filter(
                Q(coping_strategy_shared=True) |
                Q(contains_affirmation=True)
            )
        elif value == 'learn':
            return queryset.filter(
                Q(message_type__in=['resource', 'exercise']) |
                Q(therapeutic_label__icontains='learning')
            )
        elif value == 'connect':
            return queryset.filter(
                Q(message_type='text') &
                Q(emotional_tone__in=['supportive', 'hopeful', 'calm'])
            )
        
        return queryset
    
    def filter_stress_safe(self, queryset, name, value):
        """Filter for stress-safe content"""
        if value and self.user:
            # Hide potentially triggering content for high-stress users
            if self.user.current_stress_level >= 6:
                return queryset.exclude(
                    Q(is_vulnerable_share=True) |
                    Q(trigger_warning__isnull=False) |
                    Q(emotional_tone__in=['anxious', 'angry', 'overwhelmed'])
                )
        
        return queryset


# Helper functions for therapeutic filtering

def apply_therapeutic_filters(queryset, request, filter_class=None):
    """
    Apply therapeutic filters to a queryset
    """
    if not request.user.is_authenticated:
        return queryset
    
    user = request.user
    
    # Apply stress level filtering
    if hasattr(queryset.model, 'max_stress_level'):
        queryset = queryset.filter(max_stress_level__gte=user.current_stress_level)
    
    # Apply gentle mode filtering
    if user.gentle_mode:
        if hasattr(queryset.model, 'safety_level'):
            queryset = queryset.filter(safety_level__in=['safe_space', 'supportive'])
        elif hasattr(queryset.model, 'emotional_tone'):
            queryset = queryset.exclude(
                emotional_tone__in=['anxious', 'angry', 'overwhelmed']
            )
    
    # Apply time-based filtering for recent content
    if user.current_stress_level >= 6 and hasattr(queryset.model, 'created_at'):
        week_ago = timezone.now() - timedelta(days=7)
        queryset = queryset.filter(created_at__gte=week_ago)
    
    # Apply custom filter class if provided
    if filter_class:
        filter_instance = filter_class(
            request.GET,
            queryset=queryset,
            user=request.user
        )
        queryset = filter_instance.qs
    
    return queryset


def get_therapeutic_filter_params(request):
    """
    Get therapeutic filter parameters based on user state
    """
    params = request.GET.copy()
    
    if not request.user.is_authenticated:
        return params
    
    user = request.user
    
    # Add therapeutic context parameters
    params['therapeutic_context'] = {
        'user_stress_level': user.current_stress_level,
        'gentle_mode': user.gentle_mode,
        'emotional_profile': user.emotional_profile,
        'filtered_for_safety': True
    }
    
    # Auto-apply gentle mode filters
    if user.gentle_mode and 'safety_level' not in params:
        params['safety_level'] = 'safe_space,supportive'
    
    # Auto-limit results for high-stress users
    if user.current_stress_level >= 7 and 'page_size' not in params:
        params['page_size'] = '10'
    
    return params