from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
import json

class EmotionalCheckIn(models.Model):
    """Comprehensive emotional tracking with AI suggestions"""
    
    class EmotionIntensity(models.IntegerChoices):
        VERY_LOW = 1, 'Very Low'
        LOW = 2, 'Low'
        MODERATE = 3, 'Moderate'
        HIGH = 4, 'High'
        VERY_HIGH = 5, 'Very High'
    
    class PrimaryEmotion(models.TextChoices):
        ANXIOUS = 'anxious', '😰 Anxious/Worried'
        OVERWHELMED = 'overwhelmed', '😵 Overwhelmed/Stressed'
        DOUBTFUL = 'doubtful', '😔 Self-doubting/Insecure'
        FATIGUED = 'fatigued', '😴 Tired/Fatigued'
        CALM = 'calm', '😌 Calm/Peaceful'
        FOCUSED = 'focused', '🎯 Focused/Concentrated'
        HOPEFUL = 'hopeful', '🌟 Hopeful/Optimistic'
        FRUSTRATED = 'frustrated', '😤 Frustrated/Stuck'
        EXCITED = 'excited', '🚀 Excited/Motivated'
        NEUTRAL = 'neutral', '😐 Neutral/Balanced'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='emotional_checkins',
        db_index=True
    )
    
    primary_emotion = models.CharField(
        max_length=20,
        choices=PrimaryEmotion.choices,
        db_index=True
    )
    
    secondary_emotions = models.JSONField(
        default=list,
        blank=True,
        help_text="List of secondary emotions"
    )
    
    intensity = models.IntegerField(
        choices=EmotionIntensity.choices,
        default=EmotionIntensity.MODERATE
    )
    
    # Physical symptoms tracking
    PHYSICAL_SYMPTOMS = [
        ('headache', 'Headache'),
        ('stomach', 'Stomach discomfort'),
        ('fatigue', 'Fatigue'),
        ('tension', 'Muscle tension'),
        ('sleep', 'Sleep issues'),
        ('appetite', 'Appetite changes'),
        ('breathing', 'Breathing changes'),
        ('heart', 'Heart rate changes'),
        ('none', 'No physical symptoms'),
    ]
    
    physical_symptoms = models.JSONField(
        default=list,
        blank=True,
        help_text="List of physical symptoms experienced"
    )
    
    # Context and triggers
    trigger_description = models.TextField(blank=True)
    context_tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags describing context (work, learning, social, etc.)"
    )
    
    # Coping mechanisms
    coping_strategies_used = models.JSONField(
        default=list,
        blank=True,
        help_text="Coping strategies attempted"
    )
    
    coping_effectiveness = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="How effective were coping strategies (1-10)"
    )
    
    # Reflection and insights
    notes = models.TextField(blank=True, help_text="Free-form reflection")
    key_insight = models.CharField(max_length=200, blank=True)
    
    # Technical fields
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Emotional Check-in'
        verbose_name_plural = 'Emotional Check-ins'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['primary_emotion', 'created_at']),
        ]
        get_latest_by = 'created_at'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_primary_emotion_display()} ({self.created_at.date()})"
    
    def get_emotional_pattern(self):
        """Analyze emotional patterns for insights"""
        recent_checkins = EmotionalCheckIn.objects.filter(
            user=self.user,
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).order_by('created_at')
        
        emotions = [ci.primary_emotion for ci in recent_checkins]
        intensities = [ci.intensity for ci in recent_checkins]
        
        pattern = {
            'dominant_emotion': max(set(emotions), key=emotions.count) if emotions else None,
            'average_intensity': sum(intensities) / len(intensities) if intensities else 0,
            'volatility': max(intensities) - min(intensities) if intensities else 0,
            'common_triggers': self._extract_common_triggers(recent_checkins),
        }
        
        return pattern
    
    def _extract_common_triggers(self, checkins):
        """Extract common triggers from recent checkins"""
        # Simple implementation - extract keywords
        triggers = []
        for checkin in checkins:
            if checkin.trigger_description:
                words = checkin.trigger_description.lower().split()
                triggers.extend([w for w in words if len(w) > 3])
        
        from collections import Counter
        return dict(Counter(triggers).most_common(5))
    
    def suggest_coping_strategies(self):
        """Suggest coping strategies based on emotion and context"""
        strategies = {
            'anxious': [
                {'name': 'Box Breathing', 'duration': 2, 'type': 'breathing'},
                {'name': 'Grounding Exercise', 'duration': 3, 'type': 'mindfulness'},
                {'name': 'Gentle Typing Exercise', 'duration': 5, 'type': 'coding'},
            ],
            'overwhelmed': [
                {'name': 'Micro Task Completion', 'duration': 5, 'type': 'action'},
                {'name': 'Priority List', 'duration': 3, 'type': 'planning'},
                {'name': 'Screen Break', 'duration': 5, 'type': 'physical'},
            ],
            'doubtful': [
                {'name': 'Success Review', 'duration': 10, 'type': 'reflection'},
                {'name': 'Positive Affirmation', 'duration': 2, 'type': 'cognitive'},
                {'name': 'Easy Coding Pattern', 'duration': 7, 'type': 'coding'},
            ],
            'calm': [
                {'name': 'Learning Challenge', 'duration': 20, 'type': 'growth'},
                {'name': 'Teaching Exercise', 'duration': 15, 'type': 'reinforcement'},
                {'name': 'Project Planning', 'duration': 10, 'type': 'planning'},
            ],
        }
        
        return strategies.get(self.primary_emotion, [
            {'name': 'Gentle Breathing', 'duration': 3, 'type': 'breathing'},
            {'name': 'Short Walk', 'duration': 5, 'type': 'physical'},
        ])
    
    @property
    def emotional_summary(self):
        """Generate a summary of the emotional state"""
        return {
            'emotion': self.get_primary_emotion_display(),
            'intensity': self.get_intensity_display(),
            'time_since': self.get_time_since(),
            'suggestions': self.suggest_coping_strategies()[:2],
        }
    
    def get_time_since(self):
        """Get human-readable time since checkin"""
        delta = timezone.now() - self.created_at
        if delta.days > 0:
            return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
        elif delta.seconds > 3600:
            hours = delta.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif delta.seconds > 60:
            minutes = delta.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        return "Just now"


