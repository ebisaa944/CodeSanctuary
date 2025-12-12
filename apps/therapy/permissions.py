from rest_framework import permissions

class EmotionalCheckInPermission(permissions.BasePermission):
    """
    Permissions for emotional checkins.
    Users can only access their own checkins unless they're staff.
    """
    
    def has_object_permission(self, request, view, obj):
        # Staff can see everything
        if request.user.is_staff:
            return True
        
        # Users can only see their own checkins
        return obj.user == request.user
    
    def has_permission(self, request, view):
        # Anyone can create checkins if authenticated
        if request.method == 'POST':
            return request.user.is_authenticated
        
        # For list views, filter by user in queryset
        return True


class CopingStrategyPermission(permissions.BasePermission):
    """
    Permissions for coping strategies.
    Read-only for everyone, write for staff.
    """
    
    def has_permission(self, request, view):
        # Everyone can read
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only staff can create/edit/delete
        return request.user.is_staff


class TherapeuticInsightPermission(permissions.BasePermission):
    """
    Permissions for therapeutic insights.
    Requires gentle_mode for some insights.
    """
    
    def has_permission(self, request, view):
        # Check if view requires gentle_mode
        require_gentle = getattr(view, 'require_gentle_mode', False)
        
        if require_gentle and not getattr(request.user, 'gentle_mode', False):
            return False
        
        return request.user.is_authenticated