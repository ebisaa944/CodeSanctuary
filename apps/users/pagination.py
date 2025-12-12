from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class GentlePagination(PageNumberPagination):
    """Gentle pagination with therapeutic considerations"""
    page_size = 10  # Smaller batches for reduced cognitive load
    page_size_query_param = 'page_size'
    max_page_size = 50  # Prevent overwhelming requests
    
    def get_paginated_response(self, data):
        """Return response with therapeutic context"""
        return Response({
            'gentle_context': {
                'message': 'Take your time browsing these results',
                'suggested_breaks': self._suggest_breaks(),
                'current_page': self.page.number,
                'total_pages': self.page.paginator.num_pages,
                'items_per_page': self.page.paginator.per_page
            },
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
    
    def _suggest_breaks(self):
        """Suggest breaks based on page position"""
        if self.page.number > 3:
            return "Consider taking a short break"
        return None


class UserPagination(GentlePagination):
    """Pagination specifically for users"""
    page_size = 20
    max_page_size = 100
    
    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        # Add user-specific context
        response.data['gentle_context'].update({
            'privacy_note': 'User progress may be private',
            'encouragement': 'Every learner progresses at their own pace'
        })
        return response


class TherapeuticActivityPagination(PageNumberPagination):
    """Pagination for therapeutic activities"""
    page_size = 5  # Very small batches for gentle learning
    page_size_query_param = 'gentle_batch'
    max_page_size = 15
    
    def paginate_queryset(self, queryset, request, view=None):
        """Apply therapeutic filtering before pagination"""
        # Filter based on user's therapeutic state if available
        user = request.user if request.user.is_authenticated else None
        if user and hasattr(user, 'get_safe_learning_plan'):
            plan = user.get_safe_learning_plan()
            max_difficulty = plan.get('max_difficulty', 3)
            queryset = queryset.filter(difficulty_level__lte=max_difficulty)
        
        return super().paginate_queryset(queryset, request, view)
    
    def get_paginated_response(self, data):
        return Response({
            'therapeutic_planning': {
                'suggested_daily_limit': 3,  # Suggest only 3 activities per day
                'break_reminder': 'Remember to breathe between activities',
                'completion_message': 'Completing any activity is an achievement'
            },
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'activities': data
        })