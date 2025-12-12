from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError

class TherapeuticUserManager(BaseUserManager):
    """Custom manager for TherapeuticUser with therapeutic-specific methods"""
    
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')
            
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('gentle_mode', False)  # Admins don't need gentle mode
        
        return self.create_user(email, username, password, **extra_fields)

class TherapeuticUser(AbstractUser):
    """Advanced therapeutic user model with comprehensive tracking"""
    
    class EmotionalProfile(models.TextChoices):
        AVOIDANT = 'avoidant', 'Tend to avoid challenges'
        ANXIOUS = 'anxious', 'Experience learning anxiety'
        DOUBTFUL = 'doubtful', 'Struggle with self-doubt'
        OVERWHELMED = 'overwhelmed', 'Easily overwhelmed'
        BALANCED = 'balanced', 'Fairly balanced'
        RESILIENT = 'resilient', 'Building resilience'
    
    class LearningStyle(models.TextChoices):
        VISUAL = 'visual', 'Visual learner'
        AUDITORY = 'auditory', 'Auditory learner'
        KINESTHETIC = 'kinesthetic', 'Hands-on learner'
        READING = 'reading', 'Reading/writing learner'
    
    # Core therapeutic fields
    emotional_profile = models.CharField(
        max_length=20,
        choices=EmotionalProfile.choices,
        default=EmotionalProfile.BALANCED,
        db_index=True
    )
    
    learning_style = models.CharField(
        max_length=20,
        choices=LearningStyle.choices,
        default=LearningStyle.VISUAL,
        null=True,
        blank=True
    )
    
    # Time management with validation
    daily_time_limit = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(180)],
        help_text="Maximum recommended learning minutes per day"
    )
    
    preferred_learning_hours = models.JSONField(
        default=list,
        blank=True,
        help_text="List of preferred hours for learning (0-23)"
    )
    
    # Therapeutic preferences
    gentle_mode = models.BooleanField(default=True, db_index=True)
    hide_progress = models.BooleanField(default=True)
    allow_anonymous = models.BooleanField(default=True)
    receive_gentle_reminders = models.BooleanField(default=True)
    
    # Progress tracking
    current_stress_level = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        db_index=True
    )
    
    total_learning_minutes = models.PositiveIntegerField(default=0)
    consecutive_days = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    
    # Therapeutic milestones
    therapy_start_date = models.DateField(auto_now_add=True)
    breakthrough_moments = models.JSONField(
        default=list,
        blank=True,
        help_text="List of dates and descriptions of breakthrough moments"
    )
    
    # Avatar and personalization
    avatar_color = models.CharField(max_length=7, default='#3498db')  # Hex color
    custom_affirmation = models.CharField(max_length=200, blank=True)
    
    # Override default manager
    objects = TherapeuticUserManager()
    
    class Meta:
        db_table = 'therapeutic_users'
        verbose_name = 'Therapeutic User'
        verbose_name_plural = 'Therapeutic Users'
        indexes = [
            models.Index(fields=['emotional_profile', 'gentle_mode']),
            models.Index(fields=['current_stress_level']),
        ]
        ordering = ['-date_joined']
    
    def __str__(self):
        return f"{self.username} ({self.get_emotional_profile_display()})"
    
    def clean(self):
        """Custom validation"""
        if self.current_stress_level > 10 or self.current_stress_level < 1:
            raise ValidationError({
                'current_stress_level': 'Stress level must be between 1 and 10'
            })
    
    def get_safe_learning_plan(self):
        """Generate adaptive learning plan based on multiple factors"""
        from django.utils import timezone
        
        # Check if user had recent activity
        today = timezone.now().date()
        if self.last_activity_date == today:
            return self._get_gentle_review_plan()
        
        # Adaptive plan based on stress and time of day
        hour = timezone.now().hour
        is_preferred_hour = hour in self.preferred_learning_hours if self.preferred_learning_hours else True
        
        if self.current_stress_level >= 7:
            return {
                'type': 'gentle_review',
                'max_duration': 15,
                'max_difficulty': 1,
                'allow_skipping': True,
                'require_breaks': True,
                'break_frequency': 5,  # minutes
                'suggested_activities': ['breathing_exercise', 'review_past_success']
            }
        elif self.current_stress_level >= 5 or not is_preferred_hour:
            return {
                'type': 'comfort_zone',
                'max_duration': 25,
                'max_difficulty': 2,
                'allow_skipping': True,
                'require_breaks': True,
                'break_frequency': 10,
                'suggested_activities': ['practice_patterns', 'watch_tutorial']
            }
        else:
            return {
                'type': 'growth_focused',
                'max_duration': self.daily_time_limit,
                'max_difficulty': 3,
                'allow_skipping': False,
                'require_breaks': False,
                'suggested_activities': ['new_concept', 'mini_project']
            }
    
    def update_streak(self):
        """Update consecutive days streak"""
        today = timezone.now().date()
        
        if self.last_activity_date:
            days_diff = (today - self.last_activity_date).days
            if days_diff == 1:
                self.consecutive_days += 1
            elif days_diff > 1:
                self.consecutive_days = 1
            else:
                # Same day, don't update
                pass
        else:
            self.consecutive_days = 1
        
        self.last_activity_date = today
        self.save(update_fields=['consecutive_days', 'last_activity_date'])
    
    def add_breakthrough_moment(self, description):
        """Record a therapeutic breakthrough"""
        self.breakthrough_moments.append({
            'date': timezone.now().isoformat(),
            'description': description
        })
        self.save(update_fields=['breakthrough_moments'])
    
    @property
    def learning_streak_badge(self):
        """Return streak badge based on consecutive days"""
        if self.consecutive_days >= 30:
            return '🔥 30+ Day Streak'
        elif self.consecutive_days >= 14:
            return '🌟 2+ Week Streak'
        elif self.consecutive_days >= 7:
            return '✨ 1 Week Streak'
        elif self.consecutive_days >= 3:
            return '💪 3+ Day Streak'
        return '🌱 Getting Started'