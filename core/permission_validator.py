"""
Permission Validator for Role-Based Access
"""
import logging
from .role_routing_engine import RoleRoutingEngine

logger = logging.getLogger('security')

class PermissionValidator:
    """Validator for role-based access permissions"""
    
    def __init__(self):
        self.routing_engine = RoleRoutingEngine()
    
    def validate_role_access(self, user, role):
        """
        Validate if user has access to the specified role
        """
        if not user or not user.is_authenticated:
            # Guest role logic might be handled differently, but generally requires no auth
            if role == 'guest':
                return not user.is_authenticated
            return False
            
        role_config = self.routing_engine.ROLE_ROUTING_MAP.get(role)
        if not role_config:
            logger.warning(f"No configuration found for role: {role}")
            return False
            
        try:
            return role_config['permissions'](user)
        except Exception as e:
            logger.error(f"Error validating access for role {role}: {str(e)}")
            return False
