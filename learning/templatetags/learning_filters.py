# learning/templatetags/learning_filters.py
from django import template
from django.utils.timesince import timesince

register = template.Library()

@register.filter(name='get_difficulty_color')
def get_difficulty_color(difficulty_level):
    """
    Get Bootstrap color for difficulty level
    """
    color_map = {
        1: 'success',   # Beginner - Green
        2: 'info',      # Easy - Blue
        3: 'primary',   # Medium - Primary blue
        4: 'warning',   # Hard - Yellow
        5: 'danger',    # Advanced - Red
        6: 'dark',      # Expert - Black
    }
    return color_map.get(difficulty_level, 'secondary')
# Add this to your existing learning_filters.py file

@register.filter(name='split')
def split_filter(value, delimiter=','):
    """
    Split a string by delimiter
    Used in: {% with profiles=path.recommended_for_profiles|split:"," %}
    """
    if not value:
        return []
    return [item.strip() for item in str(value).split(delimiter)]

@register.filter(name='get_difficulty_icon')
def get_difficulty_icon(difficulty_level):
    """
    Get FontAwesome icon for difficulty level
    """
    icon_map = {
        1: 'seedling',      # Beginner
        2: 'leaf',          # Easy
        3: 'tree',          # Medium
        4: 'mountain',      # Hard
        5: 'fire',          # Advanced
        6: 'bolt',          # Expert
    }
    return icon_map.get(difficulty_level, 'question-circle')

@register.filter(name='get_difficulty_text')
def get_difficulty_text(difficulty_level):
    """
    Get text label for difficulty level
    """
    text_map = {
        1: 'Beginner',
        2: 'Easy',
        3: 'Medium',
        4: 'Hard',
        5: 'Advanced',
        6: 'Expert',
    }
    return text_map.get(difficulty_level, 'Unknown')

@register.filter(name='get_difficulty_bg_color')
def get_difficulty_bg_color(difficulty_level):
    """
    Get background color class for difficulty level
    """
    bg_map = {
        1: 'bg-success',
        2: 'bg-info',
        3: 'bg-primary',
        4: 'bg-warning',
        5: 'bg-danger',
        6: 'bg-dark',
    }
    return bg_map.get(difficulty_level, 'bg-secondary')

@register.filter(name='get_difficulty_text_color')
def get_difficulty_text_color(difficulty_level):
    """
    Get text color class for difficulty level
    """
    text_map = {
        1: 'text-success',
        2: 'text-info',
        3: 'text-primary',
        4: 'text-warning',
        5: 'text-danger',
        6: 'text-dark',
    }
    return text_map.get(difficulty_level, 'text-secondary')

# Emotional filters
@register.filter(name='get_emotional_icon')
def get_emotional_icon(emotional_state):
    """
    Get FontAwesome icon for emotional state
    """
    icon_map = {
        'happy': 'smile-beam',
        'excited': 'grin-stars',
        'calm': 'spa',
        'neutral': 'meh',
        'tired': 'tired',
        'stressed': 'grimace',
        'anxious': 'flushed',
        'sad': 'sad-tear',
        'overwhelmed': 'dizzy',
        'focused': 'brain',
        'motivated': 'rocket',
        'confused': 'question-circle',
        'frustrated': 'angry',
        'proud': 'medal',
        'relieved': 'cloud-sun',
        'depressed': 'cloud',  # Added for your template
        'default': 'user'
    }
    return icon_map.get(emotional_state, 'user')

@register.filter(name='get_emotional_alert_class')
def get_emotional_alert_class(emotional_state):
    """
    Get Bootstrap alert class for emotional state
    """
    class_map = {
        'happy': 'success',
        'excited': 'warning',
        'calm': 'info',
        'neutral': 'secondary',
        'tired': 'secondary',
        'stressed': 'danger',
        'anxious': 'danger',
        'sad': 'danger',
        'overwhelmed': 'danger',
        'focused': 'primary',
        'motivated': 'success',
        'confused': 'warning',
        'frustrated': 'danger',
        'proud': 'success',
        'relieved': 'info',
        'depressed': 'secondary',  # Added for your template
        'default': 'secondary'
    }
    return class_map.get(emotional_state, 'secondary')

@register.filter(name='get_emotional_color')
def get_emotional_color(emotional_state):
    """
    Get color for emotional state
    """
    color_map = {
        'happy': '#28a745',
        'excited': '#ffc107',
        'calm': '#17a2b8',
        'neutral': '#6c757d',
        'tired': '#6c757d',
        'stressed': '#dc3545',
        'anxious': '#dc3545',
        'sad': '#dc3545',
        'overwhelmed': '#dc3545',
        'focused': '#007bff',
        'motivated': '#28a745',
        'confused': '#ffc107',
        'frustrated': '#dc3545',
        'proud': '#28a745',
        'relieved': '#17a2b8',
        'depressed': '#6c757d',  # Added for your template
        'default': '#6c757d'
    }
    return color_map.get(emotional_state, '#6c757d')

@register.filter(name='format_duration')
def format_duration(minutes):
    """
    Format duration in minutes to human readable format
    """
    if not minutes:
        return "0 min"
    
    if minutes < 60:
        return f"{minutes} min"
    else:
        hours = minutes // 60
        remaining_minutes = minutes % 60
        if remaining_minutes > 0:
            return f"{hours}h {remaining_minutes}min"
        else:
            return f"{hours}h"

