# users/views.py - Updated with safe imports
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from .models import TherapeuticUser  # Only import TherapeuticUser
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserProfileSerializer,
    UserUpdateSerializer,
    UserMinimalSerializer
)
from .permissions import IsTherapeuticUserOwner
from .pagination import UserPagination
from .filters import TherapeuticUserFilter

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods , require_POST
from django.contrib.auth.views import LogoutView

from django.contrib import messages
from django.views.generic import TemplateView
from django.utils import timezone
from datetime import datetime, date

# Try to import therapy models, but don't crash if they don't exist
try:
    from therapy.models import EmotionalState, LearningPlan
    THERAPY_MODELS_AVAILABLE = True
except ImportError:
    THERAPY_MODELS_AVAILABLE = False
    EmotionalState = None
    LearningPlan = None

# ===== HTML VIEWS FOR BROWSERS =====

def landing_page(request):
    """
    Landing page for the website - accessible to all users (authenticated and non-authenticated)
    """
    context = {
        'page_title': 'Code Sanctuary',
        'page_subtitle': 'A Therapeutic Learning Environment',
    }
    
    # If user is authenticated, we can add additional context
    if request.user.is_authenticated and THERAPY_MODELS_AVAILABLE:
        try:
            # Get user's emotional state if available
            emotional_state = EmotionalState.objects.filter(
                user=request.user
            ).order_by('-created_at').first()
            if emotional_state:
                context['emotional_state'] = emotional_state.state
            
            # Get user's learning plan if available
            learning_plan = LearningPlan.objects.filter(user=request.user).first()
            if learning_plan:
                context['user_plan'] = learning_plan
        except Exception as e:
            print(f"Error loading user context: {e}")
            # Silently continue if there's an error
    
    return render(request, 'users/landing_page.html', context)

@require_http_methods(["GET", "POST"])
def html_login(request):
    """HTML login page for browsers - therapeutic approach"""
    # If user is already logged in, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('therapy:dashboard')
    
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me') == 'on'
        next_url = request.POST.get('next') or request.GET.get('next') or '/therapy/'
        
        # Validate
        if not username or not password:
            messages.error(request, 'Please enter both username and password.')
        else:
            # Try to authenticate
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Login the user
                login(request, user)
                
                # Handle "remember me" - set session expiry
                if remember_me:
                    request.session.set_expiry(1209600)  # 14 days in seconds
                else:
                    request.session.set_expiry(0)  # Browser session
                
                # Gentle success message
                messages.success(request, 
                    'Welcome back! 🌟 Remember to breathe and take gentle breaks.'
                )
                
                # Check if user has set their emotional state today
                if THERAPY_MODELS_AVAILABLE:
                    today = date.today()
                    has_emotional_state_today = EmotionalState.objects.filter(
                        user=user,
                        created_at__date=today
                    ).exists()
                    
                    if not has_emotional_state_today:
                        # Redirect to emotional state check-in
                        return redirect('users:emotional_state')
                    else:
                        # Redirect to next URL or dashboard
                        return redirect(next_url)
                else:
                    # If therapy models not available, just go to dashboard
                    return redirect(next_url)
            else:
                # Gentle error message
                messages.error(request, 
                    'Login not successful. Please check your credentials and try again. '
                    'Remember: It\'s okay to go slowly.'
                )
    
    # For GET requests or failed POST
    context = {
        'next': request.GET.get('next', '/therapy/')
    }
    return render(request, 'users/login.html', context)

# users/views.py
@require_http_methods(["GET", "POST"])
@login_required
def html_logout(request):
    """HTML logout with gentle confirmation"""
    if request.method == 'POST':
        # Perform logout
        logout(request)
        
        # Gentle farewell message
        messages.info(request, 
            'You have been logged out gently. 🌿 '
            'Remember: Learning is a marathon, not a sprint. Rest well.'
        )
        
        # Redirect to landing page
        return redirect('landing_page')  # Changed from 'users:login'
    
    # GET request - show confirmation page
    return render(request, 'users/logout_confirmation.html')

# Optional: HTML registration view if needed
@require_http_methods(["GET", "POST"])
def html_register(request):
    """HTML registration page for browsers"""
    if request.user.is_authenticated:
        return redirect('therapy:dashboard')
    
    if request.method == 'POST':
        # You can add HTML form handling here
        # For now, redirect to API registration
        return redirect('users:register')
    
    return render(request, 'users/register.html')

