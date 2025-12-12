from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta
from .models import TherapeuticUser
from .serializers import UserProfileSerializer
from .permissions import GentleModePermission

class TherapeuticCheckInView(APIView):
    """View for daily therapeutic check-in"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Submit daily check-in"""
        user = request.user
        
        # Get check-in data
        stress_level = request.data.get('stress_level')
        mood = request.data.get('mood')
        note = request.data.get('note', '')
        
        # Validate
        if not stress_level or not (1 <= int(stress_level) <= 10):
            return Response(
                {'error': 'Stress level must be between 1 and 10'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update user
        user.current_stress_level = int(stress_level)
        
        # Auto-adjust gentle mode
        if user.current_stress_level >= 7:
            user.gentle_mode = True
        
        # Update streak
        user.update_streak()
        
        # Record breakthrough if applicable
        if mood and mood.lower() in ['breakthrough', 'achievement', 'proud']:
            user.add_breakthrough_moment(note or "Daily check-in achievement")
        
        user.save()
        
        return Response({
            'message': 'Check-in recorded gently',
            'new_stress': user.current_stress_level,
            'gentle_mode': user.gentle_mode,
            'streak': user.consecutive_days,
            'suggestion': self._get_suggestion(user.current_stress_level)
        })
    
    def _get_suggestion(self, stress_level):
        suggestions = {
            1: 'Very calm - great for focused work',
            2: 'Calm - good state for learning',
            3: 'Slightly calm - normal productive state',
            4: 'Neutral - ready to begin',
            5: 'Slightly stressed - take it slow',
            6: 'Moderately stressed - gentle activities',
            7: 'Stressed - consider a short break',
            8: 'Very stressed - self-care time',
            9: 'Highly stressed - gentle mode recommended',
            10: 'Extreme stress - please rest and care for yourself'
        }
        return suggestions.get(stress_level, 'Acknowledge how you feel')


class TherapeuticProgressView(APIView):
    """View for therapeutic progress tracking"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get therapeutic progress report"""
        user = request.user
        
        # Calculate progress metrics
        total_days = (timezone.now().date() - user.therapy_start_date).days + 1
        consistency_rate = (user.consecutive_days / total_days * 100) if total_days > 0 else 0
        
        # Stress trend (simplified - would need actual historical data)
        stress_trend = 'stable'
        if user.current_stress_level <= 3:
            stress_trend = 'low'
        elif user.current_stress_level >= 7:
            stress_trend = 'high'
        
        return Response({
            'progress_summary': {
                'total_days': total_days,
                'current_streak': user.consecutive_days,
                'consistency_rate': round(consistency_rate, 1),
                'total_minutes': user.total_learning_minutes,
                'avg_daily_minutes': round(user.total_learning_minutes / max(total_days, 1), 1)
            },
            'therapeutic_state': {
                'current_stress': user.current_stress_level,
                'stress_trend': stress_trend,
                'emotional_profile': user.emotional_profile,
                'gentle_mode': user.gentle_mode
            },
            'breakthroughs': {
                'count': len(user.breakthrough_moments),
                'recent': user.breakthrough_moments[-3:] if user.breakthrough_moments else []
            },
            'recommendations': self._get_recommendations(user)
        })
    
    def _get_recommendations(self, user):
        """Get personalized therapeutic recommendations"""
        recommendations = []
        
        # Based on stress level
        if user.current_stress_level >= 7:
            recommendations.append({
                'priority': 'high',
                'type': 'self_care',
                'message': 'High stress detected',
                'action': 'Take 10 minutes for deep breathing or a walk',
                'duration': '10 minutes'
            })
        
        # Based on consistency
        if user.consecutive_days >= 7:
            recommendations.append({
                'priority': 'medium',
                'type': 'celebration',
                'message': f'{user.consecutive_days} day streak!',
                'action': 'Acknowledge your consistency',
                'duration': '2 minutes'
            })
        
        # Based on learning time
        if user.total_learning_minutes < 100:
            recommendations.append({
                'priority': 'low',
                'type': 'encouragement',
                'message': 'Getting started is the hardest part',
                'action': 'Try just 5 minutes today',
                'duration': '5 minutes'
            })
        
        return recommendations


class GentleActivityViewSet(viewsets.ViewSet):
    """ViewSet for gentle therapeutic activities"""
    permission_classes = [permissions.IsAuthenticated, GentleModePermission]
    
    @action(detail=False, methods=['GET'])
    def breathing_exercises(self, request):
        """Get breathing exercises"""
        return Response({
            'exercises': [
                {
                    'id': 'box_breathing',
                    'name': 'Box Breathing',
                    'description': '4-4-4-4 pattern: Inhale, hold, exhale, hold',
                    'duration': '2 minutes',
                    'gentle_level': 1
                },
                {
                    'id': '478_breathing',
                    'name': '4-7-8 Breathing',
                    'description': 'Inhale 4, hold 7, exhale 8',
                    'duration': '4 minutes',
                    'gentle_level': 2
                },
                {
                    'id': 'diaphragmatic',
                    'name': 'Diaphragmatic Breathing',
                    'description': 'Deep belly breathing',
                    'duration': '3 minutes',
                    'gentle_level': 1
                }
            ],
            'suggestion': 'Start with 2 minutes of box breathing'
        })
    
    @action(detail=False, methods=['GET'])
    def grounding_exercises(self, request):
        """Get grounding exercises for anxiety"""
        return Response({
            'exercises': [
                {
                    'id': '54321',
                    'name': '5-4-3-2-1 Grounding',
                    'description': 'Name 5 things you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste',
                    'duration': '3 minutes',
                    'gentle_level': 1
                },
                {
                    'id': 'body_scan',
                    'name': 'Body Scan',
                    'description': 'Focus attention on each part of your body',
                    'duration': '5 minutes',
                    'gentle_level': 2
                },
                {
                    'id': 'mindful_observation',
                    'name': 'Mindful Observation',
                    'description': 'Observe an object in detail without judgment',
                    'duration': '3 minutes',
                    'gentle_level': 1
                }
            ],
            'suggestion': 'Use 5-4-3-2-1 when feeling overwhelmed'
        })
    
    @action(detail=False, methods=['POST'])
    def complete_activity(self, request):
        """Record completion of a therapeutic activity"""
        activity_id = request.data.get('activity_id')
        duration = request.data.get('duration', 0)
        
        if not activity_id:
            return Response(
                {'error': 'Activity ID required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update user's learning minutes
        user = request.user
        user.total_learning_minutes += int(duration)
        user.save()
        
        return Response({
            'message': 'Activity completed gently',
            'duration_added': duration,
            'total_minutes': user.total_learning_minutes,
            'encouragement': 'Every small step counts'
        })


class TherapeuticInsightsView(APIView):
    """View for therapeutic insights and patterns"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get therapeutic insights"""
        user = request.user
        
        # Calculate insights (simplified - would need actual data)
        insights = {
            'learning_patterns': self._analyze_learning_patterns(user),
            'stress_patterns': self._analyze_stress_patterns(user),
            'breakthrough_triggers': self._analyze_breakthroughs(user),
            'personalized_tips': self._generate_personalized_tips(user)
        }
        
        return Response(insights)
    
    def _analyze_learning_patterns(self, user):
        """Analyze user's learning patterns"""
        return {
            'consistency': 'good' if user.consecutive_days >= 3 else 'developing',
            'preferred_pace': 'gentle' if user.gentle_mode else 'standard',
            'time_management': 'moderate' if user.daily_time_limit <= 60 else 'ambitious',
            'suggestion': 'Consider shorter, more frequent sessions' if user.daily_time_limit > 60 else 'Your pacing looks sustainable'
        }
    
    def _analyze_stress_patterns(self, user):
        """Analyze stress patterns"""
        stress_level = user.current_stress_level
        
        if stress_level <= 3:
            pattern = 'low_stress'
            tip = 'Great time for learning new concepts'
        elif stress_level <= 6:
            pattern = 'moderate_stress'
            tip = 'Good for practice and review'
        else:
            pattern = 'high_stress'
            tip = 'Focus on gentle review and self-care'
        
        return {
            'current_pattern': pattern,
            'recommendation': tip,
            'gentle_mode_suggestion': 'Consider enabling gentle mode' if stress_level >= 5 and not user.gentle_mode else None
        }
    
    def _analyze_breakthroughs(self, user):
        """Analyze breakthrough moments"""
        breakthroughs = user.breakthrough_moments
        
        if not breakthroughs:
            return {
                'count': 0,
                'message': 'Your first breakthrough is coming soon!',
                'tip': 'Celebrate small wins along the way'
            }
        
        return {
            'count': len(breakthroughs),
            'frequency': 'regular' if len(breakthroughs) >= 3 else 'occasional',
            'common_themes': self._extract_themes(breakthroughs),
            'encouragement': 'You\'re making meaningful progress'
        }
    
    def _extract_themes(self, breakthroughs):
        """Extract common themes from breakthroughs"""
        themes = []
        for moment in breakthroughs[-5:]:  # Last 5 breakthroughs
            desc = moment['description'].lower()
            if any(word in desc for word in ['first', 'started', 'began']):
                themes.append('getting_started')
            elif any(word in desc for word in ['understood', 'figured', 'learned']):
                themes.append('understanding')
            elif any(word in desc for word in ['proud', 'happy', 'excited']):
                themes.append('achievement')
        
        return list(set(themes))[:3]  # Return unique themes
    
    def _generate_personalized_tips(self, user):
        """Generate personalized therapeutic tips"""
        tips = []
        
        # Based on emotional profile
        if user.emotional_profile == 'anxious':
            tips.append('Try the 5-4-3-2-1 grounding exercise when feeling anxious')
        elif user.emotional_profile == 'avoidant':
            tips.append('Break tasks into tiny steps to reduce avoidance')
        elif user.emotional_profile == 'doubtful':
            tips.append('Keep a "proof of progress" journal')
        
        # Based on learning style
        if user.learning_style == 'visual':
            tips.append('Use diagrams and color coding in your notes')
        elif user.learning_style == 'kinesthetic':
            tips.append('Try typing examples as you learn')
        
        # Based on stress level
        if user.current_stress_level >= 6:
            tips.append('Set a timer for regular breathing breaks')
        
        return tips