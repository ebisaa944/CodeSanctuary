from rest_framework import permissions
from rest_framework.permissions import BasePermission

class IsTherapeuticUserOwner(BasePermission):
    """
    Custom permission to only allow owners or staff to access therapeutic user data.
    Respects gentle_mode and privacy settings.
    """
    
    def has_object_permission(self, request, view, obj):
        # Staff can see everything
        if request.user.is_staff:
            return True
        
        # Users can always see themselves
        if obj == request.user:
            return True
        
        # For other users, respect privacy settings
        if obj.hide_progress:
            return False
        
        # Gentle mode users might share less
        if obj.gentle_mode and not request.user.gentle_mode:
            return False
        
        return True


class GentleModePermission(BasePermission):
    """
    Permission that respects gentle_mode settings.
    Some features are only available in gentle_mode.
    """
    
    def has_permission(self, request, view):
        # Some views require gentle_mode
        require_gentle = getattr(view, 'require_gentle_mode', False)
        
        if require_gentle and not request.user.gentle_mode:
            return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        # For user objects, check gentle_mode compatibility
        if hasattr(obj, 'gentle_mode'):
            # Users in gentle_mode might not want intense interactions
            if obj.gentle_mode and request.method in ['POST', 'PUT', 'PATCH']:
                # Check if the action is gentle enough
                is_gentle_action = getattr(view, 'is_gentle_action', False)
                if not is_gentle_action:
                    return False
        
        return True


class TherapeuticAccessPermission(BasePermission):
    """
    Permission based on therapeutic state.
    High-stress users get limited access.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return True
        
        # High-stress users get limited access
        if hasattr(request.user, 'current_stress_level'):
            stress = request.user.current_stress_level
            
            if stress >= 9:
                # Very high stress - only basic access
                allowed_actions = ['retrieve', 'list']
                if view.action not in allowed_actions:
                    return False
            
            elif stress >= 7:
                # High stress - no creation/modification
                if view.action in ['create', 'update', 'partial_update', 'destroy']:
                    return False
        
        return True


class AnonymousGentlePermission(BasePermission):
    """
    Allow anonymous access to gentle features only.
    """
    
    def has_permission(self, request, view):
        # Check if view allows anonymous access
        allow_anonymous = getattr(view, 'allow_anonymous', False)
        
        if not request.user.is_authenticated and not allow_anonymous:
            return False
        
        return True