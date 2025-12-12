from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from .models import TherapeuticUser
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
    """Gentle login view with therapeutic consideration"""
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
        if user.gentle_mode:
            return f"Welcome back, {user.username}. Gentle mode is active. Take it easy today."
        
        stress_level = user.current_stress_level
        if stress_level >= 7:
            return f"Welcome back. Remember to be gentle with yourself today."
        elif stress_level >= 5:
            return f"Welcome back. Consider taking things slow today."
        else:
            return f"Welcome back, {user.username}! Ready to continue your learning journey?"


class UserLogoutView(APIView):
    """Gentle logout view"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        logout(request)
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
            public_queryset = queryset.filter(hide_progress=False)
            
            # Combine and remove duplicates
            queryset = (self_queryset | public_queryset).distinct()
        
        return queryset
    
    @action(detail=True, methods=['GET'])
    def therapeutic_plan(self, request, pk=None):
        """Get user's therapeutic learning plan"""
        user = self.get_object()
        return Response({
            'safe_learning_plan': user.get_safe_learning_plan(),
            'current_state': {
                'stress_level': user.current_stress_level,
                'emotional_profile': user.get_emotional_profile_display(),
                'gentle_mode': user.gentle_mode
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
        
        user.current_stress_level = int(stress_level)
        
        # Auto-adjust gentle mode based on stress
        if user.current_stress_level >= 7:
            user.gentle_mode = True
        
        user.save()
        
        return Response({
            'message': 'Stress level updated gently',
            'new_stress_level': user.current_stress_level,
            'gentle_mode': user.gentle_mode,
            'suggestion': self._get_stress_suggestion(user.current_stress_level)
        })
    
    def _get_recommendations(self, user):
        """Get therapeutic recommendations for user"""
        recommendations = []
        
        if user.current_stress_level >= 7:
            recommendations.append({
                'type': 'urgent',
                'message': 'High stress detected. Consider taking a break.',
                'action': 'Take 5 minutes for deep breathing'
            })
        
        if user.consecutive_days >= 7:
            recommendations.append({
                'type': 'celebration',
                'message': f'{user.consecutive_days} day streak!',
                'action': 'Acknowledge your consistency'
            })
        
        if not user.custom_affirmation:
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
            hide_progress=False,
            is_active=True
        ).exclude(id=self.request.user.id)
        
        # Filter by gentle mode preference
        if self.request.user.gentle_mode:
            queryset = queryset.filter(gentle_mode=True)
        
        # Optional: Filter by similar emotional profile
        profile_filter = self.request.query_params.get('similar_profile')
        if profile_filter == 'true':
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