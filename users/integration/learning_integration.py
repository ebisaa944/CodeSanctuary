"""Integration with learning app"""
from django.db import models

class LearningIntegration:
    """Integration methods for learning app"""
    
    @staticmethod
    def get_personalized_learning_path(user):
        """Get personalized learning path based on therapeutic profile"""
        from learning.models import Course, Lesson
        
        emotional_profile = user.emotional_profile
        learning_style = user.learning_style
        
        # Start with basic recommendations
        recommended_courses = Course.objects.filter(
            difficulty__lte=2 if user.gentle_mode else 3
        )
        
        # Filter by learning style if specified
        if learning_style:
            if learning_style == 'visual':
                recommended_courses = recommended_courses.filter(has_visual_aids=True)
            elif learning_style == 'kinesthetic':
                recommended_courses = recommended_courses.filter(has_practice_exercises=True)
            elif learning_style == 'auditory':
                recommended_courses = recommended_courses.filter(has_audio_content=True)
        
        # Adjust for emotional profile
        if emotional_profile in ['anxious', 'overwhelmed']:
            recommended_courses = recommended_courses.filter(
                is_self_paced=True,
                allows_skipping=True
            )
        
        # Create learning path
        path = {
            'recommended_courses': list(recommended_courses[:3]),
            'daily_recommendation': {
                'max_lessons': 2 if user.gentle_mode else 3,
                'max_duration': user.daily_time_limit,
                'break_frequency': 10 if user.gentle_mode else 15
            },
            'therapeutic_adaptations': {
                'allow_pausing': True,
                'allow_review': True,
                'no_time_pressure': user.gentle_mode
            }
        }
        
        return path
    
    @staticmethod
    def update_learning_progress(user, course, lesson, duration_minutes):
        """Update learning progress with therapeutic considerations"""
        from learning.models import UserProgress
        
        # Get or create progress record
        progress, created = UserProgress.objects.get_or_create(
            user=user,
            course=course,
            defaults={'current_lesson': lesson}
        )
        
        if not created and lesson.order > progress.current_lesson.order:
            progress.current_lesson = lesson
            progress.completed_lessons.append(lesson.id)
            progress.save()
            
            # Check for milestone
            if len(progress.completed_lessons) % 5 == 0:
                user.add_breakthrough_moment(
                    f"Completed {len(progress.completed_lessons)} lessons in {course.title}"
                )
        
        # Update user's therapeutic metrics
        user.total_learning_minutes += duration_minutes
        
        # Learning reduces stress (simplified)
        if duration_minutes >= 15:
            user.current_stress_level = max(1, user.current_stress_level - 1)
        
        user.update_streak()
        user.save()
        
        return {
            'course_progress': f"{len(progress.completed_lessons)}/{course.lessons.count()}",
            'total_minutes': user.total_learning_minutes,
            'streak': user.consecutive_days,
            'stress_change': -1 if duration_minutes >= 15 else 0
        }


class UserLearningProfile(models.Model):
    """Extended learning profile for users"""
    user = models.OneToOneField('users.TherapeuticUser', on_delete=models.CASCADE)
    preferred_topics = models.JSONField(default=list)
    learning_goals = models.TextField(blank=True)
    completed_courses = models.JSONField(default=list)
    learning_preferences = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Learning profile for {self.user.username}"