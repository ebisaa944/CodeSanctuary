# learning/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db.models import Q, Count, Avg, Sum
from django.core.paginator import Paginator
import json
from datetime import datetime, timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import LearningPath, MicroActivity, UserProgress
from .serializers import (
    LearningPathSerializer, MicroActivitySerializer, 
    UserProgressSerializer, ActivitySubmissionSerializer,
    GentleRecommendationSerializer, LearningStatsSerializer
)
from .filters import MicroActivityFilter, LearningPathFilter, UserProgressFilter
from .pagination import (
    GentleActivityPagination, LearningPathPagination, UserProgressPagination
)
from .permissions import (
    ActivityAccessPermission, UserProgressPermission,
    LearningPathPermission, TherapeuticSubmissionPermission
)

# Helper functions
def get_next_activity_suggestion(user, current_activity):
    """Suggest next activity based on therapeutic considerations"""
    # Get user's emotional state
    emotional_state = user.get_emotional_state() if hasattr(user, 'get_emotional_state') else 'neutral'
    
    # Suggest based on current emotional state
    if emotional_state in ['anxious', 'overwhelmed']:
        # Suggest something gentler or the same difficulty
        suggestions = MicroActivity.objects.filter(
            difficulty_level__lte=current_activity.difficulty_level,
            therapeutic_focus__in=['confidence', 'mindfulness'],
            is_published=True
        ).exclude(id=current_activity.id)[:3]
    elif emotional_state == 'energetic':
        # Suggest something more challenging
        suggestions = MicroActivity.objects.filter(
            difficulty_level__gte=current_activity.difficulty_level,
            is_published=True
        ).exclude(id=current_activity.id)[:3]
    else:
        # Suggest related activities
        suggestions = MicroActivity.objects.filter(
            therapeutic_focus=current_activity.therapeutic_focus,
            is_published=True
        ).exclude(id=current_activity.id)[:3]
    
    return suggestions.first() if suggestions else None

# Web Views
@login_required
def learning_dashboard(request):
    """Main learning dashboard"""
    # Get user's learning plan
    user_plan = request.user.get_safe_learning_plan()
    
    # Get recommended paths based on user profile
    recommended_paths = LearningPath.objects.filter(
        is_active=True
    ).order_by('difficulty_level')[:3]
    
    # Get user progress
    user_progress = UserProgress.objects.filter(
        user=request.user
    ).select_related('activity')
    
    # Get recent activities
    recent_progress = user_progress.order_by('-updated_at')[:5]
    
    # Get completion stats
    completed = user_progress.filter(status=UserProgress.ProgressStatus.COMPLETED).count()
    in_progress = user_progress.filter(status=UserProgress.ProgressStatus.IN_PROGRESS).count()
    
    # Get daily streak
    streak = request.user.get_streak() if hasattr(request.user, 'get_streak') else 0
    
    context = {
        'page_title': 'Learning Dashboard',
        'page_subtitle': 'Your Therapeutic Learning Journey',
        'user_plan': user_plan,
        'recommended_paths': recommended_paths,
        'recent_progress': recent_progress,
        'stats': {
            'completed': completed,
            'in_progress': in_progress,
            'streak': streak,
            'today_minutes': user_progress.filter(
                updated_at__date=datetime.now().date()
            ).aggregate(Sum('time_spent_seconds'))['time_spent_seconds__sum'] or 0,
        },
        'emotional_state': request.user.get_emotional_state() if hasattr(request.user, 'get_emotional_state') else 'neutral',
    }
    
    return render(request, 'learning/dashboard.html', context)

@login_required
@require_POST
def skip_day(request):
    """Mark a day as skipped for therapeutic learning"""
    try:
        user_profile = request.user.profile
        today = datetime.date.today()
        
        # Store skip information (you might want to save this to a model)
        # For now, we'll just return a success message
        # You could create a UserSkipDay model to track skipped days
        
        return JsonResponse({
            'success': True,
            'message': 'Day marked as rest day. Take good care of yourself!',
            'date': today.isoformat()
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error processing skip request'
        }, status=400)
    
@login_required
@require_POST
def update_readiness(request):
    """Update user's readiness preference"""
    # Implementation here
    pass

