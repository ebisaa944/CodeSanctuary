from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class GentleInteractionPagination(PageNumberPagination):
    """Pagination for gentle interactions"""
    
    page_size = 10
    page_size_query_param = 'interactions'
    max_page_size = 50
    
    def get_paginated_response(self, data):
        """Add community context to response"""
        community_context = {
            'gentle_reminder': 'Take your time reading these messages',
            'participation_suggestion': self._get_participation_suggestion(),
            'encouragement_focus': self._calculate_encouragement_focus(data),
            'active_members': self._estimate_active_members()
        }
        
        return Response({
            'community_context': community_context,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'interactions': data
        })
    
    def _get_participation_suggestion(self):
        """Suggest appropriate participation level"""
        if self.page.number == 1:
            return "Start by reading a few messages"
        elif self.page.number > 3:
            return "Consider taking a break from reading"
        return "You might want to respond to something that resonates"
    
    def _calculate_encouragement_focus(self, data):
        """Calculate encouragement focus of current page"""
        encouragements = sum(
            1 for item in data 
            if item.get('interaction_type') == 'encouragement'
        )
        total = len(data)
        
        if total == 0:
            return "No interactions"
        
        percentage = (encouragements / total) * 100
        
        if percentage > 50:
            return "Highly encouraging"
        elif percentage > 25:
            return "Encouraging"
        else:
            return "Mixed focus"
    
    def _estimate_active_members(self):
        """Estimate active community members"""
        # This would typically query the database
        # Simplified for example
        return "50+ gentle members"


class SupportCirclePagination(PageNumberPagination):
    """Pagination for support circles"""
    
    page_size = 8
    page_size_query_param = 'circles'
    max_page_size = 30
    
    def get_paginated_response(self, data):
        """Add therapeutic community context"""
        community_context = {
            'suggestion': 'Find one circle that feels right for you',
            'size_guidance': self._get_size_guidance(data),
            'focus_distribution': self._calculate_focus_distribution(data),
            'join_reminder': 'Most circles welcome new members gently'
        }
        
        return Response({
            'community_context': community_context,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'circles': data
        })
    
    def _get_size_guidance(self, data):
        """Provide guidance on circle sizes"""
        sizes = [item.get('member_count', 0) for item in data]
        
        if not sizes:
            return "Circles come in all sizes"
        
        avg_size = sum(sizes) / len(sizes)
        
        if avg_size < 5:
            return "Small, intimate circles"
        elif avg_size < 15:
            return "Medium-sized supportive groups"
        else:
            return "Larger, diverse communities"
    
    def _calculate_focus_distribution(self, data):
        """Calculate distribution of focus areas"""
        from collections import Counter
        
        all_focuses = []
        for item in data:
            focuses = item.get('focus_areas', [])
            if isinstance(focuses, list):
                all_focuses.extend(focuses)
        
        if not all_focuses:
            return {}
        
        counts = Counter(all_focuses)
        total = len(all_focuses)
        
        return {
            focus: f"{(count / total) * 100:.1f}%"
            for focus, count in counts.most_common(3)
        }


class AchievementPagination(PageNumberPagination):
    """Pagination for achievements"""
    
    page_size = 12
    page_size_query_param = 'achievements'
    max_page_size = 50
    
    def get_paginated_response(self, data):
        """Add achievement context"""
        achievement_context = {
            'earn_suggestion': 'Achievements celebrate your therapeutic journey',
            'tier_distribution': self._calculate_tier_distribution(data),
            'recently_earned': self._get_recent_earners(data),
            'encouragement': 'Every achievement represents growth'
        }
        
        return Response({
            'achievement_context': achievement_context,
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'achievements': data
        })
    
    def _calculate_tier_distribution(self, data):
        """Calculate tier distribution"""
        from collections import Counter
        
        tiers = [item.get('tier') for item in data if item.get('tier')]
        if not tiers:
            return {}
        
        counts = Counter(tiers)
        total = len(tiers)
        
        return {
            tier: f"{(count / total) * 100:.1f}%"
            for tier, count in counts.items()
        }
    
    def _get_recent_earners(self, data):
        """Get recent earners from current page achievements"""
        recent_earners = []
        
        for item in data[:3]:  # Check first 3 achievements
            earners = item.get('recently_earned', [])
            if earners:
                recent_earners.extend(earners[:2])  # Get 2 earners per achievement
        
        return recent_earners[:5]  # Return max 5 recent earners