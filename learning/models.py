from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.text import slugify
import json

class LearningPath(models.Model):
    """Curriculum path for therapeutic learning"""
    
    class PathDifficulty(models.IntegerChoices):
        GENTLE = 1, '🌱 Gentle Introduction'
        BUILDING = 2, '🌿 Building Confidence'
        COMFORT_PLUS = 3, '🌳 Comfort Zone +1'
        CHALLENGE = 4, '🏔️ Gentle Challenge'
        MASTERY = 5, '🚀 Mastery Track'
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField()
    
    difficulty_level = models.IntegerField(
        choices=PathDifficulty.choices,
        default=PathDifficulty.GENTLE
    )
    
    target_language = models.CharField(
        max_length=20,
        choices=[
            ('python', 'Python'),
            ('web', 'HTML/CSS/JS'),
            ('django', 'Django'),
            ('mixed', 'Mixed Technologies'),
        ]
    )
    
    # Therapeutic considerations
    recommended_for_profiles = models.JSONField(
        default=list,
        help_text="Emotional profiles this path is recommended for"
    )
    
    estimated_total_hours = models.PositiveIntegerField(default=10)
    max_daily_minutes = models.PositiveIntegerField(default=30)
    
    # Structure
    modules = models.JSONField(
        default=list,
        help_text="List of module IDs in order"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['difficulty_level', 'name']
        verbose_name_plural = 'Learning Paths'
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({self.get_difficulty_level_display()})"
    
    def get_progress_for_user(self, user):
        """Calculate user progress through this path"""
        completed = UserProgress.objects.filter(
            user=user,
            activity__learning_path=self,
            completed=True
        ).count()
        
        total = MicroActivity.objects.filter(learning_path=self).count()
        
        return {
            'completed': completed,
            'total': total,
            'percentage': (completed / total * 100) if total > 0 else 0,
            'estimated_remaining': self._estimate_remaining_time(user, completed)
        }
    
    def _estimate_remaining_time(self, user, completed):
        """Estimate remaining learning time"""
        remaining = MicroActivity.objects.filter(
            learning_path=self
        ).count() - completed
        
        avg_time = self.estimated_total_hours * 60 / MicroActivity.objects.filter(
            learning_path=self
        ).count() if MicroActivity.objects.filter(learning_path=self).count() > 0 else 30
        
        return remaining * avg_time


class MicroActivity(models.Model):
    """Professional micro-learning activity with therapeutic design"""
    
    class ActivityType(models.TextChoices):
        CONCEPT = 'concept', 'Concept Introduction'
        PRACTICE = 'practice', 'Practice Exercise'
        PROJECT = 'project', 'Mini Project'
        REVIEW = 'review', 'Review/Reflection'
        CHALLENGE = 'challenge', 'Gentle Challenge'
        GAMIFIED = 'gamified', 'Gamified Learning'
    
    class TherapeuticFocus(models.TextChoices):
        CONFIDENCE = 'confidence', 'Building Confidence'
        PATIENCE = 'patience', 'Developing Patience'
        RESILIENCE = 'resilience', 'Building Resilience'
        FOCUS = 'focus', 'Improving Focus'
        CREATIVITY = 'creativity', 'Encouraging Creativity'
        MINDFULNESS = 'mindfulness', 'Mindful Coding'
    
    # Core identification
    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    short_description = models.CharField(max_length=300)
    full_description = models.TextField()
    
    # Technical details
    activity_type = models.CharField(
        max_length=20,
        choices=ActivityType.choices,
        default=ActivityType.PRACTICE
    )
    
    therapeutic_focus = models.CharField(
        max_length=20,
        choices=TherapeuticFocus.choices,
        default=TherapeuticFocus.CONFIDENCE
    )
    
    difficulty_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        db_index=True
    )
    
    # Language and tech stack
    primary_language = models.CharField(max_length=20)
    tech_stack = models.JSONField(
        default=list,
        blank=True,
        help_text="List of technologies used"
    )
    
    # Time management
    estimated_minutes = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(60)]
    )
    
    # Therapeutic parameters
    no_time_limit = models.BooleanField(default=True)
    infinite_retries = models.BooleanField(default=True)
    skip_allowed = models.BooleanField(default=True)
    gentle_feedback = models.BooleanField(default=True)
    
    # Content
    learning_objectives = models.JSONField(
        default=list,
        help_text="List of learning objectives"
    )
    
    prerequisites = models.JSONField(
        default=list,
        blank=True,
        help_text="List of prerequisite activity IDs"
    )
    
    starter_code = models.TextField(blank=True)
    solution_code = models.TextField(blank=True)
    
    # Testing and validation
    test_cases = models.JSONField(
        default=list,
        blank=True,
        help_text="Test cases for automatic validation"
    )
    
    validation_type = models.CharField(
        max_length=20,
        choices=[
            ('completion', 'Completion is success'),
            ('output_match', 'Output must match'),
            ('test_passing', 'Tests must pass'),
            ('code_review', 'Code review required'),
            ('self_assessment', 'Self-assessment only'),
        ],
        default='completion'
    )
    
    # Multimedia and resources
    video_url = models.URLField(blank=True)
    documentation_url = models.URLField(blank=True)
    additional_resources = models.JSONField(
        default=list,
        blank=True,
        help_text="List of additional resource URLs"
    )
    
    # Therapeutic content
    therapeutic_instructions = models.JSONField(
        default=list,
        help_text="Pre- and post-activity therapeutic guidance"
    )
    
    coping_suggestions = models.JSONField(
        default=list,
        blank=True,
        help_text="Coping strategies for when stuck"
    )
    
    success_affirmations = models.JSONField(
        default=list,
        blank=True,
        help_text="Affirmations for after completion"
    )
    
    # Relationships
    learning_path = models.ForeignKey(
        LearningPath,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activities'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=True)
    order_position = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order_position', 'difficulty_level']
        verbose_name_plural = 'Micro Activities'
        indexes = [
            models.Index(fields=['difficulty_level', 'is_published']),
            models.Index(fields=['therapeutic_focus', 'difficulty_level']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while MicroActivity.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} (Level {self.difficulty_level})"
    
    def get_therapeutic_context(self):
        """Get complete therapeutic framing for this activity"""
        return {
            'preparation': [
                "Find a comfortable, quiet space",
                "Take three deep breaths before starting",
                "Remember: There's no wrong way to learn",
                "You can pause or stop anytime without penalty",
            ],
            'during': [
                "Notice your breathing as you type",
                "If feeling stuck, that's a normal part of learning",
                "Take micro-breaks every few minutes",
                "Focus on the process, not perfection",
            ],
            'completion': [
                "Notice how you feel now compared to before",
                "Acknowledge your effort, regardless of outcome",
                "What's one small thing you learned?",
                "Be kind to yourself about the experience",
            ],
            'affirmations': self.success_affirmations or [
                "Every attempt is progress",
                "Learning is a journey, not a destination",
                "You're building skills and resilience",
            ]
        }
    
    def is_suitable_for_user(self, user):
        """Check if this activity is suitable for the user's current state"""
        user_plan = user.get_safe_learning_plan()
        
        # Check difficulty
        if self.difficulty_level > user_plan['max_difficulty']:
            return False, "Activity may be too challenging right now"
        
        # Check time
        if self.estimated_minutes > user_plan['max_duration']:
            return False, "Activity may be too long for today's limit"
        
        # Check emotional compatibility
        if user.emotional_profile == 'overwhelmed' and self.difficulty_level > 2:
            return False, "Consider something gentler first"
        
        return True, "Activity is suitable"
    
    def validate_solution(self, user_code):
        """Validate user's code solution"""
        if self.validation_type == 'completion':
            return {'success': True, 'message': 'Great job completing the activity!'}
        
        # For more advanced validation, you'd integrate with a code runner
        # This is a simplified version
        return {'success': True, 'message': 'Code submitted successfully!'}


class UserProgress(models.Model):
    """Comprehensive progress tracking with therapeutic insights"""
    
    class ProgressStatus(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        SKIPPED = 'skipped', 'Skipped'
        RETRY_LATER = 'retry_later', 'Retry Later'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='learning_progress',
        db_index=True
    )
    
    activity = models.ForeignKey(
        MicroActivity,
        on_delete=models.CASCADE,
        related_name='user_progress'
    )
    
    # Progress tracking
    status = models.CharField(
        max_length=20,
        choices=ProgressStatus.choices,
        default=ProgressStatus.NOT_STARTED,
        db_index=True
    )
    
    start_time = models.DateTimeField(null=True, blank=True)
    completion_time = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    
    # Attempt tracking
    attempts = models.PositiveIntegerField(default=0)
    successful_attempts = models.PositiveIntegerField(default=0)
    
    # Code submission
    submitted_code = models.TextField(blank=True)
    code_output = models.TextField(blank=True)
    errors = models.TextField(blank=True)
    
    # Emotional tracking
    emotional_state_before = models.CharField(max_length=50, blank=True)
    emotional_state_after = models.CharField(max_length=50, blank=True)
    
    stress_level_before = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    
    stress_level_after = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    
    # Self-assessment
    confidence_before = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    confidence_after = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    self_assessment = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="How do you feel about your attempt? (1=struggled, 5=proud)"
    )
    
    # Feedback and reflection
    reflection_notes = models.TextField(blank=True)
    what_went_well = models.TextField(blank=True)
    challenges_faced = models.TextField(blank=True)
    coping_strategies_used = models.JSONField(default=list, blank=True)
    
    # Technical metrics
    code_quality_score = models.FloatField(null=True, blank=True)
    efficiency_score = models.FloatField(null=True, blank=True)
    
    # Therapeutic insights
    breakthrough_notes = models.TextField(blank=True)
    therapist_feedback = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'activity']
        ordering = ['-updated_at']
        verbose_name_plural = 'User Progress Records'
        indexes = [
            models.Index(fields=['user', 'status', '-updated_at']),
            models.Index(fields=['activity', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.activity.title} ({self.get_status_display()})"
    
    def start_activity(self):
        """Start tracking an activity"""
        self.status = self.ProgressStatus.IN_PROGRESS
        self.start_time = timezone.now()
        self.attempts += 1
        self.save()
    
    def complete_activity(self, success=True, code=''):
        """Mark activity as completed"""
        self.status = self.ProgressStatus.COMPLETED
        self.completion_time = timezone.now()
        
        if success:
            self.successful_attempts += 1
        
        if code:
            self.submitted_code = code
        
        # Calculate time spent
        if self.start_time:
            self.time_spent_seconds = (self.completion_time - self.start_time).total_seconds()
        
        self.save()
        
        # Update user's streak
        self.user.update_streak()
    
    def calculate_emotional_impact(self):
        """Calculate the emotional impact of this activity"""
        if self.stress_level_before and self.stress_level_after:
            stress_change = self.stress_level_after - self.stress_level_before
        else:
            stress_change = None
        
        if self.confidence_before and self.confidence_after:
            confidence_change = self.confidence_after - self.confidence_before
        else:
            confidence_change = None
        
        return {
            'stress_change': stress_change,
            'confidence_change': confidence_change,
            'overall_impact': self._calculate_overall_impact(stress_change, confidence_change)
        }
    
    def _calculate_overall_impact(self, stress_change, confidence_change):
        """Calculate overall therapeutic impact"""
        if stress_change is None or confidence_change is None:
            return 'neutral'
        
        if stress_change < -2 and confidence_change > 1:
            return 'highly_positive'
        elif stress_change < 0 and confidence_change > 0:
            return 'positive'
        elif stress_change > 2 or confidence_change < -1:
            return 'challenging'
        else:
            return 'neutral'
    
    @property
    def is_breakthrough(self):
        """Check if this was a therapeutic breakthrough"""
        impact = self.calculate_emotional_impact()
        return (impact['overall_impact'] == 'highly_positive' or 
                self.breakthrough_notes or 
                (self.confidence_after and self.confidence_after >= 4))