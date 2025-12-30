# chat/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import uuid

from .models import (
    ChatRoom, RoomMembership, ChatMessage,
    MessageReaction, TherapeuticChatSettings
)

User = get_user_model()


class TherapeuticRoomCreationForm(forms.ModelForm):
    """
    Form for creating therapeutic chat rooms with safety considerations
    """
    class Meta:
        model = ChatRoom
        fields = [
            'name', 'room_type', 'description', 'safety_level',
            'is_private', 'is_gated', 'requires_consent',
            'max_participants', 'max_stress_level',
            'therapeutic_goal', 'mood_tracking_enabled',
            'trigger_warnings_required', 'conversation_guidelines',
            'scheduled_open', 'scheduled_close'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter a welcoming room name',
                'autocomplete': 'off'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the purpose and atmosphere of this room...',
                'style': 'resize: vertical;'
            }),
            'room_type': forms.Select(attrs={
                'class': 'form-control therapeutic-select',
                'onchange': 'updateRoomGuidelines(this)'
            }),
            'safety_level': forms.Select(attrs={
                'class': 'form-control safety-level-select',
                'data-toggle': 'tooltip',
                'title': 'Higher safety levels provide more moderation and support'
            }),
            'therapeutic_goal': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What therapeutic outcomes are desired from this space?',
                'style': 'resize: vertical;'
            }),
            'conversation_guidelines': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'One guideline per line...',
                'style': 'resize: vertical;'
            }),
            'max_participants': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '100',
                'step': '1'
            }),
            'max_stress_level': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '10',
                'step': '1',
                'data-toggle': 'tooltip',
                'title': 'Maximum stress level allowed to join (1-10)'
            }),
            'scheduled_open': forms.DateTimeInput(attrs={
                'class': 'form-control datetimepicker',
                'type': 'datetime-local'
            }),
            'scheduled_close': forms.DateTimeInput(attrs={
                'class': 'form-control datetimepicker',
                'type': 'datetime-local'
            }),
            'is_private': forms.CheckboxInput(attrs={
                'class': 'form-check-input therapeutic-checkbox',
                'data-toggle': 'toggle',
                'data-on': 'Private',
                'data-off': 'Public'
            }),
            'is_gated': forms.CheckboxInput(attrs={
                'class': 'form-check-input therapeutic-checkbox',
                'data-toggle': 'tooltip',
                'title': 'Requires emotional readiness assessment'
            }),
            'requires_consent': forms.CheckboxInput(attrs={
                'class': 'form-check-input therapeutic-checkbox',
                'checked': 'checked'
            }),
            'mood_tracking_enabled': forms.CheckboxInput(attrs={
                'class': 'form-check-input therapeutic-checkbox'
            }),
            'trigger_warnings_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input therapeutic-checkbox',
                'checked': 'checked'
            }),
        }
        labels = {
            'name': _('Room Name'),
            'description': _('Description'),
            'room_type': _('Room Type'),
            'safety_level': _('Safety Level'),
            'is_private': _('Private Room'),
            'is_gated': _('Gated Access'),
            'requires_consent': _('Requires Consent'),
            'max_participants': _('Maximum Participants'),
            'max_stress_level': _('Maximum Stress Level'),
            'therapeutic_goal': _('Therapeutic Goal'),
            'mood_tracking_enabled': _('Enable Mood Tracking'),
            'trigger_warnings_required': _('Require Trigger Warnings'),
            'conversation_guidelines': _('Conversation Guidelines'),
        }
        help_texts = {
            'safety_level': _('Select the level of moderation and support needed'),
            'max_stress_level': _('Users with higher stress levels cannot join'),
            'is_gated': _('Users must complete emotional readiness assessment'),
            'conversation_guidelines': _('One guideline per line. These will be displayed to all participants.'),
        }

    def __init__(self, *args, **kwargs):
        self.creator = kwargs.pop('creator', None)
        super().__init__(*args, **kwargs)
        
        # Set therapeutic defaults
        if not self.instance.pk:
            self.fields['conversation_guidelines'].initial = [
                "Practice active listening",
                "Use 'I' statements when sharing",
                "Respect different emotional experiences",
                "Use trigger warnings when discussing difficult topics",
                "Take breaks when needed"
            ]
        
        # Add therapeutic CSS classes
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs['class'] = 'form-control therapeutic-input'
        
        # Make therapeutic goal required for therapeutic rooms
        if self.data.get('room_type') in ['therapy_session', 'peer_support']:
            self.fields['therapeutic_goal'].required = True
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate therapeutic settings
        max_stress_level = cleaned_data.get('max_stress_level')
        if max_stress_level and (max_stress_level < 1 or max_stress_level > 10):
            self.add_error('max_stress_level', 'Must be between 1 and 10')
        
        # Validate schedule
        scheduled_open = cleaned_data.get('scheduled_open')
        scheduled_close = cleaned_data.get('scheduled_close')
        
        if scheduled_open and scheduled_close:
            if scheduled_close <= scheduled_open:
                self.add_error('scheduled_close', 'Close time must be after open time')
        
        # Validate participant limits
        max_participants = cleaned_data.get('max_participants')
        if max_participants and max_participants < 2:
            self.add_error('max_participants', 'Must be at least 2 for therapeutic interaction')
        
        # Validate therapeutic goals for therapeutic rooms
        room_type = cleaned_data.get('room_type')
        therapeutic_goal = cleaned_data.get('therapeutic_goal')
        
        if room_type in ['therapy_session', 'peer_support', 'therapeutic_coding']:
            if not therapeutic_goal or len(therapeutic_goal.strip()) < 20:
                self.add_error('therapeutic_goal', 
                    'Please provide a meaningful therapeutic goal (at least 20 characters)')
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        if self.creator:
            instance.created_by = self.creator
        
        if commit:
            instance.save()
            
            # Auto-add creator as moderator
            if self.creator:
                RoomMembership.objects.create(
                    user=self.creator,
                    room=instance,
                    role='moderator',
                    consent_given=True
                )
        
        return instance


