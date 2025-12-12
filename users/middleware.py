from django.utils import timezone
from django.core.cache import cache
import time

class TherapeuticMiddleware:
    """Middleware for therapeutic request handling"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Start timing for gentle response
        start_time = time.time()
        
        # Add therapeutic context to request
        request.is_therapeutic = True
        request.gentle_mode = False
        
        # Check if user is authenticated and has gentle mode
        if request.user.is_authenticated and hasattr(request.user, 'gentle_mode'):
            request.gentle_mode = request.user.gentle_mode
        
        # Process the request
        response = self.get_response(request)
        
        # Check if response is a proper HTTP response before adding headers
        if hasattr(response, '__setitem__'):
            # Add therapeutic headers
            response['X-Therapeutic-Mode'] = str(request.gentle_mode).lower()
            response['X-Request-Gentle'] = 'true'
            
            # Add timing information for gentle pacing
            processing_time = time.time() - start_time
            if processing_time > 2.0 and request.gentle_mode:
                response['X-Gentle-Warning'] = f'Slow response ({processing_time:.2f}s)'
        
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Process view with therapeutic considerations"""
        
        # Skip for static/media files
        if request.path.startswith(('/static/', '/media/', '/admin/')):
            return None
        
        # Add therapeutic rate limiting for high-stress users
        if request.user.is_authenticated and hasattr(request.user, 'current_stress_level'):
            if request.user.current_stress_level >= 8:
                cache_key = f'gentle_limit_{request.user.id}_{request.path}'
                request_count = cache.get(cache_key, 0)
                
                if request_count >= 5:  # Max 5 requests per minute for high stress
                    from django.http import JsonResponse
                    return JsonResponse({
                        'error': 'gentle_limit',
                        'message': 'Please take a break. Too many requests in a short time.',
                        'suggestion': 'Try some deep breathing exercises'
                    }, status=429)
                
                cache.set(cache_key, request_count + 1, 60)  # 1 minute window
        
        return None
    
    def process_exception(self, request, exception):
        """Handle exceptions therapeutically"""
        # Log the exception
        import logging
        logger = logging.getLogger('therapeutic')
        logger.error(f"Therapeutic exception: {exception}")
        
        # Return gentle error response
        from django.http import JsonResponse
        return JsonResponse({
            'error': 'gentle_error',
            'message': 'Something went wrong gently',
            'suggestion': 'Take a deep breath and try again',
            'technical': str(exception) if request.user.is_staff else None
        }, status=500)


class StressAwareMiddleware:
    """Middleware that adjusts based on user's stress level"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Add stress-aware headers if user is authenticated AND response supports headers
        if (request.user.is_authenticated and 
            hasattr(request.user, 'current_stress_level') and
            hasattr(response, '__setitem__')):
            
            stress = request.user.current_stress_level
            
            # Add stress level to response
            response['X-User-Stress-Level'] = str(stress)
            
            # Add gentle suggestions based on stress
            if stress >= 7:
                response['X-Gentle-Suggestion'] = 'high-stress-mode'
            elif stress >= 5:
                response['X-Gentle-Suggestion'] = 'take-it-slow'
        
        return response


class GentleResponseMiddleware:
    """Middleware for gentle response formatting"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def process_template_response(self, request, response):
        """Add therapeutic context to template responses"""
        if hasattr(response, 'context_data'):
            # Add therapeutic context
            response.context_data['is_therapeutic'] = True
            
            # Add gentle mode status
            if request.user.is_authenticated and hasattr(request.user, 'gentle_mode'):
                response.context_data['gentle_mode'] = request.user.gentle_mode
            
            # Add stress level for conditional rendering
            if request.user.is_authenticated and hasattr(request.user, 'current_stress_level'):
                response.context_data['stress_level'] = request.user.current_stress_level
            
            # Add therapeutic messages
            response.context_data['therapeutic_messages'] = self._get_messages(request)
        
        return response
    
    def _get_messages(self, request):
        """Get therapeutic messages based on context"""
        messages = []
        
        if request.user.is_authenticated:
            # Time-based messages
            hour = timezone.now().hour
            if 5 <= hour < 12:
                messages.append("Good morning! Remember to start gently.")
            elif 12 <= hour < 17:
                messages.append("Good afternoon. How are you feeling?")
            elif 17 <= hour < 22:
                messages.append("Good evening. Time to wind down gently.")
            
            # Activity-based messages
            last_login = request.user.last_login
            if last_login:
                days_since = (timezone.now() - last_login).days
                if days_since > 1:
                    messages.append(f"Welcome back after {days_since} days!")
        
        return messages