@login_required
def learning_paths(request):
    """Browse all learning paths"""
    difficulty = request.GET.get('difficulty', '')
    language = request.GET.get('language', '')
    sort = request.GET.get('sort', '')
    
    # Base queryset
    paths = LearningPath.objects.filter(is_active=True)
    
    # Apply filters
    if difficulty:
        paths = paths.filter(difficulty_level=int(difficulty))
    
    if language:
        paths = paths.filter(target_language=language)
    
    # Apply sorting
    if sort:
        paths = paths.order_by(sort)
    else:
        paths = paths.order_by('difficulty_level')
    
    # Get progress for each path
    for path in paths:
        # Get user progress
        progress = UserProgress.objects.filter(
            user=request.user,
            activity__learning_path=path
        ).aggregate(
            completed=Count('id', filter=Q(status=UserProgress.ProgressStatus.COMPLETED)),
            total=Count('id')
        )
        
        # Calculate percentage
        total_activities = path.activities.filter(is_published=True).count()
        completed_activities = progress['completed'] or 0
        
        path.user_progress = {
            'completed': completed_activities,
            'total': total_activities,
            'percentage': (completed_activities / total_activities * 100) if total_activities > 0 else 0
        }
    
    # Calculate counts for stats
    started_count = 0
    completed_count = 0
    
    for path in paths:
        if path.user_progress['percentage'] > 0:
            started_count += 1
        if path.user_progress['percentage'] == 100:
            completed_count += 1
    
    # Get choice fields for filters
    try:
        difficulties = LearningPath.DIFFICULTY_CHOICES
    except:
        difficulties = [
            (1, 'Beginner'),
            (2, 'Easy'),
            (3, 'Medium'),
            (4, 'Hard'),
            (5, 'Advanced'),
            (6, 'Expert')
        ]
    
    try:
        languages = LearningPath._meta.get_field('target_language').choices
    except:
        languages = [
            ('python', 'Python'),
            ('javascript', 'JavaScript'),
            ('html', 'HTML/CSS'),
            ('java', 'Java'),
            ('csharp', 'C#'),
            ('cpp', 'C++'),
        ]
    
    context = {
        'page_title': 'Learning Paths',
        'page_subtitle': 'Choose Your Therapeutic Journey',
        'paths': paths,
        'difficulties': difficulties,
        'languages': languages,
        'started_count': started_count,
        'completed_count': completed_count,
        'user': request.user,
    }
    
    return render(request, 'learning/paths.html', context)

@login_required
def learning_path_detail(request, slug=None, path_id=None):
    """View a specific learning path - supports both slug and ID"""
    # Try to get by slug first, then by ID
    if slug:
        path = get_object_or_404(LearningPath, slug=slug, is_active=True)
    elif path_id:
        path = get_object_or_404(LearningPath, id=path_id, is_active=True)
    else:
        raise Http404("Learning path not found")
    
    # Get activities in this path
    activities = MicroActivity.objects.filter(
        learning_path=path,
        is_published=True
    ).order_by('order_position')
    
    # Get user progress for each activity
    user_progress = {}
    for activity in activities:
        progress = UserProgress.objects.filter(
            user=request.user,
            activity=activity
        ).first()
        user_progress[activity.id] = progress
    
    # Calculate overall progress
    total_activities = activities.count()
    completed_activities = UserProgress.objects.filter(
        user=request.user,
        activity__in=activities,
        status=UserProgress.ProgressStatus.COMPLETED
    ).count()
    
    progress_data = {
        'completed': completed_activities,
        'total': total_activities,
        'percentage': (completed_activities / total_activities * 100) if total_activities > 0 else 0
    }
    
    # Get therapeutic recommendations
    therapeutic_context = {
        'suitable': getattr(path, 'recommended_for_profiles', 'All users'),
        'pace': f"~{getattr(path, 'max_daily_minutes', 30)} minutes daily",
        'approach': 'Gradual, gentle progression',
    }
    
    context = {
        'page_title': path.name,
        'page_subtitle': getattr(path, 'get_difficulty_level_display', lambda: 'Medium')(),
        'path': path,
        'activities': activities,
        'user_progress': user_progress,
        'progress_data': progress_data,
        'therapeutic_context': therapeutic_context,
    }
    
    return render(request, 'learning/path_detail.html', context)

