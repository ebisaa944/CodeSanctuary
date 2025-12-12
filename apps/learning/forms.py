from django import forms
from .models import MicroActivity, UserProgress, LearningPath
from django.core.exceptions import ValidationError

class MicroActivityForm(forms.ModelForm):
    """Form for creating/editing micro activities"""
    
    class Meta:
        model = MicroActivity
        fields = [
            'title', 'short_description', 'full_description',
            'activity_type', 'therapeutic_focus', 'difficulty_level',
            'primary_language', 'tech_stack', 'estimated_minutes',
            'no_time_limit', 'infinite_retries', 'skip_allowed',
            'gentle_feedback', 'learning_objectives', 'prerequisites',
            'starter_code', 'solution_code', 'test_cases', 'validation_type',
            'video_url', 'documentation_url', 'additional_resources',
            'therapeutic_instructions', 'coping_suggestions',
            'success_affirmations', 'learning_path', 'order_position'
        ]
        widgets = {
            'short_description': forms.TextInput(attrs={
                'class': 'short-desc-input',
                'maxlength': '300'
            }),
            'full_description': forms.Textarea(attrs={
                'rows': 6,
                'class': 'full-desc-textarea'
            }),
            'difficulty_level': forms.Select(attrs={
                'class': 'difficulty-select',
                'onchange': 'updateDifficultyGuidance(this.value)'
            }),
            'estimated_minutes': forms.NumberInput(attrs={
                'min': 1,
                'max': 60,
                'class': 'time-estimate'
            }),
            'learning_objectives': forms.Textarea(attrs={
                'rows': 4,
                'class': 'objectives-textarea',
                'placeholder': 'One objective per line...'
            }),
            'starter_code': forms.Textarea(attrs={
                'rows': 10,
                'class': 'code-editor',
                'placeholder': 'Starter code here...'
            }),
            'therapeutic_instructions': forms.Textarea(attrs={
                'rows': 6,
                'class': 'therapeutic-textarea',
                'placeholder': 'Pre, during, and post activity guidance...'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate therapeutic focus based on difficulty
        difficulty = cleaned_data.get('difficulty_level', 1)
        therapeutic_focus = cleaned_data.get('therapeutic_focus')
        
        if difficulty == 1 and therapeutic_focus != 'confidence':
            self.add_warning("Gentle activities should focus on confidence building")
        
        if difficulty >= 4 and therapeutic_focus == 'confidence':
            self.add_warning("Challenging activities might be better suited for other focuses")
        
        # Validate time limits
        estimated_minutes = cleaned_data.get('estimated_minutes', 5)
        no_time_limit = cleaned_data.get('no_time_limit', True)
        
        if not no_time_limit and estimated_minutes > 30:
            raise ValidationError(
                "Timed activities should be 30 minutes or less"
            )
        
        return cleaned_data


class ActivitySubmissionForm(forms.ModelForm):
    """Form for submitting activity solutions"""
    
    class Meta:
        model = UserProgress
        fields = [
            'submitted_code', 'emotional_state_before',
            'emotional_state_after', 'stress_level_before',
            'stress_level_after', 'confidence_before',
            'confidence_after', 'self_assessment',
            'reflection_notes', 'what_went_well',
            'challenges_faced', 'coping_strategies_used'
        ]
        widgets = {
            'submitted_code': forms.Textarea(attrs={
                'rows': 15,
                'class': 'code-submission',
                'placeholder': 'Paste your solution here...'
            }),
            'reflection_notes': forms.Textarea(attrs={
                'rows': 4,
                'class': 'reflection-textarea',
                'placeholder': 'How did it feel to work on this?...'
            }),
            'stress_level_before': forms.NumberInput(attrs={
                'type': 'range',
                'min': 1,
                'max': 10,
                'class': 'stress-slider',
                'oninput': 'updateStressDisplay(this.value, "before")'
            }),
            'stress_level_after': forms.NumberInput(attrs={
                'type': 'range',
                'min': 1,
                'max': 10,
                'class': 'stress-slider',
                'oninput': 'updateStressDisplay(this.value, "after")'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.activity = kwargs.pop('activity', None)
        super().__init__(*args, **kwargs)
        
        # Add therapeutic help text
        self.fields['reflection_notes'].help_text = "Be kind to yourself in your reflection"
        self.fields['self_assessment'].help_text = "1=struggled, 5=proud"
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate stress levels
        stress_before = cleaned_data.get('stress_level_before')
        stress_after = cleaned_data.get('stress_level_after')
        
        if stress_before and stress_after:
            if stress_after - stress_before > 5:
                self.add_warning("Big stress increase - consider a gentle break")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.user:
            instance.user = self.user
        if self.activity:
            instance.activity = self.activity
        
        if commit:
            instance.save()
        
        return instance


class LearningPathForm(forms.ModelForm):
    """Form for creating/editing learning paths"""
    
    class Meta:
        model = LearningPath
        fields = [
            'name', 'description', 'difficulty_level',
            'target_language', 'recommended_for_profiles',
            'estimated_total_hours', 'max_daily_minutes',
            'modules'
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 4,
                'class': 'path-description'
            }),
            'recommended_for_profiles': forms.SelectMultiple(attrs={
                'class': 'profile-select'
            }),
            'modules': forms.Textarea(attrs={
                'rows': 6,
                'class': 'modules-textarea',
                'placeholder': 'List module IDs or names...'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate therapeutic recommendations
        difficulty = cleaned_data.get('difficulty_level', 1)
        recommended_profiles = cleaned_data.get('recommended_for_profiles', [])
        
        if difficulty >= 4 and 'anxious' in recommended_profiles:
            raise ValidationError(
                "High difficulty paths may not be suitable for anxious profiles"
            )
        
        # Validate time limits
        estimated_hours = cleaned_data.get('estimated_total_hours', 10)
        max_daily = cleaned_data.get('max_daily_minutes', 30)
        
        if max_daily < 15:
            self.add_warning("Very low daily limit - path may take longer")
        
        return cleaned_data


class GentleActivitySelectorForm(forms.Form):
    """Form for selecting activities based on therapeutic state"""
    
    TIME_CHOICES = [
        (5, '5 minutes (Quick)'),
        (15, '15 minutes (Short)'),
        (30, '30 minutes (Medium)'),
        (60, '60 minutes (Long)')
    ]
    
    available_time = forms.ChoiceField(
        choices=TIME_CHOICES,
        widget=forms.Select(attrs={'class': 'time-select'})
    )
    
    current_energy = forms.ChoiceField(
        choices=[
            ('low', 'Low energy'),
            ('medium', 'Medium energy'),
            ('high', 'High energy')
        ],
        widget=forms.RadioSelect(attrs={'class': 'energy-radio'})
    )
    
    focus_area = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Any'),
            ('python', 'Python'),
            ('web', 'Web Development'),
            ('django', 'Django')
        ],
        widget=forms.Select(attrs={'class': 'focus-select'})
    )
    
    therapeutic_goal = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Any'),
            ('confidence', 'Build confidence'),
            ('focus', 'Improve focus'),
            ('patience', 'Practice patience'),
            ('creativity', 'Spark creativity')
        ],
        widget=forms.Select(attrs={'class': 'goal-select'})
    )
    
    def get_recommendations(self, user):
        """Get activity recommendations based on form data"""
        from .models import MicroActivity
        
        time_limit = int(self.cleaned_data['available_time'])
        energy = self.cleaned_data['current_energy']
        focus = self.cleaned_data.get('focus_area')
        goal = self.cleaned_data.get('therapeutic_goal')
        
        # Start with suitable activities
        activities = MicroActivity.objects.filter(
            estimated_minutes__lte=time_limit,
            is_published=True
        )
        
        # Filter by energy level
        if energy == 'low':
            activities = activities.filter(difficulty_level__lte=2)
        elif energy == 'medium':
            activities = activities.filter(difficulty_level__lte=3)
        # High energy allows all difficulties
        
        # Filter by focus area
        if focus:
            activities = activities.filter(primary_language=focus)
        
        # Filter by therapeutic goal
        if goal:
            activities = activities.filter(therapeutic_focus=goal)
        
        # Apply user's therapeutic restrictions
        if user and hasattr(user, 'get_safe_learning_plan'):
            plan = user.get_safe_learning_plan()
            max_difficulty = plan.get('max_difficulty', 3)
            activities = activities.filter(difficulty_level__lte=max_difficulty)
        
        return activities.order_by('difficulty_level')[:5]