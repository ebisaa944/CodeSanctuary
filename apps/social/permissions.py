from rest_framework import permissions

class GentleInteractionPermission(permissions.BasePermission):
    """
    Permissions for gentle interactions.
    Respects visibility settings and therapeutic rules.
    """
    
    def has_object_permission(self, request, view, obj):
        # Staff can see everything
        if request.user.is_staff:
            return True
        
        # Check if user can see this interaction
        if not obj.can_user_see(request.user):
            return False
        
        # For modifications/deletions
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            # Only sender (if not anonymous) or staff can modify
            if obj.sender and obj.sender != request.user:
                return False
        
        return True
    
    def has_permission(self, request, view):
        # Anyone can create interactions if authenticated
        if request.method == 'POST':
            return request.user.is_authenticated
        
        return True


class SupportCirclePermission(permissions.BasePermission):
    """
    Permissions for support circles.
    """
    
    def has_object_permission(self, request, view, obj):
        # Staff can do everything
        if request.user.is_staff:
            return True
        
        # For public circles, anyone can view
        if request.method in permissions.SAFE_METHODS:
            if obj.is_public:
                return True
            # Private circles require membership
            return obj.memberships.filter(user=request.user).exists()
        
        # For modifications, need to be creator or leader
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if obj.created_by == request.user:
                return True
            
            # Check if user is a circle leader
            membership = obj.memberships.filter(user=request.user).first()
            return membership and membership.role == 'leader'
        
        return False


class CircleMembershipPermission(permissions.BasePermission):
    """
    Permissions for circle memberships.
    """
    
    def has_object_permission(self, request, view, obj):
        # Staff can do everything
        if request.user.is_staff:
            return True
        
        # Users can view their own memberships
        if request.method in permissions.SAFE_METHODS:
            return obj.user == request.user
        
        # For modifications, user can update their own membership
        if request.method in ['PUT', 'PATCH']:
            return obj.user == request.user
        
        # For deletions, user can leave or leader can remove
        if request.method == 'DELETE':
            if obj.user == request.user:
                return True  # User can leave
            
            # Check if requester is circle leader
            circle_leader = obj.circle.memberships.filter(
                user=request.user,
                role='leader'
            ).exists()
            return circle_leader
        
        return False


class AchievementPermission(permissions.BasePermission):
    """
    Permissions for achievements.
    Read-only for everyone, write for staff.
    """
    
    def has_permission(self, request, view):
        # Everyone can read
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only staff can create/edit/delete
        return request.user.is_staff


class UserAchievementPermission(permissions.BasePermission):
    """
    Permissions for user achievements.
    """
    
    def has_object_permission(self, request, view, obj):
        # Staff can see everything
        if request.user.is_staff:
            return True
        
        # Users can only see their own achievements
        return obj.user == request.user
    
    def has_permission(self, request, view):
        # Users can create achievements (when earned)
        if request.method == 'POST':
            return request.user.is_authenticated
        
        return True


class CommunityModerationPermission(permissions.BasePermission):
    """
    Permissions for community moderation.
    Staff only for moderation actions.
    """
    
    def has_permission(self, request, view):
        # Check if this is a moderation action
        is_moderation_action = getattr(view, 'is_moderation_action', False)
        
        if is_moderation_action:
            return request.user.is_staff
        
        return True