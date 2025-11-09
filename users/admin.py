from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib import messages
from .models import User, UserProfile, UserRole, UserAuditLog


class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile."""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('company_name', 'address', 'city', 'country', 'bio', 'website', 'social_media_links')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""
    
    # The forms to add and change user instances
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'phone_number', 'profile_picture')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'role', 'is_verified', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        (_('Account Status'), {
            'fields': ('is_deleted', 'deleted_at', 'deleted_by', 'is_banned', 'is_suspended'),
        }),
        (_('Ban Information'), {
            'fields': ('ban_reason', 'ban_until', 'banned_by'),
            'classes': ('collapse',),
        }),
        (_('Suspension Information'), {
            'fields': ('suspend_reason', 'suspend_until', 'suspended_by'),
            'classes': ('collapse',),
        }),
        (_('Two-Factor Authentication'), {
            'fields': ('is_2fa_enabled', 'otp_secret', 'otp_created_at', 'otp_attempts'),
            'classes': ('collapse',),
        }),
        (_('Email Verification'), {
            'fields': ('email_verification_token', 'email_verification_sent_at'),
            'classes': ('collapse',),
        }),
    )
    
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_active', 'is_staff', 'is_verified', 'is_banned', 'is_suspended', 'is_deleted', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'role', 'is_verified', 'is_banned', 'is_suspended', 'is_deleted', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'phone_number')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)
    readonly_fields = ('email_verification_token', 'last_login', 'date_joined', 'otp_created_at', 'deleted_at', 'deleted_by', 'banned_by', 'suspended_by')
    
    # Add the profile inline
    inlines = (UserProfileInline,)
    
    # Custom admin actions
    actions = ['make_verified', 'make_unverified', 'enable_2fa', 'disable_2fa', 'ban_users', 'unban_users', 'suspend_users', 'unsuspend_users', 'soft_delete_users', 'restore_users']
    
    def make_verified(self, request, queryset):
        """Mark selected users as verified."""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} users were successfully marked as verified.')
    make_verified.short_description = "Mark selected users as verified"
    
    def make_unverified(self, request, queryset):
        """Mark selected users as unverified."""
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} users were successfully marked as unverified.')
    make_unverified.short_description = "Mark selected users as unverified"
    
    def enable_2fa(self, request, queryset):
        """Enable 2FA for selected users."""
        updated = queryset.update(is_2fa_enabled=True)
        self.message_user(request, f'2FA was enabled for {updated} users.')
    enable_2fa.short_description = "Enable 2FA for selected users"
    
    def disable_2fa(self, request, queryset):
        """Disable 2FA for selected users."""
        updated = queryset.update(is_2fa_enabled=False, otp_secret=None, otp_created_at=None, otp_attempts=0)
        self.message_user(request, f'2FA was disabled for {updated} users.')
    disable_2fa.short_description = "Disable 2FA for selected users"
    
    def ban_users(self, request, queryset):
        count = 0
        for user in queryset:
            if not user.is_banned:
                user.ban(reason="Banned by admin", banned_by=request.user)
                UserAuditLog.log_action(user, 'ban', performed_by=request.user, request=request)
                count += 1
        self.message_user(request, f"{count} users have been banned.")
    
    ban_users.short_description = "Ban selected users"
    
    def unban_users(self, request, queryset):
        count = 0
        for user in queryset:
            if user.is_banned:
                user.unban()
                UserAuditLog.log_action(user, 'unban', performed_by=request.user, request=request)
                count += 1
        self.message_user(request, f"{count} users have been unbanned.")
    
    unban_users.short_description = "Unban selected users"
    
    def suspend_users(self, request, queryset):
        count = 0
        for user in queryset:
            if not user.is_suspended:
                user.suspend(reason="Suspended by admin", suspended_by=request.user)
                UserAuditLog.log_action(user, 'suspend', performed_by=request.user, request=request)
                count += 1
        self.message_user(request, f"{count} users have been suspended.")
    
    suspend_users.short_description = "Suspend selected users"
    
    def unsuspend_users(self, request, queryset):
        count = 0
        for user in queryset:
            if user.is_suspended:
                user.unsuspend()
                UserAuditLog.log_action(user, 'unsuspend', performed_by=request.user, request=request)
                count += 1
        self.message_user(request, f"{count} users have been unsuspended.")
    
    unsuspend_users.short_description = "Unsuspend selected users"
    
    def soft_delete_users(self, request, queryset):
        count = 0
        for user in queryset:
            if not user.is_deleted:
                user.soft_delete(deleted_by=request.user)
                UserAuditLog.log_action(user, 'delete', performed_by=request.user, request=request)
                count += 1
        self.message_user(request, f"{count} users have been soft deleted.")
    
    soft_delete_users.short_description = "Soft delete selected users"
    
    def restore_users(self, request, queryset):
        count = 0
        for user in queryset:
            if user.is_deleted:
                user.restore()
                UserAuditLog.log_action(user, 'restore', performed_by=request.user, request=request)
                count += 1
        self.message_user(request, f"{count} users have been restored.")
    
    restore_users.short_description = "Restore selected users"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model."""
    
    list_display = ('user', 'company_name', 'city', 'country', 'created_at')
    list_filter = ('city', 'country', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'company_name', 'city', 'country')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('User'), {'fields': ('user',)}),
        (_('Company Information'), {'fields': ('company_name', 'website')}),
        (_('Location'), {'fields': ('address', 'city', 'country')}),
        (_('About'), {'fields': ('bio', 'social_media_links')}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(UserAuditLog)
class UserAuditLogAdmin(admin.ModelAdmin):
    """Admin configuration for UserAuditLog model."""
    
    list_display = ('user', 'action', 'performed_by', 'timestamp', 'ip_address')
    list_filter = ('action', 'timestamp', 'performed_by')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'performed_by__email', 'ip_address')
    readonly_fields = ('user', 'action', 'performed_by', 'timestamp', 'details', 'ip_address', 'user_agent')
    ordering = ('-timestamp',)
    
    fieldsets = (
        (_('Action Information'), {
            'fields': ('user', 'action', 'performed_by', 'timestamp')
        }),
        (_('Request Information'), {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',),
        }),
        (_('Additional Details'), {
            'fields': ('details',),
            'classes': ('collapse',),
        }),
    )
    
    def has_add_permission(self, request):
        """Disable adding audit logs manually."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing audit logs."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable deleting audit logs."""
        return False
