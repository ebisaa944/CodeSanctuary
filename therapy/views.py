from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, generics, status
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import EmotionalCheckIn, CopingStrategy
from .serializers import (
    EmotionalCheckInSerializer, 
    CopingStrategySerializer,
    EmotionalPatternSerializer,
    QuickCheckInSerializer,
    EmotionalHistorySerializer
)
from .permissions import (
    EmotionalCheckInPermission,
    CopingStrategyPermission,
    TherapeuticInsightPermission
)
from .forms import (
    EmotionalCheckInForm,
    QuickCheckInForm,
    CopingStrategyForm,
    StrategyRecommendationForm
)
from .pagination import TherapeuticPagination, CopingStrategyPagination, EmotionalHistoryPagination
import json
from datetime import timedelta
from collections import Counter
import logging

logger = logging.getLogger(__name__)


# ==================== HTML Views ====================

# Replace your entire therapy_dashboard function with this:

@login_required
def therapy_dashboard(request):
    """Main therapy dashboard - SQLite compatible version"""
    try:
        # Get recent checkins
        recent_checkins = EmotionalCheckIn.objects.filter(
            user=request.user
        ).order_by('-created_at')[:5]
        
        # Get recommended strategies
        latest_checkin = recent_checkins.first()
        recommended_strategies = []
        
        if latest_checkin:
            # Get all strategies and filter in Python (SQLite compatible)
            all_strategies = CopingStrategy.objects.filter(is_active=True)
            
            # Filter by difficulty first (database query)
            difficulty_limit = 3 if latest_checkin.intensity > 6 else 5
            strategies_by_difficulty = all_strategies.filter(
                difficulty_level__lte=difficulty_limit
            )
            
            # Then filter by target_emotions in Python
            filtered_strategies = []
            for strategy in strategies_by_difficulty:
                # Handle both string and list formats for target_emotions
                target_emotions = strategy.target_emotions
                if isinstance(target_emotions, str):
                    # If it's stored as a string, try to parse it
                    try:
                        import json
                        target_emotions = json.loads(target_emotions)
                    except:
                        # If it can't be parsed as JSON, skip this strategy
                        continue
                
                # Check if the current emotion is in target_emotions
                if (isinstance(target_emotions, list) and 
                    latest_checkin.primary_emotion in target_emotions):
                    filtered_strategies.append(strategy)
                
                # Limit to 3 strategies
                if len(filtered_strategies) >= 3:
                    break
            
            recommended_strategies = filtered_strategies
            
            # If no strategies match the emotion, show some general ones
            if not recommended_strategies:
                recommended_strategies = strategies_by_difficulty[:3]
        else:
            # If no checkins, show some general strategies
            recommended_strategies = CopingStrategy.objects.filter(
                is_active=True,
                difficulty_level__lte=3
            )[:3]
        
        # Calculate stats
        total_checkins = EmotionalCheckIn.objects.filter(user=request.user).count()
        today_checkins = EmotionalCheckIn.objects.filter(
            user=request.user,
            created_at__date=timezone.now().date()
        ).count()
        
        # Get emotional pattern
        emotional_pattern = {}
        if latest_checkin:
            emotional_pattern = latest_checkin.get_emotional_pattern()
        
        context = {
            'recent_checkins': recent_checkins,
            'recommended_strategies': recommended_strategies,
            'total_checkins': total_checkins,
            'today_checkins': today_checkins,
            'emotional_pattern': emotional_pattern,
            'emotion_options': EmotionalCheckIn.PrimaryEmotion.choices,
            'current_emotion': latest_checkin.primary_emotion if latest_checkin else None,
            'show_quick_checkin': True,
        }
        
        return render(request, 'therapy/dashboard.html', context)
        
    except Exception as e:
        # Fallback for any errors
        print(f"Error in dashboard: {e}")
        import traceback
        traceback.print_exc()
        
        # Return a simple working version
        return render(request, 'therapy/dashboard.html', {
            'recent_checkins': EmotionalCheckIn.objects.filter(user=request.user)[:5],
            'recommended_strategies': CopingStrategy.objects.filter(is_active=True)[:3],
            'total_checkins': EmotionalCheckIn.objects.filter(user=request.user).count(),
            'today_checkins': 0,
            'show_quick_checkin': True,
        })


