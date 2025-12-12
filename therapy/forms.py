from django import forms
from .models import EmotionalCheckIn, CopingStrategy
from django.core.exceptions import ValidationError

class EmotionalCheckInForm(forms.ModelForm):
    """Form for emotional checkin with therapeutic guidance"""
    
    class Meta:
        model = EmotionalCheckIn
        fields = [
            'primary_emotion', 'secondary_emotions', 'intensity',
            'physical_symptoms', 'trigger_description', 'context_tags',
            'coping_strategies_used', 'coping_effectiveness',
            'notes', 'key_insight'
        ]
        widgets = {
            'primary_emotion': forms.Select(attrs={
                'class': 'emotion-select gentle-select',
                'onchange': 'updateEmotionGuidance(this.value)'
            }),
            'intensity': forms.NumberInput(attrs={
                'type': 'range',
                'min': 1,
                'max': 10,
                'class': 'intensity-slider',
                'oninput': 'updateIntensityDisplay(this.value)'
            }),
            'physical_symptoms': forms.CheckboxSelectMultiple(
                choices=EmotionalCheckIn.PHYSICAL_SYMPTOMS,
                attrs={'class': 'symptom-checkboxes'}
            ),
            'trigger_description': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'What happened before you felt this way?',
                'class': 'gentle-textarea'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Any other thoughts or feelings...',
                'class': 'gentle-textarea reflection-box'
            }),
            'coping_effectiveness': forms.NumberInput(attrs={
                'type': 'range',
                'min': 1,
                'max': 10,
                'class': 'effectiveness-slider'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add therapeutic help text
        self.fields['primary_emotion'].help_text = "Choose the emotion that feels strongest right now"
        self.fields['intensity'].help_text = "How strong is this feeling? (1=barely there, 10=overwhelming)"
        self.fields['physical_symptoms'].help_text = "Notice any physical sensations"
        self.fields['key_insight'].help_text = "Any small realization about this experience?"
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check intensity consistency
        emotion = cleaned_data.get('primary_emotion')
        intensity = cleaned_data.get('intensity')
        
        if emotion and intensity:
            if emotion in ['calm', 'hopeful'] and intensity > 8:
                self.add_warning("High intensity for positive emotion - that's interesting to notice")
            elif emotion in ['anxious', 'overwhelmed'] and intensity < 3:
                self.add_warning("Low intensity for challenging emotion - that's worth noting")
        
        return cleaned_data


class QuickCheckInForm(forms.Form):
    """Quick checkin form for immediate emotional tracking"""
    
    EMOTION_CHOICES = [
        ('😰', 'Anxious'),
        ('😵', 'Overwhelmed'),
        ('😔', 'Down'),
        ('😴', 'Tired'),
        ('😌', 'Calm'),
        ('🎯', 'Focused'),
        ('🌟', 'Hopeful'),
        ('😤', 'Frustrated'),
    ]
    
    emotion = forms.ChoiceField(
        choices=EMOTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'emotion-radio'})
    )
    
    intensity = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'type': 'range',
            'min': 1,
            'max': 5,
            'class': 'quick-intensity',
            'value': 3
        })
    )
    
    note = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Quick note (optional)',
            'class': 'quick-note'
        }),
        max_length=100
    )
    
    def save(self, user):
        """Save quick checkin"""
        emotion_display = dict(self.EMOTION_CHOICES)[self.cleaned_data['emotion']]
        
        return EmotionalCheckIn.objects.create(
            user=user,
            primary_emotion=emotion_display.lower(),
            intensity=self.cleaned_data['intensity'] * 2,  # Scale 1-5 to 2-10
            notes=self.cleaned_data.get('note', '')
        )


class CopingStrategyForm(forms.ModelForm):
    """Form for creating/editing coping strategies"""
    
    class Meta:
        model = CopingStrategy
        fields = [
            'name', 'description', 'strategy_type', 'target_emotions',
            'estimated_minutes', 'difficulty_level', 'coding_integration',
            'coding_language', 'coding_template', 'instructions',
            'tips_for_success', 'common_challenges'
        ]
        widgets = {
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'strategy-description'
            }),
            'target_emotions': forms.SelectMultiple(attrs={
                'class': 'target-emotions-select'
            }),
            'instructions': forms.Textarea(attrs={
                'rows': 6,
                'class': 'instruction-textarea',
                'placeholder': 'Step-by-step instructions...'
            }),
            'coding_template': forms.Textarea(attrs={
                'rows': 8,
                'class': 'code-template',
                'placeholder': 'Coding template here...'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate coding integration
        coding_integration = cleaned_data.get('coding_integration', False)
        coding_language = cleaned_data.get('coding_language')
        coding_template = cleaned_data.get('coding_template')
        
        if coding_integration and (not coding_language or not coding_template):
            raise ValidationError(
                "Coding integration requires both language and template"
            )
        
        # Validate difficulty for target emotions
        difficulty = cleaned_data.get('difficulty_level', 1)
        target_emotions = cleaned_data.get('target_emotions', [])
        
        if 'anxious' in target_emotions and difficulty > 4:
            raise ValidationError(
                "Strategies for anxiety should be lower difficulty"
            )
        
        return cleaned_data


class StrategyRecommendationForm(forms.Form):
    """Form for getting coping strategy recommendations"""
    
    emotion = forms.ChoiceField(
        choices=EmotionalCheckIn.PrimaryEmotion.choices,
        widget=forms.Select(attrs={'class': 'emotion-select'})
    )
    
    intensity = forms.IntegerField(
        min_value=1,
        max_value=10,
        widget=forms.NumberInput(attrs={
            'type': 'range',
            'class': 'intensity-slider'
        })
    )
    
    time_available = forms.IntegerField(
        min_value=1,
        max_value=60,
        label="Minutes available",
        widget=forms.NumberInput(attrs={
            'class': 'time-input',
            'placeholder': '5'
        })
    )
    
    prefer_coding = forms.BooleanField(
        required=False,
        label="Include coding activities",
        widget=forms.CheckboxInput(attrs={'class': 'coding-preference'})
    )
    
    def get_recommendations(self):
        """Get strategy recommendations based on form data"""
        emotion = self.cleaned_data['emotion']
        intensity = self.cleaned_data['intensity']
        time_available = self.cleaned_data['time_available']
        prefer_coding = self.cleaned_data['prefer_coding']
        
        # Query strategies
        strategies = CopingStrategy.objects.filter(
            target_emotions__contains=[emotion],
            estimated_minutes__lte=time_available,
            is_active=True
        )
        
        if prefer_coding:
            strategies = strategies.filter(coding_integration=True)
        
        # Filter by intensity
        if intensity >= 7:
            strategies = strategies.filter(difficulty_level__lte=2)
        elif intensity >= 5:
            strategies = strategies.filter(difficulty_level__lte=3)
        
        return strategies.order_by('difficulty_level')[:5]