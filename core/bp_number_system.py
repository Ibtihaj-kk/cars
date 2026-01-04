"""
ISO 8000 Compliant Universal Business Partner Number System
Enterprise-grade BP number generation and management following international standards
"""
import logging
import re
from datetime import datetime
from django.db import models, transaction, DatabaseError
from django.core.cache import cache
from django.conf import settings
from django.utils.crypto import get_random_string

logger = logging.getLogger('security')


class BPNumberSystem:
    """ISO 8000 compliant business partner identification system"""
    
    # ISO 8000 compliant BP number format
    BP_NUMBER_FORMAT = "BP-{country_code}-{entity_type}-{sequence:08d}"
    BP_NUMBER_REGEX = r"^BP-[A-Z]{2}-[A-Z]{3}-\d{8}$"
    
    # Entity type mapping following ISO 8000 standards
    ENTITY_TYPES = {
        'SYS': 'System',           # System entities (super admins, system accounts)
        'ADM': 'Administrative',   # Administrative entities
        'VEN': 'Vendor',           # Vendor entities
        'CUS': 'Customer',         # Customer entities
        'PAR': 'Partner',          # Business partners
        'EMP': 'Employee',         # Employee entities
        'IND': 'Individual',       # Individual users
    }
    
    # Country code mapping (ISO 3166-1 alpha-2)
    COUNTRY_CODES = {
        'SA': 'Saudi Arabia',
        'US': 'United States',
        'UK': 'United Kingdom',
        'AE': 'United Arab Emirates',
        'IN': 'India',
        'PK': 'Pakistan',
        'EG': 'Egypt',
        # Add more countries as needed
    }
    
    def __init__(self):
        self.sequence_generator = AtomicSequenceGenerator()
        self.country_mapper = CountryCodeMapper()
        self.audit_logger = None  # Will be injected
    
    def generate_bp_number(self, user, entity_type='IND'):
        """
        Generate ISO 8000 compliant BP number
        """
        try:
            # Validate entity type
            if entity_type not in self.ENTITY_TYPES:
                raise InvalidEntityTypeError(f"Invalid entity type: {entity_type}")
            
            # Get country code based on user location
            country_code = self.country_mapper.get_country_code(user)
            
            # Get next sequence number
            sequence = self.sequence_generator.get_next_sequence()
            
            # Generate BP number
            bp_number = self.BP_NUMBER_FORMAT.format(
                country_code=country_code,
                entity_type=entity_type,
                sequence=sequence
            )
            
            # Validate generated BP number
            if not self.validate_bp_number_format(bp_number):
                raise BPNumberGenerationError("Generated BP number format validation failed")
            
            # Log BP number generation
            self._log_bp_number_generation(user, bp_number, entity_type)
            
            return bp_number
            
        except DatabaseError as e:
            logger.error(f"Database error during BP number generation: {str(e)}")
            # Fallback to emergency BP number generation
            return self._generate_emergency_bp_number(user, entity_type)
        except Exception as e:
            logger.error(f"Unexpected error during BP number generation: {str(e)}")
            raise BPNumberGenerationError(f"BP number generation failed: {str(e)}")
    
    def validate_bp_number_format(self, bp_number):
        """Validate BP number format against ISO 8000 standards"""
        return re.match(self.BP_NUMBER_REGEX, bp_number) is not None
    
    def parse_bp_number(self, bp_number):
        """Parse BP number into its components"""
        if not self.validate_bp_number_format(bp_number):
            raise InvalidBPNumberError(f"Invalid BP number format: {bp_number}")
        
        try:
            # BP-{country_code}-{entity_type}-{sequence}
            parts = bp_number.split('-')
            return {
                'country_code': parts[1],
                'entity_type': parts[2],
                'sequence': int(parts[3]),
                'full_number': bp_number
            }
        except (IndexError, ValueError) as e:
            raise InvalidBPNumberError(f"Failed to parse BP number: {str(e)}")
    
    def ensure_bp_number(self, user):
        """
        Ensure user has a valid BP number
        Creates one if it doesn't exist
        """
        try:
            # Check if user already has BP number
            if hasattr(user, 'business_partner') and user.business_partner.bp_number:
                bp_number = user.business_partner.bp_number
                if self.validate_bp_number_format(bp_number):
                    return bp_number
                else:
                    # Existing BP number is invalid - regenerate
                    logger.warning(f"Invalid BP number found for user {user.id}, regenerating")
                    return self._regenerate_bp_number(user)
            
            # User doesn't have BP number - create one
            entity_type = self._determine_entity_type(user)
            bp_number = self.generate_bp_number(user, entity_type)
            
            # Create or update business partner record
            self._create_business_partner(user, bp_number, entity_type)
            
            return bp_number
            
        except Exception as e:
            logger.error(f"Error ensuring BP number for user {user.id}: {str(e)}")
            # Emergency fallback
            return self._generate_emergency_bp_number(user, 'IND')
    
    def _determine_entity_type(self, user):
        """Determine entity type based on user role and attributes"""
        if user.is_superuser:
            return 'SYS'
        elif user.is_staff:
            return 'ADM'
        elif hasattr(user, 'vendor_profile') and user.vendor_profile:
            return 'VEN'
        else:
            return 'IND'  # Individual customer
    
    def _create_business_partner(self, user, bp_number, entity_type):
        """Create or update business partner record"""
        from business_partners.models import BusinessPartner
        
        try:
            with transaction.atomic():
                business_partner, created = BusinessPartner.objects.get_or_create(
                    user=user,
                    defaults={
                        'bp_number': bp_number,
                        'name': user.get_full_name() or user.email,
                        'type': self._get_bp_type_from_entity(entity_type),
                        'status': 'active',
                        'entity_type': entity_type
                    }
                )
                
                if not created:
                    # Update existing business partner
                    business_partner.bp_number = bp_number
                    business_partner.entity_type = entity_type
                    business_partner.save()
                
                return business_partner
                
        except Exception as e:
            logger.error(f"Error creating business partner for user {user.id}: {str(e)}")
            raise
    
    def _get_bp_type_from_entity(self, entity_type):
        """Map entity type to business partner type"""
        type_mapping = {
            'SYS': 'system',
            'ADM': 'company',
            'VEN': 'company',
            'CUS': 'individual',
            'PAR': 'company',
            'EMP': 'individual',
            'IND': 'individual'
        }
        return type_mapping.get(entity_type, 'individual')
    
    def _regenerate_bp_number(self, user):
        """Regenerate BP number for user"""
        entity_type = self._determine_entity_type(user)
        bp_number = self.generate_bp_number(user, entity_type)
        
        # Update business partner record
        if hasattr(user, 'business_partner'):
            user.business_partner.bp_number = bp_number
            user.business_partner.entity_type = entity_type
            user.business_partner.save()
        else:
            self._create_business_partner(user, bp_number, entity_type)
        
        return bp_number
    
    def _generate_emergency_bp_number(self, user, entity_type):
        """Generate emergency BP number when primary system fails"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_suffix = get_random_string(4, '0123456789')
        
        emergency_bp = f"EMG-{entity_type}-{timestamp}-{random_suffix}"
        
        logger.warning(f"Generated emergency BP number for user {user.id}: {emergency_bp}")
        
        return emergency_bp
    
    def _log_bp_number_generation(self, user, bp_number, entity_type):
        """Log BP number generation for audit purposes"""
        if self.audit_logger:
            self.audit_logger.log_bp_number_generation(user, bp_number, entity_type)


class AtomicSequenceGenerator:
    """Thread-safe atomic sequence generator"""
    
    def __init__(self):
        self.sequence_key = 'bp_sequence_counter'
    
    def get_next_sequence(self):
        """Get next sequence number atomically"""
        try:
            with transaction.atomic():
                # Use database sequence or atomic counter
                from django.db.models import F
                from .models import SequenceCounter
                
                counter, created = SequenceCounter.objects.get_or_create(
                    name='bp_sequence',
                    defaults={'value': 1}
                )
                
                if not created:
                    counter.value = F('value') + 1
                    counter.save()
                    counter.refresh_from_db()
                
                return counter.value
                
        except DatabaseError:
            # Fallback to cache-based sequence
            return self._get_cache_sequence()
    
    def _get_cache_sequence(self):
        """Cache-based sequence fallback"""
        try:
            sequence = cache.incr(self.sequence_key)
            if sequence is None:
                # Initialize sequence
                cache.set(self.sequence_key, 1000000)  # Start from 1,000,000
                sequence = cache.incr(self.sequence_key)
            return sequence
        except Exception:
            # Ultimate fallback - timestamp based
            return int(datetime.now().timestamp() % 100000000)


class CountryCodeMapper:
    """Maps users to country codes based on location"""
    
    def get_country_code(self, user):
        """Get country code for user"""
        # Default to Saudi Arabia for now
        # In production, this would use:
        # 1. User profile country setting
        # 2. IP geolocation
        # 3. Registration data
        # 4. Default fallback
        
        return 'SA'  # Default to Saudi Arabia


class InvalidEntityTypeError(Exception):
    """Exception for invalid entity types"""
    pass


class InvalidBPNumberError(Exception):
    """Exception for invalid BP numbers"""
    pass


class BPNumberGenerationError(Exception):
    """Exception for BP number generation failures"""
    pass


# Utility functions for easy access
def ensure_user_has_bp_number(user):
    """Ensure user has a valid BP number"""
    bp_system = BPNumberSystem()
    return bp_system.ensure_bp_number(user)


def get_bp_number(user):
    """Get user's BP number"""
    if hasattr(user, 'business_partner') and user.business_partner.bp_number:
        return user.business_partner.bp_number
    
    # Auto-create if missing
    return ensure_user_has_bp_number(user)


def validate_bp_number_format(bp_number):
    """Validate BP number format"""
    bp_system = BPNumberSystem()
    return bp_system.validate_bp_number_format(bp_number)