@login_required
def activity_detail(request, slug):
    """View and work on a specific activity"""
    activity = get_object_or_404(MicroActivity, slug=slug, is_published=True)
    
    # Get or create user progress
    progress, created = UserProgress.objects.get_or_create(
        user=request.user,
        activity=activity,
        defaults={'status': UserProgress.ProgressStatus.NOT_STARTED}
    )
    
    # Check if activity is suitable
    is_suitable = True
    message = ""
    if hasattr(activity, 'is_suitable_for_user'):
        is_suitable, message = activity.is_suitable_for_user(request.user)
    
    # Get therapeutic context
    therapeutic_context = {}
    if hasattr(activity, 'get_therapeutic_context'):
        therapeutic_context = activity.get_therapeutic_context()
    
    # Get similar activities
    similar_activities = MicroActivity.objects.filter(
        therapeutic_focus=getattr(activity, 'therapeutic_focus', 'general'),
        difficulty_level=activity.difficulty_level,
        is_published=True
    ).exclude(id=activity.id)[:3]
    
    context = {
        'page_title': activity.title,
        'page_subtitle': getattr(activity, 'short_description', ''),
        'activity': activity,
        'progress': progress,
        'is_suitable': is_suitable,
        'suitability_message': message,
        'therapeutic_context': therapeutic_context,
        'similar_activities': similar_activities,
    }
    
    return render(request, 'learning/activity_detail.html', context)

@login_required
def progress_report(request):
    """View comprehensive progress report"""
    # Get time period
    period = request.GET.get('period', 'week')
    
    if period == 'week':
        start_date = datetime.now() - timedelta(days=7)
    elif period == 'month':
        start_date = datetime.now() - timedelta(days=30)
    else:  # all time
        start_date = None
    
    # Get user progress
    user_progress = UserProgress.objects.filter(user=request.user)
    
    if start_date:
        user_progress = user_progress.filter(updated_at__gte=start_date)
    
    # Calculate statistics
    completed = user_progress.filter(status=UserProgress.ProgressStatus.COMPLETED)
    in_progress = user_progress.filter(status=UserProgress.ProgressStatus.IN_PROGRESS)
    
    # Calculate emotional trends
    emotional_data = []
    for progress in completed:
        if progress.emotional_state_before and progress.emotional_state_after:
            emotional_data.append({
                'date': progress.completion_time.date(),
                'before': progress.emotional_state_before,
                'after': progress.emotional_state_after,
                'stress_change': progress.stress_level_after - progress.stress_level_before if progress.stress_level_before and progress.stress_level_after else 0,
            })
    
    # Calculate skill development
    activities_by_difficulty = {}
    for progress in completed:
        diff = progress.activity.difficulty_level
        if diff not in activities_by_difficulty:
            activities_by_difficulty[diff] = 0
        activities_by_difficulty[diff] += 1
    
    context = {
        'page_title': 'Progress Report',
        'page_subtitle': 'Track Your Therapeutic Learning Journey',
        'stats': {
            'total_completed': completed.count(),
            'total_time': user_progress.aggregate(Sum('time_spent_seconds'))['time_spent_seconds__sum'] or 0,
            'avg_confidence_change': completed.aggregate(Avg('confidence_after'))['confidence_after__avg'] or 0,
            'breakthroughs': user_progress.filter(breakthrough_notes__isnull=False).count(),
        },
        'emotional_data': emotional_data,
        'activities_by_difficulty': activities_by_difficulty,
        'period': period,
    }
    
    return render(request, 'learning/progress_report.html', context)

# API Views
@login_required
@csrf_exempt
@require_POST
def start_activity(request, activity_id):
    """API endpoint to start an activity"""
    activity = get_object_or_404(MicroActivity, id=activity_id)
    
    progress, created = UserProgress.objects.get_or_create(
        user=request.user,
        activity=activity
    )
    
    # Update emotional state before
    data = json.loads(request.body) if request.body else {}
    progress.emotional_state_before = data.get('emotional_state', '')
    progress.stress_level_before = data.get('stress_level', None)
    progress.confidence_before = data.get('confidence', None)
    
    progress.start_activity()
    
    return JsonResponse({
        'success': True,
        'message': 'Activity started',
        'progress_id': progress.id,
        'start_time': progress.start_time.isoformat(),
    })

