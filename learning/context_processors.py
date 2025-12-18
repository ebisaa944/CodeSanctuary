# learning/context_processors.py
from datetime import datetime

def emotional_context(request):
    """
    Add emotional context to all templates
    """
    context = {}
    
    if request.user.is_authenticated:
        # Get user's emotional state
        emotional_state = getattr(request.user, 'emotional_state', 'neutral')
        context['emotional_state'] = emotional_state
        
        # Get therapeutic recommendations
        context['therapeutic_tip'] = get_therapeutic_tip(emotional_state)
        
        # Get time of day greeting
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"
        context['time_greeting'] = greeting
    
    return context

def get_therapeutic_tip(emotional_state):
    """
    Get therapeutic tip based on emotional state
    """
    tips = {
        'happy': "Great time to learn something new!",
        'stressed': "Take a deep breath. Start with something familiar.",
        'tired': "Short activities work best when you're tired.",
        'overwhelmed': "Break tasks into smaller steps. You've got this!",
        'neutral': "Perfect time for balanced practice.",
        'anxious': "Start with a mindfulness exercise.",
        'sad': "Be gentle with yourself today.",
        'excited': "Channel your energy into focused learning!",
        'default': "Listen to your needs before starting."
    }
    return tips.get(emotional_state, tips['default'])