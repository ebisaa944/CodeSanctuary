# social/forms.py
"""
Forms for therapeutic social app
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import GentleInteraction, SupportCircle, CircleMembership, Achievement

User = get_user_model()


class GentleInteractionForm(forms.ModelForm):
    """
    Form for creating therapeutic interactions
    """
    
    class Meta:
        model = GentleInteraction
        fields = [
            'title', 'message', 'interaction_type', 
            'visibility', 'therapeutic_intent',
            'allow_replies', 'is_pinned', 'anonymous'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Give your interaction a title...'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your thoughts...'
            }),
            'interaction_type': forms.Select(attrs={'class': 'form-select'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
            'therapeutic_intent': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'What is the therapeutic purpose of this interaction?'
            }),
            'allow_replies': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_pinned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'anonymous': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_message(self):
        message = self.cleaned_data.get('message', '')
        
        # Check for concerning language
        concerning_patterns = [
            r'\b(kill|die|suicide|hurt myself)\b',
            r'\b(hate|worthless|stupid|idiot)\b',
        ]
        
        for pattern in concerning_patterns:
            if re.search(pattern, message.lower()):
                raise ValidationError(
                    "This contains language that may need therapeutic support. "
                    "Please reach out to a mental health professional if you're in crisis."
                )
        
        # Check length
        word_count = len(message.split())
        if word_count > 500:
            raise ValidationError(
                "Messages should be concise for gentle reading (max 500 words)."
            )
        
        return message
    
    def clean_title(self):
        title = self.cleaned_data.get('title', '')
        
        if title:
            # Check title length
            if len(title) > 200:
                raise ValidationError("Title is too long (max 200 characters).")
        
        return title


class QuickEncouragementForm(forms.Form):
    """
    Form for sending quick encouragement
    """
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Share some encouraging words...'
        }),
        max_length=500
    )
    recipient_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput()
    )
    anonymous = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_message(self):
        message = self.cleaned_data.get('message', '')
        
        if len(message.strip()) < 5:
            raise ValidationError("Please write a meaningful message.")
        
        return message.strip()


class SupportCircleForm(forms.ModelForm):
    """
    Form for creating support circles
    """
    
    class Meta:
        model = SupportCircle
        fields = [
            'name', 'description', 'focus_areas',
            'max_members', 'is_public', 'allow_anonymous',
            'join_code'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Circle name...'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the purpose of this circle...'
            }),
            'focus_areas': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., anxiety, stress, self-care'
            }),
            'max_members': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 5,
                'max': 100
            }),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'allow_anonymous': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'join_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional join code for private circles'
            }),
        }
    
    def clean_max_members(self):
        max_members = self.cleaned_data.get('max_members')
        
        if max_members < 5:
            raise ValidationError("Support circles must have at least 5 member capacity.")
        if max_members > 100:
            raise ValidationError("Support circles cannot have more than 100 members.")
        
        return max_members
    
    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        
        if not name:
            raise ValidationError("Circle name is required.")
        
        if len(name) > 100:
            raise ValidationError("Circle name is too long (max 100 characters).")
        
        return name
    
    def clean_join_code(self):
        join_code = self.cleaned_data.get('join_code', '').strip()
        is_public = self.cleaned_data.get('is_public', True)
        
        if not is_public and not join_code:
            raise ValidationError(
                "Private circles require a join code."
            )
        
        return join_code


class CircleJoinForm(forms.Form):
    """
    Form for joining a support circle
    """
    
    join_code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter join code...'
        })
    )
    introduction = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Tell the circle a bit about yourself...'
        }),
        max_length=500
    )
    
    def __init__(self, *args, **kwargs):
        self.circle = kwargs.pop('circle', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Only require join code for private circles
        if self.circle and self.circle.is_public:
            self.fields['join_code'].required = False
            self.fields['join_code'].widget = forms.HiddenInput()
        else:
            self.fields['join_code'].required = True
    
    def clean_join_code(self):
        join_code = self.cleaned_data.get('join_code', '').strip()
        
        if self.circle and not self.circle.is_public:
            if join_code != self.circle.join_code:
                raise ValidationError("Invalid join code.")
        
        return join_code
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check if user is already a member
        if self.user and self.circle:
            if CircleMembership.objects.filter(
                circle=self.circle,
                user=self.user
            ).exists():
                raise ValidationError("You are already a member of this circle.")
            
            # Check if circle is full
            if self.circle.active_members >= self.circle.max_members:
                raise ValidationError("This support circle is full.")
        
        return cleaned_data


class AchievementShareForm(forms.Form):
    """
    Form for sharing achievements
    """
    
    reflection = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'What does this achievement mean to you?'
        }),
        max_length=1000
    )
    share_publicly = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )