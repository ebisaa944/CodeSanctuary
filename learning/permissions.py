from rest_framework import permissions

class ActivityAccessPermission(permissions.BasePermission):
    """
    Permissions for activity access.
    Respects user's therapeutic state and gentle mode.
    """
    
    def has_permission(self, request, view):
        # Everyone can view published activities
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only staff can create/edit/delete
        return request.user.is_staff
    
    def has_object_permission(self, request, view, obj):
        # Check if activity is suitable for user
        if request.method in ['POST', 'PUT', 'PATCH']:
            if not request.user.is_staff:
                return False
        
        # For GET requests, check therapeutic suitability
        if request.method == 'GET' and request.user.is_authenticated:
            suitable, message = obj.is_suitable_for_user(request.user)
            if not suitable and not request.user.is_staff:
                # Still allow access but might show warning
                view.therapeutic_warning = message
        
        return True


class UserProgressPermission(permissions.BasePermission):
    """
    Permissions for user progress.
    Users can only access their own progress.
    """
    
    def has_object_permission(self, request, view, obj):
        # Staff can see everything
        if request.user.is_staff:
            return True
        
        # Users can only see their own progress
        return obj.user == request.user
    
    def has_permission(self, request, view):
        # Anyone can create progress if authenticated
        if request.method == 'POST':
            return request.user.is_authenticated
        
        # For list views, filter by user in queryset
        return True


class LearningPathPermission(permissions.BasePermission):
    """
    Permissions for learning paths.
    Read for everyone, write for staff.
    """
    
    def has_permission(self, request, view):
        # Everyone can read
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Only staff can create/edit/delete
        return request.user.is_staff


class TherapeuticSubmissionPermission(permissions.BasePermission):
    """
    Permissions for activity submissions.
    Limits submissions based on therapeutic state.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check user's therapeutic state
        if hasattr(request.user, 'current_stress_level'):
            stress = request.user.current_stress_level
            
            # Very high stress - limit submissions
            if stress >= 9:
                # Check submission frequency
                from .models import UserProgress
                from django.utils import timezone
                from django.db.models import Count
                
                today = timezone.now().date()
                today_submissions = UserProgress.objects.filter(
                    user=request.user,
                    updated_at__date=today
                ).count()
                
                if today_submissions >= 3:
                    return False
        
        return True