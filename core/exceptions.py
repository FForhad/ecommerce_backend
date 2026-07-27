from rest_framework.views import exception_handler
from rest_framework.response import Response
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """Custom exception handler for consistent error responses"""
    
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    if response is not None:
        return response
    
    # Handle Django ValidationError
    if isinstance(exc, ValidationError):
        return Response({
            'error': str(exc)
        }, status=400)
    
    # Handle generic exceptions
    logger.error(f"Unhandled exception: {str(exc)}")
    return Response({
        'error': 'An unexpected error occurred'
    }, status=500)