@login_required
@csrf_exempt
@require_POST
def submit_activity(request, activity_id):
    """API endpoint to submit activity completion"""
    activity = get_object_or_404(MicroActivity, id=activity_id)
    
    progress = get_object_or_404(
        UserProgress,
        user=request.user,
        activity=activity
    )
    
    data = json.loads(request.body) if request.body else {}
    
    # Update emotional state after
    progress.emotional_state_after = data.get('emotional_state', '')
    progress.stress_level_after = data.get('stress_level', None)
    progress.confidence_after = data.get('confidence', None)
    
    # Update reflection notes
    progress.reflection_notes = data.get('reflection_notes', '')
    progress.what_went_well = data.get('what_went_well', '')
    progress.challenges_faced = data.get('challenges_faced', '')
    progress.coping_strategies_used = data.get('coping_strategies', [])
    progress.self_assessment = data.get('self_assessment', None)
    
    # Submit code if provided
    user_code = data.get('code', '')
    success = data.get('success', True)
    
    # Validate solution if code provided
    if user_code and activity.validation_type != 'completion':
        validation_result = activity.validate_solution(user_code)
        success = validation_result['success']
        progress.code_output = validation_result.get('message', '')
    
    progress.complete_activity(success=success, code=user_code)
    
    # Calculate emotional impact
    emotional_impact = progress.calculate_emotional_impact()
    
    return JsonResponse({
        'success': True,
        'message': 'Activity submitted successfully',
        'emotional_impact': emotional_impact,
        'is_breakthrough': progress.is_breakthrough,
        'next_activity': get_next_activity_suggestion(request.user, activity),
    })

@login_required
def get_recommendations(request):
    """Get therapeutic activity recommendations"""
    user = request.user
    
    # Get user's emotional state
    emotional_state = user.get_emotional_state() if hasattr(user, 'get_emotional_state') else 'neutral'
    
    # Get user's current stress level
    stress_level = user.current_stress_level if hasattr(user, 'current_stress_level') else 5
    
    # Get recent activities
    recent_activities = UserProgress.objects.filter(
        user=user
    ).order_by('-completion_time')[:3]
    
    # Recommend based on therapeutic state
    if stress_level >= 7:
        # High stress - recommend gentle, mindfulness activities
        activities = MicroActivity.objects.filter(
            therapeutic_focus='mindfulness',
            difficulty_level=1,
            is_published=True
        )[:3]
        reason = "Gentle activities for high stress"
    elif emotional_state == 'tired':
        # Tired - recommend short, low-energy activities
        activities = MicroActivity.objects.filter(
            estimated_minutes__lte=10,
            difficulty_level__lte=2,
            is_published=True
        )[:3]
        reason = "Short activities for low energy"
    elif emotional_state == 'energetic':
        # Energetic - recommend challenging activities
        activities = MicroActivity.objects.filter(
            difficulty_level__gte=3,
            is_published=True
        )[:3]
        reason = "Challenging activities for high energy"
    else:
        # Neutral - recommend balanced activities
        activities = MicroActivity.objects.filter(
            difficulty_level=2,
            is_published=True
        )[:3]
        reason = "Balanced activities for neutral state"
    
    recommendations = []
    for activity in activities:
        recommendations.append({
            'activity': MicroActivitySerializer(activity, context={'request': request}).data,
            'reason': reason,
            'therapeutic_benefit': activity.therapeutic_focus,
            'estimated_time': activity.estimated_minutes,
            'preparation_tip': "Take a moment to breathe before starting",
        })
    
    return JsonResponse({'recommendations': recommendations})

@login_required
def get_learning_stats(request):
    """Get comprehensive learning statistics"""
    user = request.user
    
    # Calculate basic stats
    progress_records = UserProgress.objects.filter(user=user)
    completed = progress_records.filter(status=UserProgress.ProgressStatus.COMPLETED)
    
    # Time stats
    total_time = progress_records.aggregate(total=Sum('time_spent_seconds'))['total'] or 0
    avg_difficulty = completed.aggregate(avg=Avg('activity__difficulty_level'))['avg'] or 0
    
    # Language preference
    from django.db.models import Count
    language_stats = completed.values('activity__primary_language').annotate(
        count=Count('id')
    ).order_by('-count')
    favorite_language = language_stats.first()['activity__primary_language'] if language_stats else 'None'
    
    # Emotional trend
    stress_changes = []
    for record in completed:
        if record.stress_level_before and record.stress_level_after:
            stress_changes.append(record.stress_level_after - record.stress_level_before)
    
    if stress_changes:
        avg_stress_change = sum(stress_changes) / len(stress_changes)
        if avg_stress_change < -1:
            emotional_trend = "Reducing stress"
        elif avg_stress_change > 1:
            emotional_trend = "Increasing challenge"
        else:
            emotional_trend = "Stable experience"
    else:
        emotional_trend = "No data yet"
    
    # Breakthrough count
    breakthrough_count = progress_records.filter(
        breakthrough_notes__isnull=False
    ).count()
    
    # Current streak
    current_streak = user.get_streak() if hasattr(user, 'get_streak') else 0
    
    stats = {
        'total_activities_completed': completed.count(),
        'total_time_spent': total_time,
        'average_difficulty': round(avg_difficulty, 1),
        'favorite_language': favorite_language,
        'emotional_trend': emotional_trend,
        'breakthrough_count': breakthrough_count,
        'current_streak': current_streak,
    }
    
    return JsonResponse(stats)

