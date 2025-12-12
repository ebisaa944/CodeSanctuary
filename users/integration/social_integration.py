"""Integration with social app"""
from django.db import models
from django.utils import timezone

class SocialIntegration:
    """Integration methods for social app"""
    
    @staticmethod
    def get_safe_social_connections(user):
        """Get safe social connections based on therapeutic state"""
        from social.models import Connection, SocialGroup
        
        emotional_profile = user.emotional_profile
        stress_level = user.current_stress_level
        
        # Get existing connections
        connections = Connection.objects.filter(
            models.Q(user1=user) | models.Q(user2=user),
            status='accepted'
        )
        
        # Get recommended groups
        if stress_level <= 6 and not user.gentle_mode:
            # Can handle more social interaction
            groups = SocialGroup.objects.filter(
                is_gentle=False,
                member_count__lte=50
            )
        else:
            # Gentle social only
            groups = SocialGroup.objects.filter(
                is_gentle=True,
                member_count__lte=20
            )
        
        # Filter by emotional profile
        if emotional_profile in ['anxious', 'avoidant']:
            groups = groups.filter(
                allows_anonymous=True,
                no_obligation=True
            )
        
        return {
            'current_connections': list(connections),
            'recommended_groups': list(groups[:3]),
            'social_limits': {
                'max_daily_interactions': 5 if user.gentle_mode else 10,
                'allow_anonymous': user.allow_anonymous,
                'suggest_one_on_one': emotional_profile in ['anxious', 'avoidant']
            }
        }
    
    @staticmethod
    def record_social_interaction(user, interaction_type, duration_minutes=0):
        """Record social interaction with therapeutic tracking"""
        # Update social metrics
        user.social_interactions += 1
        
        # Social interaction affects stress differently
        if interaction_type in ['positive_chat', 'helpful_feedback']:
            # Positive interaction reduces stress
            user.current_stress_level = max(1, user.current_stress_level - 1)
        elif interaction_type in ['conflict', 'rejection']:
            # Negative interaction increases stress
            user.current_stress_level = min(10, user.current_stress_level + 2)
        
        # Long social sessions can be draining
        if duration_minutes >= 30:
            user.current_stress_level = min(10, user.current_stress_level + 1)
        
        # Record breakthrough for social anxiety progress
        if emotional_profile in ['anxious', 'avoidant'] and interaction_type == 'positive_chat':
            user.add_breakthrough_moment(
                f"Positive social interaction: {interaction_type}"
            )
        
        user.save()
        
        return {
            'social_interactions': user.social_interactions,
            'stress_change': user.current_stress_level,
            'suggestion': SocialIntegration._get_social_suggestion(user, interaction_type)
        }
    
    @staticmethod
    def _get_social_suggestion(user, interaction_type):
        """Get therapeutic suggestion after social interaction"""
        if interaction_type in ['conflict', 'rejection']:
            return "Remember that social challenges are normal. Be gentle with yourself."
        elif user.current_stress_level >= 7:
            return "That was enough social interaction for now. Take a break."
        else:
            return "Nice social interaction! Consider taking a moment to reflect."


class UserSocialProfile(models.Model):
    """Extended social profile for users"""
    user = models.OneToOneField('users.TherapeuticUser', on_delete=models.CASCADE)
    social_comfort_level = models.IntegerField(default=3)  # 1-5 scale
    preferred_interaction_types = models.JSONField(default=list)
    social_goals = models.TextField(blank=True)
    connection_history = models.JSONField(default=list)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Social profile for {self.user.username}"
    
    def update_comfort_level(self, interaction_success):
        """Update social comfort level based on interaction success"""
        if interaction_success:
            self.social_comfort_level = min(5, self.social_comfort_level + 1)
        else:
            self.social_comfort_level = max(1, self.social_comfort_level - 1)
        self.save()