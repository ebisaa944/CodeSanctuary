# social/permissions.py
"""
Advanced therapeutic permissions system with compassionate access control,
emotional awareness, and community safety features.
"""

from rest_framework import permissions
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from datetime import timedelta
import logging

from .models import (
    GentleInteraction, SupportCircle, CircleMembership,
    UserAchievement, Achievement
)

logger = logging.getLogger(__name__)


# ============================================================================
# BASE THERAPEUTIC PERMISSIONS
# ============================================================================

class TherapeuticBasePermission(BasePermission):
    """
    Base permission class with therapeutic messaging and gentle denial
    """
    
    therapeutic_message = None
    gentle_suggestion = None
    
    def has_permission(self, request, view):
        """Check permission with therapeutic messaging"""
        has_perm = self._has_permission(request, view)
        
        if not has_perm and request.user.is_authenticated:
            self._log_permission_denied(request, view)
        
        return has_perm
    
    def has_object_permission(self, request, view, obj):
        """Check object permission with therapeutic messaging"""
        has_perm = self._has_object_permission(request, view, obj)
        
        if not has_perm and request.user.is_authenticated:
            self._log_permission_denied(request, view, obj)
        
        return has_perm
    
    def _has_permission(self, request, view):
        """Override in subclasses - actual permission logic"""
        return True
    
    def _has_object_permission(self, request, view, obj):
        """Override in subclasses - actual object permission logic"""
        return True
    
    def _log_permission_denied(self, request, view, obj=None):
        """Log permission denial with context"""
        log_data = {
            'user': request.user.id,
            'view': view.__class__.__name__,
            'method': request.method,
            'path': request.path,
            'object': str(obj) if obj else None,
            'permission_class': self.__class__.__name__,
            'therapeutic_message': self.therapeutic_message,
            'gentle_suggestion': self.gentle_suggestion,
            'timestamp': timezone.now().isoformat()
        }
        
        logger.info(f"Therapeutic permission denied: {log_data}")
    
    def get_therapeutic_message(self):
        """Get therapeutic message for permission denial"""
        return self.therapeutic_message or "This action requires special permissions."
    
    def get_gentle_suggestion(self):
        """Get gentle suggestion for permission denial"""
        return self.gentle_suggestion or "Consider what you hope to contribute to the community."


# ============================================================================
# INTERACTION PERMISSIONS
# ============================================================================

class IsGentleInteractionOwner(TherapeuticBasePermission):
    """
    Permission to check if user is the owner of a gentle interaction.
    Respects anonymous interactions and therapeutic context.
    """
    
    therapeutic_message = "This interaction belongs to someone else"
    gentle_suggestion = "You can create your own gentle interactions"
    
    def _has_object_permission(self, request, view, obj):
        """Check if user owns the interaction or is allowed by therapeutic rules"""
        
        # Anonymous users can only view
        if not request.user.is_authenticated:
            return request.method in SAFE_METHODS
        
        # Safe methods are generally allowed for viewing
        if request.method in SAFE_METHODS:
            return obj.can_user_see(request.user)
        
        # For write operations, check ownership
        if isinstance(obj, GentleInteraction):
            # System-generated interactions have no owner
            if obj.sender is None:
                return False
            
            # Check if user is the sender
            is_owner = obj.sender == request.user
            
            # Special therapeutic rule: recipients can reply to private messages
            if not is_owner and request.method == 'POST' and 'reply' in request.path:
                return obj.recipient == request.user and obj.allow_replies
            
            return is_owner
        
        return False


class CanViewPrivateInteractions(TherapeuticBasePermission):
    """
    Permission to view private interactions.
    Respects therapeutic privacy boundaries.
    """
    
    therapeutic_message = "This interaction is private"
    gentle_suggestion = "Respecting privacy is important for therapeutic spaces"
    
    def _has_object_permission(self, request, view, obj):
        """Check if user can view private interaction"""
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, GentleInteraction):
            # Check visibility rules
            if obj.visibility == 'public':
                return True
            elif obj.visibility == 'community':
                return request.user.is_authenticated
            elif obj.visibility == 'anonymous':
                return True
            elif obj.visibility == 'private':
                return request.user in [obj.sender, obj.recipient]
        
        return False