# ===== EMOTIONAL STATE VIEW =====
@login_required
def emotional_state_view(request):
    """HTML view for updating emotional state"""
    # Check if therapy models are available
    if not THERAPY_MODELS_AVAILABLE:
        messages.warning(request, "Emotional state tracking is not available at the moment.")
        return redirect('therapy:dashboard')
    
    # Check if using TherapeuticUser model directly
    user = request.user  # This is already TherapeuticUser
    
    if request.method == 'POST':
        # Handle form submission
        mood = request.POST.get('mood', 'neutral')
        energy_level = request.POST.get('energy_level', 5)
        stress_level = request.POST.get('stress_level', 5)
        focus_level = request.POST.get('focus_level', 5)
        
        # Try to create/update EmotionalState record
        today = date.today()
        existing_state = EmotionalState.objects.filter(
            user=request.user,
            created_at__date=today
        ).first()
        
        if existing_state:
            existing_state.state = mood
            existing_state.intensity = stress_level
            existing_state.notes = f"Energy: {energy_level}, Focus: {focus_level}"
            existing_state.save()
        else:
            EmotionalState.objects.create(
                user=request.user,
                state=mood,
                intensity=stress_level,
                notes=f"Energy: {energy_level}, Focus: {focus_level}"
            )
        
        # Update TherapeuticUser fields
        # Note: Your TherapeuticUser model doesn't have mood, energy_level, or focus_level fields
        # but it has current_stress_level and gentle_mode
        if hasattr(user, 'current_stress_level'):
            user.current_stress_level = int(stress_level) if stress_level else 5
            
            # Auto-adjust gentle mode based on stress
            if user.current_stress_level >= 7 and hasattr(user, 'gentle_mode'):
                user.gentle_mode = True
            
            user.save()
        
        messages.success(request, 'Your emotional state has been updated gently. 🌿')
        return redirect('learning:dashboard')
    
    # Check existing state for today
    today = date.today()
    existing_state = EmotionalState.objects.filter(
        user=request.user,
        created_at__date=today
    ).first()
    
    # Predefined emotional states with descriptions
    emotional_states = [
        {
            'value': 'energetic',
            'icon': 'bolt',
            'name': 'Energetic',
            'description': 'Feeling active, motivated, and ready to take on challenges'
        },
        {
            'value': 'anxious',
            'icon': 'heartbeat',
            'name': 'Anxious',
            'description': 'Feeling nervous, worried, or uneasy about something'
        },
        {
            'value': 'overwhelmed',
            'icon': 'tachometer-alt',
            'name': 'Overwhelmed',
            'description': 'Feeling like there\'s too much to handle or process'
        },
        {
            'value': 'tired',
            'icon': 'bed',
            'name': 'Tired',
            'description': 'Feeling low on energy, needing rest or recovery'
        },
        {
            'value': 'depressed',
            'icon': 'cloud',
            'name': 'Depressed',
            'description': 'Feeling sad, low, or lacking motivation'
        },
        {
            'value': 'calm',
            'icon': 'spa',
            'name': 'Calm',
            'description': 'Feeling peaceful, relaxed, and centered'
        },
        {
            'value': 'focused',
            'icon': 'bullseye',
            'name': 'Focused',
            'description': 'Feeling concentrated, attentive, and in the zone'
        },
        {
            'value': 'neutral',
            'icon': 'meh',
            'name': 'Neutral',
            'description': 'Feeling balanced, neither particularly high nor low'
        },
        {
            'value': 'happy',
            'icon': 'smile',
            'name': 'Happy',
            'description': 'Feeling joyful, content, and positive'
        },
        {
            'value': 'excited',
            'icon': 'star',
            'name': 'Excited',
            'description': 'Feeling enthusiastic, eager, and energized'
        },
    ]
    
    # Get current stress level from TherapeuticUser
    current_stress_level = user.current_stress_level if hasattr(user, 'current_stress_level') else 5
    
    # Render a simple form
    return render(request, 'users/emotional_state.html', {
        'user': user,
        'existing_state': existing_state,
        'emotional_states': emotional_states,
        'today': today,
        'current_stress_level': current_stress_level,
        'mood_choices': [
            ('happy', '😊 Happy'),
            ('neutral', '😐 Neutral'),
            ('sad', '😔 Sad'),
            ('anxious', '😰 Anxious'),
            ('excited', '🤩 Excited'),
            ('calm', '😌 Calm'),
            ('energetic', '⚡ Energetic'),
            ('tired', '😴 Tired'),
        ]
    })

