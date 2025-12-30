# social/views.py - Updated with HTML template views
"""
Therapeutic social views - SQLite compatible version
"""
# Add at the top of the file if not already there
import re
import json
import logging
import uuid
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter
import statistics
from decimal import Decimal
from functools import lru_cache

# Optional analytics libraries
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

# Django imports
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import (
    Q, Count, Avg, F, Value, CharField, Case, When, Subquery, OuterRef,
    IntegerField, FloatField, ExpressionWrapper, Sum, Max, Min
)
from django.db.models.functions import (
    Coalesce, Concat, ExtractHour, ExtractDay, ExtractWeek, ExtractMonth,
    ExtractYear, ExtractQuarter, Now, TruncDate, TruncHour,
    TruncWeek, TruncMonth, TruncQuarter, TruncYear,
    Upper, Lower, Length, Reverse, Replace, Substr, Trim,
    Extract, Cast
)
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import (
    JsonResponse, HttpResponse, HttpResponseRedirect,
    HttpResponseBadRequest, HttpResponseForbidden,
    HttpResponseServerError
)
from django.views.decorators.cache import cache_page
from django.db import transaction
from django.core.exceptions import (
    PermissionDenied, ValidationError, ObjectDoesNotExist
)
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.views.generic import TemplateView, DetailView, FormView, CreateView, ListView
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# REST Framework imports
from rest_framework import viewsets, generics, mixins, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import (
    IsAuthenticated, AllowAny, IsAuthenticatedOrReadOnly,
    BasePermission
)
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
try:
    from rest_framework_simplejwt.authentication import JWTAuthentication
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    JWTAuthentication = None
from rest_framework.exceptions import APIException

# Local imports
from .models import (
    GentleInteraction, Achievement, UserAchievement,
    SupportCircle, CircleMembership
)
from .serializers import (
    GentleInteractionSerializer, AchievementSerializer,
    UserAchievementSerializer, SupportCircleSerializer,
    CircleMembershipSerializer, GentleEncouragementSerializer,
    CommunityStatsSerializer
)
from .forms import (
    GentleInteractionForm, QuickEncouragementForm,
    SupportCircleForm, CircleJoinForm, AchievementShareForm
)

# Setup logging
logger = logging.getLogger(__name__)
User = get_user_model()


# ============================================================================
# SIMPLIFIED ENUMS AND DATA CLASSES
# ============================================================================

@login_required
def community_home(request):
    """Function-based community homepage (optional, to match learning app)"""
    return CommunityHomeView.as_view()(request)

class TherapeuticImpactLevel:
    """Levels of therapeutic impact"""
    MINIMAL = 1
    MILD = 2
    MODERATE = 3
    SIGNIFICANT = 4
    TRANSFORMATIVE = 5
    
    @classmethod
    def from_score(cls, score: int):
        if score >= 80:
            return cls.TRANSFORMATIVE
        elif score >= 60:
            return cls.SIGNIFICANT
        elif score >= 40:
            return cls.MODERATE
        elif score >= 20:
            return cls.MILD
        return cls.MINIMAL


# ============================================================================
# EXCEPTIONS
# ============================================================================