class CanCreateGentleInteraction(TherapeuticBasePermission):
    """
    Permission to create gentle interactions with therapeutic rate limiting
    and emotional state consideration.
    """
    
    therapeutic_message = "Creating interactions requires mindful pacing"
    gentle_suggestion = "Consider journaling your thoughts first"
    
    def _has_permission(self, request, view):
        """Check if user can create interactions with therapeutic pacing"""
        if not request.user.is_authenticated:
            # Anonymous posting is allowed but rate-limited
            return request.method == 'POST' and 'anonymous' in request.data.get('visibility', '')
        
        # Check therapeutic posting limits
        if not self._check_therapeutic_pacing(request.user):
            self.therapeutic_message = "You've created many interactions recently"
            self.gentle_suggestion = "Taking breaks between posts helps with mindful communication"
            return False
        
        # Check emotional state restrictions
        if not self._check_emotional_state(request.user):
            self.therapeutic_message = "Your current emotional state suggests pausing"
            self.gentle_suggestion = "Consider gentle self-care before contributing"
            return False
        
        return True
    
    def _check_therapeutic_pacing(self, user):
        """Check therapeutic posting pace"""
        from .models import GentleInteraction
        
        today = timezone.now().date()
        today_count = GentleInteraction.objects.filter(
            sender=user,
            created_at__date=today
        ).count()
        
        # Therapeutic limit: 20 interactions per day
        if today_count >= 20:
            return False
        
        # Check rapid posting (last hour)
        last_hour = timezone.now() - timedelta(hours=1)
        last_hour_count = GentleInteraction.objects.filter(
            sender=user,
            created_at__gte=last_hour
        ).count()
        
        # Therapeutic limit: 10 interactions per hour
        if last_hour_count >= 10:
            return False
        
        return True
    
    def _check_emotional_state(self, user):
        """Check if emotional state allows interaction creation"""
        emotional_state = getattr(user, 'emotional_profile', 'balanced')
        
        # Therapeutic rule: When in crisis mode, limit posting
        if hasattr(user, 'crisis_mode') and getattr(user, 'crisis_mode', False):
            today = timezone.now().date()
            crisis_posts = GentleInteraction.objects.filter(
                sender=user,
                created_at__date=today,
                interaction_type='support'
            ).count()
            
            # Limit crisis posts to prevent overwhelming self-expression
            if crisis_posts >= 3:
                return False
        
        # Allow all states by default, can be customized
        return True


class IsAnonymousAllowed(TherapeuticBasePermission):
    """
    Permission to allow anonymous interactions while maintaining community safety.
    """
    
    therapeutic_message = "Anonymous interactions have special requirements"
    gentle_suggestion = "Consider how anonymity affects therapeutic sharing"
    
    def _has_permission(self, request, view):
        """Check if anonymous interaction is allowed"""
        if request.method in SAFE_METHODS:
            return True
        
        # For POST requests, check if anonymous is requested
        if request.method == 'POST':
            visibility = request.data.get('visibility', '')
            sender_id = request.data.get('sender', None)
            
            # Anonymous posting requires no sender specified
            if visibility == 'anonymous' and not sender_id:
                return True
            
            # Non-anonymous posting requires authentication
            return request.user.is_authenticated
        
        return False
    
    def _has_object_permission(self, request, view, obj):
        """Check object permissions for anonymous content"""
        if not request.user.is_authenticated:
            # Anonymous users can only view public/anonymous content
            if isinstance(obj, GentleInteraction):
                return obj.visibility in ['public', 'anonymous']
            return False
        
        return True


class CanModerateContent(TherapeuticBasePermission):
    """
    Permission to moderate content for therapeutic community safety.
    Includes gentle intervention capabilities.
    """
    
    therapeutic_message = "Content moderation requires special permissions"
    gentle_suggestion = "Consider reporting concerning content instead"
    
    def _has_permission(self, request, view):
        """Check if user can moderate content"""
        if not request.user.is_authenticated:
            return False
        
        # Staff and moderators can moderate
        if request.user.is_staff:
            return True
        
        # Check for moderator role
        if hasattr(request.user, 'is_moderator') and request.user.is_moderator:
            return True
        
        # Community elders (based on activity)
        if self._is_community_elder(request.user):
            return True
        
        return False
    
    def _has_object_permission(self, request, view, obj):
        """Check object-specific moderation permissions"""
        if not self._has_permission(request, view):
            return False
        
        # Special rule: Cannot moderate your own content
        if isinstance(obj, GentleInteraction) and obj.sender == request.user:
            self.therapeutic_message = "Self-moderation requires different approach"
            self.gentle_suggestion = "Consider asking a trusted community member for perspective"
            return False
        
        return True
    
    def _is_community_elder(self, user):
        """Check if user is a community elder based on therapeutic contribution"""
        from .models import GentleInteraction, CircleMembership
        
        # Criteria for community elder:
        # 1. Active for at least 90 days
        if user.date_joined > timezone.now() - timedelta(days=90):
            return False
        
        # 2. Has created therapeutic interactions
        therapeutic_interactions = GentleInteraction.objects.filter(
            sender=user,
            therapeutic_impact_score__gte=30
        ).count()
        
        if therapeutic_interactions < 10:
            return False
        
        # 3. Active in support circles
        active_circles = CircleMembership.objects.filter(
            user=user,
            last_active__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        if active_circles < 1:
            return False
        
        # 4. Has given substantial support
        total_support_given = CircleMembership.objects.filter(
            user=user
        ).aggregate(total=Sum('support_given'))['total'] or 0
        
        return total_support_given >= 20


# ============================================================================
# SUPPORT CIRCLE PERMISSIONS
# ============================================================================

class IsSupportCircleMember(TherapeuticBasePermission):
    """
    Permission to check if user is a member of a support circle.
    Respects circle privacy and therapeutic boundaries.
    """
    
    therapeutic_message = "This requires circle membership"
    gentle_suggestion = "Consider joining the circle or exploring public spaces"
    
    def _has_object_permission(self, request, view, obj):
        """Check if user is a circle member with appropriate access"""
        if not request.user.is_authenticated:
            return False
        
        # Handle different object types
        if isinstance(obj, SupportCircle):
            circle = obj
        elif hasattr(obj, 'circle'):
            circle = obj.circle
        elif hasattr(obj, 'supportcircle'):
            circle = obj.supportcircle
        else:
            return False
        
        # Check membership
        is_member = CircleMembership.objects.filter(
            circle=circle,
            user=request.user
        ).exists()
        
        # Public circles allow viewing for some actions
        if not is_member and request.method in SAFE_METHODS:
            return circle.is_public
        
        return is_member


class IsSupportCircleAdmin(TherapeuticBasePermission):
    """
    Permission for support circle administrators/leaders.
    Includes therapeutic leadership responsibilities.
    """
    
    therapeutic_message = "Circle administration requires leadership role"
    gentle_suggestion = "Consider discussing with circle leaders"
    
    def _has_object_permission(self, request, view, obj):
        """Check if user is a circle admin"""
        if not request.user.is_authenticated:
            return False
        
        # Get circle from object
        if isinstance(obj, SupportCircle):
            circle = obj
        elif hasattr(obj, 'circle'):
            circle = obj.circle
        else:
            return False
        
        # Check admin role
        try:
            membership = CircleMembership.objects.get(
                circle=circle,
                user=request.user
            )
            return membership.role in ['leader', 'admin']
        except CircleMembership.DoesNotExist:
            return False


class CanCreateSupportCircle(TherapeuticBasePermission):
    """
    Permission to create new support circles with therapeutic considerations.
    """
    
    therapeutic_message = "Creating circles requires community readiness"
    gentle_suggestion = "Consider joining existing circles first"
    
    def _has_permission(self, request, view):
        """Check if user can create support circles"""
        if not request.user.is_authenticated:
            return False
        
        # Check if user has too many circles
        user_circles = SupportCircle.objects.filter(
            created_by=request.user
        ).count()
        
        # Therapeutic limit: 3 circles per user
        if user_circles >= 3:
            self.therapeutic_message = "You're already facilitating several circles"
            self.gentle_suggestion = "Focusing on existing circles can be more therapeutic"
            return False
        
        # Check user's therapeutic standing
        if not self._check_therapeutic_standing(request.user):
            self.therapeutic_message = "Creating circles requires therapeutic stability"
            self.gentle_suggestion = "Focus on your own healing journey first"
            return False
        
        return True
    
    def _check_therapeutic_standing(self, user):
        """Check user's therapeutic standing for circle creation"""
        from .models import GentleInteraction, CircleMembership
        
        # 1. Must be active for at least 30 days
        if user.date_joined > timezone.now() - timedelta(days=30):
            return False
        
        # 2. Must have positive therapeutic contributions
        positive_interactions = GentleInteraction.objects.filter(
            sender=user,
            therapeutic_impact_score__gte=20
        ).count()
        
        if positive_interactions < 5:
            return False
        
        # 3. Must be active in at least one circle
        active_memberships = CircleMembership.objects.filter(
            user=user,
            last_active__gte=timezone.now() - timedelta(days=14)
        ).count()
        
        return active_memberships >= 1


class CanJoinSupportCircle(TherapeuticBasePermission):
    """
    Permission to join support circles with therapeutic matching.
    """
    
    therapeutic_message = "Joining circles requires alignment"
    gentle_suggestion = "Find circles that match your therapeutic needs"
    
    def _has_object_permission(self, request, view, obj):
        """Check if user can join a specific circle"""
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, SupportCircle):
            return False
        
        # Check if already member
        if CircleMembership.objects.filter(
            circle=obj,
            user=request.user
        ).exists():
            self.therapeutic_message = "You're already a member"
            self.gentle_suggestion = "Engage more deeply with your current circles"
            return False
        
        # Check if circle is full
        if obj.active_members >= obj.max_members:
            self.therapeutic_message = "This circle is currently full"
            self.gentle_suggestion = "Circles work best with limited size for intimacy"
            return False
        
        # Check therapeutic compatibility
        if not self._check_therapeutic_compatibility(request.user, obj):
            self.therapeutic_message = "This circle may not match your current needs"
            self.gentle_suggestion = "Look for circles with different focus areas"
            return False
        
        return True
    
    def _check_therapeutic_compatibility(self, user, circle):
        """Check therapeutic compatibility between user and circle"""
        user_emotional = getattr(user, 'emotional_profile', 'balanced')
        circle_focus = circle.focus_areas or []
        
        # If circle has specific focus, check compatibility
        if circle_focus:
            # Map emotional states to compatible focus areas
            compatibility_map = {
                'anxious': ['mindfulness', 'calming', 'breathing', 'grounding'],
                'depressed': ['motivation', 'activity', 'connection', 'hope'],
                'overwhelmed': ['simplification', 'prioritization', 'breaks', 'self-care'],
                'balanced': ['growth', 'learning', 'sharing', 'leadership']
            }
            
            user_compatible = compatibility_map.get(user_emotional, [])
            
            # Check if any circle focus is compatible
            for focus in circle_focus:
                if focus.lower() in user_compatible:
                    return True
            
            # No compatible focus found
            return len(circle_focus) == 0  # Allow if circle has no specific focus
        
        return True  # Allow if circle has no focus areas


