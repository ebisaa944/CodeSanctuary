from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.cache import cache
import time

class TherapeuticAuthenticationBackend(ModelBackend):
    """Custom authentication backend with therapeutic considerations"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """Authenticate user with therapeutic checks"""
        UserModel = get_user_model()
        
        # Rate limiting for therapeutic safety
        if request:
            cache_key = f'auth_attempts_{request.META.get("REMOTE_ADDR")}'
            attempts = cache.get(cache_key, 0)
            
            if attempts >= 5:  # Max 5 attempts per 15 minutes
                # Log but don't block - gentle approach
                self._log_suspicious_activity(request, 'rate_limit')
                # Add delay for therapeutic pacing
                time.sleep(2)
            
            cache.set(cache_key, attempts + 1, 900)  # 15 minutes
        
        try:
            # Try username first (this handles username authentication)
            user = UserModel.objects.get(username=username)
        except UserModel.DoesNotExist:
            try:
                # Try email (this handles email authentication)
                user = UserModel.objects.get(email=username)
            except UserModel.DoesNotExist:
                # User doesn't exist with either username or email
                return None
            except UserModel.MultipleObjectsReturned:
                # Handle duplicate emails - take first active user
                users = UserModel.objects.filter(email=username, is_active=True)
                user = users.first() if users.exists() else None
                if not user:
                    return None
        except UserModel.MultipleObjectsReturned:
            # Handle duplicate usernames - take first active user
            users = UserModel.objects.filter(username=username, is_active=True)
            user = users.first() if users.exists() else None
            if not user:
                return None
        
        # At this point, user should be found or None
        if not user:
            return None
        
        # Check password
        if user.check_password(password):
            # Therapeutic checks
            if not user.is_active:
                self._log_suspicious_activity(request, 'inactive_account')
                return None
            
            # Check if account is locked for therapeutic reasons
            if hasattr(user, 'account_locked_until') and user.account_locked_until:
                from django.utils import timezone
                if timezone.now() < user.account_locked_until:
                    self._log_suspicious_activity(request, 'therapeutic_lock')
                    return None
            
            # Successful authentication
            self._log_successful_auth(user, request)
            return user
        
        # Failed password check
        self._log_failed_auth(user, request)
        return None
    
    def _log_successful_auth(self, user, request):
        """Log successful authentication"""
        import logging
        logger = logging.getLogger('therapeutic.auth')
        
        log_data = {
            'user_id': user.id,
            'username': user.username,
            'ip': request.META.get('REMOTE_ADDR') if request else None,
            'timestamp': time.time(),
            'event': 'successful_auth',
            'therapeutic_state': {
                'stress_level': getattr(user, 'current_stress_level', None),
                'gentle_mode': getattr(user, 'gentle_mode', None)
            }
        }
        
        logger.info(f"Therapeutic auth success: {log_data}")
    
    def _log_failed_auth(self, user, request):
        """Log failed authentication attempt"""
        import logging
        logger = logging.getLogger('therapeutic.auth')
        
        log_data = {
            'attempted_username': request.POST.get('username') if request else None,
            'ip': request.META.get('REMOTE_ADDR') if request else None,
            'timestamp': time.time(),
            'event': 'failed_auth'
        }
        
        logger.warning(f"Therapeutic auth failed: {log_data}")
        
        # Increment therapeutic lock counter
        if user and request:
            cache_key = f'failed_auth_{user.id}'
            failed_count = cache.get(cache_key, 0) + 1
            
            # Apply therapeutic lock after too many attempts
            if failed_count >= 10:
                from django.utils import timezone
                user.account_locked_until = timezone.now() + timezone.timedelta(minutes=30)
                user.save()
                logger.warning(f"Therapeutic lock applied for user {user.id}")
            
            cache.set(cache_key, failed_count, 3600)  # 1 hour window
    
    def _log_suspicious_activity(self, request, activity_type):
        """Log suspicious activity"""
        import logging
        logger = logging.getLogger('therapeutic.security')
        
        log_data = {
            'ip': request.META.get('REMOTE_ADDR') if request else None,
            'activity': activity_type,
            'timestamp': time.time(),
            'user_agent': request.META.get('HTTP_USER_AGENT') if request else None
        }
        
        logger.warning(f"Therapeutic suspicious activity: {log_data}")


class GentleSessionBackend:
    """Backend for managing gentle sessions"""
    
    def create_session(self, request, user):
        """Create a therapeutic session"""
        # Set gentle session timeout
        if getattr(user, 'gentle_mode', False):
            request.session.set_expiry(1209600)  # 14 days for gentle mode
        else:
            request.session.set_expiry(604800)   # 7 days for standard
        
        # Add therapeutic session data
        request.session['therapeutic'] = {
            'user_id': user.id,
            'gentle_mode': getattr(user, 'gentle_mode', False),
            'stress_level': getattr(user, 'current_stress_level', 5),
            'session_start': time.time()
        }
        
        # Add gentle flags
        request.session['requires_gentle_pacing'] = getattr(user, 'gentle_mode', False)
        
        return True
    
    def validate_session(self, request):
        """Validate therapeutic session"""
        therapeutic_data = request.session.get('therapeutic', {})
        
        if not therapeutic_data:
            return False
        
        # Check session age for gentle mode
        session_start = therapeutic_data.get('session_start', 0)
        session_age = time.time() - session_start
        
        if therapeutic_data.get('gentle_mode', False) and session_age > 7200:  # 2 hours
            # Suggest break for gentle mode users
            request.session['suggest_break'] = True
        
        return True
    
    def end_session(self, request):
        """End therapeutic session gracefully"""
        therapeutic_data = request.session.get('therapeutic', {})
        
        if therapeutic_data:
            # Log session end
            import logging
            logger = logging.getLogger('therapeutic.sessions')
            
            session_duration = time.time() - therapeutic_data.get('session_start', time.time())
            
            log_data = {
                'user_id': therapeutic_data.get('user_id'),
                'duration': session_duration,
                'gentle_mode': therapeutic_data.get('gentle_mode', False),
                'stress_level': therapeutic_data.get('stress_level', 5)
            }
            
            logger.info(f"Therapeutic session ended: {log_data}")
        
        # Clear therapeutic session data
        if 'therapeutic' in request.session:
            del request.session['therapeutic']
        
        return True


class StressAwareBackend:
    """Backend that adjusts based on user's stress level"""
    
    def get_user_permissions(self, user, obj=None):
        """Get permissions adjusted for stress level"""
        from django.contrib.auth.models import Permission
        
        permissions = set()
        
        # Base permissions
        if user.is_active:
            # Get all permissions user has via groups
            for group in user.groups.all():
                permissions.update(group.permissions.all())
            
            # Get all permissions user has directly
            permissions.update(user.user_permissions.all())
        
        # Therapeutic adjustments
        if hasattr(user, 'current_stress_level'):
            stress = user.current_stress_level
            
            # Limit permissions for high-stress users
            if stress >= 8:
                # Remove complex permissions
                permissions = {p for p in permissions if not self._is_complex_permission(p)}
            
            # Add gentle permissions for gentle mode
            if getattr(user, 'gentle_mode', False):
                permissions.add(self._get_gentle_permission())
        
        return permissions
    
    def _is_complex_permission(self, permission):
        """Check if permission is complex (should be limited during high stress)"""
        complex_codenames = [
            'add', 'change', 'delete', 'publish', 'approve',
            'manage', 'configure', 'admin'
        ]
        
        return any(codename in permission.codename for codename in complex_codenames)
    
    def _get_gentle_permission(self):
        """Get special gentle permission"""
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        
        # This would need to be created in your database
        # For now, return a mock permission
        class MockPermission:
            codename = 'use_gentle_features'
            name = 'Can use gentle features'
        
        return MockPermission()