from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, Permission, Group
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
import uuid


class UserManager(BaseUserManager):
    """Custom user manager."""
    
    def get_queryset(self):
        """Return queryset excluding soft-deleted users by default."""
        return super().get_queryset().filter(is_deleted=False)
    
    def all_with_deleted(self):
        """Return all users including soft-deleted ones."""
        return super().get_queryset()
    
    def deleted_only(self):
        """Return only soft-deleted users."""
        return super().get_queryset().filter(is_deleted=True)
    
    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', UserRole.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self._create_user(email, password, **extra_fields)


class UserRole(models.TextChoices):
    """User role choices."""
    ADMIN = 'admin', _('Admin')
    STAFF = 'staff', _('Staff')
    SELLER = 'seller', _('Seller')
    CLIENT = 'client', _('Client')
    USER = 'user', _('User')


class User(AbstractUser):
    """Custom User model with email as the unique identifier and role-based permissions."""
    username = None
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.USER,
    )
    is_verified = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False, null=True, blank=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)
    
    # 2FA fields
    is_2fa_enabled = models.BooleanField(default=False)
    otp_secret = models.CharField(max_length=16, blank=True, null=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.PositiveSmallIntegerField(default=0)
    
    # Soft delete fields
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='deleted_users'
    )
    
    # Ban/Suspend fields
    is_banned = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    ban_reason = models.TextField(blank=True, null=True)
    suspend_reason = models.TextField(blank=True, null=True)
    ban_until = models.DateTimeField(null=True, blank=True)
    suspend_until = models.DateTimeField(null=True, blank=True)
    banned_by = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='banned_users'
    )
    suspended_by = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='suspended_users'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
    
    def get_full_name(self):
        """Return the user's full name."""
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.email
    
    def is_admin(self):
        """Check if the user is an admin."""
        return self.role == UserRole.ADMIN or self.is_superuser
    
    def is_staff_member(self):
        """Check if the user is a staff member."""
        return self.role == UserRole.STAFF or self.is_staff
    
    def is_seller(self):
        """Check if the user is a seller."""
        return self.role == UserRole.SELLER
    
    def is_client(self):
        """Check if the user is a client."""
        return self.role == UserRole.CLIENT
    
    def generate_email_verification_token(self):
        """Generate a new email verification token."""
        self.email_verification_token = uuid.uuid4()
        self.email_verification_sent_at = timezone.now()
        self.save(update_fields=['email_verification_token', 'email_verification_sent_at'])
        return self.email_verification_token
    
    def verify_email(self):
        """Mark the user's email as verified."""
        self.is_verified = True
        self.email_verification_token = None
        self.email_verification_sent_at = None
        self.save(update_fields=['is_verified', 'email_verification_token', 'email_verification_sent_at'])
    
    def generate_otp(self):
        """Generate a new OTP for 2FA."""
        import random
        import string
        
        # Generate a 6-digit OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Store the OTP hash
        self.otp_secret = otp
        self.otp_created_at = timezone.now()
        self.otp_attempts = 0
        self.save(update_fields=['otp_secret', 'otp_created_at', 'otp_attempts'])
        
        return otp
    
    def verify_otp(self, otp):
        """Verify the OTP for 2FA."""
        # Check if OTP is expired (10 minutes)
        if not self.otp_created_at or (timezone.now() - self.otp_created_at).total_seconds() > 600:
            return False
        
        # Check if too many attempts
        if self.otp_attempts >= 5:
            return False
        
        # Increment attempts
        self.otp_attempts += 1
        self.save(update_fields=['otp_attempts'])
        
        # Check if OTP matches
        return self.otp_secret == otp
    
    def soft_delete(self, deleted_by=None):
        """Soft delete the user."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = deleted_by
        self.is_active = False
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'is_active'])
    
    def restore(self):
        """Restore a soft-deleted user."""
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.is_active = True
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by', 'is_active'])
    
    def ban(self, reason=None, until=None, banned_by=None):
        """Ban the user."""
        self.is_banned = True
        self.ban_reason = reason
        self.ban_until = until
        self.banned_by = banned_by
        self.is_active = False
        self.save(update_fields=['is_banned', 'ban_reason', 'ban_until', 'banned_by', 'is_active'])
    
    def unban(self):
        """Unban the user."""
        self.is_banned = False
        self.ban_reason = None
        self.ban_until = None
        self.banned_by = None
        self.is_active = True
        self.save(update_fields=['is_banned', 'ban_reason', 'ban_until', 'banned_by', 'is_active'])
    
    def suspend(self, reason=None, until=None, suspended_by=None):
        """Suspend the user."""
        self.is_suspended = True
        self.suspend_reason = reason
        self.suspend_until = until
        self.suspended_by = suspended_by
        self.is_active = False
        self.save(update_fields=['is_suspended', 'suspend_reason', 'suspend_until', 'suspended_by', 'is_active'])
    
    def unsuspend(self):
        """Unsuspend the user."""
        self.is_suspended = False
        self.suspend_reason = None
        self.suspend_until = None
        self.suspended_by = None
        self.is_active = True
        self.save(update_fields=['is_suspended', 'suspend_reason', 'suspend_until', 'suspended_by', 'is_active'])
    
    def is_ban_expired(self):
        """Check if ban has expired."""
        if not self.is_banned or not self.ban_until:
            return False
        return timezone.now() > self.ban_until
    
    def is_suspension_expired(self):
        """Check if suspension has expired."""
        if not self.is_suspended or not self.suspend_until:
            return False
        return timezone.now() > self.suspend_until
    
    def check_and_clear_expired_restrictions(self):
        """Check and clear expired bans/suspensions."""
        updated = False
        
        if self.is_ban_expired():
            self.unban()
            updated = True
            
        if self.is_suspension_expired():
            self.unsuspend()
            updated = True
            
        return updated


class UserProfile(models.Model):
    """Extended profile information for users."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    company_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    social_media_links = models.JSONField(default=dict, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email}'s Profile"


class UserAuditLog(models.Model):
    """Audit log for user management actions."""
    
    ACTION_CHOICES = [
        ('create', 'User Created'),
        ('update', 'User Updated'),
        ('delete', 'User Deleted'),
        ('restore', 'User Restored'),
        ('ban', 'User Banned'),
        ('unban', 'User Unbanned'),
        ('suspend', 'User Suspended'),
        ('unsuspend', 'User Unsuspended'),
        ('role_change', 'Role Changed'),
        ('password_reset', 'Password Reset'),
        ('email_verification', 'Email Verified'),
        ('2fa_enabled', '2FA Enabled'),
        ('2fa_disabled', '2FA Disabled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='performed_actions'
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['performed_by', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.user.email} by {self.performed_by.email if self.performed_by else 'System'}"
    
    @classmethod
    def log_action(cls, user, action, performed_by=None, details=None, request=None):
        """Create an audit log entry."""
        log_data = {
            'user': user,
            'action': action,
            'performed_by': performed_by,
            'details': details or {},
        }
        
        if request:
            log_data['ip_address'] = cls.get_client_ip(request)
            log_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        return cls.objects.create(**log_data)
    
    @staticmethod
    def get_client_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
