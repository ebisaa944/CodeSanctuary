from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class GentleActivityPagination(PageNumberPagination):
    """Pagination for activities with therapeutic considerations"""
    
    page_size = 3  # Very small batches for gentle learning
    page_size_query_param = 'gentle_batch'
    max_page_size = 10
    
    def get_paginated_response(self, data):
        """Add therapeutic guidance to response"""
        therapeutic_guidance = {
            'daily_suggestion': 'Try 1-3 activities per day',
            'break_reminder': 'Take breaks between activities',
            'completion_message': 'Any amount of effort is valuable',
            'current_page_activities': len(data),
            'suggested_next_steps': self._suggest_next_steps()
        }
        
        return Response({
            'therapeutic_guidance': therapeutic_guidance,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'activities': data
        })
    
    def _suggest_next_steps(self):
        """Suggest next steps based on page number"""
        if self.page.number == 1:
            return "Start with the first activity that feels comfortable"
        elif self.page.number > 3:
            return "You've explored many options - maybe revisit a favorite"
        return "Choose what feels right for you now"


class LearningPathPagination(PageNumberPagination):
    """Pagination for learning paths"""
    
    page_size = 5
    page_size_query_param = 'paths_per_page'
    max_page_size = 20
    
    def get_paginated_response(self, data):
        """Add learning guidance"""
        guidance = {
            'suggestion': 'Focus on one path at a time',
            'reminder': 'Progress at your own pace',
            'path_count': len(data),
            'difficulty_distribution': self._calculate_difficulty_distribution(data)
        }
        
        return Response({
            'learning_guidance': guidance,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'paths': data
        })
    
    def _calculate_difficulty_distribution(self, data):
        """Calculate difficulty distribution of current page"""
        difficulties = [item.get('difficulty_level', 1) for item in data]
        if not difficulties:
            return {}
        
        from collections import Counter
        counts = Counter(difficulties)
        total = len(difficulties)
        
        return {
            str(level): f"{(counts.get(level, 0) / total) * 100:.1f}%"
            for level in range(1, 6)
        }


class UserProgressPagination(PageNumberPagination):
    """Pagination for user progress with therapeutic insights"""
    
    page_size = 10
    page_size_query_param = 'progress_items'
    max_page_size = 50
    
    def get_paginated_response(self, data):
        """Add progress insights"""
        insights = {
            'completion_rate': self._calculate_completion_rate(data),
            'emotional_trend': self._analyze_emotional_trend(data),
            'encouragement': self._get_encouragement(data),
            'breakthroughs': self._count_breakthroughs(data)
        }
        
        return Response({
            'progress_insights': insights,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'progress_records': data
        })
    
    def _calculate_completion_rate(self, data):
        """Calculate completion rate from current page"""
        completed = sum(1 for item in data if item.get('status') == 'completed')
        total = len(data)
        return f"{(completed / total * 100):.0f}%" if total > 0 else "N/A"
    
    def _analyze_emotional_trend(self, data):
        """Analyze emotional trend from progress data"""
        emotional_changes = []
        for item in data:
            stress_before = item.get('stress_level_before')
            stress_after = item.get('stress_level_after')
            if stress_before and stress_after:
                emotional_changes.append(stress_after - stress_before)
        
        if not emotional_changes:
            return "No emotional data"
        
        avg_change = sum(emotional_changes) / len(emotional_changes)
        
        if avg_change < -1:
            return "Activities generally reduce stress"
        elif avg_change > 1:
            return "Activities may be challenging"
        else:
            return "Emotional state remains stable"
    
    def _get_encouragement(self, data):
        """Get encouragement based on progress"""
        if not data:
            return "Every journey begins with a first step"
        
        completed = sum(1 for item in data if item.get('status') == 'completed')
        if completed >= 5:
            return f"Great work completing {completed} activities!"
        elif completed > 0:
            return f"You've completed {completed} activity/activities - well done!"
        else:
            return "Starting is often the hardest part"
    
    def _count_breakthroughs(self, data):
        """Count breakthroughs in current page"""
        return sum(1 for item in data if item.get('is_breakthrough', False))