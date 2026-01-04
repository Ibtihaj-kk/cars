"""
ISO 27001 & NIST Compliant Custom Exceptions
Enterprise-grade exception hierarchy for security and authentication systems
"""

class AuthenticationError(Exception):
    """Base authentication error with NIST-compliant error codes"""
    def __init__(self, message="Authentication failed", code="AUTH_001", details=None):
        self.code = code
        self.details = details or {}
        super().__init__(f"{message} (Code: {code})")


class RateLimitExceededError(AuthenticationError):
    """Rate limiting violation - NIST AC-7"""
    def __init__(self, message="Rate limit exceeded", retry_after=None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, "RATE_001", details)


class CircuitBreakerOpenError(AuthenticationError):
    """Circuit breaker is open - NIST SC-5"""
    def __init__(self, message="Service temporarily unavailable", retry_after=300):
        details = {"retry_after": retry_after}
        super().__init__(message, "CIRCUIT_001", details)


class SecurityViolationError(AuthenticationError):
    """Security policy violation - NIST AC-2, AC-3"""
    def __init__(self, message="Security policy violation", violation_type=None):
        details = {"violation_type": violation_type} if violation_type else {}
        super().__init__(message, "SECURITY_001", details)


class DatabaseConnectionError(AuthenticationError):
    """Database connection failure - NIST SC-36"""
    def __init__(self, message="Database connection failed", service=None):
        details = {"service": service} if service else {}
        super().__init__(message, "DB_001", details)


class InvalidCredentialsError(AuthenticationError):
    """Invalid username/password combination"""
    def __init__(self, message="Invalid credentials"):
        super().__init__(message, "CREDENTIALS_001")


class AccountLockedError(AuthenticationError):
    """Account is locked due to multiple failed attempts"""
    def __init__(self, message="Account temporarily locked", unlock_time=None):
        details = {"unlock_time": unlock_time} if unlock_time else {}
        super().__init__(message, "LOCKED_001", details)


class SessionExpiredError(AuthenticationError):
    """User session has expired"""
    def __init__(self, message="Session expired"):
        super().__init__(message, "SESSION_001")


class PermissionDeniedError(AuthenticationError):
    """User lacks required permissions"""
    def __init__(self, message="Permission denied", required_permissions=None):
        details = {"required_permissions": required_permissions} if required_permissions else {}
        super().__init__(message, "PERMISSION_001", details)


class ConfigurationError(Exception):
    """System configuration error"""
    def __init__(self, message="Configuration error", component=None):
        details = {"component": component} if component else {}
        super().__init__(f"{message} (Component: {component})")


class AuditLogError(Exception):
    """Audit logging failure"""
    def __init__(self, message="Audit logging failed", log_data=None):
        details = {"log_data": log_data} if log_data else {}
        super().__init__(f"{message} - {details}")