@login_required
def emotional_state_history(request):
    """
    View history of emotional states
    """
    if not THERAPY_MODELS_AVAILABLE:
        messages.warning(request, "Emotional state history is not available.")
        return redirect('users:profile')
    
    states = EmotionalState.objects.filter(user=request.user).order_by('-created_at')
    
    # Group by date
    states_by_date = {}
    for state in states:
        date_key = state.created_at.date()
        if date_key not in states_by_date:
            states_by_date[date_key] = []
        states_by_date[date_key].append(state)
    
    context = {
        'states_by_date': states_by_date,
    }
    
    return render(request, 'users/emotional_state_history.html', context)

@login_required
def profile(request):
    """
    User profile page - using TherapeuticUser directly since there's no separate Profile model
    """
    user = request.user  # This is TherapeuticUser
    
    if request.method == "POST":
        # Handle profile updates for TherapeuticUser fields
        # Note: Your TherapeuticUser model doesn't have bio, location, birth_date, etc.
        # So we'll only update the fields that exist
        
        # Update emotional profile if it exists in the form
        if hasattr(user, 'emotional_profile'):
            new_emotional_profile = request.POST.get('emotional_profile')
            if new_emotional_profile:
                user.emotional_profile = new_emotional_profile
        
        # Update learning style if it exists
        if hasattr(user, 'learning_style'):
            new_learning_style = request.POST.get('learning_style')
            if new_learning_style:
                user.learning_style = new_learning_style
        
        # Update daily time limit
        if hasattr(user, 'daily_time_limit'):
            new_daily_limit = request.POST.get('daily_time_limit')
            if new_daily_limit:
                try:
                    user.daily_time_limit = int(new_daily_limit)
                except ValueError:
                    pass
        
        # Update gentle mode preference
        if hasattr(user, 'gentle_mode'):
            user.gentle_mode = request.POST.get('gentle_mode') == 'on'
        
        # Update custom affirmation
        if hasattr(user, 'custom_affirmation'):
            user.custom_affirmation = request.POST.get('custom_affirmation', '')
        
        # Update avatar color
        if hasattr(user, 'avatar_color'):
            new_color = request.POST.get('avatar_color')
            if new_color:
                user.avatar_color = new_color
        
        user.save()
        messages.success(request, "Profile updated successfully!")
        return redirect('users:profile')
    
    # Get available emotional profile choices
    emotional_profile_choices = []
    if hasattr(user, 'EmotionalProfile'):
        emotional_profile_choices = user.EmotionalProfile.choices
    elif hasattr(TherapeuticUser, 'EmotionalProfile'):
        emotional_profile_choices = TherapeuticUser.EmotionalProfile.choices
    
    # Get learning style choices
    learning_style_choices = []
    if hasattr(user, 'LearningStyle'):
        learning_style_choices = user.LearningStyle.choices
    elif hasattr(TherapeuticUser, 'LearningStyle'):
        learning_style_choices = TherapeuticUser.LearningStyle.choices
    
    context = {
        'user': user,
        'emotional_profile_choices': emotional_profile_choices,
        'learning_style_choices': learning_style_choices,
    }
    return render(request, 'users/profile.html', context)

def about(request):
    """
    About page for the website
    """
    context = {
        'page_title': 'About Code Sanctuary',
        'page_subtitle': 'Our Mission and Vision',
    }
    return render(request, 'users/about.html', context)

def contact(request):
    """
    Contact page
    """
    if request.method == "POST":
        # Handle contact form submission
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        message = request.POST.get('message', '')
        
        # In a real application, you would:
        # 1. Send an email
        # 2. Save to database
        # 3. Send confirmation
        
        messages.success(request, "Thank you for your message! We'll get back to you soon.")
        return redirect('landing_page')
    
    return render(request, 'users/contact.html')