@register.filter(name='get_progress_color')
def get_progress_color(percentage):
    """
    Get color for progress percentage
    """
    if percentage >= 90:
        return 'success'
    elif percentage >= 70:
        return 'info'
    elif percentage >= 50:
        return 'primary'
    elif percentage >= 30:
        return 'warning'
    else:
        return 'danger'

@register.filter(name='get_status_badge')
def get_status_badge(status):
    """
    Get badge class for activity status
    """
    badge_map = {
        'not_started': 'badge-secondary',
        'in_progress': 'badge-primary',
        'completed': 'badge-success',
        'skipped': 'badge-warning',
        'blocked': 'badge-danger',
    }
    return badge_map.get(status, 'badge-secondary')

# NEW FILTERS NEEDED FOR YOUR TEMPLATE:

# NEW FILTERS NEEDED FOR YOUR TEMPLATE:

@register.filter(name='divide')
def divide(value, arg):
    """
    Divide the value by the arg
    Used in: {{ progress.time_spent_seconds|divide:60 }}
    """
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError, TypeError):
        return 0


@register.filter(name='default')
def default(value, arg):
    """
    Return default if value is empty
    Used in: {{ user_plan.focus|default:"Balanced learning" }}
    """
    return arg if not value else value

@register.filter(name='title')
def title_case(value):
    """
    Convert to title case
    Used in: {{ path.target_language|title }}
    """
    return value.title() if value else ''

@register.filter(name='floatformat')
def floatformat_filter(value, arg=None):
    """
    Format float to specified decimal places
    Used in: {{ path.user_progress.percentage|default:0|floatformat:0 }}
    """
    try:
        if arg is not None:
            return f"{float(value):.{arg}f}"
        else:
            return f"{float(value):.0f}"
    except (ValueError, TypeError):
        return value

@register.filter(name='truncatewords')
def truncatewords_filter(value, arg):
    """
    Truncate string to specified number of words
    Used in: {{ path.description|truncatewords:25 }}
    """
    try:
        words = value.split()
        if len(words) > int(arg):
            return ' '.join(words[:int(arg)]) + '...'
        return value
    except (ValueError, AttributeError):
        return value

@register.filter(name='timesince')
def timesince_filter(value):
    """
    Get human-readable time difference
    Used in: {{ progress.updated_at|timesince }} ago
    """
    return timesince(value) if value else ''

@register.filter(name='make_list')
def make_list(value):
    """
    Convert string to list of characters
    Used in: {% for i in "12345"|make_list %}
    """
    return list(str(value))

# Add these to your existing learning_filters.py

@register.filter(name='get_dict_value')
def get_dict_value(dictionary, key):
    """Get value from dictionary by key"""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter(name='first')
def first_filter(iterable):
    """Get first item from iterable"""
    try:
        return iterable[0] if iterable else None
    except (TypeError, IndexError):
        return None

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get item from dictionary - alias for get_dict_value"""
    return get_dict_value(dictionary, key)

@register.filter(name='get_therapeutic_color')
def get_therapeutic_color(focus):
    """Get color for therapeutic focus"""
    color_map = {
        'mindfulness': 'info',
        'confidence': 'success',
        'anxiety': 'warning',
        'stress': 'danger',
        'focus': 'primary',
        'creativity': 'purple',
        'persistence': 'orange',
    }
    return color_map.get(focus.lower(), 'secondary')

@register.filter(name='get_activity_type_display')
def get_activity_type_display(activity_type):
    """Get display text for activity type"""
    type_map = {
        'tutorial': 'Tutorial',
        'exercise': 'Exercise',
        'challenge': 'Challenge',
        'project': 'Project',
        'quiz': 'Quiz',
        'reflection': 'Reflection',
    }
    return type_map.get(activity_type, activity_type.title())

@register.filter(name='get_therapeutic_focus_display')
def get_therapeutic_focus_display(focus):
    """Get display text for therapeutic focus"""
    focus_map = {
        'mindfulness': 'Mindfulness',
        'confidence': 'Confidence Building',
        'anxiety': 'Anxiety Reduction',
        'stress': 'Stress Management',
        'focus': 'Focus Enhancement',
        'creativity': 'Creativity Boost',
        'persistence': 'Persistence Training',
    }
    return focus_map.get(focus, focus.title())

# Add these to your existing learning_filters.py

@register.filter(name='get_emotional_change_class')
def get_emotional_change_class(stress_change):
    """Get CSS class for emotional change based on stress change"""
    try:
        stress_change = float(stress_change)
        if stress_change < -1:
            return 'positive'  # Stress decreased significantly
        elif stress_change > 1:
            return 'challenging'  # Stress increased significantly
        else:
            return 'neutral'  # Little change
    except (ValueError, TypeError):
        return 'neutral'

@register.filter(name='pluralize')
def pluralize_filter(value, suffix='s'):
    """Add 's' if value is not 1"""
    try:
        if int(value) == 1:
            return ''
        return suffix
    except (ValueError, TypeError):
        return suffix

@register.simple_tag
def widthratio(numerator, denominator, scale=100):
    """
    Calculate ratio for progress bars
    Used in: {% widthratio stats.completed 50 100 %}
    """
    try:
        return int(float(numerator) / float(denominator) * float(scale))
    except (ValueError, ZeroDivisionError):
        return 0