class TherapeuticAPIException(APIException):
    """Base exception for therapeutic social features"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'A therapeutic error occurred'
    
    def __init__(self, detail=None, therapeutic_message=None):
        super().__init__(detail)
        self.therapeutic_message = therapeutic_message or "Please take a gentle moment before trying again."


# ============================================================================
# HTML TEMPLATE VIEWS
# ============================================================================

class CommunityHomeView(TemplateView):
    """
    HTML community homepage
    """
    template_name = 'social/community_home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        recent_interactions = GentleInteraction.objects.filter(
            visibility__in=['public', 'community'],
            created_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('sender').order_by('-created_at')[:20]
        
        active_circles = SupportCircle.objects.filter(
            is_public=True
        ).order_by('-active_members')[:10]
        
        recent_achievements = UserAchievement.objects.filter(
            shared_publicly=True
        ).select_related('user', 'achievement').order_by('-earned_at')[:5]
        
        context.update({
            'recent_interactions': recent_interactions,
            'active_circles': active_circles,
            'recent_achievements': recent_achievements,
            'user': self.request.user if self.request.user.is_authenticated else None,
            'community_stats': self._get_community_stats()
        })
        
        return context
    
    def _get_community_stats(self):
        """Get community statistics for template"""
        return {
            'total_members': User.objects.count(),
            'today_interactions': GentleInteraction.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            'active_circles': SupportCircle.objects.count(),
            'total_encouragements': GentleInteraction.objects.filter(
                interaction_type='encouragement'
            ).count()
        }


class InteractionListView(ListView):
    """
    List all interactions
    """
    template_name = 'social/interactions/list.html'
    context_object_name = 'interactions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = GentleInteraction.objects.filter(
            Q(visibility='public') | Q(visibility='community')
        ).select_related('sender').prefetch_related('replies')
        
        # Apply filters
        interaction_type = self.request.GET.get('type')
        if interaction_type:
            queryset = queryset.filter(interaction_type=interaction_type)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(message__icontains=search) |
                Q(therapeutic_intent__icontains=search)
            )
        
        # Apply sorting
        sort = self.request.GET.get('sort', 'newest')
        if sort == 'oldest':
            queryset = queryset.order_by('created_at')
        elif sort == 'most_liked':
            queryset = queryset.order_by('-likes_count')
        elif sort == 'most_commented':
            queryset = queryset.annotate(
                reply_count=Count('replies')
            ).order_by('-reply_count')
        else:  # newest
            queryset = queryset.order_by('-created_at')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_interactions'] = GentleInteraction.objects.count()
        context['user'] = self.request.user
        return context


class InteractionDetailView(DetailView):
    """
    View a single interaction
    """
    template_name = 'social/interactions/detail.html'
    model = GentleInteraction
    context_object_name = 'interaction'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('sender')
        
        # Check visibility
        user = self.request.user
        if user.is_authenticated:
            queryset = queryset.filter(
                Q(visibility='public') |
                Q(visibility='community') |
                Q(visibility='anonymous') |
                Q(sender=user)
            )
        else:
            queryset = queryset.filter(
                Q(visibility='public') |
                Q(visibility='anonymous')
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        interaction = self.object
        
        # Get replies
        replies = interaction.replies.select_related('sender').order_by('created_at')
        
        # Check if user likes this interaction
        user_likes = False
        if self.request.user.is_authenticated:
            # Note: You'll need to implement a likes model for this
            # For now, we'll use a placeholder
            user_likes = False
        
        # Get similar interactions
        similar_interactions = GentleInteraction.objects.filter(
            interaction_type=interaction.interaction_type
        ).exclude(id=interaction.id).select_related('sender')[:5]
        
        context.update({
            'replies': replies,
            'user_likes': user_likes,
            'similar_interactions': similar_interactions,
            'user': self.request.user
        })
        
        return context
    
def post(self, request, *args, **kwargs):
    # ...
    # Change from:
    # return redirect('interaction-detail', pk=interaction.pk)
    # To:
        return redirect('social:interaction_detail', pk=interaction.pk)


@method_decorator(login_required, name='dispatch')
class InteractionCreateView(CreateView):
    """
    Create a new interaction
    """
    template_name = 'social/interactions/create.html'
    form_class = GentleInteractionForm
    model = GentleInteraction
    
    def get_success_url(self):
    # Change from:
    # return reverse('interaction-detail', kwargs={'pk': self.object.pk})
    # To:
        return reverse('social:interaction_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.sender = self.request.user
        
        # Set therapeutic impact score
        message = form.cleaned_data.get('message', '')
        form.instance.therapeutic_impact_score = self._calculate_therapeutic_score(message)
        
        response = super().form_valid(form)
        
        # Create achievement if applicable
        self._check_achievements(self.request.user)
        
        messages.success(self.request, 'Interaction created successfully!')
        return response
    
    def _calculate_therapeutic_score(self, message):
        """Calculate therapeutic impact score for message"""
        # Simple implementation - in production, use NLP
        positive_words = ['support', 'encourage', 'progress', 'growth', 'heal', 'hope']
        score = 50  # Base score
        
        message_lower = message.lower()
        for word in positive_words:
            if word in message_lower:
                score += 5
        
        # Cap at 100
        return min(score, 100)
    
    def _check_achievements(self, user):
        """Check and award achievements"""
        # First interaction achievement
        user_interactions = GentleInteraction.objects.filter(sender=user).count()
        if user_interactions == 1:
            try:
                achievement = Achievement.objects.get(name='First Interaction')
                UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=achievement,
                    defaults={'earned_at': timezone.now()}
                )
            except Achievement.DoesNotExist:
                pass
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


class SupportCircleListView(ListView):
    """
    List all support circles
    """
    template_name = 'social/circles/list.html'
    context_object_name = 'circles'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = SupportCircle.objects.prefetch_related('memberships__user')
        
        # Filter based on user authentication
        user = self.request.user
        if user.is_authenticated:
            queryset = queryset.filter(
                Q(is_public=True) | Q(memberships__user=user)
            ).distinct()
        else:
            queryset = queryset.filter(is_public=True)
        
        # Apply search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(focus_areas__icontains=search)
            )
        
        return queryset.order_by('-active_members', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        
        # Add user memberships for template
        if self.request.user.is_authenticated:
            user_memberships = CircleMembership.objects.filter(
                user=self.request.user
            ).values_list('circle_id', flat=True)
            context['user_memberships'] = list(user_memberships)
        
        return context


class SupportCircleDetailView(DetailView):
    """
    View a single support circle
    """
    template_name = 'social/circles/detail.html'
    model = SupportCircle
    context_object_name = 'circle'
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('created_by')
        
        # Check visibility and membership
        user = self.request.user
        if user.is_authenticated:
            queryset = queryset.filter(
                Q(is_public=True) | Q(memberships__user=user)
            ).distinct()
        else:
            queryset = queryset.filter(is_public=True)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        circle = self.object
        
        # Get circle memberships
        memberships = CircleMembership.objects.filter(
            circle=circle
        ).select_related('user').order_by('-role', 'joined_at')
        
        # Check if user is a member
        user_membership = None
        if self.request.user.is_authenticated:
            try:
                user_membership = CircleMembership.objects.get(
                    circle=circle,
                    user=self.request.user
                )
            except CircleMembership.DoesNotExist:
                pass
        
        # Get circle interactions
        circle_interactions = GentleInteraction.objects.filter(
            Q(visibility='circle') | Q(visibility='community'),
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('sender').order_by('-created_at')[:20]
        
        context.update({
            'memberships': memberships,
            'user_membership': user_membership,
            'circle_interactions': circle_interactions,
            'user': self.request.user
        })
        
        return context


@method_decorator(login_required, name='dispatch')
class SupportCircleJoinView(FormView):
    """
    Join a support circle
    """
    template_name = 'social/circles/join.html'
    form_class = CircleJoinForm
    
    def dispatch(self, request, *args, **kwargs):
        self.circle = get_object_or_404(SupportCircle, pk=self.kwargs['pk'])
        
        # Check if user is already a member
        if CircleMembership.objects.filter(
            circle=self.circle,
            user=request.user
        ).exists():
            messages.warning(request, 'You are already a member of this circle')
            return redirect('social:circle_detail', pk=self.circle.pk)
        
        # Check if circle is full
        if self.circle.active_members >= self.circle.max_members:
            messages.error(request, 'This support circle is full')
            return redirect('social:circle_detail', pk=self.circle.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['circle'] = self.circle
        context['user'] = self.request.user
        return context
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['circle'] = self.circle
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Create membership
                membership = CircleMembership.objects.create(
                    circle=self.circle,
                    user=self.request.user,
                    role='member',
                    notification_preferences=form.cleaned_data.get(
                        'notification_preferences',
                        {'new_messages': True, 'meeting_reminders': True}
                    ),
                    introduction=form.cleaned_data.get('introduction', '')
                )
                
                # Update circle member count
                self.circle.active_members += 1
                self.circle.save(update_fields=['active_members'])
                
                # Check achievements
                self._check_membership_achievements(self.request.user)
                
                messages.success(
                    self.request,
                    f'Successfully joined {self.circle.name}!'
                )
                
                return redirect('circle-detail', pk=self.circle.pk)
                
        except Exception as e:
            logger.error(f"Error joining circle: {e}")
            messages.error(self.request, 'Failed to join circle. Please try again.')
            return self.form_invalid(form)
    
    def _check_membership_achievements(self, user):
        """Check and award membership achievements"""
        # First circle join achievement
        user_circles = CircleMembership.objects.filter(user=user).count()
        if user_circles == 1:
            try:
                achievement = Achievement.objects.get(name='Circle Explorer')
                UserAchievement.objects.get_or_create(
                    user=user,
                    achievement=achievement,
                    defaults={'earned_at': timezone.now()}
                )
            except Achievement.DoesNotExist:
                pass


class AchievementListView(ListView):
    """
    List all achievements
    """
    template_name = 'social/achievements/list.html'
    context_object_name = 'achievements'
    
    def get_queryset(self):
        return Achievement.objects.filter(is_active=True).order_by('tier', 'name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get user achievements if logged in
        if self.request.user.is_authenticated:
            user_achievements = UserAchievement.objects.filter(
                user=self.request.user
            ).select_related('achievement').order_by('-earned_at')
            context['user_achievements'] = user_achievements
        
        # Get recent community achievements
        recent_community_achievements = UserAchievement.objects.filter(
            shared_publicly=True
        ).select_related('user', 'achievement').order_by('-earned_at')[:10]
        context['recent_community_achievements'] = recent_community_achievements
        
        context['user'] = self.request.user
        return context


@method_decorator(login_required, name='dispatch')
class UserAchievementsView(TemplateView):
    """
    View user's personal achievements
    """
    template_name = 'social/achievements/user_achievements.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Get user achievements
        user_achievements = UserAchievement.objects.filter(
            user=user
        ).select_related('achievement').order_by('-earned_at')
        
        # Calculate statistics
        total_achievements = user_achievements.count()
        bronze_count = user_achievements.filter(achievement__tier='bronze').count()
        silver_count = user_achievements.filter(achievement__tier='silver').count()
        gold_count = user_achievements.filter(achievement__tier='gold').count()
        
        # Calculate percentages
        total_available = Achievement.objects.filter(is_active=True).count()
        progress_percentage = (total_achievements / total_available * 100) if total_available > 0 else 0
        
        # Next achievements (not yet earned)
        earned_achievement_ids = user_achievements.values_list('achievement_id', flat=True)
        next_achievements = Achievement.objects.filter(
            is_active=True
        ).exclude(id__in=earned_achievement_ids).order_by('tier', 'name')[:5]
        
        # Get earliest and latest achievements
        earliest = user_achievements.order_by('earned_at').first()
        latest = user_achievements.order_by('-earned_at').first()
        
        # Calculate achievement streak (simplified)
        achievement_streak = self._calculate_achievement_streak(user_achievements)
        
        # Calculate community rank percentile (simplified)
        total_users = User.objects.count()
        users_with_achievements = User.objects.filter(
            userachievement__isnull=False
        ).distinct().count()
        community_rank_percentile = 100 if total_users == 0 else round(
            (users_with_achievements / total_users) * 100, 1
        )
        
        context.update({
            'user_achievements': user_achievements,
            'total_achievements': total_achievements,
            'bronze_count': bronze_count,
            'silver_count': silver_count,
            'gold_count': gold_count,
            'progress_percentage': round(progress_percentage, 1),
            'next_achievements': next_achievements,
            'earliest_achievement': earliest,
            'latest_achievement': latest,
            'achievement_streak': achievement_streak,
            'community_rank_percentile': community_rank_percentile,
            'user': user
        })
        
        return context
    
    def _calculate_achievement_streak(self, user_achievements):
        """Calculate consecutive days with achievements"""
        if not user_achievements:
            return 0
        
        # Get dates of achievements
        achievement_dates = user_achievements.values_list('earned_at', flat=True)
        
        # Convert to dates
        dates = [date.date() for date in achievement_dates]
        unique_dates = sorted(set(dates), reverse=True)
        
        # Calculate streak
        streak = 1
        current_date = timezone.now().date()
        
        for i in range(1, len(unique_dates)):
            if (unique_dates[i-1] - unique_dates[i]).days == 1:
                streak += 1
            else:
                break
        
        return streak


# ============================================================================
# VIEWSETS - SIMPLIFIED
# ============================================================================

class GentleInteractionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for therapeutic gentle interactions
    """
    
    queryset = GentleInteraction.objects.select_related(
        'sender', 'recipient'
    ).filter(
        expires_at__gt=timezone.now()
    ).order_by('-is_pinned', '-created_at')
    
    serializer_class = GentleInteractionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'message', 'therapeutic_intent']
    ordering_fields = ['created_at', 'therapeutic_impact_score', 'likes_count']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Override queryset to apply visibility filters
        """
        queryset = super().get_queryset()
        user = self.request.user if self.request else None
        
        # Apply visibility filtering
        if user and user.is_authenticated:
            queryset = queryset.filter(
                Q(visibility='public') |
                Q(visibility='community') |
                Q(visibility='anonymous') |
                Q(sender=user) |
                Q(recipient=user)
            ).distinct()
        else:
            queryset = queryset.filter(
                Q(visibility='public') |
                Q(visibility='anonymous')
            )
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """
        Create interaction with therapeutic validation
        """
        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                
                self._analyze_therapeutic_content(serializer.validated_data)
                self.perform_create(serializer)
                
                headers = self.get_success_headers(serializer.data)
                return Response(
                    serializer.data,
                    status=status.HTTP_201_CREATED,
                    headers=headers
                )
                
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], url_path='send-encouragement')
    def send_encouragement(self, request):
        """
        Send quick encouragement
        """
        serializer = GentleEncouragementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        recipient_id = data.get('recipient_id')
        
        try:
            if recipient_id:
                recipient = User.objects.get(id=recipient_id)
                if hasattr(recipient, 'hide_progress') and recipient.hide_progress:
                    return Response(
                        {'error': 'Cannot send to private users'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                recipient = None
            
            interaction = GentleInteraction.objects.create(
                sender=None if data['anonymous'] else request.user,
                recipient=recipient,
                interaction_type='encouragement',
                message=data['message'],
                visibility='anonymous' if data['anonymous'] else 'community',
                therapeutic_intent="To offer support and encouragement"
            )
            
            return Response(
                GentleInteractionSerializer(interaction).data,
                status=status.HTTP_201_CREATED
            )
            
        except User.DoesNotExist:
            return Response(
                {'error': 'Recipient not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'], url_path='create-reply')
    def create_reply(self, request, pk=None):
        """
        Create a therapeutic reply to an interaction
        """
        interaction = self.get_object()
        
        if not interaction.allow_replies:
            return Response(
                {'error': 'Replies are not allowed for this interaction'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message = request.data.get('message')
        anonymous = request.data.get('anonymous', False)
        
        if not message:
            return Response(
                {'error': 'Reply message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            reply = interaction.create_reply(
                user=request.user,
                message=message,
                anonymous=anonymous
            )
            
            return Response(
                GentleInteractionSerializer(reply).data,
                status=status.HTTP_201_CREATED
            )
            
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def _analyze_therapeutic_content(self, data):
        """Analyze content for therapeutic appropriateness"""
        message = data.get('message', '').lower()
        title = data.get('title', '').lower()
        
        concerning_patterns = [
            r'\b(kill|die|suicide|hurt myself)\b',
            r'\b(hate|worthless|stupid|idiot)\b',
        ]
        
        for pattern in concerning_patterns:
            if re.search(pattern, message) or re.search(pattern, title):
                raise ValidationError(
                    "This contains language that may need therapeutic support"
                )
        
        word_count = len(message.split())
        if word_count > 500:
            raise ValidationError(
                "Messages should be concise for gentle reading"
            )


class AchievementViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for therapeutic achievements system
    """
    
    queryset = Achievement.objects.filter(is_active=True).order_by('tier', 'name')
    serializer_class = AchievementSerializer
    permission_classes = [AllowAny]
    pagination_class = PageNumberPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'tier']
    ordering_fields = ['tier', 'name', 'created_at']
    ordering = ['tier', 'name']
    
    @action(detail=True, methods=['get'], url_path='recent-earners')
    def recent_earners(self, request, pk=None):
        """Get recent earners of this achievement"""
        achievement = self.get_object()
        
        recent_earners = UserAchievement.objects.filter(
            achievement=achievement
        ).select_related('user').order_by('-earned_at')[:10]
        
        data = [
            {
                'user': {
                    'id': ua.user.id,
                    'username': ua.user.username,
                    'avatar_color': getattr(ua.user, 'avatar_color', '#000000')
                },
                'earned_at': ua.earned_at,
                'reflection': ua.reflection_notes[:100] if ua.reflection_notes else None
            }
            for ua in recent_earners
        ]
        
        return Response(data)
    
    @action(detail=True, methods=['post'], url_path='add-reflection')
    def add_reflection(self, request, pk=None):
        """Add reflection to user achievement"""
        user_achievement = get_object_or_404(
            UserAchievement,
            achievement_id=pk,
            user=request.user
        )
        
        reflection = request.data.get('reflection', '').strip()
        share_publicly = request.data.get('share_publicly', False)
        
        if not reflection:
            return Response(
                {'error': 'Reflection is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_achievement.reflection_notes = reflection
        user_achievement.shared_publicly = share_publicly
        user_achievement.save()
        
        return Response({
            'success': True,
            'message': 'Reflection added successfully'
        })
    
    @action(detail=True, methods=['post'], url_path='share')
    def share_achievement(self, request, pk=None):
        """Share achievement with community"""
        user_achievement = get_object_or_404(
            UserAchievement,
            achievement_id=pk,
            user=request.user
        )
        
        user_achievement.shared_publicly = True
        user_achievement.save()
        
        return Response({
            'success': True,
            'message': 'Achievement shared with community'
        })


class SupportCircleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for therapeutic support circles
    """
    
    queryset = SupportCircle.objects.select_related(
        'created_by'
    ).prefetch_related(
        'memberships__user'
    ).order_by('-active_members', 'name')
    
    serializer_class = SupportCircleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'focus_areas']
    ordering_fields = ['active_members', 'total_interactions', 'created_at', 'name']
    ordering = ['-active_members', 'name']
    
    def get_queryset(self):
        """Filter circles based on visibility and membership"""
        queryset = super().get_queryset()
        user = self.request.user
        
        if user and user.is_authenticated:
            queryset = queryset.filter(
                Q(is_public=True) |
                Q(memberships__user=user)
            ).distinct()
        else:
            queryset = queryset.filter(is_public=True)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create support circle with therapeutic validation"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        serializer.validated_data['created_by'] = request.user
        
        with transaction.atomic():
            circle = serializer.save()
            
            CircleMembership.objects.create(
                circle=circle,
                user=request.user,
                role='leader'
            )
            
            circle.active_members = 1
            circle.save(update_fields=['active_members'])
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
    @action(detail=True, methods=['post'], url_path='join')
    def join_circle(self, request, pk=None):
        """Join a support circle"""
        circle = self.get_object()
        user = request.user
        
        if CircleMembership.objects.filter(
            circle=circle,
            user=user
        ).exists():
            return Response(
                {'error': 'Already a member of this circle'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if circle.active_members >= circle.max_members:
            return Response(
                {'error': 'Support circle is full'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not circle.is_public:
            join_code = request.data.get('join_code', '')
            if join_code != circle.join_code:
                return Response(
                    {'error': 'Invalid join code'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            with transaction.atomic():
                membership = CircleMembership.objects.create(
                    circle=circle,
                    user=user,
                    role='member',
                    notification_preferences={
                        'new_messages': True,
                        'meeting_reminders': True,
                        'member_joins': False
                    }
                )
                
                circle.active_members += 1
                circle.save(update_fields=['active_members'])
                
                return Response(
                    CircleMembershipSerializer(membership).data,
                    status=status.HTTP_201_CREATED
                )
                
        except Exception as e:
            logger.error(f"Error joining circle: {e}")
            return Response(
                {'error': 'Failed to join circle'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='leave')
    def leave_circle(self, request, pk=None):
        """Leave a support circle"""
        circle = self.get_object()
        user = request.user
        
        membership = get_object_or_404(
            CircleMembership,
            circle=circle,
            user=user
        )
        
        # Check if user is the last leader
        if membership.role == 'leader':
            other_leaders = CircleMembership.objects.filter(
                circle=circle,
                role='leader'
            ).exclude(user=user).exists()
            
            if not other_leaders:
                # Need to transfer leadership before leaving
                new_leader_id = request.data.get('new_leader_id')
                if not new_leader_id:
                    return Response(
                        {'error': 'Please transfer leadership before leaving'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                try:
                    new_leader_membership = CircleMembership.objects.get(
                        circle=circle,
                        user_id=new_leader_id
                    )
                    new_leader_membership.role = 'leader'
                    new_leader_membership.save()
                except CircleMembership.DoesNotExist:
                    return Response(
                        {'error': 'Selected new leader not found in circle'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
        
        try:
            with transaction.atomic():
                membership.delete()
                
                circle.active_members -= 1
                circle.save(update_fields=['active_members'])
                
                return Response({
                    'success': True,
                    'message': 'Successfully left the circle'
                })
                
        except Exception as e:
            logger.error(f"Error leaving circle: {e}")
            return Response(
                {'error': 'Failed to leave circle'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# ANALYTICS VIEWS
# ============================================================================

class CommunityAnalyticsView(APIView):
    """
    Community analytics
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get community analytics"""
        cache_key = f'community_analytics_{timezone.now().date()}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        analytics = self._calculate_community_analytics()
        cache.set(cache_key, analytics, 3600)
        
        return Response(analytics)
    
    def _calculate_community_analytics(self):
        """Calculate community analytics"""
        total_members = User.objects.count()
        active_today = User.objects.filter(
            last_login__date=timezone.now().date()
        ).count()
        
        total_interactions = GentleInteraction.objects.count()
        encouragements = GentleInteraction.objects.filter(
            interaction_type='encouragement'
        ).count()
        
        support_circles = SupportCircle.objects.count()
        circle_memberships = CircleMembership.objects.count()
        achievements_earned = UserAchievement.objects.count()
        
        avg_therapeutic_score = GentleInteraction.objects.aggregate(
            avg_score=Avg('therapeutic_impact_score')
        )['avg_score'] or 0
        
        engagement_rate = self._calculate_engagement_rate()
        positivity_score = self._calculate_positivity_score()
        
        data = {
            'total_members': total_members,
            'active_today': active_today,
            'total_interactions': total_interactions,
            'encouragements': encouragements,
            'support_circles': support_circles,
            'circle_memberships': circle_memberships,
            'achievements_earned': achievements_earned,
            'avg_therapeutic_score': round(float(avg_therapeutic_score), 2),
            'engagement_rate': round(float(engagement_rate), 3),
            'positivity_score': round(float(positivity_score), 3),
            'calculated_at': timezone.now().isoformat()
        }
        
        return data
    
    def _calculate_engagement_rate(self):
        """Calculate community engagement rate"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        active_users = User.objects.filter(
            last_login__gte=week_ago
        ).count()
        
        total_users = User.objects.count()
        
        if total_users == 0:
            return 0.0
        
        return active_users / total_users
    
    def _calculate_positivity_score(self):
        """Calculate community positivity score"""
        positive_words = [
            'great', 'good', 'happy', 'proud', 'progress',
            'improve', 'better', 'support', 'encourage', 'thank'
        ]
        
        recent_interactions = GentleInteraction.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        )[:1000]
        
        if not recent_interactions:
            return 0.5
        
        positive_count = 0
        total_words = 0
        
        for interaction in recent_interactions:
            message = interaction.message.lower()
            words = message.split()
            total_words += len(words)
            
            for word in positive_words:
                if word in message:
                    positive_count += 1
        
        if total_words == 0:
            return 0.5
        
        return positive_count / total_words


