# Add to chat/forms.py or create chat/form_utils.py

class TherapeuticBulkActionForm(forms.Form):
    """
    Form for bulk therapeutic actions in chat
    """
    ACTION_CHOICES = [
        ('archive_messages', 'Archive Selected Messages'),
        ('export_conversation', 'Export Conversation for Therapy'),
        ('generate_insights', 'Generate Therapeutic Insights'),
        ('schedule_break', 'Schedule Group Break'),
        ('create_summary', 'Create Session Summary'),
        ('set_reminders', 'Set Gentle Reminders'),
        ('update_goals', 'Update Therapeutic Goals'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        label=_('Bulk Action'),
        widget=forms.Select(attrs={
            'class': 'form-control bulk-action-select',
            'onchange': 'updateBulkActionFields(this)'
        })
    )
    
    message_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    room_id = forms.UUIDField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    parameters = forms.JSONField(
        required=False,
        widget=forms.HiddenInput()
    )
    
    confirmation_text = forms.CharField(
        required=False,
        label=_('Type to Confirm'),
        help_text=_('Type "I understand this therapeutic action" to proceed'),
        widget=forms.TextInput(attrs={
            'class': 'form-control confirmation-input',
            'placeholder': 'I understand this therapeutic action'
        })
    )
    
    def clean_confirmation_text(self):
        confirmation = self.cleaned_data.get('confirmation_text', '')
        expected = "I understand this therapeutic action"
        
        if confirmation.strip().lower() != expected.lower():
            raise ValidationError(
                _('Please type the exact confirmation phrase'),
                code='confirmation_required'
            )
        
        return confirmation
    
    def clean_message_ids(self):
        message_ids_str = self.cleaned_data.get('message_ids', '')
        if message_ids_str:
            try:
                message_ids = [uuid.UUID(id.strip()) for id in message_ids_str.split(',')]
                return message_ids
            except ValueError:
                raise ValidationError(
                    _('Invalid message ID format'),
                    code='invalid_message_ids'
                )
        return []


class ChatRoomTemplateForm(forms.Form):
    """
    Form for creating therapeutic chat rooms from templates
    """
    TEMPLATE_CHOICES = [
        ('gentle_intro', 'Gentle Introduction Space'),
        ('coping_strategies', 'Coping Strategies Exchange'),
        ('progress_celebration', 'Progress Celebration'),
        ('quiet_reflection', 'Quiet Reflection Space'),
        ('skill_practice', 'Skill Practice & Feedback'),
        ('peer_support', 'Peer Support Circle'),
        ('therapeutic_break', 'Therapeutic Break Room'),
    ]
    
    template = forms.ChoiceField(
        choices=TEMPLATE_CHOICES,
        label=_('Room Template'),
        widget=forms.Select(attrs={
            'class': 'form-control template-select',
            'onchange': 'loadTemplateDetails(this)'
        })
    )
    
    custom_name = forms.CharField(
        required=False,
        label=_('Custom Room Name'),
        widget=forms.TextInput(attrs={
            'class': 'form-control custom-name-input',
            'placeholder': 'Optional custom name for your room'
        })
    )
    
    therapeutic_focus = forms.CharField(
        required=False,
        label=_('Specific Therapeutic Focus'),
        help_text=_('Optional: What specific area do you want to focus on?'),
        widget=forms.TextInput(attrs={
            'class': 'form-control focus-input',
            'placeholder': 'e.g., Social anxiety, Sleep issues, Self-compassion...'
        })
    )
    
    def get_template_details(self, template_id):
        """Return therapeutic settings for the selected template"""
        templates = {
            'gentle_intro': {
                'name': 'Gentle Introduction Space',
                'description': 'A safe space for newcomers to introduce themselves gently',
                'room_type': 'general',
                'safety_level': 'safe_space',
                'max_stress_level': 5,
                'conversation_guidelines': [
                    'Welcome at your own pace',
                    'Share only what feels comfortable',
                    'Focus on strengths and hopes',
                    'Celebrate small steps',
                    'Practice kind curiosity about others'
                ],
                'therapeutic_goal': 'Build initial comfort and connection in a therapeutic community'
            },
            'coping_strategies': {
                'name': 'Coping Strategies Exchange',
                'description': 'Share and discover healthy coping mechanisms in a supportive environment',
                'room_type': 'peer_support',
                'safety_level': 'supportive',
                'mood_tracking_enabled': True,
                'trigger_warnings_required': True,
                'conversation_guidelines': [
                    'Share what works for you, not advice for others',
                    'Acknowledge that different strategies work for different people',
                    'Celebrate effort, not just success',
                    'Use "I" statements when sharing',
                    'Take breaks if discussions become triggering'
                ],
                'therapeutic_goal': 'Expand personal coping toolkit through shared experience'
            },
            # Add other templates...
        }
        
        return templates.get(template_id, {})