# ============================================================================
# ACHIEVEMENT PERMISSIONS
# ============================================================================

class IsAchievementOwner(TherapeuticBasePermission):
    """
    Permission to check if user owns an achievement record.
    """
    
    therapeutic_message = "These achievements belong to someone else"
    gentle_suggestion = "Celebrate others' progress while focusing on your own journey"
    
    def _has_object_permission(self, request, view, obj):
        """Check if user owns the achievement"""
        if not request.user.is_authenticated:
            return False
        
        if isinstance(obj, UserAchievement):
            return obj.user == request.user
        
        return False


class CanEarnAchievement(TherapeuticBasePermission):
    """
    Permission to earn achievements with therapeutic pacing.
    """
    
    therapeutic_message = "Achievements require meaningful progress"
    gentle_suggestion = "Focus on the therapeutic journey, not just the milestones"
    
    def _has_object_permission(self, request, view, obj):
        """Check if user can earn a specific achievement"""
        if not request.user.is_authenticated:
            return False
        
        if not isinstance(obj, Achievement):
            return False
        
        # Check if already earned
        if UserAchievement.objects.filter(
            user=request.user,
            achievement=obj
        ).exists():
            self.therapeutic_message = "You've already earned this achievement"
            self.gentle_suggestion = "Revisit what this achievement means to you"
            return False
        
        # Check therapeutic pacing
        if not self._check_achievement_pacing(request.user):
            self.therapeutic_message = "Achievements should be spaced meaningfully"
            self.gentle_suggestion = "Allow time to integrate each achievement"
            return False
        
        return True
    
    def _check_achievement_pacing(self, user):
        """Check therapeutic pacing for achievements"""
        recent_achievements = UserAchievement.objects.filter(
            user=user,
            earned_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        # Therapeutic limit: 3 achievements per week
        return recent_achievements < 3


# ============================================================================
# COMMUNITY AND VISIBILITY PERMISSIONS
# ============================================================================

class IsTherapeuticCommunityMember(TherapeuticBasePermission):
    """
    Permission to access therapeutic community features.
    Different from regular authentication - considers therapeutic standing.
    """
    
    therapeutic_message = "Community access requires therapeutic engagement"
    gentle_suggestion = "Start by gently engaging with public content"
    
    def _has_permission(self, request, view):
        """Check if user is a therapeutic community member"""
        if not request.user.is_authenticated:
            return False
        
        # New users have limited access initially
        if user.date_joined > timezone.now() - timedelta(days=1):
            # First day: read-only access to public content
            return request.method in SAFE_METHODS
        
        # After first interaction, full community access
        from .models import GentleInteraction
        has_interacted = GentleInteraction.objects.filter(
            sender=request.user
        ).exists()
        
        if not has_interacted:
            # Can view but not post until first gentle interaction
            return request.method in SAFE_METHODS
        
        return True


class HasTherapeuticPermission(TherapeuticBasePermission):
    """
    Generic permission for therapeutic actions based on user's therapeutic state.
    """
    
    therapeutic_message = "This action requires therapeutic readiness"
    gentle_suggestion = "Consider your current emotional state and capacity"
    
    def __init__(self, permission_type=None, **kwargs):
        """Initialize with specific permission type"""
        super().__init__()
        self.permission_type = permission_type
        self.kwargs = kwargs
    
    def _has_permission(self, request, view):
        """Check therapeutic permission based on type"""
        if not request.user.is_authenticated:
            return False
        
        # Check based on permission type
        if self.permission_type == 'create_encouragement':
            return self._can_create_encouragement(request.user)
        
        elif self.permission_type == 'share_reflection':
            return self._can_share_reflection(request.user)
        
        elif self.permission_type == 'request_support':
            return self._can_request_support(request.user)
        
        elif self.permission_type == 'lead_discussion':
            return self._can_lead_discussion(request.user)
        
        # Default: check emotional state
        return self._check_emotional_readiness(request.user)
    
    def _can_create_encouragement(self, user):
        """Check if user can create encouragement"""
        emotional_state = getattr(user, 'emotional_profile', 'balanced')
        
        # All states can encourage, but with different limits
        return True
    
    def _can_share_reflection(self, user):
        """Check if user can share reflections"""
        # Requires some therapeutic stability
        emotional_state = getattr(user, 'emotional_profile', 'balanced')
        
        if emotional_state == 'crisis':
            self.therapeutic_message = "Reflection may be difficult in crisis"
            self.gentle_suggestion = "Focus on immediate self-care first"
            return False
        
        return True
    
    def _can_request_support(self, user):
        """Check if user can request support"""
        # Check recent support requests
        from .models import GentleInteraction
        
        recent_requests = GentleInteraction.objects.filter(
            sender=user,
            interaction_type='support',
            created_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        # Therapeutic limit: 3 support requests per day
        if recent_requests >= 3:
            self.therapeutic_message = "Frequent support requests may need different approach"
            self.gentle_suggestion = "Consider professional support or different coping strategies"
            return False
        
        return True
    
    def _can_lead_discussion(self, user):
        """Check if user can lead discussions"""
        # Requires therapeutic stability and community trust
        emotional_state = getattr(user, 'emotional_profile', 'balanced')
        
        if emotional_state in ['crisis', 'overwhelmed']:
            self.therapeutic_message = "Leading requires emotional stability"
            self.gentle_suggestion = "Participate as a member until you feel more centered"
            return False
        
        # Check community standing
        from .models import GentleInteraction
        positive_contributions = GentleInteraction.objects.filter(
            sender=user,
            therapeutic_impact_score__gte=30
        ).count()
        
        return positive_contributions >= 10
    
    def _check_emotional_readiness(self, user):
        """Generic emotional readiness check"""
        emotional_state = getattr(user, 'emotional_profile', 'balanced')
        
        # Crisis mode has limited permissions
        if hasattr(user, 'crisis_mode') and getattr(user, 'crisis_mode', False):
            # In crisis, can only request support and view content
            allowed_actions = ['support_request', 'view_content']
            # This would need integration with view/action checking
            return True  # Simplified for example
        
        return True


# ============================================================================
# PERMISSION COMBINATIONS AND UTILITIES
# ============================================================================

class TherapeuticPermissionMixin:
    """
    Mixin to add therapeutic permission methods to views
    """
    
    def get_therapeutic_permissions(self):
        """Get therapeutic permissions for current request"""
        permissions = []
        
        # Add base permissions
        if self.request.user.is_authenticated:
            permissions.append('authenticated')
            
            # Add therapeutic state permissions
            emotional_state = getattr(self.request.user, 'emotional_profile', 'balanced')
            permissions.append(f'emotional_state_{emotional_state}')
            
            # Add community standing
            if self._has_therapeutic_standing():
                permissions.append('therapeutic_standing')
            
            # Add crisis mode if applicable
            if hasattr(self.request.user, 'crisis_mode') and getattr(self.request.user, 'crisis_mode', False):
                permissions.append('crisis_mode')
        
        return permissions
    
    def _has_therapeutic_standing(self):
        """Check if user has therapeutic standing"""
        from .models import GentleInteraction
        
        # Simplified check - in production would be more comprehensive
        positive_contributions = GentleInteraction.objects.filter(
            sender=self.request.user,
            therapeutic_impact_score__gte=20
        ).count()
        
        return positive_contributions >= 5
    
    def check_therapeutic_permission(self, permission_type):
        """Check specific therapeutic permission"""
        permission_checker = HasTherapeuticPermission(permission_type)
        return permission_checker.has_permission(self.request, self)


def therapeutic_permission_required(permission_type):
    """
    Decorator for requiring therapeutic permissions
    
    Usage:
    @therapeutic_permission_required('create_encouragement')
    def my_view(request):
        ...
    """
    def decorator(view_func):
        def wrapped_view(request, *args, **kwargs):
            permission_checker = HasTherapeuticPermission(permission_type)
            
            if not permission_checker.has_permission(request, None):
                # Return therapeutic denial response
                return JsonResponse({
                    'error': 'Therapeutic permission required',
                    'therapeutic_message': permission_checker.get_therapeutic_message(),
                    'gentle_suggestion': permission_checker.get_gentle_suggestion()
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator


# ============================================================================
# PERMISSION FACTORIES
# ============================================================================

class PermissionFactory:
    """
    Factory for creating therapeutic permission combinations
    """
    
    @staticmethod
    def for_gentle_interaction(action, interaction_type=None):
        """Get permissions for gentle interaction actions"""
        permissions = []
        
        if action == 'view':
            permissions = [IsAuthenticatedOrReadOnly, CanViewPrivateInteractions]
        elif action == 'create':
            permissions = [IsAuthenticated, CanCreateGentleInteraction]
            if interaction_type == 'anonymous':
                permissions.append(IsAnonymousAllowed)
        elif action == 'update':
            permissions = [IsAuthenticated, IsGentleInteractionOwner]
        elif action == 'delete':
            permissions = [IsAuthenticated, IsGentleInteractionOwner]
        elif action == 'moderate':
            permissions = [IsAuthenticated, CanModerateContent]
        
        return permissions
    
    @staticmethod
    def for_support_circle(action):
        """Get permissions for support circle actions"""
        permissions = []
        
        if action == 'view':
            permissions = [IsAuthenticatedOrReadOnly]
        elif action == 'create':
            permissions = [IsAuthenticated, CanCreateSupportCircle]
        elif action == 'join':
            permissions = [IsAuthenticated, CanJoinSupportCircle]
        elif action == 'manage':
            permissions = [IsAuthenticated, IsSupportCircleAdmin]
        elif action == 'participate':
            permissions = [IsAuthenticated, IsSupportCircleMember]
        
        return permissions
    
    @staticmethod
    def for_achievement(action):
        """Get permissions for achievement actions"""
        permissions = []
        
        if action == 'view':
            permissions = [AllowAny]
        elif action == 'earn':
            permissions = [IsAuthenticated, CanEarnAchievement]
        elif action == 'share':
            permissions = [IsAuthenticated, IsAchievementOwner]
        
        return permissions


# ============================================================================
# CUSTOM PERMISSION CLASSES FOR SPECIFIC VIEWS
# ============================================================================

class CanAccessTherapeuticAnalytics(TherapeuticBasePermission):
    """
    Permission to access therapeutic analytics and community metrics
    """
    
    therapeutic_message = "Analytics access requires community stewardship"
    gentle_suggestion = "Focus on personal therapeutic metrics instead"
    
    def _has_permission(self, request, view):
        """Check if user can access analytics"""
        if not request.user.is_authenticated:
            return False
        
        # Staff and moderators
        if request.user.is_staff or getattr(request.user, 'is_moderator', False):
            return True
        
        # Community elders with analytics role
        if self._is_analytics_elder(request.user):
            return True
        
        return False
    
    def _is_analytics_elder(self, user):
        """Check if user is an analytics elder"""
        from .models import GentleInteraction
        
        # Must be active for 6+ months
        if user.date_joined > timezone.now() - timedelta(days=180):
            return False
        
        # Must have high therapeutic impact
        high_impact_count = GentleInteraction.objects.filter(
            sender=user,
            therapeutic_impact_score__gte=50
        ).count()
        
        return high_impact_count >= 5


class CanSendDirectEncouragement(TherapeuticBasePermission):
    """
    Permission to send direct encouragement to specific users
    """
    
    therapeutic_message = "Direct encouragement requires relationship consideration"
    gentle_suggestion = "Consider community encouragement or ask if direct support is welcome"
    
    def _has_permission(self, request, view):
        """Check if user can send direct encouragement"""
        if not request.user.is_authenticated:
            return False
        
        # Check recipient privacy
        recipient_id = request.data.get('recipient_id')
        if recipient_id:
            from apps.users.models import TherapeuticUser
            try:
                recipient = TherapeuticUser.objects.get(id=recipient_id)
                if recipient.hide_progress:
                    return False
            except TherapeuticUser.DoesNotExist:
                return False
        
        # Check therapeutic pacing for direct encouragement
        recent_direct = GentleInteraction.objects.filter(
            sender=request.user,
            recipient__isnull=False,
            created_at__gte=timezone.now() - timedelta(days=1)
        ).count()
        
        # Therapeutic limit: 5 direct encouragements per day
        return recent_direct < 5


class CanPinCommunityContent(TherapeuticBasePermission):
    """
    Permission to pin important therapeutic content
    """
    
    therapeutic_message = "Pinning content requires community perspective"
    gentle_suggestion = "Consider bookmarking for yourself instead"
    
    def _has_object_permission(self, request, view, obj):
        """Check if user can pin content"""
        if not request.user.is_authenticated:
            return False
        
        # Staff and moderators
        if request.user.is_staff or getattr(request.user, 'is_moderator', False):
            return True
        
        # Circle leaders can pin in their circles
        if isinstance(obj, GentleInteraction):
            # Check if interaction is in a circle context
            # This would require additional model relationships
            pass
        
        # Community elders with pinning privilege
        if self._has_pinning_privilege(request.user):
            return True
        
        return False
    
    def _has_pinning_privilege(self, user):
        """Check if user has pinning privilege"""
        from .models import GentleInteraction, CircleMembership
        
        # Must be active for 3+ months
        if user.date_joined > timezone.now() - timedelta(days=90):
            return False
        
        # Must have consistently high therapeutic impact
        avg_impact = GentleInteraction.objects.filter(
            sender=user
        ).aggregate(avg=Avg('therapeutic_impact_score'))['avg'] or 0
        
        if avg_impact < 40:
            return False
        
        # Must be active in community
        recent_activity = GentleInteraction.objects.filter(
            sender=user,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        return recent_activity >= 10


# ============================================================================
# PERMISSION SETS FOR COMMON USE CASES
# ============================================================================

COMMUNITY_MEMBER_PERMISSIONS = [
    IsAuthenticated,
    IsTherapeuticCommunityMember
]

SUPPORT_CIRCLE_LEADER_PERMISSIONS = [
    IsAuthenticated,
    IsSupportCircleMember,
    IsSupportCircleAdmin
]

CONTENT_MODERATOR_PERMISSIONS = [
    IsAuthenticated,
    CanModerateContent
]

ANONYMOUS_SAFE_PERMISSIONS = [
    AllowAny,
    IsAnonymousAllowed
]

THERAPEUTIC_CREATOR_PERMISSIONS = [
    IsAuthenticated,
    CanCreateGentleInteraction,
    HasTherapeuticPermission
]


# ============================================================================
# PERMISSION UTILITIES
# ============================================================================

def check_therapeutic_access(user, resource_type, resource_id=None, action='view'):
    """
    Utility function to check therapeutic access programmatically
    
    Args:
        user: User object
        resource_type: Type of resource ('interaction', 'circle', 'achievement')
        resource_id: Optional resource ID for object-level check
        action: Action to perform ('view', 'create', 'update', 'delete')
    
    Returns:
        Tuple of (has_access, therapeutic_message, gentle_suggestion)
    """
    from .models import GentleInteraction, SupportCircle, UserAchievement
    
    # Map resource type to model
    resource_map = {
        'interaction': GentleInteraction,
        'circle': SupportCircle,
        'user_achievement': UserAchievement
    }
    
    if resource_type not in resource_map:
        return False, "Unknown resource type", "Check your request"
    
    model = resource_map[resource_type]
    
    # Get object if ID provided
    obj = None
    if resource_id:
        try:
            obj = model.objects.get(id=resource_id)
        except model.DoesNotExist:
            return False, "Resource not found", "The resource may have been removed"
    
    # Create appropriate permission checker
    if resource_type == 'interaction':
        if action == 'view':
            checker = CanViewPrivateInteractions()
        elif action == 'create':
            checker = CanCreateGentleInteraction()
        elif action in ['update', 'delete']:
            checker = IsGentleInteractionOwner()
        else:
            checker = TherapeuticBasePermission()
    
    elif resource_type == 'circle':
        if action == 'view':
            checker = IsSupportCircleMember()
        elif action == 'create':
            checker = CanCreateSupportCircle()
        elif action == 'join':
            checker = CanJoinSupportCircle()
        else:
            checker = IsSupportCircleAdmin()
    
    elif resource_type == 'user_achievement':
        checker = IsAchievementOwner()
    
    else:
        checker = TherapeuticBasePermission()
    
    # Check permission
    if obj:
        has_access = checker.has_object_permission(None, None, obj)
    else:
        has_access = checker.has_permission(None, None)
    
    return (
        has_access,
        checker.get_therapeutic_message(),
        checker.get_gentle_suggestion()
    )


def get_user_therapeutic_permissions(user):
    """
    Get comprehensive therapeutic permissions for a user
    
    Returns:
        Dict of permissions by category
    """
    permissions = {
        'community': {
            'can_view': True,  # Everyone can view public content
            'can_create': user.is_authenticated,
            'can_moderate': CanModerateContent().has_permission(None, None),
            'can_analytics': CanAccessTherapeuticAnalytics().has_permission(None, None)
        },
        'interactions': {
            'can_create': CanCreateGentleInteraction().has_permission(None, None) if user.is_authenticated else False,
            'can_anonymous': IsAnonymousAllowed().has_permission(None, None),
            'can_direct_encourage': CanSendDirectEncouragement().has_permission(None, None) if user.is_authenticated else False,
            'can_pin': CanPinCommunityContent().has_permission(None, None) if user.is_authenticated else False
        },
        'circles': {
            'can_create': CanCreateSupportCircle().has_permission(None, None) if user.is_authenticated else False,
            'can_join': True,  # Checked per circle
            'can_lead': False  # Would check per circle
        },
        'achievements': {
            'can_earn': CanEarnAchievement().has_permission(None, None) if user.is_authenticated else False,
            'can_share': user.is_authenticated  # Checked per achievement
        }
    }
    
    # Calculate therapeutic standing
    if user.is_authenticated:
        from .models import GentleInteraction
        positive_contributions = GentleInteraction.objects.filter(
            sender=user,
            therapeutic_impact_score__gte=30
        ).count()
        
        permissions['therapeutic_standing'] = {
            'has_standing': positive_contributions >= 5,
            'contribution_level': 'beginner' if positive_contributions < 5 else
                                'contributor' if positive_contributions < 20 else
                                'elder',
            'positive_contributions': positive_contributions
        }
    
    return permissions