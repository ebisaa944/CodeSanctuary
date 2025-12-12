"""Integration with therapy app"""
from django.db import models
from django.utils import timezone

class TherapyIntegration:
    """Integration methods for therapy app"""
    
    @staticmethod
    def get_daily_therapy_plan(user):
        """Get daily therapy plan based on user's therapeutic state"""
        from therapy.models import TherapySession
        
        stress_level = user.current_stress_level
        emotional_profile = user.emotional_profile
        
        # Filter sessions based on therapeutic state
        if stress_level >= 7 or emotional_profile in ['anxious', 'overwhelmed']:
            # Gentle sessions only
            sessions = TherapySession.objects.filter(
                difficulty_level__lte=2,
                is_gentle=True
            )
        elif stress_level >= 5:
            # Moderate sessions
            sessions = TherapySession.objects.filter(
                difficulty_level__lte=3
            )
        else:
            # All sessions
            sessions = TherapySession.objects.all()
        
        # Apply gentle mode filter
        if user.gentle_mode:
            sessions = sessions.filter(is_gentle=True)
        
        # Limit by daily time limit
        total_duration = 0
        recommended_sessions = []
        
        for session in sessions.order_by('difficulty_level'):
            if total_duration + session.estimated_duration <= user.daily_time_limit:
                recommended_sessions.append(session)
                total_duration += session.estimated_duration
        
        return {
            'recommended_sessions': recommended_sessions,
            'total_duration': total_duration,
            'therapeutic_context': {
                'stress_level': stress_level,
                'emotional_profile': emotional_profile,
                'gentle_mode': user.gentle_mode
            }
        }
    
    @staticmethod
    def record_therapy_completion(user, session, duration_minutes):
        """Record completion of a therapy session"""
        # Update user's therapeutic metrics
        user.total_learning_minutes += duration_minutes
        
        # Update streak
        user.update_streak()
        
        # Check for breakthrough
        if session.difficulty_level >= 3 and duration_minutes >= 15:
            user.add_breakthrough_moment(
                f"Completed challenging therapy session: {session.title}"
            )
        
        # Adjust stress level (simplified)
        if duration_minutes >= 20:
            # Therapeutic activity reduces stress
            user.current_stress_level = max(1, user.current_stress_level - 1)
        
        user.save()
        
        return {
            'updated_stress': user.current_stress_level,
            'total_minutes': user.total_learning_minutes,
            'streak': user.consecutive_days
        }


class UserTherapyProfile(models.Model):
    """Extended therapy profile for users"""
    user = models.OneToOneField('users.TherapeuticUser', on_delete=models.CASCADE)
    favorite_therapy_types = models.JSONField(default=list)
    completed_sessions = models.JSONField(default=list)
    therapy_goals = models.TextField(blank=True)
    therapy_journal = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Therapy profile for {self.user.username}"
    
    def add_journal_entry(self, entry_type, content, emotion=None):
        """Add entry to therapy journal"""
        self.therapy_journal.append({
            'date': timezone.now().isoformat(),
            'type': entry_type,
            'content': content,
            'emotion': emotion
        })
        self.save()