@login_required
def checkin_list(request):
    """List emotional checkins with filtering"""
    checkins = EmotionalCheckIn.objects.filter(user=request.user).order_by('-created_at')
    
    # Apply simple filters from GET parameters
    emotion_filter = request.GET.get('emotion', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    intensity_min = request.GET.get('intensity_min', '')
    intensity_max = request.GET.get('intensity_max', '')
    
    if emotion_filter:
        checkins = checkins.filter(primary_emotion=emotion_filter)
    
    if date_from:
        checkins = checkins.filter(created_at__date__gte=date_from)
    
    if date_to:
        checkins = checkins.filter(created_at__date__lte=date_to)
    
    if intensity_min:
        checkins = checkins.filter(intensity__gte=intensity_min)
    
    if intensity_max:
        checkins = checkins.filter(intensity__lte=intensity_max)
    
    # Check for physical symptoms filter
    has_symptoms = request.GET.get('has_symptoms', '')
    if has_symptoms == 'yes':
        checkins = checkins.exclude(physical_symptoms=[])
    elif has_symptoms == 'no':
        checkins = checkins.filter(physical_symptoms=[])
    
    # Pagination
    paginator = Paginator(checkins, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'emotion_options': EmotionalCheckIn.PrimaryEmotion.choices,
        'total_checkins': checkins.count(),
        'current_filters': {
            'emotion': emotion_filter,
            'date_from': date_from,
            'date_to': date_to,
            'intensity_min': intensity_min,
            'intensity_max': intensity_max,
            'has_symptoms': has_symptoms,
        }
    }
    
    return render(request, 'therapy/checkin_list.html', context)


@login_required
def checkin_detail(request, pk):
    """Detailed view of a single checkin"""
    checkin = get_object_or_404(EmotionalCheckIn, pk=pk, user=request.user)
    
    # Get similar checkins
    similar_checkins = EmotionalCheckIn.objects.filter(
        user=request.user,
        primary_emotion=checkin.primary_emotion
    ).exclude(pk=pk).order_by('-created_at')[:3]
    
    # Get coping strategies
    coping_strategies = CopingStrategy.objects.filter(
        target_emotions__contains=[checkin.primary_emotion]
    )[:5]
    
    context = {
        'checkin': checkin,
        'similar_checkins': similar_checkins,
        'coping_strategies': coping_strategies,
        'suggested_strategies': checkin.suggest_coping_strategies(),
        'emotional_pattern': checkin.get_emotional_pattern(),
    }
    
    return render(request, 'therapy/checkin_detail.html', context)


@login_required
def checkin_create(request):
    """Create a new emotional checkin"""
    if request.method == 'POST':
        form = EmotionalCheckInForm(request.POST)
        if form.is_valid():
            checkin = form.save(commit=False)
            checkin.user = request.user
            
            # Process JSON fields - WITH NULL CHECKS
            if 'secondary_emotions' in form.cleaned_data and form.cleaned_data['secondary_emotions']:
                checkin.secondary_emotions = form.cleaned_data['secondary_emotions']
            
            if 'physical_symptoms' in form.cleaned_data and form.cleaned_data['physical_symptoms']:
                checkin.physical_symptoms = form.cleaned_data['physical_symptoms']
            
            # FIX: Check if context_tags exists and is not None
            if 'context_tags' in form.cleaned_data and form.cleaned_data['context_tags']:
                tags = form.cleaned_data['context_tags'].split(',')
                checkin.context_tags = [tag.strip() for tag in tags if tag.strip()]
            else:
                checkin.context_tags = []  # Set to empty list if None
            
            # Also fix other optional fields
            if 'coping_strategies_used' in form.cleaned_data and form.cleaned_data['coping_strategies_used']:
                # Handle coping_strategies_used if it's a string
                if isinstance(form.cleaned_data['coping_strategies_used'], str):
                    strategies = form.cleaned_data['coping_strategies_used'].split(',')
                    checkin.coping_strategies_used = [s.strip() for s in strategies if s.strip()]
                else:
                    checkin.coping_strategies_used = form.cleaned_data['coping_strategies_used']
            
            checkin.save()
            
            messages.success(request, 'Check-in recorded successfully!')
            return redirect('therapy:checkin_detail', pk=checkin.pk)
    else:
        form = EmotionalCheckInForm()
    
    context = {
        'form': form,
        'emotion_options': EmotionalCheckIn.PrimaryEmotion.choices,
        'physical_symptoms': EmotionalCheckIn.PHYSICAL_SYMPTOMS,
    }
    
    return render(request, 'therapy/checkin_form.html', context)


@login_required
def quick_checkin(request):
    """Quick emotional checkin"""
    if request.method == 'POST':
        form = QuickCheckInForm(request.POST)
        if form.is_valid():
            checkin = form.save(request.user)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Quick check-in recorded!',
                    'checkin_id': checkin.id,
                    'emotion': checkin.get_primary_emotion_display(),
                })
            
            messages.success(request, 'Quick check-in recorded!')
            return redirect('therapy:dashboard')
    else:
        form = QuickCheckInForm()
    
    # If AJAX request but GET, return form HTML
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'therapy/partials/quick_checkin_form.html', {'form': form})
    
    return render(request, 'therapy/quick_checkin.html', {'form': form})


