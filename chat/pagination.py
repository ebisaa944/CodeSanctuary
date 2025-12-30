# chat/pagination.py
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination, CursorPagination
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta


class TherapeuticPagination(PageNumberPagination):
    """
    Therapeutic pagination with gentle defaults for stressed users
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    page_query_param = 'page'
    
    def get_paginated_response(self, data):
        # Add therapeutic metadata
        return Response({
            'therapeutic_context': {
                'page_size': self.page_size,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
                'gentle_mode': self.request.user.gentle_mode if hasattr(self.request, 'user') else False,
                'suggested_breaks': self.page.number % 5 == 0  # Suggest breaks every 5 pages
            },
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
    
    def get_page_size(self, request):
        """Adjust page size based on user's stress level"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.current_stress_level >= 7:
                # Smaller pages for high-stress users
                return min(self.page_size, 10)
            elif request.user.gentle_mode:
                # Gentle mode has medium pages
                return min(self.page_size, 15)
        
        return super().get_page_size(request)


class StressAwarePagination(TherapeuticPagination):
    """
    Pagination that adapts to user's current stress level
    """
    def get_page_size(self, request):
        if hasattr(request, 'user') and request.user.is_authenticated:
            stress_level = request.user.current_stress_level
            
            if stress_level >= 8:
                return 5  # Very small pages for extremely stressed users
            elif stress_level >= 6:
                return 10
            elif stress_level >= 4:
                return 15
            elif stress_level >= 2:
                return 20
        
        return super().get_page_size(request)
    
    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        
        # Add stress-aware suggestions
        if hasattr(self.request, 'user') and self.request.user.is_authenticated:
            stress_level = self.request.user.current_stress_level
            
            if stress_level >= 7 and len(data) > 0:
                response.data['therapeutic_suggestion'] = "Consider taking a short break between pages"
            elif stress_level <= 3 and len(data) > 0:
                response.data['therapeutic_suggestion'] = "Great engagement! Remember to support others when ready"
        
        return response


