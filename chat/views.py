# chat/views.py
from rest_framework import viewsets, generics, status, permissions, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, F, Subquery, OuterRef, Prefetch
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
import json
import uuid
from datetime import timedelta

from .models import (
    ChatRoom, RoomMembership, ChatMessage, MessageReaction,
    ChatSessionAnalytics, ChatNotification, TherapeuticChatSettings
)
from .serializers import (
    ChatRoomSerializer, ChatRoomCreateSerializer,
    ChatMessageSerializer, ChatMessageCreateSerializer,
    RoomMembershipSerializer, MessageReactionSerializer,
    ChatSessionAnalyticsSerializer, ChatNotificationSerializer,
    TherapeuticChatSettingsSerializer, TherapeuticUserLiteSerializer,
    ChatBulkActionSerializer, TherapeuticInsightSerializer,
    ChatStatisticsSerializer, ChatExportSerializer
)
from .permissions import (
    IsTherapeuticUser, RoomAccessPermission, MessagePermission,
    RoomMembershipPermission, ModerationPermission, ReactionPermission,
    TherapeuticSettingsPermission, VulnerableSharePermission,
    StressLevelPermission, IsTherapist, IsModerator,
    TherapeuticAccessPermission, GentleModeCompositePermission,
    AnonymousPostingPermission, EmotionalCheckInPermission,
    SafetyPlanPermission, ExportPermission, TherapeuticInsightPermission,
    RoomTemplatePermission, BulkActionPermission
)
from .pagination import (
    TherapeuticPagination, StressAwarePagination,
    ThreadAwarePagination, EmotionalTonePagination,
    TimeBasedTherapeuticPagination, GentleProgressivePagination,
    BreakAwarePagination, CompositeTherapeuticPagination,
    get_therapeutic_pagination_class, configure_therapeutic_pagination
)
from .filters import (
    TherapeuticChatRoomFilter, TherapeuticChatMessageFilter,
    TherapeuticRoomMembershipFilter, TherapeuticMessageReactionFilter,
    TherapeuticSearchFilter, TherapeuticFilterBackend
)

User = get_user_model()


# ============================================================================
# Therapeutic Chat Room Views
# ============================================================================

class TherapeuticChatRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for therapeutic chat rooms with comprehensive therapeutic features
    """
    queryset = ChatRoom.objects.all()
    serializer_class = ChatRoomSerializer
    permission_classes = [IsTherapeuticUser, TherapeuticAccessPermission]
    filter_backends = [TherapeuticFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TherapeuticChatRoomFilter
    search_fields = ['name', 'description', 'therapeutic_goal']
    ordering_fields = ['name', 'created_at', 'updated_at', 'max_stress_level']
    pagination_class = TherapeuticPagination
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return ChatRoomCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ChatRoomSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        """Custom permissions per action"""
        if self.action == 'create':
            permission_classes = [IsTherapeuticUser, StressLevelPermission]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsTherapeuticUser, ModerationPermission]
        elif self.action in ['join', 'leave', 'update_membership']:
            permission_classes = [IsTherapeuticUser, RoomMembershipPermission]
        elif self.action in ['moderation_actions', 'manage_moderators']:
            permission_classes = [IsTherapeuticUser, ModerationPermission]
        elif self.action == 'therapeutic_insights':
            permission_classes = [IsTherapeuticUser, TherapeuticInsightPermission]
        else:
            permission_classes = self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Apply therapeutic filters to queryset"""
        queryset = super().get_queryset()
        
        # Apply therapeutic pre-filters based on user state
        if self.request.user.is_authenticated:
            user = self.request.user
            
            # Filter by stress level
            queryset = queryset.filter(max_stress_level__gte=user.current_stress_level)
            
            # Hide archived rooms by default unless requested
            if not self.request.GET.get('show_archived'):
                queryset = queryset.filter(is_archived=False)
            
            # For gentle mode, prioritize safer rooms
            if user.gentle_mode:
                queryset = queryset.filter(safety_level__in=['safe_space', 'supportive'])
        
        return queryset.order_by('-updated_at')
    
    def get_paginator(self):
        """Get therapeutic paginator based on user state"""
        pagination_class = get_therapeutic_pagination_class(self.request, self)
        return pagination_class()
    
    def perform_create(self, serializer):
        """Create room with therapeutic defaults"""
        with transaction.atomic():
            room = serializer.save(created_by=self.request.user)
            
            # Auto-add creator as moderator
            RoomMembership.objects.create(
                user=self.request.user,
                room=room,
                role='moderator',
                consent_given=True
            )
            
            # Log therapeutic event
            self.request.user.add_breakthrough_moment(
                f"Created therapeutic chat room: {room.name}"
            )
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """
        Join a therapeutic chat room with emotional readiness checks
        """
        room = self.get_object()
        user = request.user
        
        # Check if user can join
        can_join, message = room.can_user_join(user)
        if not can_join:
            return Response(
                {'detail': message},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already a member
        existing_membership = RoomMembership.objects.filter(
            user=user,
            room=room
        ).first()
        
        if existing_membership:
            if existing_membership.is_active:
                return Response(
                    {'detail': 'Already a member of this room'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            else:
                # Reactivate membership
                existing_membership.is_active = True
                existing_membership.joined_at = timezone.now()
                existing_membership.save()
                serializer = RoomMembershipSerializer(existing_membership)
                return Response(serializer.data)
        
        # Create new membership
        membership_data = {
            'user': user.id,
            'room': room.id,
            'role': 'participant',
            'consent_given': room.requires_consent,
            'entry_stress_level': user.current_stress_level,
            'comfort_level': 3,  # Neutral
        }
        
        serializer = RoomMembershipSerializer(data=membership_data)
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        
        # Create welcome notification
        if room.requires_consent:
            welcome_message = f"Welcome to {room.name}. Remember to respect therapeutic boundaries."
        else:
            welcome_message = f"Welcome to {room.name}. We're glad you're here."
        
        ChatNotification.objects.create(
            user=user,
            notification_type='room_invite',
            title=f"Joined {room.name}",
            message=welcome_message,
            is_gentle=True
        )
        
        # Log therapeutic event
        user.add_breakthrough_moment(
            f"Joined therapeutic chat room: {room.name}"
        )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """
        Leave a therapeutic chat room with emotional closure
        """
        room = self.get_object()
        user = request.user
        
        try:
            membership = RoomMembership.objects.get(
                user=user,
                room=room,
                is_active=True
            )
            
            # Update exit stress level
            exit_stress = request.data.get('exit_stress_level', user.current_stress_level)
            membership.mark_exit(exit_stress)
            
            # Create session analytics if room tracks mood
            if room.mood_tracking_enabled:
                ChatSessionAnalytics.objects.create(
                    user=user,
                    room=room,
                    session_start=membership.joined_at,
                    session_end=timezone.now(),
                    starting_stress_level=membership.entry_stress_level or user.current_stress_level,
                    ending_stress_level=exit_stress,
                    messages_sent=ChatMessage.objects.filter(
                        user=user,
                        room=room,
                        created_at__gte=membership.joined_at,
                        created_at__lte=timezone.now()
                    ).count()
                )
            
            # Gentle notification
            ChatNotification.objects.create(
                user=user,
                notification_type='gentle_reminder',
                title="Room Left",
                message=f"You've left {room.name}. Take care of yourself.",
                is_gentle=True
            )
            
            return Response(
                {'detail': 'Successfully left the room'},
                status=status.HTTP_200_OK
            )
            
        except RoomMembership.DoesNotExist:
            return Response(
                {'detail': 'Not a member of this room'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """
        Get therapeutic room members with emotional context
        """
        room = self.get_object()
        
        # Check access
        if not room.moderators.filter(id=request.user.id).exists():
            # Regular users can only see active, non-anonymous members
            memberships = RoomMembership.objects.filter(
                room=room,
                is_active=True,
                is_anonymous=False
            )
        else:
            # Moderators can see all members
            memberships = RoomMembership.objects.filter(room=room, is_active=True)
        
        # Filter and paginate
        filter_backend = TherapeuticFilterBackend()
        filtered_memberships = filter_backend.filter_queryset(
            request, memberships, self
        )
        
        paginator = TherapeuticPagination()
        page = paginator.paginate_queryset(filtered_memberships, request)
        
        if page is not None:
            serializer = RoomMembershipSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = RoomMembershipSerializer(filtered_memberships, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def update_membership(self, request, pk=None):
        """
        Update therapeutic membership (role, comfort level, etc.)
        """
        room = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'detail': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            membership = RoomMembership.objects.get(
                room=room,
                user_id=user_id,
                is_active=True
            )
        except RoomMembership.DoesNotExist:
            return Response(
                {'detail': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permissions
        if request.user != membership.user and not room.moderators.filter(id=request.user.id).exists():
            return Response(
                {'detail': 'Insufficient permissions'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = RoomMembershipSerializer(
            membership,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mute_member(self, request, pk=None):
        """
        Therapeutically mute a member (temporary timeout)
        """
        room = self.get_object()
        user_id = request.data.get('user_id')
        duration_minutes = request.data.get('duration_minutes', 60)
        therapeutic_reason = request.data.get('therapeutic_reason', '')
        
        if not user_id:
            return Response(
                {'detail': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check moderator permissions
        if not room.moderators.filter(id=request.user.id).exists():
            return Response(
                {'detail': 'Moderator privileges required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            membership = RoomMembership.objects.get(
                room=room,
                user_id=user_id,
                is_active=True
            )
        except RoomMembership.DoesNotExist:
            return Response(
                {'detail': 'Member not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Don't mute moderators or therapists
        if membership.role in ['moderator', 'therapist']:
            return Response(
                {'detail': 'Cannot mute moderators or therapists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Apply mute
        membership.is_muted = True
        membership.save()
        
        # Schedule unmute
        from django_q.tasks import schedule
        from django_q.models import Schedule
        
        schedule(
            'chat.tasks.unmute_member',
            membership.id,
            schedule_type=Schedule.ONCE,
            next_run=timezone.now() + timedelta(minutes=duration_minutes)
        )
        
        # Create therapeutic notification for muted user
        ChatNotification.objects.create(
            user=membership.user,
            notification_type='moderation',
            title="Therapeutic Timeout",
            message=f"You've been muted in {room.name} for {duration_minutes} minutes. Reason: {therapeutic_reason}",
            is_gentle=True,
            delay_until=timezone.now() + timedelta(minutes=5)  # Gentle delay
        )
        
        return Response({
            'detail': f'Member muted for {duration_minutes} minutes',
            'therapeutic_reason': therapeutic_reason
        })
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Get therapeutic messages for a room with emotional filtering
        """
        room = self.get_object()
        
        # Check room access
        permission = RoomAccessPermission()
        if not permission.has_object_permission(request, self, room):
            return Response(
                {'detail': permission.message},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get messages with therapeutic filtering
        messages = ChatMessage.objects.filter(
            room=room,
            deleted=False
        ).select_related('user', 'room').prefetch_related('reactions')
        
        # Apply therapeutic filters
        filter_backend = TherapeuticFilterBackend()
        filtered_messages = filter_backend.filter_queryset(
            request, messages, self
        )
        
        # Use thread-aware pagination for conversations
        paginator = ThreadAwarePagination()
        page = paginator.paginate_queryset(filtered_messages, request)
        
        if page is not None:
            serializer = ChatMessageSerializer(page, many=True, context={
                'request': request,
                'room_id': room.id
            })
            return paginator.get_paginated_response(serializer.data)
        
        serializer = ChatMessageSerializer(filtered_messages, many=True, context={
            'request': request,
            'room_id': room.id
        })
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def therapeutic_insights(self, request, pk=None):
        """
        Generate therapeutic insights from room conversations
        """
        room = self.get_object()
        
        # Check access
        if not room.moderators.filter(id=request.user.id).exists():
            return Response(
                {'detail': 'Moderator or therapist privileges required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate insights (simplified - in reality would use AI/ML)
        messages = ChatMessage.objects.filter(
            room=room,
            deleted=False,
            created_at__gte=timezone.now() - timedelta(days=30)
        )
        
        insights = self.generate_therapeutic_insights(messages, room)
        
        return Response({
            'room': room.name,
            'insights_generated': timezone.now(),
            'time_period': 'last_30_days',
            'insights': insights
        })
    
    def generate_therapeutic_insights(self, messages, room):
        """Generate therapeutic insights from messages"""
        insights = []
        
        # Emotional tone analysis
        emotional_tones = messages.exclude(emotional_tone__isnull=True).values(
            'emotional_tone'
        ).annotate(count=Count('emotional_tone')).order_by('-count')[:5]
        
        if emotional_tones:
            insights.append({
                'type': 'emotional_pattern',
                'title': 'Common Emotional Tones',
                'description': 'Most frequent emotional expressions in this space',
                'data': list(emotional_tones),
                'confidence': 0.8
            })
        
        # Vulnerability patterns
        vulnerable_shares = messages.filter(is_vulnerable_share=True)
        if vulnerable_shares.exists():
            share_count = vulnerable_shares.count()
            response_rate = messages.filter(
                parent_message__in=vulnerable_shares
            ).count() / max(share_count, 1)
            
            insights.append({
                'type': 'support_network',
                'title': 'Vulnerability Support',
                'description': f'{share_count} vulnerable shares with {response_rate:.1f} average responses',
                'data': {
                    'vulnerable_shares': share_count,
                    'average_responses': response_rate,
                    'support_level': 'high' if response_rate > 1 else 'moderate'
                },
                'confidence': 0.7
            })
        
        # Coping strategy sharing
        coping_strategies = messages.filter(coping_strategy_shared=True)
        if coping_strategies.exists():
            insights.append({
                'type': 'coping_strategy',
                'title': 'Coping Strategy Exchange',
                'description': f'{coping_strategies.count()} coping strategies shared',
                'data': {
                    'count': coping_strategies.count(),
                    'topics': list(coping_strategies.values_list(
                        'therapeutic_label', flat=True
                    ).distinct()[:5])
                },
                'confidence': 0.9
            })
        
        # Activity patterns
        hourly_activity = messages.extra({
            'hour': "EXTRACT(HOUR FROM created_at)"
        }).values('hour').annotate(count=Count('id')).order_by('hour')
        
        if hourly_activity.exists():
            insights.append({
                'type': 'communication_style',
                'title': 'Activity Patterns',
                'description': 'Peak activity hours in this therapeutic space',
                'data': list(hourly_activity),
                'confidence': 0.6
            })
        
        return insights
    
    @action(detail=True, methods=['post'])
    def emotional_checkin(self, request, pk=None):
        """
        Perform an emotional check-in for the room
        """
        room = self.get_object()
        user = request.user
        
        # Check if user is a member
        try:
            membership = RoomMembership.objects.get(
                user=user,
                room=room,
                is_active=True
            )
        except RoomMembership.DoesNotExist:
            return Response(
                {'detail': 'Not a member of this room'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get check-in data
        current_feeling = request.data.get('current_feeling')
        stress_level = request.data.get('stress_level', user.current_stress_level)
        need_support = request.data.get('need_support', 'just_sharing')
        brief_context = request.data.get('brief_context', '')
        share_with_group = request.data.get('share_with_group', True)
        
        # Update user's stress level if different
        if stress_level != user.current_stress_level:
            user.current_stress_level = stress_level
            user.save(update_fields=['current_stress_level'])
        
        # Update membership comfort level based on check-in
        if stress_level <= 3:
            membership.comfort_level = 5  # Feeling Safe
        elif stress_level <= 6:
            membership.comfort_level = 3  # Comfortable
        else:
            membership.comfort_level = 1  # Uncomfortable
        membership.save(update_fields=['comfort_level'])
        
        # Create check-in message if sharing with group
        if share_with_group:
            message_content = f"Emotional check-in: {current_feeling}\n"
            message_content += f"Stress level: {stress_level}/10\n"
            message_content += f"Support needed: {need_support}"
            
            if brief_context:
                message_content += f"\n\nContext: {brief_context}"
            
            chat_message = ChatMessage.objects.create(
                room=room,
                user=user,
                content=message_content,
                message_type='checkin',
                emotional_tone=current_feeling,
                is_vulnerable_share=stress_level >= 7
            )
            
            message_serializer = ChatMessageSerializer(
                chat_message,
                context={'request': request}
            )
            message_data = message_serializer.data
        else:
            message_data = None
        
        # Create therapeutic notification
        if stress_level >= 7:
            ChatNotification.objects.create(
                user=user,
                notification_type='safety_check',
                title="High Stress Check-in",
                message="You checked in with high stress. Remember your coping strategies.",
                is_gentle=True
            )
        
        return Response({
            'checkin_completed': True,
            'timestamp': timezone.now(),
            'stress_level': stress_level,
            'comfort_level': membership.comfort_level,
            'checkin_message': message_data,
            'therapeutic_suggestion': self.get_checkin_suggestion(stress_level, need_support)
        })
    
    def get_checkin_suggestion(self, stress_level, need_support):
        """Get therapeutic suggestion based on check-in"""
        if stress_level >= 8:
            return "Consider taking a break and practicing deep breathing"
        elif stress_level >= 6 and need_support != 'just_sharing':
            return "Reach out for support in the chat when ready"
        elif stress_level <= 3:
            return "Great self-awareness! Consider supporting others"
        else:
            return "Continue checking in regularly for self-care"
    
    @action(detail=True, methods=['post'])
    def safety_plan_activation(self, request, pk=None):
        """
        Activate safety plan for room (for high-stress situations)
        """
        room = self.get_object()
        user = request.user
        
        # Check if user is a member
        try:
            membership = RoomMembership.objects.get(
                user=user,
                room=room,
                is_active=True
            )
        except RoomMembership.DoesNotExist:
            return Response(
                {'detail': 'Not a member of this room'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update membership with safety plan
        membership.has_safety_plan = True
        membership.save(update_fields=['has_safety_plan'])
        
        # Notify moderators/therapists
        moderators = room.moderators.all()
        therapists = room.therapists.all()
        
        for moderator in moderators:
            ChatNotification.objects.create(
                user=moderator,
                notification_type='safety_check',
                title="Safety Plan Activated",
                message=f"{user.username} activated their safety plan in {room.name}",
                is_urgent=True
            )
        
        for therapist in therapists:
            ChatNotification.objects.create(
                user=therapist,
                notification_type='safety_check',
                title="Safety Plan Activated",
                message=f"{user.username} activated their safety plan in {room.name}",
                is_urgent=True
            )
        
        # Create system message in room
        if request.data.get('notify_room', False):
            ChatMessage.objects.create(
                room=room,
                user=user,
                content="I'm activating my safety plan. I may need extra support right now.",
                message_type='system',
                visibility='public',
                is_vulnerable_share=True
            )
        
        return Response({
            'safety_plan_activated': True,
            'timestamp': timezone.now(),
            'emergency_contact_notified': request.data.get('notify_emergency_contact', False)
        })
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """
        Get therapeutic statistics for the room
        """
        room = self.get_object()
        
        # Check if user has access to statistics
        if not room.moderators.filter(id=request.user.id).exists():
            return Response(
                {'detail': 'Moderator privileges required for statistics'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Calculate statistics
        total_messages = ChatMessage.objects.filter(room=room, deleted=False).count()
        active_participants = RoomMembership.objects.filter(room=room, is_active=True).count()
        
        # Therapeutic metrics
        vulnerable_shares = ChatMessage.objects.filter(
            room=room, is_vulnerable_share=True, deleted=False
        ).count()
        
        coping_strategies = ChatMessage.objects.filter(
            room=room, coping_strategy_shared=True, deleted=False
        ).count()
        
        affirmations = ChatMessage.objects.filter(
            room=room, contains_affirmation=True, deleted=False
        ).count()
        
        # Emotional metrics
        emotional_breakdown = ChatMessage.objects.filter(
            room=room, emotional_tone__isnull=False, deleted=False
        ).values('emotional_tone').annotate(count=Count('emotional_tone')).order_by('-count')[:5]
        
        # Time-based metrics
        today = timezone.now().date()
        messages_today = ChatMessage.objects.filter(
            room=room, created_at__date=today, deleted=False
        ).count()
        
        last_week = timezone.now() - timedelta(days=7)
        active_last_week = RoomMembership.objects.filter(
            room=room, last_seen__gte=last_week
        ).count()
        
        statistics = {
            'room_name': room.name,
            'room_type': room.room_type,
            'safety_level': room.safety_level,
            'total_messages': total_messages,
            'active_participants': active_participants,
            'therapeutic_metrics': {
                'vulnerable_shares': vulnerable_shares,
                'coping_strategies_shared': coping_strategies,
                'affirmations_given': affirmations,
                'therapeutic_engagement_score': (
                    vulnerable_shares * 3 + 
                    coping_strategies * 2 + 
                    affirmations
                )
            },
            'emotional_metrics': {
                'top_emotional_tones': list(emotional_breakdown),
                'most_common_tone': emotional_breakdown[0]['emotional_tone'] if emotional_breakdown else None
            },
            'activity_metrics': {
                'messages_today': messages_today,
                'active_last_week': active_last_week,
                'weekly_retention': active_last_week / max(active_participants, 1)
            },
            'generated_at': timezone.now()
        }
        
        serializer = ChatStatisticsSerializer(data=statistics)
        serializer.is_valid(raise_exception=True)
        
        return Response(serializer.data)


# ============================================================================
# Therapeutic Chat Message Views
# ============================================================================

class TherapeuticChatMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for therapeutic chat messages with emotional intelligence
    """
    queryset = ChatMessage.objects.filter(deleted=False)
    serializer_class = ChatMessageSerializer
    permission_classes = [IsTherapeuticUser, MessagePermission, VulnerableSharePermission]
    filter_backends = [TherapeuticFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = TherapeuticChatMessageFilter
    search_fields = ['content', 'emotional_tone', 'therapeutic_label']
    ordering_fields = ['created_at', 'updated_at', 'helpful_votes']
    pagination_class = StressAwarePagination
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_serializer_class(self):
        """Use different serializers for different actions"""
        if self.action == 'create':
            return ChatMessageCreateSerializer
        return super().get_serializer_class()
    
    def get_permissions(self):
        """Custom permissions per action"""
        if self.action == 'create':
            permission_classes = [
                IsTherapeuticUser, 
                MessagePermission,
                VulnerableSharePermission,
                AnonymousPostingPermission,
                StressLevelPermission
            ]
        elif self.action in ['update', 'partial_update']:
            permission_classes = [IsTherapeuticUser, MessagePermission]
        elif self.action == 'destroy':
            permission_classes = [IsTherapeuticUser, MessagePermission]
        elif self.action in ['react', 'reactions']:
            permission_classes = [IsTherapeuticUser, ReactionPermission]
        elif self.action == 'mark_helpful':
            permission_classes = [IsTherapeuticUser, MessagePermission]
        elif self.action == 'trigger_safety_check':
            permission_classes = [IsTherapeuticUser, SafetyPlanPermission]
        else:
            permission_classes = self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Apply therapeutic filters to queryset"""
        queryset = super().get_queryset()
        
        # Apply therapeutic pre-filters
        if self.request.user.is_authenticated:
            user = self.request.user
            
            # Filter by user's room memberships
            user_rooms = ChatRoom.objects.filter(
                memberships__user=user,
                memberships__is_active=True
            )
            queryset = queryset.filter(room__in=user_rooms)
            
            # Apply visibility restrictions
            queryset = queryset.filter(
                Q(visibility__in=['public', 'anonymous']) |
                Q(user=user) |
                Q(visibility='moderators_only', room__moderators=user) |
                Q(visibility='therapist_only', room__therapists=user) |
                Q(visibility='self_reflection', user=user)
            ).distinct()
            
            # Stress-based filtering
            if user.current_stress_level >= 7:
                queryset = queryset.exclude(
                    Q(is_vulnerable_share=True) &
                    Q(emotional_tone__in=['anxious', 'sad', 'frustrated'])
                )
        
        return queryset.select_related('user', 'room').prefetch_related('reactions')
    
    def get_paginator(self):
        """Get therapeutic paginator based on message context"""
        if self.request.GET.get('group_threads') == 'true':
            return ThreadAwarePagination()
        
        if self.request.GET.get('balance_emotions') == 'true':
            return EmotionalTonePagination()
        
        return StressAwarePagination()
    
    def perform_create(self, serializer):
        """Create message with therapeutic context"""
        with transaction.atomic():
            message = serializer.save(user=self.request.user)
            
            # Update room activity
            message.room.updated_at = timezone.now()
            message.room.save(update_fields=['updated_at'])
            
            # Update user's last activity
            self.request.user.last_activity_date = timezone.now().date()
            self.request.user.update_streak()
            
            # Log therapeutic event for vulnerable shares
            if message.is_vulnerable_share:
                self.request.user.add_breakthrough_moment(
                    f"Shared vulnerably in chat: {message.content[:50]}..."
                )
            
            # Create gentle notification for vulnerable shares
            if message.is_vulnerable_share and self.request.user.receive_gentle_reminders:
                ChatNotification.objects.create(
                    user=self.request.user,
                    notification_type='therapeutic_insight',
                    title="Thank you for sharing",
                    message="Sharing vulnerable thoughts is brave. Remember to practice self-care.",
                    is_gentle=True
                )
    
    def perform_update(self, serializer):
        """Update message with therapeutic considerations"""
        message = self.get_object()
        
        # Check if message can be edited
        time_since_creation = timezone.now() - message.created_at
        can_edit = False
        
        if message.user == self.request.user:
            can_edit = time_since_creation.total_seconds() < 900  # 15 minutes
        elif self.request.user in message.room.moderators.all():
            can_edit = time_since_creation.total_seconds() < 3600  # 1 hour
        elif self.request.user in message.room.therapists.all():
            can_edit = True
        
        if not can_edit:
            raise ValidationError("Message can no longer be edited")
        
        serializer.save(edited=True, edited_at=timezone.now())
    
    def perform_destroy(self, instance):
        """Soft delete message with therapeutic consideration"""
        instance.soft_delete(self.request.user)
    
    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """
        Add therapeutic reaction to a message
        """
        message = self.get_object()
        user = request.user
        
        # Check if user can react to this message
        permission = ReactionPermission()
        if not permission.can_react_to_message(user, message):
            return Response(
                {'detail': permission.message},
                status=status.HTTP_403_FORBIDDEN
            )
        
        reaction_data = {
            'message': message.id,
            'reaction_type': request.data.get('reaction_type'),
            'emotional_context': request.data.get('emotional_context', ''),
            'is_anonymous': request.data.get('is_anonymous', False)
        }
        
        serializer = MessageReactionSerializer(
            data=reaction_data,
            context={'request': request, 'message': message, 'user': user}
        )
        serializer.is_valid(raise_exception=True)
        
        try:
            reaction = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            # Reaction was toggled (removed)
            return Response(
                {'detail': str(e)},
                status=status.HTTP_200_OK
            )
    
    @action(detail=True, methods=['get'])
    def reactions(self, request, pk=None):
        """
        Get therapeutic reactions for a message
        """
        message = self.get_object()
        reactions = message.reactions.all()
        
        # Filter reactions
        filter_backend = TherapeuticFilterBackend()
        filtered_reactions = filter_backend.filter_queryset(
            request, reactions, self
        )
        
        paginator = TherapeuticPagination()
        page = paginator.paginate_queryset(filtered_reactions, request)
        
        if page is not None:
            serializer = MessageReactionSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = MessageReactionSerializer(filtered_reactions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_helpful(self, request, pk=None):
        """
        Mark message as helpful (therapeutic validation)
        """
        message = self.get_object()
        user = request.user
        
        # Check if user can mark as helpful
        try:
            RoomMembership.objects.get(
                user=user,
                room=message.room,
                is_active=True
            )
        except RoomMembership.DoesNotExist:
            return Response(
                {'detail': 'Not a member of this room'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if already marked helpful
        if MessageReaction.objects.filter(
            message=message,
            user=user,
            reaction_type='✅'
        ).exists():
            return Response(
                {'detail': 'Already marked as helpful'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add helpful reaction
        reaction = MessageReaction.objects.create(
            message=message,
            user=user,
            reaction_type='✅',
            emotional_context='Found this helpful',
            is_supportive=True
        )
        
        # Update message helpful votes
        message.mark_as_helpful()
        
        # Notify message author
        if message.user != user:
            ChatNotification.objects.create(
                user=message.user,
                notification_type='reaction',
                title="Your Message Helped Someone",
                message=f"{user.username} found your message helpful in {message.room.name}",
                is_gentle=True
            )
        
        return Response({
            'marked_helpful': True,
            'helpful_votes': message.helpful_votes,
            'reaction_id': reaction.id
        })
    
    @action(detail=True, methods=['post'])
    def trigger_safety_check(self, request, pk=None):
        """
        Trigger safety check for a vulnerable message
        """
        message = self.get_object()
        
        # Check if message is vulnerable
        if not message.is_vulnerable_share:
            return Response(
                {'detail': 'Message is not marked as vulnerable'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user has permission
        if not message.room.moderators.filter(id=request.user.id).exists():
            return Response(
                {'detail': 'Moderator privileges required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Notify therapists and moderators
        therapists = message.room.therapists.all()
        moderators = message.room.moderators.all()
        
        for therapist in therapists:
            ChatNotification.objects.create(
                user=therapist,
                notification_type='safety_check',
                title="Safety Check Needed",
                message=f"Vulnerable message from {message.user.username} in {message.room.name} needs attention",
                is_urgent=True,
                content_object=message
            )
        
        for moderator in moderators:
            if moderator != request.user:
                ChatNotification.objects.create(
                    user=moderator,
                    notification_type='moderation',
                    title="Vulnerable Message Check",
                    message=f"Please check vulnerable message from {message.user.username}",
                    is_gentle=True,
                    content_object=message
                )
        
        # Update message flags
        message.requires_moderation = True
        message.save(update_fields=['requires_moderation'])
        
        return Response({
            'safety_check_triggered': True,
            'notified_therapists': therapists.count(),
            'notified_moderators': moderators.count() - 1  # Exclude requester
        })
    
    @action(detail=True, methods=['post'])
    def moderate(self, request, pk=None):
        """
        Moderate a message (therapeutic moderation)
        """
        message = self.get_object()
        
        # Check moderator permissions
        if not message.room.moderators.filter(id=request.user.id).exists():
            return Response(
                {'detail': 'Moderator privileges required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        action = request.data.get('action')
        reason = request.data.get('reason', '')
        notes = request.data.get('notes', '')
        
        if action == 'remove':
            # Soft delete with therapeutic consideration
            message.soft_delete(request.user)
            message.moderation_notes = notes
            message.moderated_by = request.user
            message.save()
            
            # Notify user
            ChatNotification.objects.create(
                user=message.user,
                notification_type='moderation',
                title="Message Removed",
                message=f"Your message in {message.room.name} was removed. Reason: {reason}",
                is_gentle=True
            )
            
            return Response({'action': 'removed', 'reason': reason})
        
        elif action == 'request_edit':
            # Request therapeutic edit
            message.requires_moderation = True
            message.moderation_notes = f"Edit requested: {notes}"
            message.save()
            
            # Notify user
            ChatNotification.objects.create(
                user=message.user,
                notification_type='moderation',
                title="Edit Requested",
                message=f"Please consider editing your message in {message.room.name}. Reason: {reason}",
                is_gentle=True
            )
            
            return Response({'action': 'edit_requested', 'reason': reason})
        
        elif action == 'clear':
            # Clear moderation flags
            message.requires_moderation = False
            message.is_flagged = False
            message.flagged_reason = None
            message.moderated_by = request.user
            message.moderation_notes = notes
            message.save()
            
            return Response({'action': 'cleared', 'notes': notes})
        
        return Response(
            {'detail': 'Invalid moderation action'},
            status=status.HTTP_400_BAD_REQUEST
        )


# ============================================================================
# Therapeutic Room Membership Views
# ============================================================================

class TherapeuticRoomMembershipViewSet(viewsets.ModelViewSet):
    """
    ViewSet for therapeutic room memberships
    """
    queryset = RoomMembership.objects.filter(is_active=True)
    serializer_class = RoomMembershipSerializer
    permission_classes = [IsTherapeuticUser, RoomMembershipPermission]
    filter_backends = [TherapeuticFilterBackend, filters.OrderingFilter]
    filterset_class = TherapeuticRoomMembershipFilter
    ordering_fields = ['joined_at', 'last_seen', 'comfort_level']
    pagination_class = TherapeuticPagination
    
    def get_permissions(self):
        """Custom permissions per action"""
        if self.action == 'update_comfort':
            permission_classes = [IsTherapeuticUser]
        elif self.action in ['update_role', 'mute', 'unmute']:
            permission_classes = [IsTherapeuticUser, ModerationPermission]
        else:
            permission_classes = self.permission_classes
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter memberships based on therapeutic context"""
        queryset = super().get_queryset()
        
        if self.request.user.is_authenticated:
            # Users can only see memberships in rooms they belong to
            user_rooms = ChatRoom.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True
            )
            queryset = queryset.filter(room__in=user_rooms)
        
        return queryset.select_related('user', 'room')
    
    @action(detail=True, methods=['post'])
    def update_comfort(self, request, pk=None):
        """
        Update therapeutic comfort level
        """
        membership = self.get_object()
        
        # Users can only update their own comfort level
        if membership.user != request.user:
            return Response(
                {'detail': 'Can only update your own comfort level'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        comfort_level = request.data.get('comfort_level')
        
        if not comfort_level or not 1 <= int(comfort_level) <= 5:
            return Response(
                {'detail': 'Comfort level must be between 1 and 5'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = membership.update_comfort_level(int(comfort_level))
        
        if success:
            return Response({
                'comfort_level_updated': True,
                'new_comfort_level': membership.comfort_level,
                'comfort_level_display': membership.get_comfort_level_display()
            })
        
        return Response(
            {'detail': 'Failed to update comfort level'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @action(detail=True, methods=['post'])
    def update_role(self, request, pk=None):
        """
        Update therapeutic role (moderator/therapist only)
        """
        membership = self.get_object()
        
        # Check if requester can modify roles
        if not membership.room.moderators.filter(id=request.user.id).exists():
            return Response(
                {'detail': 'Moderator privileges required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        new_role = request.data.get('role')
        
        if new_role not in dict(RoomMembership.MemberRole.choices):
            return Response(
                {'detail': 'Invalid role'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update role
        membership.role = new_role
        membership.save(update_fields=['role'])
        
        # Update room moderators/therapists if needed
        if new_role == 'moderator':
            membership.room.moderators.add(membership.user)
        elif membership.role == 'moderator' and new_role != 'moderator':
            membership.room.moderators.remove(membership.user)
        
        if new_role == 'therapist':
            membership.room.therapists.add(membership.user)
        elif membership.role == 'therapist' and new_role != 'therapist':
            membership.room.therapists.remove(membership.user)
        
        # Notify user
        ChatNotification.objects.create(
            user=membership.user,
            notification_type='moderation',
            title="Role Updated",
            message=f"Your role in {membership.room.name} has been updated to {new_role}",
            is_gentle=True
        )
        
        return Response({
            'role_updated': True,
            'new_role': new_role,
            'role_display': membership.get_role_display()
        })
    
    @action(detail=True, methods=['post'])
    def mute(self, request, pk=None):
        """
        Therapeutically mute a member
        """
        membership = self.get_object()
        
        # Check permissions
        if not membership.room.moderators.filter(id=request.user.id).exists():
            return Response(
                {'detail': 'Moderator privileges required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        duration_minutes = request.data.get('duration_minutes', 60)
        therapeutic_reason = request.data.get('therapeutic_reason', '')
        
        # Mute the member
        membership.is_muted = True
        membership.save(update_fields=['is_muted'])
        
        # Schedule unmute
        from django_q.tasks import schedule
        from django_q.models import Schedule
        
        schedule(
            'chat.tasks.unmute_member',
            membership.id,
            schedule_type=Schedule.ONCE,
            next_run=timezone.now() + timedelta(minutes=duration_minutes)
        )
        
        return Response({
            'muted': True,
            'duration_minutes': duration_minutes,
            'therapeutic_reason': therapeutic_reason
        })
    
    @action(detail=True, methods=['post'])
    def unmute(self, request, pk=None):
        """
        Unmute a member
        """
        membership = self.get_object()
        
        # Check permissions
        if not membership.room.moderators.filter(id=request.user.id).exists():
            return Response(
                {'detail': 'Moderator privileges required'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        membership.is_muted = False
        membership.save(update_fields=['is_muted'])
        
        return Response({'unmuted': True})


# ============================================================================
# Therapeutic Notification Views
# ============================================================================

class TherapeuticNotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for therapeutic chat notifications
    """
    queryset = ChatNotification.objects.all()
    serializer_class = ChatNotificationSerializer
    permission_classes = [IsTherapeuticUser]
    pagination_class = TherapeuticPagination
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Users can only see their own notifications"""
        queryset = super().get_queryset()
        
        if self.request.user.is_authenticated:
            queryset = queryset.filter(user=self.request.user)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications"""
        notifications = self.get_queryset().filter(is_read=False)
        
        paginator = TherapeuticPagination()
        page = paginator.paginate_queryset(notifications, request)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        notifications = self.get_queryset().filter(is_read=False)
        count = notifications.count()
        
        notifications.update(is_read=True, read_at=timezone.now())
        
        return Response({
            'marked_read': count,
            'timestamp': timezone.now()
        })
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark single notification as read"""
        notification = self.get_object()
        
        if notification.user != request.user:
            return Response(
                {'detail': 'Cannot mark others\' notifications as read'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        notification.mark_as_read()
        
        return Response({
            'marked_read': True,
            'read_at': notification.read_at
        })
    
    @action(detail=False, methods=['get'])
    def gentle_summary(self, request):
        """
        Get gentle notification summary for stressed users
        """
        if not request.user.is_authenticated:
            return Response({'notifications': []})
        
        # For high-stress users, provide gentle summary
        if request.user.current_stress_level >= 7:
            notifications = self.get_queryset().filter(
                is_read=False,
                is_urgent=True  # Only urgent notifications for high stress
            )[:3]  # Limit to 3
            
            serializer = self.get_serializer(notifications, many=True)
            
            return Response({
                'gentle_summary': True,
                'stress_level_considered': request.user.current_stress_level,
                'limited_to_urgent': True,
                'notifications': serializer.data
            })
        
        # Regular summary
        notifications = self.get_queryset().filter(is_read=False)[:10]
        serializer = self.get_serializer(notifications, many=True)
        
        return Response({
            'gentle_summary': False,
            'total_unread': self.get_queryset().filter(is_read=False).count(),
            'notifications': serializer.data
        })


# ============================================================================
# Therapeutic Chat Settings Views
# ============================================================================

class TherapeuticChatSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for therapeutic chat settings
    """
    queryset = TherapeuticChatSettings.objects.all()
    serializer_class = TherapeuticChatSettingsSerializer
    permission_classes = [IsTherapeuticUser, TherapeuticSettingsPermission]
    
    def get_queryset(self):
        """Users can only see their own settings"""
        queryset = super().get_queryset()
        
        if self.request.user.is_authenticated:
            queryset = queryset.filter(user=self.request.user)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create settings for user"""
        # Check if settings already exist
        if TherapeuticChatSettings.objects.filter(user=self.request.user).exists():
            raise ValidationError('Settings already exist for this user')
        
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['get'])
    def mine(self, request):
        """Get current user's settings"""
        try:
            settings = TherapeuticChatSettings.objects.get(user=request.user)
            serializer = self.get_serializer(settings)
            return Response(serializer.data)
        except TherapeuticChatSettings.DoesNotExist:
            # Create default settings
            default_settings = TherapeuticChatSettings.objects.create(user=request.user)
            serializer = self.get_serializer(default_settings)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def safe_notifications(self, request, pk=None):
        """
        Get safe notification settings based on current stress level
        """
        settings = self.get_object()
        
        if settings.user != request.user:
            return Response(
                {'detail': 'Cannot access others\' settings'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        safe_settings = settings.get_safe_notification_settings()
        
        return Response({
            'safe_settings': safe_settings,
            'current_stress_level': request.user.current_stress_level,
            'gentle_mode': request.user.gentle_mode,
            'calculated_at': timezone.now()
        })


# ============================================================================
# Therapeutic Search Views
# ============================================================================

class TherapeuticSearchView(generics.GenericAPIView):
    """
    Comprehensive therapeutic search across chat entities
    """
    permission_classes = [IsTherapeuticUser]
    filter_backends = [TherapeuticFilterBackend]
    filterset_class = TherapeuticSearchFilter
    
    def get(self, request):
        """
        Perform therapeutic search with emotional intelligence
        """
        # Use therapeutic search filter
        filter_instance = self.filter_queryset(ChatMessage.objects.none())
        
        # Get search type
        search_type = request.GET.getlist('search_type', ['rooms', 'messages', 'users'])
        
        results = {
            'rooms': [],
            'messages': [],
            'users': [],
            'reactions': [],
            'therapeutic_context': {
                'user_stress_level': request.user.current_stress_level,
                'gentle_mode': request.user.gentle_mode,
                'search_adapted': True,
            }
        }
        
        # Search rooms
        if 'rooms' in search_type:
            room_filter = TherapeuticChatRoomFilter(
                request.GET,
                queryset=ChatRoom.objects.all(),
                user=request.user
            )
            rooms = room_filter.qs[:10]  # Limit results
            results['rooms'] = ChatRoomSerializer(rooms, many=True).data
        
        # Search messages
        if 'messages' in search_type:
            message_filter = TherapeuticChatMessageFilter(
                request.GET,
                queryset=ChatMessage.objects.filter(deleted=False),
                user=request.user
            )
            messages = message_filter.qs.select_related('user', 'room')[:20]
            
            # Apply therapeutic ordering for high-stress users
            if request.user.current_stress_level >= 7:
                messages = messages.filter(
                    Q(emotional_tone__in=['calm', 'supportive', 'hopeful']) |
                    Q(contains_affirmation=True)
                )
            
            results['messages'] = ChatMessageSerializer(
                messages, 
                many=True,
                context={'request': request}
            ).data
        
        # Search users
        if 'users' in search_type:
            users = TherapeuticUser.objects.filter(
                Q(username__icontains=request.GET.get('q', '')) |
                Q(email__icontains=request.GET.get('q', ''))
            )[:10]
            results['users'] = TherapeuticUserLiteSerializer(users, many=True).data
        
        return Response(results)


# ============================================================================
# Therapeutic Bulk Actions View
# ============================================================================

class TherapeuticBulkActionView(generics.GenericAPIView):
    """
    Perform bulk therapeutic actions
    """
    permission_classes = [IsTherapeuticUser, BulkActionPermission]
    serializer_class = ChatBulkActionSerializer
    
    def post(self, request):
        """
        Perform bulk therapeutic action
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action = serializer.validated_data['action']
        target_ids = serializer.validated_data.get('target_ids', [])
        room_id = serializer.validated_data.get('room_id')
        user_ids = serializer.validated_data.get('user_ids', [])
        parameters = serializer.validated_data.get('parameters', {})
        
        results = {}
        
        if action == 'mark_read':
            # Mark notifications as read
            notifications = ChatNotification.objects.filter(
                id__in=target_ids,
                user=request.user
            )
            count = notifications.count()
            notifications.update(is_read=True, read_at=timezone.now())
            results = {'marked_read': count}
        
        elif action == 'delete':
            # Soft delete messages
            messages = ChatMessage.objects.filter(
                id__in=target_ids,
                user=request.user
            )
            count = messages.count()
            for message in messages:
                message.soft_delete(request.user)
            results = {'deleted': count}
        
        elif action == 'archive':
            # Archive room
            try:
                room = ChatRoom.objects.get(id=room_id)
                if room.created_by == request.user or room.moderators.filter(id=request.user.id).exists():
                    room.is_archived = True
                    room.save()
                    results = {'archived': room.name}
                else:
                    return Response(
                        {'detail': 'Cannot archive this room'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except ChatRoom.DoesNotExist:
                return Response(
                    {'detail': 'Room not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif action == 'mute':
            # Mute multiple users
            room = get_object_or_404(ChatRoom, id=room_id)
            
            if not room.moderators.filter(id=request.user.id).exists():
                return Response(
                    {'detail': 'Moderator privileges required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            memberships = RoomMembership.objects.filter(
                room=room,
                user_id__in=user_ids,
                is_active=True
            )
            
            count = memberships.count()
            memberships.update(is_muted=True)
            
            # Schedule unmute if duration specified
            duration_minutes = parameters.get('duration_minutes', 60)
            if duration_minutes:
                from django_q.tasks import schedule
                from django_q.models import Schedule
                
                for membership in memberships:
                    schedule(
                        'chat.tasks.unmute_member',
                        membership.id,
                        schedule_type=Schedule.ONCE,
                        next_run=timezone.now() + timedelta(minutes=duration_minutes)
                    )
            
            results = {'muted': count, 'duration_minutes': duration_minutes}
        
        elif action == 'trigger_safety_check':
            # Trigger safety check for room
            room = get_object_or_404(ChatRoom, id=room_id)
            
            if not room.moderators.filter(id=request.user.id).exists():
                return Response(
                    {'detail': 'Moderator privileges required'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Notify all therapists and moderators
            therapists = room.therapists.all()
            moderators = room.moderators.all()
            
            for therapist in therapists:
                ChatNotification.objects.create(
                    user=therapist,
                    notification_type='safety_check',
                    title="Bulk Safety Check",
                    message=f"Safety check triggered in {room.name}",
                    is_urgent=True
                )
            
            for moderator in moderators:
                if moderator != request.user:
                    ChatNotification.objects.create(
                        user=moderator,
                        notification_type='safety_check',
                        title="Safety Check",
                        message=f"Safety check triggered in {room.name}",
                        is_gentle=True
                    )
            
            results = {
                'safety_check_triggered': True,
                'room': room.name,
                'notified_count': therapists.count() + moderators.count() - 1
            }
        
        return Response({
            'action': action,
            'completed': True,
            'timestamp': timezone.now(),
            'results': results
        })


# ============================================================================
# Therapeutic Export Views
# ============================================================================

class TherapeuticExportView(generics.GenericAPIView):
    """
    Export therapeutic chat data for therapy or personal reflection
    """
    permission_classes = [IsTherapeuticUser, ExportPermission]
    serializer_class = ChatExportSerializer
    
    def post(self, request):
        """
        Export therapeutic chat data
        """
        # Check export consent
        if not request.data.get('export_consent'):
            return Response(
                {'detail': 'Export consent is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get export parameters
        room_id = request.data.get('room_id')
        date_from = request.data.get('date_from')
        date_to = request.data.get('date_to')
        export_format = request.data.get('format', 'json')
        
        # Build queryset
        messages = ChatMessage.objects.filter(
            user=request.user,
            deleted=False
        )
        
        if room_id:
            messages = messages.filter(room_id=room_id)
        
        if date_from:
            messages = messages.filter(created_at__gte=date_from)
        
        if date_to:
            messages = messages.filter(created_at__lte=date_to)
        
        # Limit to last 1000 messages for safety
        messages = messages.order_by('-created_at')[:1000]
        
        # Serialize data
        serializer = self.get_serializer(messages, many=True)
        
        # Create export data
        export_data = {
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'emotional_profile': request.user.emotional_profile,
                'export_date': timezone.now().isoformat()
            },
            'export_context': {
                'purpose': 'therapeutic_review',
                'date_range': {'from': date_from, 'to': date_to},
                'room_id': room_id,
                'message_count': messages.count()
            },
            'messages': serializer.data
        }
        
        # Log export for therapeutic tracking
        request.user.add_breakthrough_moment(
            f"Exported chat data for therapeutic review"
        )
        
        # Return in requested format
        if export_format == 'json':
            return Response(export_data)
        else:
            # For other formats, you'd generate files
            return Response({
                'detail': f'{export_format} export not yet implemented',
                'data_available_in_json': True,
                'preview': export_data
            })


# ============================================================================
# Therapeutic Dashboard Views
# ============================================================================

class TherapeuticDashboardView(generics.GenericAPIView):
    """
    Therapeutic dashboard for chat activity
    """
    permission_classes = [IsTherapeuticUser]
    
    def get(self, request):
        """
        Get therapeutic dashboard data
        """
        user = request.user
        
        # Get user's rooms
        user_rooms = ChatRoom.objects.filter(
            memberships__user=user,
            memberships__is_active=True
        )
        
        # Get recent activity
        recent_messages = ChatMessage.objects.filter(
            room__in=user_rooms,
            deleted=False,
            created_at__gte=timezone.now() - timedelta(days=7)
        ).select_related('room').order_by('-created_at')[:10]
        
        # Get notifications
        unread_notifications = ChatNotification.objects.filter(
            user=user,
            is_read=False
        ).count()
        
        # Get therapeutic statistics
        vulnerable_shares = ChatMessage.objects.filter(
            user=user,
            is_vulnerable_share=True,
            deleted=False,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        coping_strategies = ChatMessage.objects.filter(
            user=user,
            coping_strategy_shared=True,
            deleted=False,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        affirmations = ChatMessage.objects.filter(
            user=user,
            contains_affirmation=True,
            deleted=False,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Get comfort levels across rooms
        memberships = RoomMembership.objects.filter(
            user=user,
            is_active=True
        ).select_related('room')
        
        room_comforts = [
            {
                'room_name': m.room.name,
                'comfort_level': m.comfort_level,
                'comfort_display': m.get_comfort_level_display(),
                'last_seen': m.last_seen
            }
            for m in memberships
        ]
        
        # Therapeutic recommendations
        recommendations = self.get_therapeutic_recommendations(user, vulnerable_shares, coping_strategies)
        
        dashboard_data = {
            'user': {
                'username': user.username,
                'emotional_profile': user.emotional_profile,
                'stress_level': user.current_stress_level,
                'gentle_mode': user.gentle_mode,
                'streak_badge': user.learning_streak_badge
            },
            'activity': {
                'active_rooms': user_rooms.count(),
                'recent_messages': ChatMessageSerializer(
                    recent_messages,
                    many=True,
                    context={'request': request}
                ).data,
                'unread_notifications': unread_notifications
            },
            'therapeutic_engagement': {
                'vulnerable_shares_30d': vulnerable_shares,
                'coping_strategies_30d': coping_strategies,
                'affirmations_30d': affirmations,
                'engagement_score': (
                    vulnerable_shares * 3 + 
                    coping_strategies * 2 + 
                    affirmations
                )
            },
            'comfort_metrics': {
                'room_comforts': room_comforts,
                'average_comfort': sum(m.comfort_level for m in memberships) / max(len(memberships), 1)
            },
            'therapeutic_recommendations': recommendations,
            'generated_at': timezone.now()
        }
        
        return Response(dashboard_data)
    
    def get_therapeutic_recommendations(self, user, vulnerable_shares, coping_strategies):
        """Get therapeutic recommendations based on user activity"""
        recommendations = []
        
        # Based on stress level
        if user.current_stress_level >= 8:
            recommendations.append({
                'type': 'self_care',
                'priority': 'high',
                'message': 'Your stress level is high. Consider taking a break from chat.',
                'action': 'practice_breathing'
            })
        elif user.current_stress_level >= 6:
            recommendations.append({
                'type': 'gentle_engagement',
                'priority': 'medium',
                'message': 'You might benefit from gentle, supportive conversations.',
                'action': 'join_supportive_room'
            })
        
        # Based on engagement
        if vulnerable_shares == 0 and user.current_stress_level < 6:
            recommendations.append({
                'type': 'therapeutic_growth',
                'priority': 'low',
                'message': 'Consider sharing something small when you feel ready.',
                'action': 'try_vulnerable_share'
            })
        
        if coping_strategies == 0:
            recommendations.append({
                'type': 'skill_building',
                'priority': 'medium',
                'message': 'Sharing coping strategies can help others and reinforce your own skills.',
                'action': 'share_coping_strategy'
            })
        
        # Based on gentle mode
        if user.gentle_mode and len(recommendations) > 2:
            recommendations.append({
                'type': 'pace_yourself',
                'priority': 'low',
                'message': 'Remember to go at your own pace in gentle mode.',
                'action': 'take_breaks'
            })
        
        return recommendations


# ============================================================================
# Function-based Views for WebSocket/Real-time
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def therapeutic_websocket_token(request):
    """
    Get token for therapeutic WebSocket connection
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    
    # Generate a unique token for this session
    token = str(uuid.uuid4())
    
    # Store token in user's session
    request.session['websocket_token'] = token
    request.session['websocket_user_id'] = request.user.id
    request.session.modified = True
    
    # Get rooms user can access
    user_rooms = ChatRoom.objects.filter(
        memberships__user=request.user,
        memberships__is_active=True
    ).values_list('id', flat=True)
    
    return Response({
        'token': token,
        'user_id': request.user.id,
        'accessible_rooms': list(user_rooms),
        'gentle_mode': request.user.gentle_mode,
        'stress_level': request.user.current_stress_level,
        'expires_in': 3600  # 1 hour
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def therapeutic_typing_indicator(request, room_id):
    """
    Send therapeutic typing indicator
    """
    try:
        room = ChatRoom.objects.get(id=room_id)
        
        # Check if user is a member
        RoomMembership.objects.get(
            user=request.user,
            room=room,
            is_active=True
        )
        
        # Get typing data
        is_typing = request.data.get('is_typing', True)
        message_type = request.data.get('message_type', 'text')
        
        # Send typing indicator via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        
        async_to_sync(channel_layer.group_send)(
            f'chat_room_{room_id}',
            {
                'type': 'typing_indicator',
                'user_id': request.user.id,
                'username': request.user.username,
                'is_typing': is_typing,
                'message_type': message_type,
                'timestamp': timezone.now().isoformat(),
                'gentle_mode': request.user.gentle_mode
            }
        )
        
        return Response({
            'typing_indicator_sent': True,
            'room': room.name,
            'is_typing': is_typing
        })
        
    except (ChatRoom.DoesNotExist, RoomMembership.DoesNotExist):
        return Response(
            {'detail': 'Room not found or not a member'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def therapeutic_presence_update(request):
    """
    Update therapeutic presence status
    """
    room_id = request.data.get('room_id')
    status_type = request.data.get('status', 'active')  # active, away, busy, offline
    emotional_state = request.data.get('emotional_state', '')
    
    if room_id:
        try:
            room = ChatRoom.objects.get(id=room_id)
            membership = RoomMembership.objects.get(
                user=request.user,
                room=room,
                is_active=True
            )
            
            # Update last seen
            membership.last_seen = timezone.now()
            membership.save(update_fields=['last_seen'])
            
            # Update emotional state if provided
            if emotional_state and membership.comfort_level:
                # Map emotional state to comfort level
                emotional_to_comfort = {
                    'calm': 5,
                    'comfortable': 4,
                    'neutral': 3,
                    'uncomfortable': 2,
                    'distressed': 1
                }
                
                if emotional_state in emotional_to_comfort:
                    membership.comfort_level = emotional_to_comfort[emotional_state]
                    membership.save(update_fields=['comfort_level'])
            
            # Broadcast presence update
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            
            async_to_sync(channel_layer.group_send)(
                f'chat_room_{room_id}',
                {
                    'type': 'presence_update',
                    'user_id': request.user.id,
                    'username': request.user.username,
                    'status': status_type,
                    'emotional_state': emotional_state,
                    'comfort_level': membership.comfort_level,
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            return Response({
                'presence_updated': True,
                'room': room.name,
                'status': status_type,
                'emotional_state': emotional_state
            })
            
        except (ChatRoom.DoesNotExist, RoomMembership.DoesNotExist):
            return Response(
                {'detail': 'Room not found or not a member'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    return Response(
        {'detail': 'room_id is required'},
        status=status.HTTP_400_BAD_REQUEST
    )


# ============================================================================
# Therapeutic Template Views
# ============================================================================

class TherapeuticTemplateView(generics.GenericAPIView):
    """
    Views for therapeutic chat templates
    """
    permission_classes = [IsTherapeuticUser, RoomTemplatePermission]
    
    def get(self, request):
        """
        Get available therapeutic room templates
        """
        templates = [
            {
                'id': 'gentle_intro',
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
                'therapeutic_goal': 'Build initial comfort and connection in a therapeutic community',
                'suggested_for': ['new_users', 'gentle_mode', 'high_stress']
            },
            {
                'id': 'coping_strategies',
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
                'therapeutic_goal': 'Expand personal coping toolkit through shared experience',
                'suggested_for': ['building_skills', 'mutual_support', 'moderate_stress']
            },
            {
                'id': 'progress_celebration',
                'name': 'Progress Celebration',
                'description': 'Celebrate therapeutic progress and small victories',
                'room_type': 'social',
                'safety_level': 'supportive',
                'conversation_guidelines': [
                    'Celebrate all progress, no matter how small',
                    'Focus on effort and persistence',
                    'Avoid comparison - everyone\'s journey is unique',
                    'Share what helped you make progress',
                    'Offer genuine encouragement'
                ],
                'therapeutic_goal': 'Reinforce positive changes and build self-efficacy',
                'suggested_for': ['motivation', 'positive_focus', 'all_stress_levels']
            },
            {
                'id': 'quiet_reflection',
                'name': 'Quiet Reflection Space',
                'description': 'A calm space for personal reflection and quiet conversation',
                'room_type': 'general',
                'safety_level': 'safe_space',
                'max_participants': 10,
                'conversation_guidelines': [
                    'Respect quiet and reflective atmosphere',
                    'Share thoughts when moved to do so',
                    'Practice deep listening',
                    'Allow space for silence',
                    'Focus on present moment awareness'
                ],
                'therapeutic_goal': 'Practice mindfulness and thoughtful self-expression',
                'suggested_for': ['mindfulness', 'low_stimulation', 'high_stress']
            }
        ]
        
        # Filter templates based on user state
        filtered_templates = []
        for template in templates:
            # Check if template is suitable for user's stress level
            max_stress = template.get('max_stress_level', 10)
            if request.user.current_stress_level <= max_stress:
                filtered_templates.append(template)
        
        return Response({
            'templates': filtered_templates,
            'filtered_by_stress_level': True,
            'user_stress_level': request.user.current_stress_level
        })
    
    def post(self, request):
        """
        Create room from therapeutic template
        """
        template_id = request.data.get('template_id')
        custom_name = request.data.get('custom_name')
        therapeutic_focus = request.data.get('therapeutic_focus', '')
        
        # Get template
        templates_response = self.get(request)
        templates = templates_response.data['templates']
        
        template = None
        for t in templates:
            if t['id'] == template_id:
                template = t
                break
        
        if not template:
            return Response(
                {'detail': 'Template not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create room from template
        room_data = {
            'name': custom_name or template['name'],
            'description': template['description'],
            'room_type': template['room_type'],
            'safety_level': template['safety_level'],
            'max_stress_level': template.get('max_stress_level', 7),
            'therapeutic_goal': template['therapeutic_goal'],
            'conversation_guidelines': template['conversation_guidelines']
        }
        
        # Add therapeutic focus if provided
        if therapeutic_focus:
            room_data['therapeutic_goal'] += f" | Focus: {therapeutic_focus}"
        
        serializer = ChatRoomCreateSerializer(
            data=room_data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        room = serializer.save()
        
        # Log therapeutic event
        request.user.add_breakthrough_moment(
            f"Created therapeutic room from template: {room.name}"
        )
        
        return Response({
            'room_created': True,
            'room': ChatRoomSerializer(room).data,
            'from_template': template_id,
            'therapeutic_focus': therapeutic_focus
        })


# ============================================================================
# Emergency/Safety Views
# ============================================================================

class TherapeuticSafetyView(generics.GenericAPIView):
    """
    Emergency safety views for therapeutic chat
    """
    permission_classes = [IsTherapeuticUser]
    
    def post(self, request):
        """
        Emergency safety action
        """
        action = request.data.get('action')
        
        if action == 'pause_all_notifications':
            # Pause all notifications temporarily
            request.session['notifications_paused'] = True
            request.session['notifications_paused_until'] = (
                timezone.now() + timedelta(hours=1)
            ).isoformat()
            request.session.modified = True
            
            return Response({
                'notifications_paused': True,
                'paused_until': request.session['notifications_paused_until'],
                'reason': 'emotional_overload_protection'
            })
        
        elif action == 'leave_all_rooms':
            # Leave all chat rooms temporarily
            memberships = RoomMembership.objects.filter(
                user=request.user,
                is_active=True
            )
            
            count = 0
            for membership in memberships:
                membership.mark_exit(request.user.current_stress_level)
                count += 1
            
            # Create safety notification
            ChatNotification.objects.create(
                user=request.user,
                notification_type='safety_check',
                title="Safety Mode Activated",
                message="You have left all chat rooms. Take time for self-care.",
                is_gentle=True,
                delay_until=timezone.now() + timedelta(minutes=30)
            )
            
            return Response({
                'left_all_rooms': True,
                'rooms_left': count,
                'safety_mode_activated': True
            })
        
        elif action == 'get_safety_resources':
            # Get emergency safety resources
            resources = [
                {
                    'type': 'crisis',
                    'name': 'Crisis Text Line',
                    'contact': 'Text HOME to 741741',
                    'available': '24/7',
                    'description': 'Free, 24/7 crisis counseling via text'
                },
                {
                    'type': 'therapy',
                    'name': 'BetterHelp Online Therapy',
                    'contact': 'betterhelp.com',
                    'available': 'Online',
                    'description': 'Online therapy with licensed professionals'
                },
                {
                    'type': 'grounding',
                    'name': '5-4-3-2-1 Grounding Technique',
                    'contact': 'Self-guided',
                    'available': 'Immediate',
                    'description': 'Notice 5 things you see, 4 things you feel, 3 things you hear, 2 things you smell, 1 thing you taste'
                }
            ]
            
            return Response({
                'safety_resources': resources,
                'user_stress_level': request.user.current_stress_level,
                'recommended_resource': 'crisis' if request.user.current_stress_level >= 8 else 'grounding'
            })
        
        return Response(
            {'detail': 'Invalid safety action'},
            status=status.HTTP_400_BAD_REQUEST
        )


# ============================================================================
# URL Patterns would be defined in chat/urls.py
# ============================================================================