class TherapeuticMessageForm(forms.ModelForm):
    """
    Form for sending therapeutic chat messages with emotional considerations
    """
    is_anonymous = forms.BooleanField(
        required=False,
        initial=False,
        label=_('Send anonymously'),
        help_text=_('Your username will be hidden from other participants'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input anonymous-toggle',
            'data-toggle': 'tooltip',
            'title': 'Only available if you have enabled anonymous posting'
        })
    )
    
    trigger_warning = forms.CharField(
        required=False,
        max_length=200,
        label=_('Trigger Warning'),
        help_text=_('Add content warnings for sensitive topics'),
        widget=forms.TextInput(attrs={
            'class': 'form-control trigger-warning-input',
            'placeholder': 'e.g., mentions of anxiety, trauma, etc.',
            'data-toggle': 'tooltip',
            'title': 'Help others prepare emotionally for difficult content'
        })
    )
    
    emotional_tone = forms.ChoiceField(
        required=False,
        choices=[
            ('', '-- Select emotional tone --'),
            ('hopeful', 'Hopeful'),
            ('anxious', 'Anxious'),
            ('proud', 'Proud'),
            ('vulnerable', 'Vulnerable'),
            ('supportive', 'Supportive'),
            ('curious', 'Curious'),
            ('frustrated', 'Frustrated'),
            ('calm', 'Calm'),
            ('excited', 'Excited'),
            ('sad', 'Sad'),
        ],
        label=_('Emotional Tone'),
        help_text=_('Optional: How are you feeling right now?'),
        widget=forms.Select(attrs={
            'class': 'form-control emotional-tone-select',
            'data-toggle': 'tooltip',
            'title': 'Helps others understand your emotional state'
        })
    )
    
    attachment = forms.FileField(
        required=False,
        label=_('Attachment'),
        help_text=_('Upload images, documents, or code files (max 10MB)'),
        widget=forms.FileInput(attrs={
            'class': 'form-control-file therapeutic-file-input',
            'accept': '.jpg,.jpeg,.png,.gif,.pdf,.doc,.docx,.txt,.py,.js,.html,.css,.json'
        })
    )
    
    class Meta:
        model = ChatMessage
        fields = [
            'content', 'message_type', 'visibility',
            'trigger_warning', 'is_vulnerable_share',
            'coping_strategy_shared', 'contains_affirmation',
            'emotional_tone', 'attachment', 'attachment_caption'
        ]
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control therapeutic-message-input',
                'rows': 4,
                'placeholder': 'Type your message here...',
                'data-toggle': 'tooltip',
                'title': 'Be mindful of your emotional state and the impact of your words',
                'style': 'resize: vertical;'
            }),
            'message_type': forms.Select(attrs={
                'class': 'form-control message-type-select',
                'onchange': 'updateMessageFields(this)'
            }),
            'visibility': forms.Select(attrs={
                'class': 'form-control visibility-select'
            }),
            'is_vulnerable_share': forms.CheckboxInput(attrs={
                'class': 'form-check-input vulnerable-share-toggle',
                'data-toggle': 'tooltip',
                'title': 'Mark if sharing something personal or difficult',
                'onchange': 'toggleTriggerWarning(this)'
            }),
            'coping_strategy_shared': forms.CheckboxInput(attrs={
                'class': 'form-check-input coping-strategy-toggle',
                'data-toggle': 'tooltip',
                'title': 'Mark if sharing a helpful coping strategy'
            }),
            'contains_affirmation': forms.CheckboxInput(attrs={
                'class': 'form-check-input affirmation-toggle',
                'data-toggle': 'tooltip',
                'title': 'Mark if message contains positive self-talk or affirmation'
            }),
            'attachment_caption': forms.TextInput(attrs={
                'class': 'form-control attachment-caption',
                'placeholder': 'Describe the attachment...'
            }),
        }
        labels = {
            'content': _('Message'),
            'message_type': _('Message Type'),
            'visibility': _('Visibility'),
            'is_vulnerable_share': _('Vulnerable Share'),
            'coping_strategy_shared': _('Coping Strategy'),
            'contains_affirmation': _('Contains Affirmation'),
            'attachment_caption': _('Attachment Caption'),
        }
        help_texts = {
            'is_vulnerable_share': _('Consider using a trigger warning for vulnerable shares'),
            'coping_strategy_shared': _('Help others by sharing what works for you'),
            'contains_affirmation': _('Positive self-talk can be healing for everyone'),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.room = kwargs.pop('room', None)
        self.parent_message = kwargs.pop('parent_message', None)
        
        super().__init__(*args, **kwargs)
        
        # Set initial values based on user's therapeutic state
        if self.user:
            # Auto-detect emotional tone based on stress level
            if self.user.current_stress_level >= 7:
                self.fields['emotional_tone'].initial = 'anxious'
            elif self.user.current_stress_level <= 3:
                self.fields['emotional_tone'].initial = 'calm'
            
            # Check if user allows anonymous posting
            if not self.user.allow_anonymous:
                self.fields.pop('is_anonymous')
                self.fields['visibility'].choices = [
                    (value, label) for value, label in self.fields['visibility'].choices
                    if value != 'anonymous'
                ]
        
        # Set room-specific defaults
        if self.room:
            if self.room.trigger_warnings_required:
                self.fields['trigger_warning'].required = True
            
            # Limit visibility options based on room type
            if self.room.room_type == 'therapy_session':
                self.fields['visibility'].choices = [
                    ('public', 'Visible to all'),
                    ('therapist_only', 'Therapists only'),
                    ('self_reflection', 'Private reflection'),
                ]
        
        # Handle thread replies
        if self.parent_message:
            self.fields['content'].widget.attrs['placeholder'] = 'Type your reply here...'
            self.instance.parent_message = self.parent_message
            self.instance.thread_depth = self.parent_message.thread_depth + 1
        
        # Add therapeutic CSS classes
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control therapeutic-input'
        
        # Add data attributes for JavaScript
        self.fields['content'].widget.attrs.update({
            'data-max-length': '5000',
            'data-char-count': 'true'
        })
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check user's stress level
        if self.user and self.user.current_stress_level >= 9:
            raise ValidationError(
                _('Your stress level is very high (9/10). Please practice self-care before sending messages.'),
                code='high_stress'
            )
        
        # Validate vulnerable shares
        is_vulnerable_share = cleaned_data.get('is_vulnerable_share', False)
        trigger_warning = cleaned_data.get('trigger_warning', '')
        
        if is_vulnerable_share and self.room and self.room.trigger_warnings_required:
            if not trigger_warning or len(trigger_warning.strip()) < 5:
                self.add_error('trigger_warning', 
                    _('Trigger warning is required for vulnerable shares in this room'))
        
        # Validate content length for therapeutic messages
        content = cleaned_data.get('content', '')
        if len(content) > 5000:
            self.add_error('content', 
                _('Message is too long (maximum 5000 characters). Consider breaking it into smaller parts.'))
        
        # Validate attachment size
        attachment = cleaned_data.get('attachment')
        if attachment and attachment.size > 10 * 1024 * 1024:  # 10MB
            self.add_error('attachment', 
                _('File size must be less than 10MB'))
        
        # Check for therapeutic content
        if is_vulnerable_share:
            # Suggest taking a break after vulnerable share
            if self.user:
                self.user.add_breakthrough_moment(
                    f"Shared vulnerably in chat: {content[:50]}..."
                )
        
        # Validate anonymous posting
        is_anonymous = cleaned_data.get('is_anonymous', False)
        if is_anonymous and self.user and not self.user.allow_anonymous:
            self.add_error('is_anonymous',
                _('You have disabled anonymous posting in your settings'))
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set therapeutic context
        if self.user:
            instance.user = self.user
        
        if self.room:
            instance.room = self.room
        
        # Handle anonymous posting
        is_anonymous = self.cleaned_data.get('is_anonymous', False)
        if is_anonymous and self.user.allow_anonymous:
            instance.visibility = 'anonymous'
        
        # Auto-detect therapeutic labels
        content = instance.content.lower()
        if 'breakthrough' in content:
            instance.message_type = 'breakthrough'
        elif 'affirmation' in content or any(phrase in content for phrase in ['i am', 'i can', 'i will']):
            instance.contains_affirmation = True
        
        if commit:
            instance.save()
            
            # Update room's activity timestamp
            if self.room:
                self.room.updated_at = timezone.now()
                self.room.save()
        
        return instance


class TherapeuticReactionForm(forms.ModelForm):
    """
    Form for adding therapeutic reactions to messages
    """
    emotional_context = forms.CharField(
        required=False,
        max_length=50,
        label=_('How are you feeling?'),
        help_text=_('Optional: Share the emotion behind this reaction'),
        widget=forms.TextInput(attrs={
            'class': 'form-control emotional-context-input',
            'placeholder': 'e.g., moved, understood, hopeful...',
            'maxlength': '50'
        })
    )
    
    is_anonymous = forms.BooleanField(
        required=False,
        initial=False,
        label=_('React anonymously'),
        help_text=_('Your reaction will be shown without your username'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input anonymous-reaction-toggle'
        })
    )
    
    class Meta:
        model = MessageReaction
        fields = ['reaction_type', 'emotional_context', 'is_anonymous']
        widgets = {
            'reaction_type': forms.Select(attrs={
                'class': 'form-control reaction-select therapeutic-reaction',
                'onchange': 'updateReactionEmoji(this)'
            }),
        }
        labels = {
            'reaction_type': _('Reaction'),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.message = kwargs.pop('message', None)
        
        super().__init__(*args, **kwargs)
        
        # Group reactions by therapeutic category
        therapeutic_reactions = {
            'Emotional Support': [
                ('❤️', 'Heart (Support)'),
                ('🤗', 'Virtual Hug'),
                ('✅', 'I Understand'),
            ],
            'Growth & Progress': [
                ('⭐', 'Shining Moment'),
                ('💡', 'Great Idea'),
                ('👏', 'Well Done'),
                ('🚀', 'Making Progress'),
                ('🌱', 'New Beginning'),
            ],
            'Safety & Grounding': [
                ('🛡️', 'I Feel Safe'),
                ('⚓', 'Stay Grounded'),
                ('🌊', 'Riding the Wave'),
                ('🌬️', 'Take a Breath'),
            ],
            'Trigger Awareness': [
                ('⚠️', 'Trigger Warning'),
                ('🚪', 'Need Space'),
                ('🤝', 'Reaching Out'),
            ],
        }
        
        # Create choice groups
        choices = []
        for category, reaction_list in therapeutic_reactions.items():
            choices.append((category, [(r[0], r[1]) for r in reaction_list]))
        
        self.fields['reaction_type'].choices = choices
        
        # Check if user allows anonymous reactions
        if self.user and not self.user.allow_anonymous:
            self.fields.pop('is_anonymous')
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Check if user has already reacted with same type
        if self.user and self.message:
            reaction_type = cleaned_data.get('reaction_type')
            existing = MessageReaction.objects.filter(
                message=self.message,
                user=self.user,
                reaction_type=reaction_type
            ).first()
            
            if existing:
                # Allow toggling reactions
                existing.delete()
                self.message.reaction_count = max(0, self.message.reaction_count - 1)
                self.message.save()
                raise ValidationError(
                    _('Reaction removed.'),
                    code='reaction_toggled'
                )
        
        # Validate emotional context length
        emotional_context = cleaned_data.get('emotional_context', '')
        if emotional_context and len(emotional_context) > 50:
            self.add_error('emotional_context',
                _('Emotional context must be 50 characters or less'))
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set context
        if self.user:
            instance.user = self.user
        
        if self.message:
            instance.message = self.message
        
        # Set therapeutic flags based on reaction type
        reaction_type = instance.reaction_type
        supportive_reactions = ['❤️', '🤗', '✅', '🛡️', '🤝']
        therapeutic_reactions = ['🌊', '⚓', '🌬️', '🚪', '⚠️']
        
        if reaction_type in supportive_reactions:
            instance.is_supportive = True
        
        if reaction_type in therapeutic_reactions:
            instance.is_therapeutic = True
        
        if commit:
            instance.save()
            
            # Update message reaction count
            self.message.reaction_count += 1
            self.message.save()
            
            # Update supportive responses if applicable
            if instance.is_supportive:
                self.message.supportive_responses += 1
                self.message.save()
        
        return instance


class RoomMembershipForm(forms.ModelForm):
    """
    Form for managing therapeutic room memberships
    """
    therapeutic_goals = forms.CharField(
        required=False,
        label=_('Personal Goals'),
        help_text=_('What do you hope to gain from this space? (one per line)'),
        widget=forms.Textarea(attrs={
            'class': 'form-control therapeutic-goals-input',
            'rows': 3,
            'placeholder': 'e.g., Practice sharing feelings\nLearn coping strategies\nConnect with others',
            'style': 'resize: vertical;'
        })
    )
    
    triggers_disclosed = forms.CharField(
        required=False,
        label=_('Disclosed Triggers'),
        help_text=_('Optional: Share triggers you want the group to be aware of (one per line)'),
        widget=forms.Textarea(attrs={
            'class': 'form-control triggers-input',
            'rows': 3,
            'placeholder': 'e.g., Discussions about family trauma\nReferences to self-harm\nLoud sudden noises',
            'style': 'resize: vertical;'
        })
    )
    
    class Meta:
        model = RoomMembership
        fields = [
            'role', 'comfort_level', 'consent_given',
            'notification_preference', 'is_anonymous',
            'therapeutic_goals', 'triggers_disclosed'
        ]
        widgets = {
            'role': forms.Select(attrs={
                'class': 'form-control role-select',
                'disabled': 'disabled'  # Role typically managed by moderators
            }),
            'comfort_level': forms.Select(attrs={
                'class': 'form-control comfort-level-select therapeutic-slider',
                'data-toggle': 'tooltip',
                'title': 'How comfortable do you feel in this space right now?'
            }),
            'consent_given': forms.CheckboxInput(attrs={
                'class': 'form-check-input consent-toggle',
                'required': 'required',
                'data-toggle': 'tooltip',
                'title': 'I agree to respect the therapeutic boundaries of this space'
            }),
            'notification_preference': forms.Select(attrs={
                'class': 'form-control notification-select'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input anonymous-membership-toggle',
                'data-toggle': 'tooltip',
                'title': 'Participate without revealing your identity'
            }),
        }
        labels = {
            'role': _('Role'),
            'comfort_level': _('Comfort Level'),
            'consent_given': _('Give Consent'),
            'notification_preference': _('Notifications'),
            'is_anonymous': _('Participate Anonymously'),
        }
        help_texts = {
            'comfort_level': _('1 = Uncomfortable, 5 = Feeling Safe'),
            'consent_given': _('Required to join therapeutic spaces'),
            'is_anonymous': _('Your participation will be anonymous to other members'),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.room = kwargs.pop('room', None)
        
        super().__init__(*args, **kwargs)
        
        # Set initial therapeutic goals based on room type
        if self.room and not self.instance.pk:
            if self.room.room_type == 'therapy_session':
                self.fields['therapeutic_goals'].initial = [
                    'Process difficult emotions',
                    'Gain self-awareness',
                    'Develop coping strategies'
                ]
            elif self.room.room_type == 'learning_group':
                self.fields['therapeutic_goals'].initial = [
                    'Learn in a supportive environment',
                    'Ask questions without judgment',
                    'Practice new skills safely'
                ]
        
        # Require consent for therapeutic rooms
        if self.room and self.room.requires_consent:
            self.fields['consent_given'].required = True
        
        # Disable anonymous option if user doesn't allow it
        if self.user and not self.user.allow_anonymous:
            self.fields.pop('is_anonymous')
        
        # Add therapeutic CSS classes
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control therapeutic-input'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate comfort level
        comfort_level = cleaned_data.get('comfort_level')
        if comfort_level and (comfort_level < 1 or comfort_level > 5):
            self.add_error('comfort_level',
                _('Comfort level must be between 1 and 5'))
        
        # Validate consent for therapeutic rooms
        consent_given = cleaned_data.get('consent_given', False)
        if self.room and self.room.requires_consent and not consent_given:
            self.add_error('consent_given',
                _('Consent is required to join this therapeutic space'))
        
        # Parse therapeutic goals and triggers
        therapeutic_goals = cleaned_data.get('therapeutic_goals', '')
        triggers_disclosed = cleaned_data.get('triggers_disclosed', '')
        
        if therapeutic_goals:
            cleaned_data['therapeutic_goals'] = [
                goal.strip() for goal in therapeutic_goals.split('\n')
                if goal.strip()
            ]
        
        if triggers_disclosed:
            cleaned_data['triggers_disclosed'] = [
                trigger.strip() for trigger in triggers_disclosed.split('\n')
                if trigger.strip()
            ]
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set therapeutic context
        if self.user:
            instance.user = self.user
        
        if self.room:
            instance.room = self.room
        
        # Record entry stress level
        if not instance.pk and self.user:
            instance.entry_stress_level = self.user.current_stress_level
        
        if commit:
            instance.save()
        
        return instance


class TherapeuticChatSettingsForm(forms.ModelForm):
    """
    Form for user's therapeutic chat settings
    """
    class Meta:
        model = TherapeuticChatSettings
        fields = [
            'auto_trigger_warnings', 'vulnerability_timeout',
            'notify_on_mention', 'notify_on_reaction', 'notify_on_breakthrough',
            'enable_emotional_tone_detection', 'enable_coping_suggestions',
            'enable_affirmation_suggestions', 'show_stress_level_in_chat',
            'allow_anonymous_posting', 'archive_chats_after_days',
            'gentle_notification_sounds', 'gentle_message_colors',
            'hide_stressful_content', 'link_chats_to_learning'
        ]
        widgets = {
            'auto_trigger_warnings': forms.CheckboxInput(attrs={
                'class': 'form-check-input setting-toggle',
                'data-toggle': 'toggle',
                'data-on': 'Enabled',
                'data-off': 'Disabled'
            }),
            'vulnerability_timeout': forms.NumberInput(attrs={
                'class': 'form-control vulnerability-timeout-slider',
                'min': '5',
                'max': '300',
                'step': '5',
                'data-toggle': 'tooltip',
                'title': 'Time to reconsider before sending vulnerable messages'
            }),
            'archive_chats_after_days': forms.NumberInput(attrs={
                'class': 'form-control archive-days-slider',
                'min': '1',
                'max': '365',
                'step': '7',
                'data-toggle': 'tooltip',
                'title': 'Automatically archive old chats to reduce overwhelm'
            }),
            'notify_on_mention': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-toggle'
            }),
            'notify_on_reaction': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-toggle'
            }),
            'notify_on_breakthrough': forms.CheckboxInput(attrs={
                'class': 'form-check-input notification-toggle'
            }),
            'enable_emotional_tone_detection': forms.CheckboxInput(attrs={
                'class': 'form-check-input feature-toggle',
                'data-toggle': 'tooltip',
                'title': 'AI helps identify emotional tone in messages'
            }),
            'enable_coping_suggestions': forms.CheckboxInput(attrs={
                'class': 'form-check-input feature-toggle',
                'data-toggle': 'tooltip',
                'title': 'Get gentle suggestions for coping strategies'
            }),
            'enable_affirmation_suggestions': forms.CheckboxInput(attrs={
                'class': 'form-check-input feature-toggle',
                'data-toggle': 'tooltip',
                'title': 'Receive positive affirmation suggestions'
            }),
            'show_stress_level_in_chat': forms.CheckboxInput(attrs={
                'class': 'form-check-input privacy-toggle',
                'data-toggle': 'tooltip',
                'title': 'Let others see your current stress level'
            }),
            'allow_anonymous_posting': forms.CheckboxInput(attrs={
                'class': 'form-check-input privacy-toggle',
                'data-toggle': 'tooltip',
                'title': 'Allow posting messages without revealing identity'
            }),
            'gentle_notification_sounds': forms.CheckboxInput(attrs={
                'class': 'form-check-input gentle-toggle',
                'data-toggle': 'tooltip',
                'title': 'Use calming sounds for notifications'
            }),
            'gentle_message_colors': forms.CheckboxInput(attrs={
                'class': 'form-check-input gentle-toggle',
                'data-toggle': 'tooltip',
                'title': 'Use soft, calming colors in chat interface'
            }),
            'hide_stressful_content': forms.CheckboxInput(attrs={
                'class': 'form-check-input safety-toggle',
                'data-toggle': 'tooltip',
                'title': 'Automatically hide content when you\'re highly stressed'
            }),
            'link_chats_to_learning': forms.CheckboxInput(attrs={
                'class': 'form-check-input integration-toggle',
                'data-toggle': 'tooltip',
                'title': 'Connect chat discussions to your learning activities'
            }),
        }
        labels = {
            'auto_trigger_warnings': _('Auto Trigger Warnings'),
            'vulnerability_timeout': _('Vulnerability Timeout (minutes)'),
            'notify_on_mention': _('Notify on @mentions'),
            'notify_on_reaction': _('Notify on Reactions'),
            'notify_on_breakthrough': _('Notify on Breakthroughs'),
            'enable_emotional_tone_detection': _('Emotional Tone Detection'),
            'enable_coping_suggestions': _('Coping Strategy Suggestions'),
            'enable_affirmation_suggestions': _('Affirmation Suggestions'),
            'show_stress_level_in_chat': _('Show Stress Level'),
            'allow_anonymous_posting': _('Allow Anonymous Posting'),
            'archive_chats_after_days': _('Archive Chats After (days)'),
            'gentle_notification_sounds': _('Gentle Notification Sounds'),
            'gentle_message_colors': _('Gentle Message Colors'),
            'hide_stressful_content': _('Hide Stressful Content'),
            'link_chats_to_learning': _('Link Chats to Learning'),
        }
        help_texts = {
            'vulnerability_timeout': _('Time to reconsider before sending vulnerable messages'),
            'archive_chats_after_days': _('Old chats are archived to reduce overwhelm'),
            'hide_stressful_content': _('Protect yourself when stress levels are high'),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set therapeutic defaults for new users
        if not self.instance.pk and self.user:
            # Adjust defaults based on user's emotional profile
            if self.user.emotional_profile in ['ANXIOUS', 'OVERWHELMED']:
                self.fields['gentle_notification_sounds'].initial = True
                self.fields['gentle_message_colors'].initial = True
                self.fields['hide_stressful_content'].initial = True
                self.fields['vulnerability_timeout'].initial = 60
            
            if self.user.gentle_mode:
                self.fields['auto_trigger_warnings'].initial = True
        
        # Add therapeutic CSS classes
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control therapeutic-input'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate vulnerability timeout
        vulnerability_timeout = cleaned_data.get('vulnerability_timeout')
        if vulnerability_timeout and (vulnerability_timeout < 5 or vulnerability_timeout > 300):
            self.add_error('vulnerability_timeout',
                _('Vulnerability timeout must be between 5 and 300 minutes'))
        
        # Validate archive days
        archive_days = cleaned_data.get('archive_chats_after_days')
        if archive_days and (archive_days < 1 or archive_days > 365):
            self.add_error('archive_chats_after_days',
                _('Archive days must be between 1 and 365'))
        
        # Check therapeutic consistency
        if cleaned_data.get('hide_stressful_content') and not cleaned_data.get('gentle_notification_sounds'):
            self.add_error('gentle_notification_sounds',
                _('Gentle notifications recommended when hiding stressful content'))
        
        return cleaned_data


class RoomInvitationForm(forms.Form):
    """
    Form for inviting users to therapeutic chat rooms
    """
    user_ids = forms.MultipleChoiceField(
        label=_('Select Users'),
        help_text=_('Choose users to invite to this therapeutic space'),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control user-select therapeutic-multiselect',
            'data-live-search': 'true',
            'data-max-options': '10'
        })
    )
    
    invitation_message = forms.CharField(
        required=False,
        label=_('Personal Message'),
        help_text=_('Optional: Add a warm, welcoming message'),
        widget=forms.Textarea(attrs={
            'class': 'form-control invitation-message-input',
            'rows': 3,
            'placeholder': 'I thought you might appreciate this supportive space...',
            'style': 'resize: vertical;'
        })
    )
    
    require_consent = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Require Explicit Consent'),
        help_text=_('Users must give consent before joining therapeutic spaces'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input consent-requirement-toggle'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.room = kwargs.pop('room', None)
        self.inviter = kwargs.pop('inviter', None)
        
        super().__init__(*args, **kwargs)
        
        # Populate user choices with therapeutic considerations
        if self.room and self.inviter:
            # Get users who aren't already members
            existing_members = RoomMembership.objects.filter(
                room=self.room,
                is_active=True
            ).values_list('user_id', flat=True)
            
            # Filter users based on therapeutic criteria
            users = User.objects.exclude(id__in=existing_members).exclude(id=self.inviter.id)
            
            # Apply therapeutic filters
            if self.room.max_stress_level:
                users = users.filter(current_stress_level__lte=self.room.max_stress_level)
            
            if self.room.is_gated:
                # Only invite users with certain emotional profiles
                users = users.exclude(emotional_profile__in=['ANXIOUS', 'OVERWHELMED'])
            
            # Create choices
            user_choices = []
            for user in users:
                label = f"{user.username} ({user.get_emotional_profile_display()}, Stress: {user.current_stress_level}/10)"
                user_choices.append((user.id, label))
            
            self.fields['user_ids'].choices = user_choices
        
        # Add therapeutic CSS classes
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control therapeutic-input'
    
    def clean_user_ids(self):
        user_ids = self.cleaned_data['user_ids']
        
        # Check if any users are at too high stress level
        if self.room:
            high_stress_users = User.objects.filter(
                id__in=user_ids,
                current_stress_level__gt=self.room.max_stress_level
            )
            
            if high_stress_users.exists():
                usernames = ', '.join([u.username for u in high_stress_users])
                raise ValidationError(
                    _('The following users have stress levels too high for this room: %(usernames)s'),
                    params={'usernames': usernames},
                    code='high_stress_users'
                )
        
        return user_ids


class TherapeuticSearchForm(forms.Form):
    """
    Form for searching therapeutic chat content with emotional filters
    """
    query = forms.CharField(
        required=False,
        label=_('Search Messages'),
        widget=forms.TextInput(attrs={
            'class': 'form-control therapeutic-search-input',
            'placeholder': 'Search messages, users, or therapeutic topics...',
            'autocomplete': 'off'
        })
    )
    
    room = forms.ModelChoiceField(
        required=False,
        queryset=ChatRoom.objects.none(),
        label=_('Filter by Room'),
        widget=forms.Select(attrs={
            'class': 'form-control room-filter-select'
        })
    )
    
    message_type = forms.MultipleChoiceField(
        required=False,
        choices=ChatMessage.MessageType.choices,
        label=_('Message Types'),
        widget=forms.SelectMultiple(attrs={
            'class': 'form-control message-type-filter'
        })
    )
    
    emotional_tone = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Any Emotional Tone'),
            ('hopeful', 'Hopeful'),
            ('anxious', 'Anxious'),
            ('proud', 'Proud'),
            ('vulnerable', 'Vulnerable'),
            ('supportive', 'Supportive'),
            ('calm', 'Calm'),
        ],
        label=_('Emotional Tone'),
        widget=forms.Select(attrs={
            'class': 'form-control emotional-tone-filter'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        label=_('From Date'),
        widget=forms.DateInput(attrs={
            'class': 'form-control date-filter',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        label=_('To Date'),
        widget=forms.DateInput(attrs={
            'class': 'form-control date-filter',
            'type': 'date'
        })
    )
    
    include_vulnerable = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Include Vulnerable Shares'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input vulnerable-filter-toggle'
        })
    )
    
    include_affirmations = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Include Affirmations'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input affirmation-filter-toggle'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set room queryset based on user's memberships
        if self.user:
            user_rooms = ChatRoom.objects.filter(
                memberships__user=self.user,
                memberships__is_active=True
            )
            self.fields['room'].queryset = user_rooms
        
        # Add therapeutic CSS classes
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control therapeutic-input'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate date range
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_to < date_from:
            self.add_error('date_to',
                _('End date must be after start date'))
        
        return cleaned_data