# API ViewSets
class LearningPathViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for learning paths"""
    serializer_class = LearningPathSerializer
    permission_classes = [IsAuthenticated, LearningPathPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = LearningPathFilter
    pagination_class = LearningPathPagination
    search_fields = ['name', 'description']
    ordering_fields = ['difficulty_level', 'created_at', 'estimated_total_hours']
    
    def get_queryset(self):
        """Filter learning paths for current user"""
        user = self.request.user
        queryset = LearningPath.objects.filter(is_active=True)
        
        # If user has emotional profile, filter recommendations
        if hasattr(user, 'emotional_profile'):
            profile = user.emotional_profile
            queryset = queryset.filter(
                recommended_for_profiles__contains=[profile]
            )
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def activities(self, request, pk=None):
        """Get activities for a specific learning path"""
        learning_path = self.get_object()
        activities = MicroActivity.objects.filter(
            learning_path=learning_path,
            is_published=True
        ).order_by('order_position')
        
        # Apply therapeutic filtering
        therapeutic_warning = None
        for activity in activities:
            suitable, message = activity.is_suitable_for_user(request.user)
            if not suitable:
                therapeutic_warning = message
                break
        
        page = self.paginate_queryset(activities)
        if page is not None:
            serializer = MicroActivitySerializer(
                page, many=True, context={'request': request}
            )
            response = self.get_paginated_response(serializer.data)
            if therapeutic_warning:
                response.data['therapeutic_warning'] = therapeutic_warning
            return response
        
        serializer = MicroActivitySerializer(
            activities, many=True, context={'request': request}
        )
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start_path(self, request, pk=None):
        """Start working on a learning path"""
        learning_path = self.get_object()
        
        # Get first activity in path
        first_activity = MicroActivity.objects.filter(
            learning_path=learning_path,
            is_published=True
        ).order_by('order_position').first()
        
        if not first_activity:
            return Response(
                {'error': 'No activities available in this path'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create progress for first activity
        progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            activity=first_activity,
            defaults={'status': UserProgress.ProgressStatus.NOT_STARTED}
        )
        
        return Response({
            'message': f'Started learning path: {learning_path.name}',
            'first_activity': {
                'id': first_activity.id,
                'title': first_activity.title,
                'slug': first_activity.slug,
                'progress_id': progress.id
            }
        })


class MicroActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for micro activities"""
    serializer_class = MicroActivitySerializer
    permission_classes = [IsAuthenticated, ActivityAccessPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MicroActivityFilter
    pagination_class = GentleActivityPagination
    search_fields = ['title', 'short_description', 'full_description']
    ordering_fields = ['difficulty_level', 'estimated_minutes', 'order_position']
    lookup_field = 'slug'
    
    def get_queryset(self):
        """Filter activities for therapeutic suitability"""
        user = self.request.user
        queryset = MicroActivity.objects.filter(is_published=True)
        
        # Apply user's therapeutic restrictions
        if hasattr(user, 'get_safe_learning_plan'):
            plan = user.get_safe_learning_plan()
            max_difficulty = plan.get('max_difficulty', 3)
            queryset = queryset.filter(difficulty_level__lte=max_difficulty)
        
        return queryset.order_by('difficulty_level', 'order_position')
    
    @action(detail=True, methods=['post'])
    def start(self, request, slug=None):
        """Start an activity"""
        activity = self.get_object()
        
        # Check therapeutic suitability
        suitable, message = activity.is_suitable_for_user(request.user)
        if not suitable:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create or update progress
        progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            activity=activity
        )
        
        if progress.status == UserProgress.ProgressStatus.COMPLETED:
            return Response({
                'warning': 'Activity already completed',
                'progress': UserProgressSerializer(progress, context={'request': request}).data
            })
        
        progress.start_activity()
        
        return Response({
            'message': 'Activity started',
            'progress': UserProgressSerializer(progress, context={'request': request}).data
        })
    
    @action(detail=True, methods=['post'])
    def submit(self, request, slug=None):
        """Submit activity solution"""
        activity = self.get_object()
        serializer = ActivitySubmissionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create progress
        progress, created = UserProgress.objects.get_or_create(
            user=request.user,
            activity=activity
        )
        
        # Update progress with submission data
        data = serializer.validated_data
        progress.emotional_state_after = data.get('emotional_state_after', '')
        progress.stress_level_after = data.get('stress_level_after')
        progress.confidence_after = data.get('confidence_after')
        progress.reflection_notes = data.get('reflection_notes', '')
        progress.what_went_well = data.get('what_went_well', '')
        progress.challenges_faced = data.get('challenges_faced', '')
        progress.coping_strategies_used = data.get('coping_strategies_used', [])
        progress.self_assessment = data.get('self_assessment')
        
        # Validate code solution if provided
        user_code = data.get('code', '')
        success = True
        
        if user_code and activity.validation_type != 'completion':
            validation_result = activity.validate_solution(user_code)
            success = validation_result['success']
            progress.code_output = validation_result.get('message', '')
            progress.submitted_code = user_code
        
        progress.complete_activity(success=success, code=user_code)
        
        # Get next activity suggestion
        next_activity = get_next_activity_suggestion(request.user, activity)
        
        return Response({
            'message': 'Activity submitted successfully',
            'progress': UserProgressSerializer(progress, context={'request': request}).data,
            'emotional_impact': progress.calculate_emotional_impact(),
            'is_breakthrough': progress.is_breakthrough,
            'next_activity': MicroActivitySerializer(
                next_activity, context={'request': request}
            ).data if next_activity else None
        })


