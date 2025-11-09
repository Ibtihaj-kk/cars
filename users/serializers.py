from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import UserProfile, UserRole, UserAuditLog

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile data."""
    
    class Meta:
        model = UserProfile
        fields = ['company_name', 'bio', 'address', 'city', 'country', 'website', 'social_media_links']


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user data."""
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'phone_number', 
                 'profile_picture', 'role', 'is_verified', 'is_2fa_enabled', 'date_joined', 'profile']
        read_only_fields = ['id', 'date_joined', 'is_verified', 'role']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    role = serializers.ChoiceField(choices=UserRole.choices, default=UserRole.USER)
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone_number', 'password', 'password_confirm', 'role']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, data):
        # Check that the two password entries match
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
            
        # Validate password strength
        try:
            validate_password(data['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
            
        return data
    
    def create(self, validated_data):
        # Remove password_confirm from the data
        validated_data.pop('password_confirm')
        
        # Only admins can create admin or staff users
        request = self.context.get('request')
        if request and not (request.user.is_authenticated and request.user.is_admin()):
            if validated_data.get('role') in [UserRole.ADMIN, UserRole.STAFF]:
                validated_data['role'] = UserRole.USER
        
        # Create the user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            role=validated_data.get('role', UserRole.USER)
        )
        
        # Generate email verification token
        user.generate_email_verification_token()
        
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer that includes user data."""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add user data to response
        user = self.user
        data.update({
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'is_verified': user.is_verified,
            'is_2fa_enabled': user.is_2fa_enabled,
        })
        
        # Check if 2FA is enabled
        if user.is_2fa_enabled:
            # Generate OTP and remove tokens from response
            otp = user.generate_otp()
            # In a real app, send OTP via email or SMS here
            data.pop('access', None)
            data.pop('refresh', None)
            data['requires_2fa'] = True
            # Don't include the OTP in the response for security
            # Instead, send it via email/SMS
        
        return data


class VerifyOTPSerializer(serializers.Serializer):
    """Serializer for OTP verification."""
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6, min_length=6)
    
    def validate(self, attrs):
        email = attrs.get('email')
        otp = attrs.get('otp')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "User with this email does not exist."})
        
        if not user.is_2fa_enabled:
            raise serializers.ValidationError({"detail": "2FA is not enabled for this user."})
        
        if not user.verify_otp(otp):
            raise serializers.ValidationError({"otp": "Invalid or expired OTP."})
        
        attrs['user'] = user
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer for email verification."""
    token = serializers.UUIDField()
    
    def validate(self, attrs):
        token = attrs.get('token')
        
        try:
            user = User.objects.get(email_verification_token=token)
        except User.DoesNotExist:
            raise serializers.ValidationError({"token": "Invalid verification token."})
        
        # Check if token is expired (24 hours)
        from django.utils import timezone
        from datetime import timedelta
        
        if not user.email_verification_sent_at or \
           (timezone.now() - user.email_verification_sent_at) > timedelta(hours=24):
            raise serializers.ValidationError({"token": "Verification token has expired."})
        
        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request."""
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation."""
    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, required=True)
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Validate password strength
        try:
            validate_password(attrs['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        
        # Verify token
        token = attrs.get('token')
        try:
            user = User.objects.get(email_verification_token=token)
        except User.DoesNotExist:
            raise serializers.ValidationError({"token": "Invalid reset token."})
        
        # Check if token is expired (24 hours)
        from django.utils import timezone
        from datetime import timedelta
        
        if not user.email_verification_sent_at or \
           (timezone.now() - user.email_verification_sent_at) > timedelta(hours=24):
            raise serializers.ValidationError({"token": "Reset token has expired."})
        
        attrs['user'] = user
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""
    old_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(required=True, write_only=True, style={'input_type': 'password'})
    
    def validate(self, attrs):
        # Check that the two new password entries match
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Password fields didn't match."})
        
        # Validate password strength
        try:
            validate_password(attrs['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
            
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Enhanced serializer for user profile updates with email validation."""
    profile = UserProfileSerializer(required=False)
    email = serializers.EmailField(required=False)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone_number', 'profile']
    
    def validate_email(self, value):
        """Validate that email is unique (excluding current user)."""
        user = self.instance
        if User.objects.filter(email=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_phone_number(self, value):
        """Validate phone number format."""
        if value and len(value) < 10:
            raise serializers.ValidationError("Phone number must be at least 10 digits.")
        return value
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Track if email is being changed for audit logging
        email_changed = False
        old_email = instance.email
        
        # Update user fields
        for attr, value in validated_data.items():
            if attr == 'email' and value != old_email:
                email_changed = True
                # If email is changed, mark as unverified
                instance.is_verified = False
                instance.generate_email_verification_token()
            setattr(instance, attr, value)
        
        instance.save()
        
        # Update or create profile
        if profile_data:
            profile, created = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        # Log the profile update
        UserAuditLog.log_action(
            user=instance,
            action='update',
            details={
                'fields_updated': list(validated_data.keys()),
                'email_changed': email_changed,
                'profile_updated': profile_data is not None
            },
            request=self.context.get('request')
        )
        
        return instance


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user data."""
    profile = UserProfileSerializer(required=False)
    role = serializers.ChoiceField(choices=UserRole.choices, read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    is_2fa_enabled = serializers.BooleanField(required=False)
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number', 'profile', 'role', 'is_verified', 'is_2fa_enabled']
        read_only_fields = ['role', 'is_verified']
    
    def update(self, instance, validated_data):
        profile_data = validated_data.pop('profile', None)
        
        # Update user fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # If 2FA is being disabled, clear OTP fields
        if 'is_2fa_enabled' in validated_data and not validated_data['is_2fa_enabled']:
            instance.otp_secret = None
            instance.otp_created_at = None
            instance.otp_attempts = 0
        
        instance.save()
        
        # Update or create profile
        if profile_data:
            profile, created = UserProfile.objects.get_or_create(user=instance)
            for attr, value in profile_data.items():
                setattr(profile, attr, value)
            profile.save()
        
        return instance


class UserAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for user audit logs."""
    user_email = serializers.CharField(source='user.email', read_only=True)
    performed_by_email = serializers.CharField(source='performed_by.email', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = UserAuditLog
        fields = ['id', 'user', 'user_email', 'action', 'action_display', 'performed_by', 
                 'performed_by_email', 'timestamp', 'details', 'ip_address']
        read_only_fields = ['id', 'timestamp']


class AdminUserSerializer(serializers.ModelSerializer):
    """Serializer for admin user management."""
    profile = UserProfileSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name', 'phone_number', 
                 'profile_picture', 'role', 'is_verified', 'is_2fa_enabled', 'date_joined',
                 'is_active', 'is_deleted', 'deleted_at', 'deleted_by', 'is_banned', 
                 'is_suspended', 'ban_reason', 'suspend_reason', 'ban_until', 'suspend_until',
                 'banned_by', 'suspended_by', 'profile']
        read_only_fields = ['id', 'date_joined', 'deleted_at', 'deleted_by', 'banned_by', 'suspended_by']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class BanUserSerializer(serializers.Serializer):
    """Serializer for banning users."""
    reason = serializers.CharField(required=True, max_length=500)
    until = serializers.DateTimeField(required=False, allow_null=True)


class SuspendUserSerializer(serializers.Serializer):
    """Serializer for suspending users."""
    reason = serializers.CharField(required=True, max_length=500)
    until = serializers.DateTimeField(required=False, allow_null=True)


class RoleChangeSerializer(serializers.Serializer):
    """Serializer for changing user roles."""
    role = serializers.ChoiceField(choices=UserRole.choices, required=True)