@login_required
def coping_strategies_list(request):
    """List coping strategies - SQLite compatible version"""
    # Start with all active strategies
    strategies = CopingStrategy.objects.filter(is_active=True)
    
    # Apply simple filters that work with SQLite
    strategy_type = request.GET.get('type', '')
    emotion_target = request.GET.get('emotion', '')
    max_duration = request.GET.get('duration', '')
    difficulty = request.GET.get('difficulty', '')
    coding_only = request.GET.get('coding', '')
    
    if strategy_type:
        strategies = strategies.filter(strategy_type=strategy_type)
    
    # IMPORTANT: For SQLite, we can't use target_emotions__contains
    # We'll filter in Python instead
    
    if max_duration:
        strategies = strategies.filter(estimated_minutes__lte=int(max_duration))
    
    if difficulty:
        strategies = strategies.filter(difficulty_level=int(difficulty))
    
    if coding_only == 'yes':
        strategies = strategies.filter(coding_integration=True)
    
    # Convert to list for Python filtering
    strategies_list = list(strategies)
    
    # Filter by emotion in Python (SQLite compatible)
    if emotion_target:
        filtered_strategies = []
        for strategy in strategies_list:
            target_emotions = strategy.target_emotions
            
            # Handle different formats
            if isinstance(target_emotions, str):
                try:
                    import json
                    target_emotions = json.loads(target_emotions)
                except:
                    # If it can't be parsed, check if it's a direct match
                    if target_emotions == emotion_target:
                        filtered_strategies.append(strategy)
                    continue
            
            # Check if emotion is in the list
            if isinstance(target_emotions, list) and emotion_target in target_emotions:
                filtered_strategies.append(strategy)
        
        strategies_list = filtered_strategies
    
    # Apply gentle mode restrictions
    if getattr(request.user, 'gentle_mode', False):
        strategies_list = [s for s in strategies_list if s.difficulty_level <= 3]
    
    # Pagination
    paginator = Paginator(strategies_list, 12)
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.get_page(page_number)
    except:
        # If there's an error (like empty page), show first page
        page_obj = paginator.get_page(1)
    
    context = {
        'page_obj': page_obj,
        'strategy_types': CopingStrategy.StrategyType.choices,
        'emotion_options': EmotionalCheckIn.PrimaryEmotion.choices,
        'duration_options': [
            (5, '5 mins or less'),
            (10, '10 mins or less'),
            (20, '20 mins or less'),
            (60, 'Any duration'),
        ],
        'difficulty_levels': [(i, f"Level {i}") for i in range(1, 6)],
        'current_filters': {
            'type': strategy_type,
            'emotion': emotion_target,
            'duration': max_duration,
            'difficulty': difficulty,
            'coding': coding_only,
        }
    }
    
    return render(request, 'therapy/strategies_list.html', context)


@login_required
def coping_strategy_detail(request, pk):
    """Detail view of a coping strategy"""
    strategy = get_object_or_404(CopingStrategy, pk=pk, is_active=True)
    
    # Get similar strategies
    similar_strategies = CopingStrategy.objects.filter(
        strategy_type=strategy.strategy_type,
        is_active=True
    ).exclude(pk=pk)[:3]
    
    # Check if recommended for user
    is_recommended = strategy.get_recommended_for_user(request.user)
    
    context = {
        'strategy': strategy,
        'similar_strategies': similar_strategies,
        'is_recommended': is_recommended,
        'instructions': strategy.instructions if isinstance(strategy.instructions, list) else [],
    }
    
    return render(request, 'therapy/strategy_detail.html', context)