# ===== API VIEWS (FOR MOBILE APPS & AJAX) =====
# users/views.py
@require_POST
@login_required
def web_logout(request):
    """Web logout view for HTML templates"""
    logout(request)
    return redirect('landing_page')  # Changed from 'users:login'
class UserRegistrationView(generics.CreateAPIView):
    """View for user registration with therapeutic defaults"""
    queryset = TherapeuticUser.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Auto-login after registration
        login(request, user)
        
        return Response({
            'user': UserProfileSerializer(user, context={'request': request}).data,
            'message': 'Welcome to Code Sanctuary! Your gentle learning journey begins now.',
            'therapeutic_tip': 'Take a moment to breathe. You can explore at your own pace.'
        }, status=status.HTTP_201_CREATED)

class UserLoginView(APIView):
    """API login view for mobile apps (POST only)"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            login(request, user)
            
            # Get CSRF token for session
            csrf_token = get_token(request)
            
            return Response({
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'csrf_token': csrf_token,
                'therapeutic_context': serializer.validated_data['therapeutic_context'],
                'welcome_message': self._get_welcome_message(user)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_welcome_message(self, user):
        """Get personalized welcome message"""
        if hasattr(user, 'gentle_mode') and user.gentle_mode:
            return f"Welcome back, {user.username}. Gentle mode is active. Take it easy today."
        
        if hasattr(user, 'current_stress_level'):
            stress_level = user.current_stress_level
            if stress_level >= 7:
                return f"Welcome back. Remember to be gentle with yourself today."
            elif stress_level >= 5:
                return f"Welcome back. Consider taking things slow today."
        
        return f"Welcome back, {user.username}! Ready to continue your learning journey?"

class UserLogoutView(APIView):
    """API logout view for mobile apps"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        
        # This is API-only, always return JSON
        return Response({
            'message': 'Logged out gently. Take care of yourself.',
            'gentle_reminder': 'Learning is a marathon, not a sprint. Rest is important.'
        })

