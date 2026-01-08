from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


class NoCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        # Add no-cache headers to all responses
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware to add security headers to all responses.
    Helps protect against common web vulnerabilities.
    """
    def process_response(self, request, response):
        # Prevent MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response['X-Frame-Options'] = 'SAMEORIGIN'
        
        # XSS Protection (legacy browsers)
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (restrict certain browser features)
        response['Permissions-Policy'] = 'geolocation=(self), microphone=(), camera=()'
        
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all requests for auditing purposes.
    Useful for debugging and security monitoring.
    """
    def process_request(self, request):
        # Log request details (only for authenticated users to avoid spam)
        if request.user.is_authenticated:
            logger.info(
                f"Request: {request.method} {request.path} | "
                f"User: {request.user.username} | "
                f"IP: {self.get_client_ip(request)}"
            )
    
    def get_client_ip(self, request):
        """Get the real client IP, handling proxy servers."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')


class ErrorHandlingMiddleware(MiddlewareMixin):
    """
    Middleware to catch and handle unexpected errors gracefully.
    Logs errors and returns user-friendly responses.
    """
    def process_exception(self, request, exception):
        # Log the error with full details
        logger.error(
            f"Unhandled exception: {type(exception).__name__}: {str(exception)} | "
            f"Path: {request.path} | "
            f"User: {request.user.username if request.user.is_authenticated else 'anonymous'} | "
            f"IP: {request.META.get('REMOTE_ADDR', 'unknown')}",
            exc_info=True
        )
        
        # For AJAX requests, return JSON error
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'error': True,
                'message': 'An unexpected error occurred. Please try again later.'
            }, status=500)
        
        # For regular requests, let Django's error handling take over
        return None