@login_required
def get_recommendations(request):
    """Get coping strategy recommendations based on current state - SQLite compatible"""
    if request.method == 'POST':
        form = StrategyRecommendationForm(request.POST)
        if form.is_valid():
            try:
                # Get form data
                emotion = form.cleaned_data['emotion']
                intensity = form.cleaned_data['intensity']
                time_available = form.cleaned_data['time_available']
                prefer_coding = form.cleaned_data['prefer_coding']
                
                # Query strategies - FIXED: No more target_emotions__contains
                strategies = CopingStrategy.objects.filter(
                    is_active=True,
                    estimated_minutes__lte=time_available
                )
                
                if prefer_coding:
                    strategies = strategies.filter(coding_integration=True)
                
                # SQLite compatible filtering for target_emotions
                filtered_strategies = []
                for strategy in strategies:
                    target_emotions = strategy.target_emotions
                    
                    # Handle different formats for target_emotions
                    if isinstance(target_emotions, str):
                        try:
                            import json
                            target_emotions = json.loads(target_emotions)
                        except:
                            # If it can't be parsed, skip this strategy
                            continue
                    
                    # Check if emotion is in target_emotions list
                    if isinstance(target_emotions, list) and emotion in target_emotions:
                        filtered_strategies.append(strategy)
                
                strategies = filtered_strategies
                
                # Filter by intensity
                if intensity >= 7:
                    strategies = [s for s in strategies if s.difficulty_level <= 2]
                elif intensity >= 5:
                    strategies = [s for s in strategies if s.difficulty_level <= 3]
                
                # Sort by difficulty and limit to 5
                strategies = sorted(strategies, key=lambda x: x.difficulty_level)[:5]
                
                # If no strategies found with emotion filter, fall back to some general ones
                if not strategies:
                    # Get some general strategies
                    strategies = CopingStrategy.objects.filter(
                        is_active=True,
                        estimated_minutes__lte=time_available
                    )
                    
                    if prefer_coding:
                        strategies = strategies.filter(coding_integration=True)
                    
                    # Apply intensity filters
                    if intensity >= 7:
                        strategies = [s for s in strategies if s.difficulty_level <= 2]
                    elif intensity >= 5:
                        strategies = [s for s in strategies if s.difficulty_level <= 3]
                    
                    strategies = list(strategies)[:5]
                
                # Check for AJAX request
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    try:
                        serialized = CopingStrategySerializer(
                            strategies, 
                            many=True,
                            context={'request': request}
                        )
                        return JsonResponse({
                            'success': True,
                            'recommendations': serialized.data
                        })
                    except Exception as e:
                        return JsonResponse({
                            'success': False,
                            'error': 'Failed to serialize data'
                        })
                
                # Regular HTML response
                context = {
                    'recommendations': strategies,
                    'form_data': form.cleaned_data,
                    'emotion_options': EmotionalCheckIn.PrimaryEmotion.choices,
                }
                
                return render(request, 'therapy/recommendations.html', context)
                
            except Exception as e:
                # Log the error
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Error in get_recommendations: {e}', exc_info=True)
                
                # Show error to user
                messages.error(request, f'Error getting recommendations: {str(e)}')
                return redirect('therapy:get_recommendations')
    else:
        form = StrategyRecommendationForm()
    
    context = {
        'form': form,
        'emotion_options': EmotionalCheckIn.PrimaryEmotion.choices,
    }
    
    return render(request, 'therapy/get_recommendations.html', context)


@login_required
def emotional_insights(request):
    """View emotional patterns and insights"""
    # Get checkins from last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    checkins = EmotionalCheckIn.objects.filter(
        user=request.user,
        created_at__gte=thirty_days_ago
    ).order_by('created_at')
    
    # Calculate insights
    if checkins.exists():
        # Most common emotions
        emotions = [c.primary_emotion for c in checkins]
        common_emotions = Counter(emotions).most_common(3)
        
        # Average intensity
        avg_intensity = checkins.aggregate(Avg('intensity'))['intensity__avg']
        
        # Time patterns
        morning = checkins.filter(created_at__hour__range=(6, 12)).count()
        afternoon = checkins.filter(created_at__hour__range=(12, 18)).count()
        evening = checkins.filter(created_at__hour__range=(18, 22)).count()
        night = checkins.filter(
            Q(created_at__hour__gte=22) | Q(created_at__hour__lt=6)
        ).count()
        
        # Common triggers
        all_triggers = []
        for checkin in checkins:
            if checkin.trigger_description:
                words = checkin.trigger_description.lower().split()
                all_triggers.extend([w for w in words if len(w) > 4])
        
        common_triggers = Counter(all_triggers).most_common(5)
        
        # Days of week patterns
        weekday_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        for checkin in checkins:
            weekday_counts[checkin.created_at.weekday()] += 1
        
        context = {
            'checkins': checkins,
            'total_checkins': checkins.count(),
            'common_emotions': common_emotions,
            'avg_intensity': round(avg_intensity, 1) if avg_intensity else 0,
            'time_patterns': {
                'morning': morning,
                'afternoon': afternoon,
                'evening': evening,
                'night': night,
            },
            'common_triggers': common_triggers,
            'weekday_patterns': weekday_counts,
            'start_date': thirty_days_ago.date(),
            'end_date': timezone.now().date(),
        }
    else:
        context = {
            'no_data': True,
            'message': 'No check-in data yet. Start by recording how you feel!'
        }
    
    return render(request, 'therapy/insights.html', context)