# ============================================================================
# API ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def api_community_stats(request):
    """API endpoint for community statistics"""
    stats = {
        'total_members': User.objects.count(),
        'active_today': User.objects.filter(
            last_login__date=timezone.now().date()
        ).count(),
        'total_interactions': GentleInteraction.objects.count(),
        'total_encouragements': GentleInteraction.objects.filter(
            interaction_type='encouragement'
        ).count(),
        'support_circles': SupportCircle.objects.count(),
        'achievements_earned': UserAchievement.objects.count()
    }
    
    return Response(stats)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_send_quick_encouragement(request):
    """API endpoint for quick encouragement"""
    serializer = GentleEncouragementSerializer(data=request.data)
    
    if serializer.is_valid():
        data = serializer.validated_data
        
        try:
            recipient = None
            if data.get('recipient_id'):
                recipient = User.objects.get(id=data['recipient_id'])
            
            interaction = GentleInteraction.objects.create(
                sender=None if data['anonymous'] else request.user,
                recipient=recipient,
                interaction_type='encouragement',
                message=data['message'],
                visibility='anonymous' if data['anonymous'] else 'community'
            )
            
            return Response(
                GentleInteractionSerializer(interaction).data,
                status=status.HTTP_201_CREATED
            )
            
        except User.DoesNotExist:
            return Response(
                {'error': 'Recipient not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_share_progress(request):
    """Share achievement progress summary"""
    user = request.user
    
    # Get user achievements
    user_achievements = UserAchievement.objects.filter(
        user=user,
        shared_publicly=True
    ).count()
    
    # Mark remaining achievements as shared
    unshared_achievements = UserAchievement.objects.filter(
        user=user,
        shared_publicly=False
    )
    
    updated_count = unshared_achievements.update(shared_publicly=True)
    
    return Response({
        'success': True,
        'message': f'Shared {updated_count} achievements with community',
        'total_shared': user_achievements + updated_count
    })


# ============================================================================
# HEALTH CHECK
# ============================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check endpoint for monitoring"""
    try:
        User.objects.count()
        
        cache.set('health_check', 'ok', 10)
        cache_result = cache.get('health_check') == 'ok'
        
        GentleInteraction.objects.exists()
        SupportCircle.objects.exists()
        
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'database': 'connected',
            'cache': 'working' if cache_result else 'warning',
            'version': '1.0.0'
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return Response(
            {'status': 'unhealthy', 'error': str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )


# Initialize logging
logging.basicConfig(level=logging.INFO)
logger.info("Therapeutic Social Views initialized")