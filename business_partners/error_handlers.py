import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, APIException
from django.core.exceptions import ValidationError as DjangoValidationError
from functools import wraps
import traceback

logger = logging.getLogger(__name__)


class VendorAPIErrorHandler:
    """Centralized error handling for vendor API operations."""
    
    @staticmethod
    def handle_validation_error(exception, field=None):
        """Handle validation errors with detailed field information."""
        error_data = {
            'error_type': 'validation_error',
            'message': str(exception),
            'field': field,
            'error_code': 'VALIDATION_ERROR'
        }
        logger.warning(f"Validation error: {error_data}")
        return error_data
    
    @staticmethod
    def handle_permission_error(user, action):
        """Handle permission-related errors."""
        error_data = {
            'error_type': 'permission_denied',
            'message': f"User '{user}' does not have permission to {action}",
            'user': str(user),
            'action': action,
            'error_code': 'PERMISSION_DENIED'
        }
        logger.warning(f"Permission denied: {error_data}")
        return error_data
    
    @staticmethod
    def handle_not_found_error(resource, resource_id):
        """Handle resource not found errors."""
        error_data = {
            'error_type': 'not_found',
            'message': f"{resource} with ID {resource_id} not found",
            'resource': resource,
            'resource_id': resource_id,
            'error_code': 'NOT_FOUND'
        }
        logger.warning(f"Resource not found: {error_data}")
        return error_data
    
    @staticmethod
    def handle_database_error(exception, operation=None):
        """Handle database-related errors."""
        error_data = {
            'error_type': 'database_error',
            'message': 'A database error occurred',
            'operation': operation,
            'error_code': 'DATABASE_ERROR',
            'details': str(exception) if settings.DEBUG else None
        }
        logger.error(f"Database error during {operation}: {str(exception)}", exc_info=True)
        return error_data
    
    @staticmethod
    def handle_workflow_error(exception, workflow_state=None):
        """Handle workflow-related errors."""
        error_data = {
            'error_type': 'workflow_error',
            'message': f"Workflow error: {str(exception)}",
            'workflow_state': workflow_state,
            'error_code': 'WORKFLOW_ERROR'
        }
        logger.error(f"Workflow error: {error_data}", exc_info=True)
        return error_data


def create_error_response(message, error_code=None, status_code=status.HTTP_400_BAD_REQUEST, details=None):
    """Create a standardized error response."""
    response_data = {
        'success': False,
        'error': {
            'message': message,
            'error_code': error_code or 'GENERIC_ERROR',
            'details': details
        }
    }
    return Response(response_data, status=status_code)


def create_validation_error_response(message, field_errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """Create a standardized validation error response."""
    response_data = {
        'success': False,
        'error': {
            'message': message,
            'error_code': 'VALIDATION_ERROR',
            'field_errors': field_errors or {}
        }
    }
    return Response(response_data, status=status_code)


def create_success_response(message, data=None, status_code=status.HTTP_200_OK):
    """Create a standardized success response."""
    response_data = {
        'success': True,
        'message': message,
        'data': data or {}
    }
    return Response(response_data, status=status_code)


def handle_vendor_api_errors(func):
    """Decorator to handle common vendor API errors."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
            
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {str(e)}")
            return create_validation_error_response(
                'Validation failed',
                field_errors=e.detail if hasattr(e, 'detail') else None
            )
            
        except DjangoValidationError as e:
            logger.warning(f"Django validation error in {func.__name__}: {str(e)}")
            return create_validation_error_response(
                'Validation failed',
                field_errors={'general': str(e)}
            )
            
        except PermissionError as e:
            logger.warning(f"Permission error in {func.__name__}: {str(e)}")
            return create_error_response(
                'Permission denied',
                error_code='PERMISSION_DENIED',
                status_code=status.HTTP_403_FORBIDDEN
            )
            
        except APIException as e:
            logger.error(f"API exception in {func.__name__}: {str(e)}")
            return create_error_response(
                str(e),
                error_code='API_ERROR',
                status_code=e.status_code if hasattr(e, 'status_code') else status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            error_message = str(e) if settings.DEBUG else 'An unexpected error occurred'
            return create_error_response(
                error_message,
                error_code='INTERNAL_ERROR',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                details=traceback.format_exc() if settings.DEBUG else None
            )
    
    return wrapper


# Import settings at the end to avoid circular imports
from django.conf import settings