class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for user profiles with therapeutic permissions"""
    queryset = TherapeuticUser.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsTherapeuticUserOwner]
    pagination_class = UserPagination
    filterset_class = TherapeuticUserFilter
    
    def get_queryset(self):
        """Filter queryset based on permissions"""
        queryset = super().get_queryset()
        
        # Non-staff users can only see themselves and non-private users
        if not self.request.user.is_staff:
            # Users can always see themselves
            self_queryset = queryset.filter(id=self.request.user.id)
            
            # Plus other users who don't hide progress
            if hasattr(TherapeuticUser, 'hide_progress'):
                public_queryset = queryset.filter(hide_progress=False)
            else:
                public_queryset = queryset.none()
            
            # Combine and remove duplicates
            queryset = (self_queryset | public_queryset).distinct()
        
        return queryset
    
    @action(detail=True, methods=['GET'])
    def therapeutic_plan(self, request, pk=None):
        """Get user's therapeutic learning plan"""
        user = self.get_object()
        
        plan_data = {}
        if THERAPY_MODELS_AVAILABLE:
            # Try to get learning plan from therapy models
            try:
                learning_plan = LearningPlan.objects.filter(user=user).first()
                if learning_plan:
                    plan_data = {
                        'max_difficulty': learning_plan.max_difficulty,
                        'max_duration': learning_plan.max_duration,
                        'focus': learning_plan.focus,
                        'preferred_times': learning_plan.preferred_times,
                    }
            except:
                pass
        
        # If no learning plan from therapy models, use TherapeuticUser's own method
        if not plan_data and hasattr(user, 'get_safe_learning_plan'):
            plan_data = user.get_safe_learning_plan()
        
        return Response({
            'safe_learning_plan': plan_data,
            'current_state': {
                'stress_level': user.current_stress_level if hasattr(user, 'current_stress_level') else 5,
                'emotional_profile': user.get_emotional_profile_display() if hasattr(user, 'get_emotional_profile_display') else 'balanced',
                'gentle_mode': user.gentle_mode if hasattr(user, 'gentle_mode') else False
            },
            'recommendations': self._get_recommendations(user)
        })
    
    @action(detail=False, methods=['GET'])
    def current_user(self, request):
        """Get current authenticated user"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=True, methods=['POST'])
    def update_stress(self, request, pk=None):
        """Update user's stress level with therapeutic validation"""
        user = self.get_object()
        
        # Check permission
        if not (request.user == user or request.user.is_staff):
            return Response(
                {'error': 'You can only update your own stress level'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        stress_level = request.data.get('stress_level')
        
        if not stress_level or not (1 <= int(stress_level) <= 10):
            return Response(
                {'error': 'Stress level must be between 1 and 10'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if hasattr(user, 'current_stress_level'):
            user.current_stress_level = int(stress_level)
            
            # Auto-adjust gentle mode based on stress
            if user.current_stress_level >= 7 and hasattr(user, 'gentle_mode'):
                user.gentle_mode = True
        
        user.save()
        
        return Response({
            'message': 'Stress level updated gently',
            'new_stress_level': user.current_stress_level if hasattr(user, 'current_stress_level') else stress_level,
            'gentle_mode': user.gentle_mode if hasattr(user, 'gentle_mode') else False,
            'suggestion': self._get_stress_suggestion(int(stress_level))
        })
    
    def _get_recommendations(self, user):
        """Get therapeutic recommendations for user"""
        recommendations = []
        
        if hasattr(user, 'current_stress_level') and user.current_stress_level >= 7:
            recommendations.append({
                'type': 'urgent',
                'message': 'High stress detected. Consider taking a break.',
                'action': 'Take 5 minutes for deep breathing'
            })
        
        if hasattr(user, 'consecutive_days') and user.consecutive_days >= 7:
            recommendations.append({
                'type': 'celebration',
                'message': f'{user.consecutive_days} day streak!',
                'action': 'Acknowledge your consistency'
            })
        
        if hasattr(user, 'custom_affirmation') and (not user.custom_affirmation or user.custom_affirmation.strip() == ''):
            recommendations.append({
                'type': 'suggestion',
                'message': 'Consider setting a personal affirmation',
                'action': 'Add a kind message to yourself in settings'
            })
        
        return recommendations
    
    def _get_stress_suggestion(self, stress_level):
        """Get suggestion based on stress level"""
        suggestions = {
            1: 'Very calm - great for focused learning',
            2: 'Calm - good learning state',
            3: 'Slightly calm - normal learning state',
            4: 'Neutral - ready to learn',
            5: 'Slightly stressed - take it slow',
            6: 'Moderately stressed - gentle activities recommended',
            7: 'Stressed - consider a break',
            8: 'Very stressed - self-care is important',
            9: 'Highly stressed - gentle mode activated',
            10: 'Extreme stress - please take care of yourself'
        }
        return suggestions.get(stress_level, 'Notice how you feel')

class UserSettingsView(APIView):
    """View for updating user settings"""
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Settings updated gently',
                'user': UserProfileSerializer(user, context={'request': request}).data,
                'changes': serializer.validated_data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TherapeuticCommunityView(generics.ListAPIView):
    """View for therapeutic community (gentle social discovery)"""
    serializer_class = UserMinimalSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UserPagination
    
    def get_queryset(self):
        """Get community members with therapeutic filtering"""
        queryset = TherapeuticUser.objects.filter(
            is_active=True
        ).exclude(id=self.request.user.id)
        
        # Only include users who don't hide progress
        if hasattr(TherapeuticUser, 'hide_progress'):
            queryset = queryset.filter(hide_progress=False)
        
        # Filter by gentle mode preference
        if hasattr(self.request.user, 'gentle_mode') and self.request.user.gentle_mode:
            queryset = queryset.filter(gentle_mode=True)
        
        # Optional: Filter by similar emotional profile
        profile_filter = self.request.query_params.get('similar_profile')
        if profile_filter == 'true' and hasattr(TherapeuticUser, 'emotional_profile'):
            queryset = queryset.filter(
                emotional_profile=self.request.user.emotional_profile
            )
        
        return queryset.order_by('?')  # Random order for gentle discovery
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        # Add therapeutic context
        response.data['community_context'] = {
            'total_members': self.get_queryset().count(),
            'gentle_reminder': 'Everyone progresses at their own pace',
            'connection_suggestion': 'Send gentle encouragement if inspired',
            'privacy_note': 'All members here have chosen to share their progress'
        }
        
        return response