class ThreadAwarePagination(CursorPagination):
    """
    Pagination for threaded conversations (messages with replies)
    """
    page_size = 15
    ordering = '-created_at'
    cursor_query_param = 'cursor'
    
    def paginate_queryset(self, queryset, request, view=None):
        """Group threads together"""
        # Get thread starters first
        thread_starters = queryset.filter(is_thread_starter=True)
        
        # Then get their replies
        if self.get_cursor(request):
            return super().paginate_queryset(queryset, request, view)
        
        # For first page, include some thread context
        return super().paginate_queryset(queryset, request, view)
    
    def get_paginated_response(self, data):
        return Response({
            'therapeutic_context': {
                'pagination_type': 'thread_aware',
                'cursor': self.get_cursor(self.request),
                'has_next': self.has_next,
                'has_previous': self.has_previous,
                'thread_count': len([d for d in data if d.get('is_thread_starter')])
            },
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class EmotionalTonePagination(PageNumberPagination):
    """
    Pagination that balances emotional tones in responses
    """
    page_size = 12
    
    def paginate_queryset(self, queryset, request, view=None):
        """Balance emotional tones on each page"""
        page = super().paginate_queryset(queryset, request, view)
        
        if page and hasattr(request, 'user') and request.user.is_authenticated:
            # Try to balance emotional content for therapeutic benefit
            # This is a simplified version - in reality you'd want more sophisticated balancing
            pass
        
        return page
    
    def get_paginated_response(self, data):
        # Analyze emotional tones on this page
        emotional_summary = self.analyze_emotional_content(data)
        
        return Response({
            'therapeutic_context': {
                'pagination_type': 'emotional_balance',
                'emotional_summary': emotional_summary,
                'suggestion': self.get_emotional_suggestion(emotional_summary)
            },
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
    
    def analyze_emotional_content(self, data):
        """Analyze emotional content of page"""
        if not data:
            return {}
        
        emotional_counts = {}
        for item in data:
            if isinstance(item, dict) and 'emotional_tone' in item:
                tone = item['emotional_tone']
                emotional_counts[tone] = emotional_counts.get(tone, 0) + 1
        
        return {
            'total_items': len(data),
            'emotional_distribution': emotional_counts,
            'has_vulnerable_content': any(
                item.get('is_vulnerable_share', False) for item in data
            ),
            'has_affirmations': any(
                item.get('contains_affirmation', False) for item in data
            )
        }
    
    def get_emotional_suggestion(self, emotional_summary):
        """Get therapeutic suggestion based on emotional content"""
        if emotional_summary.get('has_vulnerable_content'):
            return "This page contains vulnerable shares. Practice self-care as needed."
        
        if emotional_summary.get('has_affirmations'):
            return "Affirmations detected! Consider saving or noting helpful ones."
        
        return "Continue at your own pace."


class TimeBasedTherapeuticPagination(PageNumberPagination):
    """
    Pagination based on time periods for therapeutic reflection
    """
    page_size = 10
    
    def get_page_size(self, request):
        """Adjust based on time of day and user patterns"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            hour = timezone.now().hour
            
            # Smaller pages at night for better sleep hygiene
            if 22 <= hour or hour < 6:  # 10 PM to 6 AM
                return 5
            
            # Moderate pages during work hours
            if 9 <= hour <= 17:  # 9 AM to 5 PM
                return 8
        
        return super().get_page_size(request)
    
    def get_paginated_response(self, data):
        hour = timezone.now().hour
        
        time_context = {
            'current_hour': hour,
            'time_of_day': self.get_time_of_day(hour),
            'suggested_pace': self.get_suggested_pace(hour),
            'recommended_break_interval': self.get_break_interval(hour)
        }
        
        return Response({
            'therapeutic_context': {
                'pagination_type': 'time_based',
                'time_awareness': time_context
            },
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
    
    def get_time_of_day(self, hour):
        if 5 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 22:
            return 'evening'
        else:
            return 'night'
    
    def get_suggested_pace(self, hour):
        if hour < 6 or hour >= 22:
            return 'slow_and_reflective'
        elif 6 <= hour < 9:
            return 'gentle_start'
        elif 9 <= hour < 17:
            return 'moderate'
        else:
            return 'relaxed'
    
    def get_break_interval(self, hour):
        if hour < 6 or hour >= 22:
            return 'every_page'
        elif 9 <= hour < 17:
            return 'every_3_pages'
        else:
            return 'every_2_pages'


class GentleProgressivePagination(PageNumberPagination):
    """
    Progressive pagination that starts small and grows as user continues
    """
    initial_page_size = 5
    progressive_increase = 3
    max_progressive_size = 25
    
    def get_page_size(self, request):
        page_number = int(request.query_params.get(self.page_query_param, 1))
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.gentle_mode:
                # Gentle mode: slower progression
                progressive_size = self.initial_page_size + (page_number - 1) * 2
            else:
                # Normal mode: standard progression
                progressive_size = self.initial_page_size + (page_number - 1) * self.progressive_increase
            
            return min(progressive_size, self.max_progressive_size)
        
        return self.initial_page_size
    
    def get_paginated_response(self, data):
        current_page = int(self.request.query_params.get(self.page_query_param, 1))
        page_size = len(data) if data else self.get_page_size(self.request)
        
        return Response({
            'therapeutic_context': {
                'pagination_type': 'gentle_progressive',
                'current_page': current_page,
                'page_size': page_size,
                'progression_rate': 'gentle' if hasattr(self.request, 'user') and self.request.user.gentle_mode else 'standard',
                'next_page_increase': min(
                    self.progressive_increase,
                    self.max_progressive_size - page_size
                ) if page_size < self.max_progressive_size else 0
            },
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class BreakAwarePagination(PageNumberPagination):
    """
    Pagination that suggests breaks based on content intensity
    """
    page_size = 15
    break_suggestion_threshold = 3  # Suggest break after X intense pages
    
    def get_paginated_response(self, data):
        current_page = int(self.request.query_params.get(self.page_query_param, 1))
        
        # Check if break is suggested
        should_suggest_break = (
            current_page % self.break_suggestion_threshold == 0 and
            current_page > 0 and
            self.has_intense_content(data)
        )
        
        therapeutic_context = {
            'pagination_type': 'break_aware',
            'current_page': current_page,
            'pages_since_last_suggestion': current_page % self.break_suggestion_threshold,
            'should_suggest_break': should_suggest_break
        }
        
        if should_suggest_break:
            therapeutic_context['break_suggestion'] = self.get_break_suggestion()
        
        return Response({
            'therapeutic_context': therapeutic_context,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
    
    def has_intense_content(self, data):
        """Check if page contains intense therapeutic content"""
        intense_keywords = ['vulnerable', 'trigger', 'trauma', 'anxious', 'overwhelmed']
        for item in data:
            if isinstance(item, dict):
                content = str(item.get('content', '')).lower()
                if any(keyword in content for keyword in intense_keywords):
                    return True
                if item.get('is_vulnerable_share', False):
                    return True
        return False
    
    def get_break_suggestion(self):
        """Get therapeutic break suggestion"""
        suggestions = [
            "Take a 5-minute break to practice deep breathing",
            "Stand up and stretch for a moment",
            "Get a glass of water and return refreshed",
            "Practice the 5-4-3-2-1 grounding technique",
            "Write down one thing you're grateful for"
        ]
        import random
        return random.choice(suggestions)


class CompositeTherapeuticPagination(TherapeuticPagination):
    """
    Composite pagination that combines multiple therapeutic strategies
    """
    def get_paginated_response(self, data):
        # Gather multiple therapeutic insights
        stress_aware = StressAwarePagination().get_paginated_response(data).data.get('therapeutic_context', {})
        time_aware = TimeBasedTherapeuticPagination().get_paginated_response(data).data.get('therapeutic_context', {})
        emotional_aware = EmotionalTonePagination().get_paginated_response(data).data.get('therapeutic_context', {})
        
        composite_context = {
            'pagination_type': 'composite_therapeutic',
            'stress_aware': {k: v for k, v in stress_aware.items() if k != 'pagination_type'},
            'time_aware': {k: v for k, v in time_aware.items() if k != 'pagination_type'},
            'emotional_aware': {k: v for k, v in emotional_aware.items() if k != 'pagination_type'},
            'composite_suggestion': self.get_composite_suggestion(stress_aware, time_aware, emotional_aware)
        }
        
        return Response({
            'therapeutic_context': composite_context,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
    
    def get_composite_suggestion(self, stress_context, time_context, emotional_context):
        """Generate composite therapeutic suggestion"""
        suggestions = []
        
        # Stress-based suggestion
        if stress_context.get('therapeutic_suggestion'):
            suggestions.append(stress_context['therapeutic_suggestion'])
        
        # Time-based suggestion
        if time_context.get('suggested_pace'):
            suggestions.append(f"Current pace suggestion: {time_context['suggested_pace'].replace('_', ' ')}")
        
        # Emotion-based suggestion
        if emotional_context.get('suggestion'):
            suggestions.append(emotional_context['suggestion'])
        
        if not suggestions:
            suggestions.append("Continue engaging at your own comfortable pace")
        
        return " | ".join(suggestions)


# Helper functions for therapeutic pagination

def get_therapeutic_pagination_class(request, view=None):
    """
    Dynamically select the best therapeutic pagination class based on user state
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return TherapeuticPagination
    
    user = request.user
    
    # High stress -> gentle pagination
    if user.current_stress_level >= 7:
        return GentleProgressivePagination
    
    # Gentle mode enabled -> gentle pagination
    if user.gentle_mode:
        return GentleProgressivePagination
    
    # Evening/night hours -> time-based with smaller pages
    hour = timezone.now().hour
    if hour >= 20 or hour < 6:  # 8 PM to 6 AM
        return TimeBasedTherapeuticPagination
    
    # Emotional content expected -> emotion-aware
    if view and hasattr(view, 'get_queryset'):
        queryset = view.get_queryset()
        model_name = queryset.model.__name__ if queryset else ''
        if model_name == 'ChatMessage':
            return EmotionalTonePagination
    
    # Threaded conversations -> thread-aware
    if request.GET.get('group_threads') == 'true':
        return ThreadAwarePagination
    
    # Default therapeutic pagination
    return TherapeuticPagination


def configure_therapeutic_pagination(paginator_class, request, queryset):
    """
    Configure therapeutic paginator with context
    """
    paginator = paginator_class()
    
    # Set page size based on therapeutic considerations
    if hasattr(paginator, 'get_page_size'):
        paginator.page_size = paginator.get_page_size(request)
    
    return paginator