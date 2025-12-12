from django import forms
from .models import GentleInteraction, SupportCircle, CircleMembership
from django.core.exceptions import ValidationError
from django.forms import JSONField  # FIXED


# ---------------------------------------
# Helper mixin for warnings
# ---------------------------------------
class WarningMixin:
    """Allows forms to collect non-blocking warnings."""

    def add_warning(self, message):
        if not hasattr(self, "_warnings"):
            self._warnings = []
        self._warnings.append(message)

    def get_warnings(self):
        return getattr(self, "_warnings", [])


# ---------------------------------------
# Gentle Interaction Form
# ---------------------------------------
class GentleInteractionForm(WarningMixin, forms.ModelForm):

    class Meta:
        model = GentleInteraction
        fields = [
            'interaction_type', 'recipient', 'title', 'message',
            'visibility', 'allow_replies', 'therapeutic_intent',
            'expected_response_time'
        ]
        widgets = {
            'interaction_type': forms.Select(attrs={
                'class': 'interaction-type-select',
                'onchange': 'updateInteractionGuidance(this.value)'
            }),
            'message': forms.Textarea(attrs={
                'rows': 4,
                'class': 'gentle-message',
                'placeholder': 'Share something gentle and supportive...'
            }),
            'visibility': forms.Select(attrs={'class': 'visibility-select'}),
            'therapeutic_intent': forms.Textarea(attrs={
                'rows': 2,
                'class': 'intent-textarea',
                'placeholder': 'What is your hope for this interaction?...'
            })
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        self.fields['message'].help_text = "Use kind, supportive language"
        self.fields['therapeutic_intent'].help_text = "Optional: your positive intention"

    def clean(self):
        cleaned_data = super().clean()

        # Message length check
        message = cleaned_data.get('message', '')
        if len(message.split()) > 200:
            self.add_warning("Consider keeping messages concise for gentle reading")

        # Visibility rules
        visibility = cleaned_data.get('visibility')
        recipient = cleaned_data.get('recipient')

        if visibility == 'private' and not recipient:
            raise ValidationError("Private messages require a recipient")

        if visibility == 'anonymous' and recipient:
            self.add_warning("Anonymous messages typically go to the community")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.user and instance.visibility != 'anonymous':
            instance.sender = self.user

        if commit:
            instance.save()

        return instance


# ---------------------------------------
# Quick Encouragement Form
# ---------------------------------------
class QuickEncouragementForm(forms.Form):

    MESSAGE_CHOICES = [
        ('keep_going', 'You\'re doing great! Keep going. 💪'),
        ('proud', 'I\'m proud of your effort today. 🌟'),
        ('progress', 'Every small step is progress. 🚶‍♂️'),
        ('breathe', 'Remember to breathe. You\'ve got this. 🌬️'),
        ('kind', 'Be kind to yourself today. You deserve it. ❤️'),
        ('custom', 'Write my own message...')
    ]

    message_type = forms.ChoiceField(
        choices=MESSAGE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'message-radio'})
    )

    custom_message = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'custom-message',
            'placeholder': 'Your gentle message...',
            'maxlength': '100'
        })
    )

    anonymous = forms.BooleanField(
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'anonymous-checkbox'})
    )

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('message_type') == 'custom' and not cleaned_data.get('custom_message'):
            raise ValidationError("Please write a custom message")

        return cleaned_data

    def create_interaction(self, user, recipient=None):
        message_type = self.cleaned_data['message_type']
        anonymous = self.cleaned_data['anonymous']

        if message_type == 'custom':
            message = self.cleaned_data['custom_message']
        else:
            message = dict(self.MESSAGE_CHOICES)[message_type]

        visibility = 'anonymous' if anonymous else 'community'

        return GentleInteraction.objects.create(
            sender=None if anonymous else user,
            recipient=recipient,
            interaction_type='encouragement',
            message=message,
            visibility=visibility
        )


# ---------------------------------------
# Support Circle Form
# ---------------------------------------
class SupportCircleForm(WarningMixin, forms.ModelForm):

    class Meta:
        model = SupportCircle
        fields = [
            'name', 'description', 'max_members', 'is_public',
            'join_code', 'focus_areas', 'community_guidelines',
            'meeting_schedule'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'circle-description'}),
            'community_guidelines': forms.Textarea(attrs={
                'rows': 6,
                'class': 'guidelines-textarea',
                'placeholder': 'Our gentle community agreements...'
            }),
            'meeting_schedule': forms.Textarea(attrs={
                'rows': 4,
                'class': 'schedule-textarea',
                'placeholder': 'Weekly meeting times...'
            })
        }

    def __init__(self, *args, **kwargs):
        self.creator = kwargs.pop('creator', None)
        super().__init__(*args, **kwargs)

        self.fields['join_code'].help_text = "Optional code for private circles"
        self.fields['focus_areas'].help_text = "Comma-separated therapeutic focus areas"

    def clean(self):
        cleaned_data = super().clean()
        max_members = cleaned_data.get('max_members', 10)

        if max_members < 3:
            raise ValidationError("Support circles need at least 3 members")

        if max_members > 50:
            self.add_warning("Large circles can be overwhelming for some")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        if self.creator and not instance.pk:
            instance.created_by = self.creator

        if commit:
            instance.save()

            # Auto-join creator
            if self.creator:
                CircleMembership.objects.create(
                    circle=instance,
                    user=self.creator,
                    role='leader'
                )
                instance.active_members = 1
                instance.save(update_fields=['active_members'])

        return instance


# ---------------------------------------
# Circle Join Form
# ---------------------------------------
class CircleJoinForm(forms.Form):
    join_code = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'join-code-input',
            'placeholder': 'Enter join code if required'
        }),
        max_length=20
    )

    introduction = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'introduction-textarea',
            'placeholder': 'Brief introduction (optional)...'
        }),
        max_length=300
    )

    notification_preferences = JSONField(
        initial={'new_messages': True, 'meeting_reminders': True},
        widget=forms.HiddenInput()
    )

    def clean(self):
        cleaned_data = super().clean()

        circle = getattr(self, 'circle', None)

        if circle and not circle.is_public:
            code = cleaned_data.get('join_code', '')
            if code != circle.join_code:
                raise ValidationError("Invalid join code")

        return cleaned_data


# ---------------------------------------
# Achievement Share Form
# ---------------------------------------
class AchievementShareForm(forms.Form):

    share_publicly = forms.BooleanField(
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'share-checkbox'})
    )

    reflection = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'achievement-reflection',
            'placeholder': 'What does earning this achievement mean to you?...'
        }),
        max_length=500
    )

    include_encouragement = forms.BooleanField(
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'encouragement-checkbox'})
    )

    def share_achievement(self, user_achievement):
        if self.cleaned_data['share_publicly']:
            message = f"I just earned {user_achievement.achievement.name}!"

            if self.cleaned_data['reflection']:
                message += f" {self.cleaned_data['reflection']}"

            if self.cleaned_data['include_encouragement']:
                message += f" {user_achievement.achievement.therapeutic_message}"

            interaction = GentleInteraction.objects.create(
                sender=user_achievement.user,
                interaction_type='achievement',
                title=f"Achievement: {user_achievement.achievement.name}",
                message=message,
                visibility='community'
            )

            user_achievement.shared_publicly = True
            user_achievement.reflection_notes = self.cleaned_data['reflection']
            user_achievement.save()

            return interaction

        return None