@login_required
def export_data(request, format='json'):
    """Export emotional checkin data"""
    checkins = EmotionalCheckIn.objects.filter(user=request.user)
    
    if format == 'json':
        data = []
        for checkin in checkins:
            data.append({
                'date': checkin.created_at.isoformat(),
                'emotion': checkin.primary_emotion,
                'emotion_display': checkin.get_primary_emotion_display(),
                'intensity': checkin.intensity,
                'notes': checkin.notes,
                'trigger': checkin.trigger_description,
            })
        
        response = JsonResponse(data, safe=False)
        response['Content-Disposition'] = f'attachment; filename="emotional_checkins_{timezone.now().date()}.json"'
        return response
    
    elif format == 'csv':
        import csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="emotional_checkins_{timezone.now().date()}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Emotion', 'Intensity', 'Notes', 'Trigger'])
        
        for checkin in checkins:
            writer.writerow([
                checkin.created_at.strftime('%Y-%m-%d %H:%M'),
                checkin.get_primary_emotion_display(),
                checkin.intensity,
                checkin.notes,
                checkin.trigger_description,
            ])
        
        return response
    
    return redirect('therapy:dashboard')


# ==================== API Views ====================

class EmotionalCheckInViewSet(viewsets.ModelViewSet):
    """API endpoint for emotional checkins"""
    serializer_class = EmotionalCheckInSerializer
    permission_classes = [IsAuthenticated, EmotionalCheckInPermission]
    pagination_class = TherapeuticPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['notes', 'trigger_description', 'key_insight']
    ordering_fields = ['created_at', 'intensity', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = EmotionalCheckIn.objects.all()
        
        # Filter by user if not staff
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Apply filters from query parameters
        emotion = self.request.query_params.get('emotion', None)
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        intensity_min = self.request.query_params.get('intensity_min', None)
        intensity_max = self.request.query_params.get('intensity_max', None)
        
        if emotion:
            queryset = queryset.filter(primary_emotion=emotion)
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        if intensity_min:
            queryset = queryset.filter(intensity__gte=intensity_min)
        
        if intensity_max:
            queryset = queryset.filter(intensity__lte=intensity_max)
        
        # Apply gentle mode restrictions
        if getattr(self.request.user, 'gentle_mode', False):
            queryset = queryset.filter(intensity__lte=8)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's checkins"""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(created_at__date=today)
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def patterns(self, request):
        """Get emotional patterns"""
        queryset = self.get_queryset()
        
        # Calculate patterns
        if queryset.exists():
            latest = queryset.first()
            pattern_data = latest.get_emotional_pattern()
            
            # Add timeframe
            pattern_data.update({
                'timeframe': 'Last 7 days',
                'total_checkins': queryset.count(),
                'dominant_weekday': self._get_dominant_weekday(queryset),
            })
            
            serializer = EmotionalPatternSerializer(data=pattern_data)
            if serializer.is_valid():
                return Response(serializer.data)
        
        return Response({'message': 'Not enough data for pattern analysis'})
    
    @action(detail=True, methods=['get'])
    def suggestions(self, request, pk=None):
        """Get suggestions for a specific checkin"""
        checkin = self.get_object()
        suggestions = checkin.suggest_coping_strategies()
        return Response(suggestions)
    
    def _get_dominant_weekday(self, queryset):
        """Find which weekday has most checkins"""
        weekdays = [c.created_at.weekday() for c in queryset]
        if weekdays:
            weekday_counts = Counter(weekdays)
            dominant = weekday_counts.most_common(1)[0][0]
            days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            return days[dominant]
        return None


class CopingStrategyViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for coping strategies"""
    serializer_class = CopingStrategySerializer
    permission_classes = [IsAuthenticated, CopingStrategyPermission]
    pagination_class = CopingStrategyPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['name', 'description', 'tips_for_success']
    ordering_fields = ['difficulty_level', 'estimated_minutes', 'created_at']
    ordering = ['difficulty_level']
    
    def get_queryset(self):
        queryset = CopingStrategy.objects.filter(is_active=True)
        
        # Apply filters from query parameters
        strategy_type = self.request.query_params.get('type', None)
        emotion = self.request.query_params.get('emotion', None)
        max_duration = self.request.query_params.get('duration', None)
        difficulty = self.request.query_params.get('difficulty', None)
        coding = self.request.query_params.get('coding', None)
        
        if strategy_type:
            queryset = queryset.filter(strategy_type=strategy_type)
        
        if emotion:
            queryset = queryset.filter(target_emotions__contains=[emotion])
        
        if max_duration:
            queryset = queryset.filter(estimated_minutes__lte=int(max_duration))
        
        if difficulty:
            queryset = queryset.filter(difficulty_level=int(difficulty))
        
        if coding == 'yes':
            queryset = queryset.filter(coding_integration=True)
        
        # Apply gentle mode filter
        if self.request.user.is_authenticated and getattr(self.request.user, 'gentle_mode', False):
            queryset = queryset.filter(difficulty_level__lte=3)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def recommended(self, request):
        """Get recommended strategies for current user"""
        emotion = request.query_params.get('emotion', None)
        max_duration = request.query_params.get('duration', None)
        
        queryset = self.get_queryset()
        
        if emotion:
            queryset = queryset.filter(target_emotions__contains=[emotion])
        
        if max_duration:
            queryset = queryset.filter(estimated_minutes__lte=int(max_duration))
        
        # Filter by user suitability
        recommended = []
        for strategy in queryset:
            if strategy.get_recommended_for_user(request.user):
                recommended.append(strategy)
        
        page = self.paginate_queryset(recommended)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(recommended, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_tried(self, request, pk=None):
        """Mark a strategy as tried by user"""
        strategy = self.get_object()
        
        # In a real app, you'd have a UserStrategy model
        # For now, we'll just log it
        logger.info(f"User {request.user.username} tried strategy {strategy.name}")
        
        return Response({
            'success': True,
            'message': f'Marked "{strategy.name}" as tried',
            'suggestion': 'Consider rating how effective it was in your next check-in'
        })


class QuickCheckInAPI(APIView):
    """API for quick emotional checkins"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = QuickCheckInSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            checkin = serializer.save()
            
            # Get quick recommendations
            strategies = CopingStrategy.objects.filter(
                target_emotions__contains=[checkin.primary_emotion],
                estimated_minutes__lte=5
            )[:2]
            
            return Response({
                'success': True,
                'checkin': EmotionalCheckInSerializer(checkin).data,
                'quick_suggestions': CopingStrategySerializer(strategies, many=True).data,
                'message': f"Recorded feeling {checkin.get_primary_emotion_display()}"
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmotionalHistoryAPI(generics.ListAPIView):
    """API for emotional history with trends"""
    serializer_class = EmotionalHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = EmotionalHistoryPagination
    
    def get_queryset(self):
        return EmotionalCheckIn.objects.filter(
            user=self.request.user
        ).order_by('-created_at')


class TherapeuticInsightsAPI(APIView):
    """API for therapeutic insights"""
    permission_classes = [IsAuthenticated, TherapeuticInsightPermission]
    require_gentle_mode = False  # Set to True for sensitive insights
    
    def get(self, request):
        # Get data for insights
        checkins = EmotionalCheckIn.objects.filter(user=request.user)
        
        if not checkins.exists():
            return Response({
                'message': 'Start by recording your emotions to get insights'
            })
        
        # Calculate insights
        insights = self._calculate_insights(checkins)
        
        return Response(insights)
    
    def _calculate_insights(self, checkins):
        """Calculate therapeutic insights"""
        # Most recent checkin
        latest = checkins.latest('created_at')
        
        # Emotional trends
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent = checkins.filter(created_at__gte=seven_days_ago)
        
        insights = {
            'current_state': {
                'emotion': latest.primary_emotion,
                'intensity': latest.intensity,
                'time_since': latest.get_time_since(),
            },
            'patterns': latest.get_emotional_pattern(),
            'recent_trend': self._get_trend(recent),
            'coping_effectiveness': self._get_coping_effectiveness(checkins),
            'triggers_analysis': self._analyze_triggers(checkins),
            'recommendations': self._generate_recommendations(latest, checkins),
        }
        
        return insights
    
    def _get_trend(self, checkins):
        """Get emotional trend over time"""
        if len(checkins) < 2:
            return "Not enough data for trend analysis"
        
        # Simple trend analysis
        emotions = [c.primary_emotion for c in checkins]
        
        positive_emotions = ['calm', 'focused', 'hopeful', 'excited']
        negative_emotions = ['anxious', 'overwhelmed', 'doubtful', 'frustrated']
        
        positive_count = sum(1 for e in emotions if e in positive_emotions)
        negative_count = sum(1 for e in emotions if e in negative_emotions)
        
        if positive_count > negative_count * 1.5:
            return "Trending positive"
        elif negative_count > positive_count * 1.5:
            return "Trending challenging"
        else:
            return "Mixed patterns"
    
    def _get_coping_effectiveness(self, checkins):
        """Analyze coping strategy effectiveness"""
        with_coping = checkins.exclude(coping_strategies_used=[])
        
        if with_coping.exists():
            avg_effectiveness = with_coping.aggregate(Avg('coping_effectiveness'))['coping_effectiveness__avg']
            return {
                'average_score': round(avg_effectiveness, 1) if avg_effectiveness else None,
                'total_with_coping': with_coping.count(),
                'percentage': round((with_coping.count() / checkins.count()) * 100, 1) if checkins.count() > 0 else 0,
            }
        
        return {'message': 'No coping strategies recorded yet'}
    
    def _analyze_triggers(self, checkins):
        """Analyze common triggers"""
        triggers = []
        for checkin in checkins:
            if checkin.trigger_description:
                triggers.append(checkin.trigger_description.lower())
        
        if triggers:
            # Simple word frequency analysis
            words = []
            for trigger in triggers:
                words.extend([w for w in trigger.split() if len(w) > 3])
            
            common_words = Counter(words).most_common(5)
            
            return {
                'total_triggers': len(triggers),
                'common_themes': dict(common_words),
                'suggestion': 'Notice patterns in what triggers different emotions'
            }
        
        return {'message': 'No triggers recorded yet'}
    
    def _generate_recommendations(self, latest_checkin, all_checkins):
        """Generate therapeutic recommendations"""
        recommendations = []
        
        # Based on current emotion
        if latest_checkin.intensity >= 8:
            recommendations.append({
                'type': 'immediate',
                'message': 'High intensity detected. Consider a grounding exercise.',
                'action': 'Try a 2-minute breathing exercise'
            })
        
        # Based on patterns
        pattern = latest_checkin.get_emotional_pattern()
        if pattern.get('volatility', 0) > 3:
            recommendations.append({
                'type': 'pattern',
                'message': 'Emotional volatility detected. Consistency might help.',
                'action': 'Try the same coping strategy for 3 days in a row'
            })
        
        # Based on time of day
        hour = latest_checkin.created_at.hour
        if 22 <= hour or hour < 6:
            recommendations.append({
                'type': 'timing',
                'message': 'Late night check-in. Sleep affects emotions.',
                'action': 'Consider a pre-sleep wind-down routine'
            })
        
        if not recommendations:
            recommendations.append({
                'type': 'general',
                'message': 'Continue regular check-ins to build self-awareness',
                'action': 'Schedule a check-in for tomorrow at the same time'
            })
        
        return recommendations


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def emotional_summary(request):
    """Get emotional summary for dashboard"""
    user = request.user
    
    # Today's checkins
    today = timezone.now().date()
    today_checkins = EmotionalCheckIn.objects.filter(
        user=user,
        created_at__date=today
    )
    
    # Week overview
    week_ago = timezone.now() - timedelta(days=7)
    week_checkins = EmotionalCheckIn.objects.filter(
        user=user,
        created_at__gte=week_ago
    )
    
    # Get dominant emotion
    def get_dominant_emotion(checkins):
        if checkins.exists():
            emotions = [c.primary_emotion for c in checkins]
            most_common = Counter(emotions).most_common(1)
            if most_common:
                return most_common[0][0]
        return None
    
    # Get week trend
    def get_week_trend(checkins):
        if len(checkins) < 2:
            return "Not enough data"
        
        # Simple trend: compare first half to second half of week
        sorted_checkins = sorted(checkins, key=lambda x: x.created_at)
        mid = len(sorted_checkins) // 2
        
        first_half = sorted_checkins[:mid]
        second_half = sorted_checkins[mid:]
        
        first_avg = sum(c.intensity for c in first_half) / len(first_half) if first_half else 0
        second_avg = sum(c.intensity for c in second_half) / len(second_half) if second_half else 0
        
        if second_avg < first_avg * 0.8:
            return "Decreasing intensity"
        elif second_avg > first_avg * 1.2:
            return "Increasing intensity"
        else:
            return "Stable"
    
    # Get daily recommendations
    def get_daily_recommendations(user):
        """Get daily therapeutic recommendations"""
        recommendations = [
            "Take 3 deep breaths before your next task",
            "Notice one thing you're grateful for today",
            "Set a gentle intention for your coding session",
        ]
        
        # Check if user has done checkin today
        today_checkin = EmotionalCheckIn.objects.filter(
            user=user,
            created_at__date=timezone.now().date()
        ).first()
        
        if today_checkin:
            if today_checkin.intensity >= 7:
                recommendations.insert(0, "Consider a 5-minute mindfulness break")
            elif today_checkin.primary_emotion in ['calm', 'focused']:
                recommendations.insert(0, "Use this calm energy for focused work")
        
        return recommendations[:3]
    
    summary = {
        'today': {
            'count': today_checkins.count(),
            'average_intensity': today_checkins.aggregate(Avg('intensity'))['intensity__avg'],
            'dominant_emotion': get_dominant_emotion(today_checkins),
        },
        'week': {
            'count': week_checkins.count(),
            'average_intensity': week_checkins.aggregate(Avg('intensity'))['intensity__avg'],
            'trend': get_week_trend(week_checkins),
        },
        'recommendations': get_daily_recommendations(user),
    }
    
    return Response(summary)


# ==================== Utility Views ====================

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def log_activity(request):
    """Log therapeutic activity (for AJAX calls)"""
    try:
        data = json.loads(request.body)
        activity_type = data.get('type', '')
        details = data.get('details', {})
        
        logger.info(f"Therapeutic activity: {activity_type} - {details}")
        
        return JsonResponse({
            'success': True,
            'message': 'Activity logged'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)


@api_view(['GET'])
def therapy_resources(request):
    """Get therapy resources and information"""
    resources = {
        'breathing_exercises': [
            {
                'name': 'Box Breathing',
                'steps': ['Inhale for 4', 'Hold for 4', 'Exhale for 4', 'Hold for 4'],
                'duration': '2 minutes',
                'benefit': 'Calms nervous system'
            },
            {
                'name': '4-7-8 Breathing',
                'steps': ['Inhale for 4', 'Hold for 7', 'Exhale for 8'],
                'duration': '1 minute',
                'benefit': 'Reduces anxiety'
            }
        ],
        'grounding_techniques': [
            '5-4-3-2-1: Notice 5 things you see, 4 things you feel, 3 things you hear, 2 things you smell, 1 thing you taste',
            'Body scan: Slowly notice sensations from head to toe',
            'Mindful typing: Type slowly, noticing each key press'
        ],
        'emergency_contacts': [
            'Crisis Text Line: Text HOME to 741741',
            'National Suicide Prevention Lifeline: 988',
            'Trevor Project (LGBTQ+): 1-866-488-7386'
        ],
        'coding_therapy': [
            'Write a function that describes how you feel',
            'Create a program that generates positive affirmations',
            'Build a simple mood tracker in your favorite language'
        ]
    }
    
    return Response(resources)


# ==================== Admin Views ====================

@login_required
def coping_strategy_create(request):
    """Admin view for creating coping strategies"""
    if not request.user.is_staff:
        messages.error(request, 'Only staff members can create coping strategies.')
        return redirect('therapy:strategies_list')
    
    if request.method == 'POST':
        form = CopingStrategyForm(request.POST)
        if form.is_valid():
            strategy = form.save()
            messages.success(request, f'Coping strategy "{strategy.name}" created successfully!')
            return redirect('therapy:strategy_detail', pk=strategy.pk)
    else:
        form = CopingStrategyForm()
    
    return render(request, 'therapy/admin/strategy_form.html', {'form': form})


@login_required
def coping_strategy_update(request, pk):
    """Admin view for updating coping strategies"""
    if not request.user.is_staff:
        messages.error(request, 'Only staff members can edit coping strategies.')
        return redirect('therapy:strategies_list')
    
    strategy = get_object_or_404(CopingStrategy, pk=pk)
    
    if request.method == 'POST':
        form = CopingStrategyForm(request.POST, instance=strategy)
        if form.is_valid():
            strategy = form.save()
            messages.success(request, f'Coping strategy "{strategy.name}" updated successfully!')
            return redirect('therapy:strategy_detail', pk=strategy.pk)
    else:
        form = CopingStrategyForm(instance=strategy)
    
    return render(request, 'therapy/admin/strategy_form.html', {'form': form, 'strategy': strategy})