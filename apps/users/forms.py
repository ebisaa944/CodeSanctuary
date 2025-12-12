from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.core.exceptions import ValidationError
from .models import TherapeuticUser

class TherapeuticUserCreationForm(UserCreationForm):
    """Form for creating therapeutic users with gentle defaults"""
    
    class Meta:
        model = TherapeuticUser
        fields = [
            'username', 'email', 'password1', 'password2',
            'emotional_profile', 'gentle_mode', 'daily_time_limit'
        ]
        widgets = {
            'emotional_profile': forms.Select(attrs={
                'class': 'gentle-select',
                'data-gentle': 'true'
            }),
            'gentle_mode': forms.CheckboxInput(attrs={
                'class': 'gentle-checkbox',
                'checked': True
            }),
            'daily_time_limit': forms.NumberInput(attrs={
                'class': 'gentle-number',
                'min': 5,
                'max': 180,
                'value': 30
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add therapeutic help text
        self.fields['emotional_profile'].help_text = "This helps us personalize your learning experience"
        self.fields['gentle_mode'].help_text = "Start with extra support and gentle pacing"
        self.fields['daily_time_limit'].help_text = "Maximum minutes per day (5-180)"
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Apply therapeutic rules
        emotional_profile = cleaned_data.get('emotional_profile')
        gentle_mode = cleaned_data.get('gentle_mode', True)
        
        if emotional_profile in ['anxious', 'overwhelmed'] and not gentle_mode:
            cleaned_data['gentle_mode'] = True
            self.add_warning("Gentle mode enabled for your emotional profile")
        
        return cleaned_data


class TherapeuticUserChangeForm(UserChangeForm):
    """Form for updating therapeutic user settings"""
    
    class Meta:
        model = TherapeuticUser
        fields = [
            'email', 'first_name', 'last_name',
            'emotional_profile', 'learning_style',
            'daily_time_limit', 'gentle_mode',
            'hide_progress', 'allow_anonymous',
            'avatar_color', 'custom_affirmation'
        ]
        widgets = {
            'emotional_profile': forms.Select(attrs={'class': 'therapeutic-select'}),
            'learning_style': forms.Select(attrs={'class': 'learning-style-select'}),
            'custom_affirmation': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Write a kind affirmation for yourself...',
                'class': 'gentle-textarea'
            }),
            'avatar_color': forms.TextInput(attrs={
                'type': 'color',
                'class': 'color-picker'
            })
        }
    
    def clean_daily_time_limit(self):
        """Validate daily time limit"""
        limit = self.cleaned_data['daily_time_limit']
        if limit < 5:
            raise ValidationError("Minimum 5 minutes per day")
        if limit > 180:
            raise ValidationError("Maximum 180 minutes per day")
        return limit
    
    def clean(self):
        """Apply therapeutic validation rules"""
        cleaned_data = super().clean()
        
        # Check if stress level requires gentle mode
        current_stress = self.instance.current_stress_level if self.instance else 5
        if current_stress >= 7:
            cleaned_data['gentle_mode'] = True
        
        # Validate preferred hours
        if 'preferred_learning_hours' in cleaned_data:
            hours = cleaned_data['preferred_learning_hours']
            if hours and (min(hours) < 0 or max(hours) > 23):
                raise ValidationError("Hours must be between 0 and 23")
        
        return cleaned_data


class EmotionalProfileUpdateForm(forms.ModelForm):
    """Form specifically for updating emotional profile"""
    
    class Meta:
        model = TherapeuticUser
        fields = ['emotional_profile', 'current_stress_level', 'gentle_mode']
        widgets = {
            'emotional_profile': forms.Select(attrs={
                'class': 'emotional-profile-select',
                'onchange': 'updateTherapeuticSuggestions(this.value)'
            }),
            'current_stress_level': forms.NumberInput(attrs={
                'type': 'range',
                'min': 1,
                'max': 10,
                'class': 'stress-slider',
                'oninput': 'updateStressValue(this.value)'
            }),
            'gentle_mode': forms.CheckboxInput(attrs={
                'class': 'gentle-toggle'
            })
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Auto-enable gentle mode for high stress
        stress = cleaned_data.get('current_stress_level')
        if stress and stress >= 7:
            cleaned_data['gentle_mode'] = True
        
        return cleaned_data


class GentleLoginForm(forms.Form):
    """Gentle login form with therapeutic messaging"""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'gentle-input',
            'placeholder': 'Your username',
            'autocomplete': 'username'
        }),
        label="Username"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'gentle-input',
            'placeholder': 'Your password',
            'autocomplete': 'current-password'
        }),
        label="Password"
    )
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'gentle-checkbox'
        }),
        label="Remember me for 14 days"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = "Take your time, there's no rush"
        self.fields['password'].help_text = ""


class PasswordResetGentleForm(forms.Form):
    """Gentle password reset form"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'gentle-input',
            'placeholder': 'Your email address'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].help_text = "We'll send you a gentle reminder to reset your password"