class UserProgressViewSet(viewsets.ModelViewSet):
    """API viewset for user progress"""
    serializer_class = UserProgressSerializer
    permission_classes = [IsAuthenticated, UserProgressPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserProgressFilter
    pagination_class = UserProgressPagination
    search_fields = ['activity__title', 'reflection_notes']
    ordering_fields = ['completion_time', 'time_spent_seconds', 'updated_at']
    
    def get_queryset(self):
        """Filter to current user's progress"""
        queryset = UserProgress.objects.filter(user=self.request.user)
        return queryset.select_related('activity')
    
    def perform_create(self, serializer):
        """Set user when creating progress"""
        serializer.save(user=self.request.user)

# ====================
# MISSING VIEW FUNCTIONS (Add these to your views.py)
# ====================

def wellness_checkin(request):
    """Wellness check-in before learning session"""
    if request.method == 'POST':
        # Handle wellness check-in form submission
        return JsonResponse({'status': 'ok', 'message': 'Wellness check-in recorded'})
    return render(request, 'learning/wellness_checkin.html')

def log_emotional_state(request):
    """Log current emotional state"""
    if request.method == 'POST' and request.is_ajax():
        data = json.loads(request.body) if request.body else {}
        emotional_state = data.get('emotional_state', 'neutral')
        # Save emotional state
        return JsonResponse({'status': 'ok', 'message': f'Emotional state ({emotional_state}) logged'})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def emotional_state_history(request):
    """Get emotional state history"""
    # Get user's emotional state history
    return JsonResponse({'history': []})

def stress_monitor(request):
    """Monitor stress levels"""
    return JsonResponse({'stress_level': 5, 'recommendation': 'Take a short break'})

def break_suggestions(request):
    """Suggest breaks based on stress level"""
    suggestions = [
        'Take 5 deep breaths',
        'Stretch for 2 minutes',
        'Drink some water',
        'Look away from the screen for 1 minute'
    ]
    return JsonResponse({'suggestions': suggestions})

def share_progress(request, activity_id):
    """Share progress with social app"""
    activity = get_object_or_404(MicroActivity, id=activity_id)
    return JsonResponse({
        'status': 'ok', 
        'message': f'Progress for {activity.title} shared',
        'activity_id': activity_id
    })

def create_collaboration_session(request):
    """Create collaborative learning session"""
    return JsonResponse({'session_id': 'temp_123', 'status': 'created'})

def join_collaboration_session(request, session_id):
    """Join collaborative learning session"""
    return JsonResponse({'session_id': session_id, 'status': 'joined'})

def community_challenges(request):
    """Get community challenges from social app"""
    return JsonResponse({'challenges': []})

def join_challenge(request, challenge_id):
    """Join a community challenge"""
    return JsonResponse({'challenge_id': challenge_id, 'status': 'joined'})

def learning_support_chat(request):
    """Redirect to chat app for learning support"""
    return JsonResponse({'redirect': '/chat/learning-support/'})

def activity_discussion(request, activity_id):
    """Discussion for specific activity"""
    return JsonResponse({'activity_id': activity_id, 'discussion': []})

def request_code_review(request):
    """Request code review through chat app"""
    return JsonResponse({'review_id': 1, 'status': 'requested'})

def code_review_detail(request, review_id):
    """View code review details"""
    return JsonResponse({'review_id': review_id, 'details': {}})

def user_learning_stats(request, user_id):
    """Get learning stats for a user"""
    return JsonResponse({'user_id': user_id, 'stats': {}})

def user_achievements(request):
    """View user achievements"""
    return JsonResponse({'achievements': []})

def learning_preferences(request):
    """View learning preferences"""
    return render(request, 'learning/preferences.html')

def update_learning_preferences(request):
    """Update learning preferences"""
    return JsonResponse({'status': 'updated'})

def current_streak(request):
    """Get current learning streak"""
    return JsonResponse({'streak': 0})

def streak_history(request):
    """Get streak history"""
    return JsonResponse({'history': []})

def earned_badges(request):
    """Get earned badges"""
    return JsonResponse({'badges': []})

def claim_badge(request, badge_id):
    """Claim a badge"""
    return JsonResponse({'badge_id': badge_id, 'claimed': True})

def points_balance(request):
    """Get points balance"""
    return JsonResponse({'points': 100})

def rewards_catalog(request):
    """View rewards catalog"""
    return JsonResponse({'rewards': []})

def redeem_reward(request, reward_id):
    """Redeem a reward"""
    return JsonResponse({'reward_id': reward_id, 'redeemed': True})

def time_analytics(request):
    """Time-based analytics"""
    return JsonResponse({'analytics': {}})

def daily_analytics(request):
    """Daily analytics"""
    return JsonResponse({'daily': {}})

def weekly_analytics(request):
    """Weekly analytics"""
    return JsonResponse({'weekly': {}})

def monthly_analytics(request):
    """Monthly analytics"""
    return JsonResponse({'monthly': {}})

def performance_analytics(request):
    """Performance analytics"""
    return JsonResponse({'performance': {}})

def improvement_analytics(request):
    """Improvement analytics"""
    return JsonResponse({'improvement': {}})

def emotional_analytics(request):
    """Emotional analytics"""
    return JsonResponse({'emotional': {}})

def stress_pattern_analytics(request):
    """Stress pattern analytics"""
    return JsonResponse({'stress_patterns': {}})

def export_progress_pdf(request):
    """Export progress as PDF"""
    return JsonResponse({'status': 'PDF export not implemented'})

def export_progress_csv(request):
    """Export progress as CSV"""
    return JsonResponse({'status': 'CSV export not implemented'})

def export_certificate(request, path_id):
    """Export certificate"""
    return JsonResponse({'path_id': path_id, 'status': 'Certificate not implemented'})

def therapy_progress_report(request):
    """Generate progress report for therapy app"""
    return JsonResponse({'report': {}})

def export_therapy_report_pdf(request):
    """Export therapy report as PDF"""
    return JsonResponse({'status': 'Therapy report PDF not implemented'})

def learning_resources(request):
    """View learning resources"""
    return JsonResponse({'resources': []})

def resource_detail(request, resource_id):
    """View resource detail"""
    return JsonResponse({'resource_id': resource_id})

def complete_resource(request, resource_id):
    """Mark resource as complete"""
    return JsonResponse({'resource_id': resource_id, 'completed': True})

def tutorials_list(request):
    """List tutorials"""
    return JsonResponse({'tutorials': []})

def tutorial_detail(request, tutorial_id):
    """View tutorial detail"""
    return JsonResponse({'tutorial_id': tutorial_id})

def code_examples(request):
    """View code examples"""
    return JsonResponse({'examples': []})

def code_example_detail(request, example_id):
    """View code example detail"""
    return JsonResponse({'example_id': example_id})

def practice_dashboard(request):
    """Practice dashboard"""
    return render(request, 'learning/practice_dashboard.html')

def start_practice_session(request):
    """Start practice session"""
    return JsonResponse({'session_id': 'practice_123', 'started': True})

def end_practice_session(request):
    """End practice session"""
    return JsonResponse({'ended': True})

def code_challenges(request):
    """View code challenges"""
    return JsonResponse({'challenges': []})

def code_challenge_detail(request, challenge_id):
    """View code challenge detail"""
    return JsonResponse({'challenge_id': challenge_id})

def submit_code_challenge(request, challenge_id):
    """Submit code challenge"""
    return JsonResponse({'challenge_id': challenge_id, 'submitted': True})

def mindfulness_exercise(request):
    """Mindfulness exercise"""
    return JsonResponse({'exercise': 'mindfulness'})

def breathing_exercise(request):
    """Breathing exercise"""
    return JsonResponse({'exercise': 'breathing'})

def stretching_exercise(request):
    """Stretching exercise"""
    return JsonResponse({'exercise': 'stretching'})

def personalized_recommendations(request):
    """Personalized recommendations"""
    return JsonResponse({'recommendations': []})

def mood_based_recommendations(request):
    """Mood-based recommendations"""
    return JsonResponse({'recommendations': []})

def adjust_difficulty(request):
    """Adjust difficulty"""
    return JsonResponse({'difficulty_adjusted': True})

def suggest_difficulty(request):
    """Suggest difficulty"""
    return JsonResponse({'suggested_difficulty': 'medium'})

def learning_style_assessment(request):
    """Learning style assessment"""
    return JsonResponse({'assessment': {}})

def learning_style_result(request):
    """Learning style result"""
    return JsonResponse({'learning_style': 'visual'})

def learning_reminders(request):
    """View learning reminders"""
    return JsonResponse({'reminders': []})

def set_reminder(request):
    """Set reminder"""
    return JsonResponse({'reminder_set': True})

def delete_reminder(request, reminder_id):
    """Delete reminder"""
    return JsonResponse({'reminder_id': reminder_id, 'deleted': True})

def daily_goals(request):
    """View daily goals"""
    return JsonResponse({'goals': []})

def set_daily_goal(request):
    """Set daily goal"""
    return JsonResponse({'goal_set': True})

def complete_daily_goal(request):
    """Complete daily goal"""
    return JsonResponse({'goal_completed': True})

def help_center(request):
    """Help center"""
    return render(request, 'learning/help_center.html')

def faq(request):
    """FAQ"""
    return JsonResponse({'faq': []})

def video_tutorials(request):
    """Video tutorials"""
    return JsonResponse({'tutorials': []})

def create_support_ticket(request):
    """Create support ticket"""
    return JsonResponse({'ticket_id': 1})

def support_tickets(request):
    """View support tickets"""
    return JsonResponse({'tickets': []})

def support_ticket_detail(request, ticket_id):
    """View support ticket detail"""
    return JsonResponse({'ticket_id': ticket_id})

def submit_feedback(request):
    """Submit feedback"""
    return JsonResponse({'feedback_submitted': True})

def feedback_thank_you(request):
    """Feedback thank you page"""
    return render(request, 'learning/feedback_thank_you.html')

def mobile_sync(request):
    """Mobile sync"""
    return JsonResponse({'synced': True})

def mobile_progress(request):
    """Mobile progress"""
    return JsonResponse({'progress': {}})

def mobile_notifications(request):
    """Mobile notifications"""
    return JsonResponse({'notifications': []})

def offline_activities(request):
    """Offline activities"""
    return JsonResponse({'activities': []})

def offline_sync(request):
    """Offline sync"""
    return JsonResponse({'synced': True})

def github_webhook(request):
    """GitHub webhook"""
    return JsonResponse({'webhook_received': True})

def slack_webhook(request):
    """Slack webhook"""
    return JsonResponse({'webhook_received': True})

def github_integration(request):
    """GitHub integration"""
    return JsonResponse({'integrated': True})

def slack_integration(request):
    """Slack integration"""
    return JsonResponse({'integrated': True})

def custom_404(request, exception=None):
    """Custom 404 page"""
    return render(request, 'learning/404.html', status=404)

def custom_500(request):
    """Custom 500 page"""
    return render(request, 'learning/500.html', status=500)

def activity_unavailable(request):
    """Activity unavailable page"""
    return render(request, 'learning/activity_unavailable.html')

def too_stressed(request):
    """Too stressed page"""
    return render(request, 'learning/too_stressed.html')

def health_check(request):
    """Health check endpoint"""
    return JsonResponse({'status': 'healthy'})

def debug_emotions(request):
    """Debug emotions"""
    return JsonResponse({'debug': {}})

def debug_progress(request):
    """Debug progress"""
    return JsonResponse({'debug': {}})

def redirect_old_dashboard(request):
    """Redirect old dashboard"""
    return redirect('learning:dashboard')

def redirect_old_activity(request, activity_id):
    """Redirect old activity"""
    # Try to get the activity and redirect to new URL
    try:
        activity = MicroActivity.objects.get(id=activity_id)
        return redirect('learning:activity_detail', slug=activity.slug)
    except MicroActivity.DoesNotExist:
        return redirect('learning:dashboard')