class TherapeuticModerationForm(forms.Form):
    """
    Form for therapeutic moderation actions
    """
    ACTION_CHOICES = [
        ('warn', 'Issue Gentle Warning'),
        ('mute', 'Temporarily Mute User'),
        ('remove_message', 'Remove Message'),
        ('request_edit', 'Request Therapeutic Edit'),
        ('safety_check', 'Initiate Safety Check'),
        ('escalate', 'Escalate to Therapist'),
        ('timeout', 'Therapeutic Timeout'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        label=_('Moderation Action'),
        widget=forms.Select(attrs={
            'class': 'form-control moderation-action-select',
            'onchange': 'updateModerationFields(this)'
        })
    )
    
    target_user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label=_('Target User'),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control user-select'
        })
    )
    
    target_message = forms.ModelChoiceField(
        queryset=ChatMessage.objects.none(),
        label=_('Target Message'),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control message-select'
        })
    )
    
    reason = forms.CharField(
        label=_('Therapeutic Reason'),
        help_text=_('Explain the therapeutic basis for this action'),
        widget=forms.Textarea(attrs={
            'class': 'form-control therapeutic-reason-input',
            'rows': 3,
            'placeholder': 'This action is being taken because...',
            'style': 'resize: vertical;'
        })
    )
    
    duration_minutes = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=1440,  # 24 hours
        label=_('Duration (minutes)'),
        help_text=_('For temporary actions only'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control duration-slider',
            'min': '1',
            'max': '1440'
        })
    )
    
    private_note = forms.CharField(
        required=False,
        label=_('Private Note'),
        help_text=_('Internal note for moderation team'),
        widget=forms.Textarea(attrs={
            'class': 'form-control private-note-input',
            'rows': 2,
            'style': 'resize: vertical;'
        })
    )
    
    notify_user = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Notify User Gently'),
        help_text=_('Send a gentle notification about this action'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input notification-toggle'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.room = kwargs.pop('room', None)
        self.moderator = kwargs.pop('moderator', None)
        
        super().__init__(*args, **kwargs)
        
        # Set user and message querysets
        if self.room:
            # Users in the room
            user_ids = RoomMembership.objects.filter(
                room=self.room,
                is_active=True
            ).values_list('user_id', flat=True)
            
            self.fields['target_user'].queryset = User.objects.filter(id__in=user_ids)
            
            # Recent messages in the room
            self.fields['target_message'].queryset = ChatMessage.objects.filter(
                room=self.room,
                created_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).order_by('-created_at')[:50]  # Limit to recent messages
        
        # Add therapeutic CSS classes
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control therapeutic-input'
    
    def clean(self):
        cleaned_data = super().clean()
        
        action = cleaned_data.get('action')
        target_user = cleaned_data.get('target_user')
        target_message = cleaned_data.get('target_message')
        duration_minutes = cleaned_data.get('duration_minutes')
        
        # Validate required fields based on action
        if action in ['warn', 'mute', 'timeout'] and not target_user:
            self.add_error('target_user',
                _('Target user is required for this action'))
        
        if action in ['remove_message', 'request_edit'] and not target_message:
            self.add_error('target_message',
                _('Target message is required for this action'))
        
        if action in ['mute', 'timeout'] and not duration_minutes:
            self.add_error('duration_minutes',
                _('Duration is required for temporary actions'))
        
        # Validate therapeutic reason
        reason = cleaned_data.get('reason', '')
        if len(reason.strip()) < 10:
            self.add_error('reason',
                _('Please provide a meaningful therapeutic reason (at least 10 characters)'))
        
        return cleaned_data


class EmotionalCheckInForm(forms.Form):
    """
    Form for therapeutic emotional check-ins within chat
    """
    CURRENT_FEELING_CHOICES = [
        ('', '-- How are you feeling right now? --'),
        ('calm', '😌 Calm and centered'),
        ('anxious', '😰 Anxious or nervous'),
        ('overwhelmed', '😵 Overwhelmed'),
        ('sad', '😔 Sad or low'),
        ('angry', '😠 Angry or frustrated'),
        ('hopeful', '😊 Hopeful or optimistic'),
        ('proud', '🥰 Proud of myself'),
        ('tired', '😴 Tired or drained'),
        ('excited', '😄 Excited or energized'),
        ('numb', '😐 Numb or disconnected'),
    ]
    
    current_feeling = forms.ChoiceField(
        choices=CURRENT_FEELING_CHOICES,
        label=_('Current Feeling'),
        widget=forms.Select(attrs={
            'class': 'form-control emotional-checkin-select',
            'onchange': 'updateEmotionalSupport(this)'
        })
    )
    
    stress_level = forms.IntegerField(
        min_value=1,
        max_value=10,
        initial=5,
        label=_('Stress Level (1-10)'),
        help_text=_('1 = Very relaxed, 10 = Extremely stressed'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control stress-level-slider',
            'min': '1',
            'max': '10',
            'data-toggle': 'tooltip',
            'title': 'Be honest with yourself about your current stress'
        })
    )
    
    need_support = forms.ChoiceField(
        choices=[
            ('just_sharing', 'Just sharing - no support needed'),
            ('listening_ear', 'Could use a listening ear'),
            ('coping_ideas', 'Looking for coping ideas'),
            ('urgent_support', 'Need immediate support'),
        ],
        label=_('Support Needed'),
        widget=forms.Select(attrs={
            'class': 'form-control support-need-select'
        })
    )
    
    brief_context = forms.CharField(
        required=False,
        max_length=200,
        label=_('Brief Context (Optional)'),
        help_text=_('What\'s contributing to how you feel?'),
        widget=forms.TextInput(attrs={
            'class': 'form-control context-input',
            'placeholder': 'e.g., Tough day at work, breakthrough in therapy...',
            'maxlength': '200'
        })
    )
    
    share_with_group = forms.BooleanField(
        required=False,
        initial=True,
        label=_('Share with Group'),
        help_text=_('Allow others to see and respond to your check-in'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input share-toggle'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set initial stress level from user's current state
        if self.user:
            self.fields['stress_level'].initial = self.user.current_stress_level
        
        # Add therapeutic CSS classes
        for field_name, field in self.fields.items():
            if hasattr(field.widget, 'attrs'):
                if 'class' not in field.widget.attrs:
                    field.widget.attrs['class'] = 'form-control therapeutic-input'
    
    def clean(self):
        cleaned_data = super().clean()
        
        stress_level = cleaned_data.get('stress_level')
        need_support = cleaned_data.get('need_support')
        
        # Check for urgent support needs
        if need_support == 'urgent_support' and stress_level >= 8:
            # This would trigger emergency protocols in real implementation
            pass
        
        # Validate context length
        brief_context = cleaned_data.get('brief_context', '')
        if brief_context and len(brief_context) > 200:
            self.add_error('brief_context',
                _('Context must be 200 characters or less'))
        
        return cleaned_data
    
    def save_as_message(self, room, user):
        """Convert check-in form data to a therapeutic message"""
        from .models import ChatMessage
        
        message_content = f"Emotional check-in: {self.cleaned_data['current_feeling']}"
        
        if self.cleaned_data.get('brief_context'):
            message_content += f"\n\nContext: {self.cleaned_data['brief_context']}"
        
        message_content += f"\n\nStress level: {self.cleaned_data['stress_level']}/10"
        message_content += f"\nSupport needed: {self.cleaned_data['need_support']}"
        
        message = ChatMessage(
            room=room,
            user=user,
            content=message_content,
            message_type='checkin',
            visibility='public' if self.cleaned_data['share_with_group'] else 'self_reflection',
            emotional_tone=self.cleaned_data['current_feeling'],
            is_vulnerable_share=self.cleaned_data['stress_level'] >= 7
        )
        
        message.save()
        return message

# Add to chat/forms.py

def validate_therapeutic_content(content, user=None, room=None):
    """
    Validate content for therapeutic considerations
    Returns (is_valid, errors, therapeutic_metadata)
    """
    errors = []
    therapeutic_metadata = {}
    
    # Check content length
    if len(content) > 5000:
        errors.append('Content too long (max 5000 characters)')
    
    # Check for potentially harmful language (simplified example)
    harmful_phrases = [
        'kill myself', 'want to die', 'end it all',
        'hurt myself', 'self harm', 'suicide'
    ]
    
    content_lower = content.lower()
    for phrase in harmful_phrases:
        if phrase in content_lower:
            therapeutic_metadata['safety_concern'] = True
            therapeutic_metadata['concern_level'] = 'high'
            break
    
    # Detect emotional tone (simplified example)
    emotional_keywords = {
        'anxious': ['worried', 'nervous', 'anxious', 'panic', 'afraid'],
        'hopeful': ['hope', 'looking forward', 'excited', 'optimistic'],
        'proud': ['proud', 'accomplished', 'achieved', 'progress'],
        'sad': ['sad', 'depressed', 'lonely', 'empty', 'hopeless'],
    }
    
    detected_tones = []
    for tone, keywords in emotional_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            detected_tones.append(tone)
    
    if detected_tones:
        therapeutic_metadata['emotional_tones'] = detected_tones
    
    # Detect therapeutic content
    if any(word in content_lower for word in ['coping', 'strategy', 'technique']):
        therapeutic_metadata['coping_related'] = True
    
    if any(word in content_lower for word in ['affirmation', 'i am', 'i can', 'i will']):
        therapeutic_metadata['contains_affirmation'] = True
    
    # User-specific validation
    if user:
        if user.current_stress_level >= 9 and len(content) > 1000:
            errors.append('Consider shorter messages when stress levels are very high')
    
    return len(errors) == 0, errors, therapeutic_metadata


def get_therapeutic_form_class(user, room=None, message_type=None):
    """
    Return appropriate form class based on therapeutic context
    """
    if message_type == 'reaction':
        return TherapeuticReactionForm
    
    if message_type == 'room_creation':
        return TherapeuticRoomCreationForm
    
    if message_type == 'settings':
        return TherapeuticChatSettingsForm
    
    # Default to message form
    return TherapeuticMessageForm


def create_therapeutic_form_instance(form_class, user, **kwargs):
    """
    Create form instance with therapeutic context
    """
    form_kwargs = kwargs.copy()
    form_kwargs['user'] = user
    
    # Add room context if available
    if 'room' not in form_kwargs and hasattr(user, 'current_room'):
        form_kwargs['room'] = user.current_room
    
    return form_class(**form_kwargs)