class CopingStrategy(models.Model):
    """Library of therapeutic coping strategies"""
    
    class StrategyType(models.TextChoices):
        BREATHING = 'breathing', 'Breathing Exercise'
        MINDFULNESS = 'mindfulness', 'Mindfulness Practice'
        COGNITIVE = 'cognitive', 'Cognitive Reframing'
        PHYSICAL = 'physical', 'Physical Activity'
        SOCIAL = 'social', 'Social Connection'
        CREATIVE = 'creative', 'Creative Expression'
        CODING = 'coding', 'Coding Integration'
        PLANNING = 'planning', 'Planning/Organization'
    
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    strategy_type = models.CharField(max_length=20, choices=StrategyType.choices)
    
    target_emotions = models.JSONField(
        default=list,
        help_text="List of emotions this strategy helps with"
    )
    
    # Implementation details
    estimated_minutes = models.PositiveIntegerField(default=5)
    difficulty_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # For coding-integrated strategies
    coding_integration = models.BooleanField(default=False)
    coding_language = models.CharField(max_length=20, blank=True)
    coding_template = models.TextField(blank=True)
    
    # Therapeutic guidance
    instructions = models.JSONField(
        default=list,
        help_text="Step-by-step instructions"
    )
    
    tips_for_success = models.TextField(blank=True)
    common_challenges = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['strategy_type', 'difficulty_level']
        verbose_name_plural = 'Coping Strategies'
    
    def __str__(self):
        return f"{self.name} ({self.get_strategy_type_display()})"
    
    def get_recommended_for_user(self, user):
        """Check if this strategy is recommended for a specific user"""
        user_profile = user.emotional_profile.lower()
        
        # Some strategies might be too challenging for certain profiles
        if user_profile == 'avoidant' and self.difficulty_level > 3:
            return False
        if user_profile == 'anxious' and self.estimated_minutes > 10:
            return False
            
        return True