from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    BusinessPartner, BusinessPartnerRole, ContactInfo, Address,
    VendorProfile, CustomerProfile, VendorApplication, ReorderNotification
)
from .document_models import VendorDocument


class BusinessPartnerRoleInline(admin.TabularInline):
    """Inline admin for Business Partner Roles"""
    model = BusinessPartnerRole
    extra = 1
    verbose_name = "Role"
    verbose_name_plural = "Roles"


class ContactInfoInline(admin.TabularInline):
    """Inline admin for Contact Information"""
    model = ContactInfo
    extra = 1
    fields = ('contact_type', 'value', 'is_primary')
    verbose_name = "Contact"
    verbose_name_plural = "Contact Information"


class AddressInline(admin.StackedInline):
    """Inline admin for Addresses"""
    model = Address
    extra = 1
    fields = (
        'address_type', 'is_primary', 'street', 
        ('city', 'state_province'), 
        ('postal_code', 'country')
    )
    verbose_name = "Address"
    verbose_name_plural = "Addresses"


class VendorProfileInline(admin.StackedInline):
    """Inline admin for Vendor Profile"""
    model = VendorProfile
    fields = (
        ('payment_terms', 'preferred_currency'),
        ('vendor_rating', 'tax_id'),
        'bank_account_details'
    )
    verbose_name = "Vendor Profile"
    verbose_name_plural = "Vendor Profile"


class CustomerProfileInline(admin.StackedInline):
    """Inline admin for Customer Profile"""
    model = CustomerProfile
    fields = (
        ('credit_limit', 'preferred_currency'),
        ('loyalty_tier', 'discount_percentage')
    )
    verbose_name = "Customer Profile"
    verbose_name_plural = "Customer Profile"


@admin.register(BusinessPartner)
class BusinessPartnerAdmin(admin.ModelAdmin):
    """Admin interface for Business Partner"""
    
    list_display = (
        'bp_number', 'name', 'type', 'status', 
        'get_roles_display', 'created_at'
    )
    list_filter = ('type', 'status', 'created_at', 'roles__role_type')
    search_fields = ('bp_number', 'name', 'legal_identifier')
    readonly_fields = ('bp_number', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('bp_number', 'name', 'type', 'legal_identifier', 'status')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    inlines = [
        BusinessPartnerRoleInline,
        ContactInfoInline,
        AddressInline,
        VendorProfileInline,
        CustomerProfileInline
    ]
    
    def get_roles_display(self, obj):
        """Display roles as colored badges"""
        roles = obj.get_roles()
        if not roles:
            return "No roles"
        
        role_colors = {
            'customer': '#28a745',  # Green
            'vendor': '#007bff',    # Blue
            'prospect': '#ffc107'   # Yellow
        }
        
        badges = []
        for role in roles:
            color = role_colors.get(role.role_type, '#6c757d')
            badges.append(
                f'<span style="background-color: {color}; color: white; '
                f'padding: 2px 6px; border-radius: 3px; font-size: 11px; '
                f'margin-right: 3px;">{role.get_role_type_display()}</span>'
            )
        
        return format_html(''.join(badges))
    
    get_roles_display.short_description = 'Roles'
    get_roles_display.allow_tags = True
    
    def save_model(self, request, obj, form, change):
        """Set created_by field when creating new business partner"""
        if not change:  # Only set on creation
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BusinessPartnerRole)
class BusinessPartnerRoleAdmin(admin.ModelAdmin):
    """Admin interface for Business Partner Role"""
    
    list_display = ('business_partner', 'role_type', 'created_at')
    list_filter = ('role_type', 'created_at')
    search_fields = ('business_partner__name', 'business_partner__bp_number')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business_partner')


@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    """Admin interface for Contact Information"""
    
    list_display = (
        'business_partner', 'contact_type', 'value', 
        'is_primary', 'created_at'
    )
    list_filter = ('contact_type', 'is_primary', 'created_at')
    search_fields = (
        'business_partner__name', 'business_partner__bp_number', 'value'
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business_partner')


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    """Admin interface for Address"""
    
    list_display = (
        'business_partner', 'address_type', 'city', 
        'country', 'is_primary', 'created_at'
    )
    list_filter = ('address_type', 'is_primary', 'country', 'created_at')
    search_fields = (
        'business_partner__name', 'business_partner__bp_number', 
        'city', 'country', 'street'
    )
    
    fieldsets = (
        ('Business Partner', {
            'fields': ('business_partner', 'address_type', 'is_primary')
        }),
        ('Address Details', {
            'fields': ('street', ('city', 'state_province'), ('postal_code', 'country'))
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business_partner')


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    """Admin interface for Vendor Profile"""
    
    list_display = (
        'business_partner', 'payment_terms', 'vendor_rating', 
        'preferred_currency', 'updated_at'
    )
    list_filter = ('payment_terms', 'preferred_currency', 'vendor_rating')
    search_fields = ('business_partner__name', 'business_partner__bp_number')
    
    fieldsets = (
        ('Business Partner', {
            'fields': ('business_partner',)
        }),
        ('Payment Information', {
            'fields': ('payment_terms', 'preferred_currency', 'bank_account_details')
        }),
        ('Vendor Details', {
            'fields': ('vendor_rating', 'tax_id')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business_partner')


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Admin interface for Customer Profile"""
    
    list_display = (
        'business_partner', 'credit_limit', 'loyalty_tier', 
        'discount_percentage', 'preferred_currency', 'updated_at'
    )
    list_filter = ('loyalty_tier', 'preferred_currency')
    search_fields = ('business_partner__name', 'business_partner__bp_number')
    
    fieldsets = (
        ('Business Partner', {
            'fields': ('business_partner',)
        }),
        ('Customer Details', {
            'fields': (
                ('credit_limit', 'preferred_currency'),
                ('loyalty_tier', 'discount_percentage')
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('business_partner')


@admin.register(VendorApplication)
class VendorApplicationAdmin(admin.ModelAdmin):
    """Admin interface for Vendor Applications with approval workflow"""
    
    list_display = (
        'application_id', 'company_name', 'user', 'status', 
        'current_step', 'completion_percentage', 'created_at', 'submitted_at',
        'can_process_application'
    )
    list_filter = (
        'status', 'current_step', 'business_type', 
        'created_at', 'submitted_at', 'reviewed_at'
    )
    search_fields = (
        'application_id', 'company_name', 'user__email', 
        'commercial_registration_number', 'legal_identifier'
    )
    readonly_fields = (
        'application_id', 'created_at', 'updated_at', 
        'submitted_at', 'reviewed_at', 'approved_at',
        'completion_percentage', 'get_review_info'
    )
    
    fieldsets = (
        ('Application Overview', {
            'fields': ('application_id', 'user', 'status', 'current_step', 'completion_percentage')
        }),
        ('Step 1: Business Details', {
            'fields': (
                'company_name', 'business_type', 'establishment_date',
                'commercial_registration_number', 'legal_identifier',
                'cr_document', 'business_license', 'business_description'
            ),
            'classes': ('collapse',)
        }),
        ('Step 2: Contact Information', {
            'fields': (
                ('contact_person_name', 'contact_person_title'),
                ('business_phone', 'business_email'),
                'website',
                'street_address',
                ('city', 'state_province'),
                ('postal_code', 'country')
            ),
            'classes': ('collapse',)
        }),
        ('Step 3: Bank Details', {
            'fields': (
                ('bank_name', 'bank_branch'),
                'account_holder_name', 'account_number',
                ('iban', 'swift_code'),
                'bank_statement'
            ),
            'classes': ('collapse',)
        }),
        ('Step 4: Additional Information', {
            'fields': (
                'expected_monthly_volume', 'years_in_business',
                'product_categories', 'references'
            ),
            'classes': ('collapse',)
        }),
        ('Review Information', {
            'fields': ('reviewed_by', 'reviewed_at', 'rejection_reason', 'review_notes', 'get_review_info'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'submitted_at', 'approved_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['approve_applications', 'reject_applications', 'request_changes', 'show_review_summary']
    
    def completion_percentage(self, obj):
        """Display completion percentage with color coding"""
        percentage = obj.get_completion_percentage()
        if percentage >= 100:
            color = 'green'
        elif percentage >= 75:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {};">{} %</span>',
            color, percentage
        )
    completion_percentage.short_description = 'Completion'
    
    def can_process_application(self, obj):
        """Check if application can be processed (approved/rejected/changes requested)"""
        if obj.status in ['submitted', 'under_review']:
            return format_html(
                '<span style="color: green;">✓ Ready for Review</span>'
            )
        elif obj.status == 'requires_changes':
            return format_html(
                '<span style="color: orange;">⚠ Changes Required</span>'
            )
        elif obj.status == 'approved':
            return format_html(
                '<span style="color: blue;">✓ Approved</span>'
            )
        elif obj.status == 'rejected':
            return format_html(
                '<span style="color: red;">✗ Rejected</span>'
            )
        else:
            return format_html(
                '<span style="color: gray;">⏳ In Progress</span>'
            )
    can_process_application.short_description = 'Review Status'
    
    def get_review_info(self, obj):
        """Display review information in a formatted way"""
        if obj.reviewed_by:
            return format_html(
                '<div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px;">'
                '<strong>Reviewed by:</strong> {}<br>'
                '<strong>Reviewed at:</strong> {}<br>'
                '<strong>Status:</strong> {}'
                '</div>',
                obj.reviewed_by.get_full_name() or obj.reviewed_by.username,
                obj.reviewed_at.strftime('%Y-%m-%d %H:%M') if obj.reviewed_at else 'N/A',
                obj.get_status_display()
            )
        return format_html('<span style="color: gray;">Not reviewed yet</span>')
    get_review_info.short_description = 'Review Information'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'reviewed_by')
    
    def approve_applications(self, request, queryset):
        """Bulk approve vendor applications"""
        approved_count = 0
        for application in queryset.filter(status__in=['submitted', 'under_review']):
            try:
                # Get the old status for logging
                old_status = application.status
                
                # Approve the application
                business_partner = application.approve(request.user, "Bulk approved by admin")
                
                # Log the approval action
                from core.audit_logging import AuditLogger
                AuditLogger.log_model_change(
                    user=request.user,
                    instance=application,
                    action_type='UPDATE',
                    changes={'status': {'old': old_status, 'new': 'approved'}},
                    request=request
                )
                
                approved_count += 1
                
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error approving {application.application_id}: {str(e)}", 
                    level='error'
                )
        
        if approved_count > 0:
            self.message_user(
                request, 
                f"Successfully approved {approved_count} applications."
            )
    approve_applications.short_description = "Approve selected applications"
    
    def reject_applications(self, request, queryset):
        """Reject vendor applications"""
        rejected_count = 0
        for application in queryset.filter(status__in=['submitted', 'under_review']):
            try:
                # Get the old status for logging
                old_status = application.status
                
                # Reject the application
                application.reject(request.user, "Rejected by admin")
                
                # Log the rejection action
                from core.audit_logging import AuditLogger
                AuditLogger.log_model_change(
                    user=request.user,
                    instance=application,
                    action_type='UPDATE',
                    changes={'status': {'old': old_status, 'new': 'rejected'}},
                    request=request
                )
                
                rejected_count += 1
                
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error rejecting application {application.application_id}: {str(e)}",
                    level='error'
                )
        
        if rejected_count > 0:
            self.message_user(
                request, 
                f"Successfully rejected {rejected_count} applications."
            )
    reject_applications.short_description = "Reject selected applications"
    
    def request_changes(self, request, queryset):
        """Request changes for vendor applications"""
        changed_count = 0
        for application in queryset.filter(status__in=['submitted', 'under_review']):
            try:
                # Get the old status for logging
                old_status = application.status
                
                # Request changes for the application
                application.request_changes(
                    request.user, 
                    "Changes requested by admin", 
                    "Please review and update your application"
                )
                
                # Log the changes requested action
                from core.audit_logging import AuditLogger
                AuditLogger.log_model_change(
                    user=request.user,
                    instance=application,
                    action_type='UPDATE',
                    changes={'status': {'old': old_status, 'new': 'requires_changes'}},
                    request=request
                )
                
                changed_count += 1
                
            except Exception as e:
                self.message_user(
                    request, 
                    f"Error requesting changes for application {application.application_id}: {str(e)}",
                    level='error'
                )
        
        if changed_count > 0:
            self.message_user(
                request, 
                f"Successfully requested changes for {changed_count} applications."
            )
    request_changes.short_description = "Request changes for selected applications"
    
    def show_review_summary(self, request, queryset):
        """Show summary of applications that can be processed"""
        total_count = queryset.count()
        can_process = queryset.filter(status__in=['submitted', 'under_review']).count()
        already_processed = queryset.filter(status__in=['approved', 'rejected', 'requires_changes']).count()
        in_progress = queryset.filter(status__in=['draft', 'business_details_completed', 'contact_info_completed', 'bank_details_completed']).count()
        
        message = f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
            <h4>📊 Application Review Summary</h4>
            <ul>
                <li><strong>Total Selected:</strong> {total_count} applications</li>
                <li><strong>Ready for Review:</strong> {can_process} applications (can be approved/rejected)</li>
                <li><strong>Already Processed:</strong> {already_processed} applications (approved/rejected/requires changes)</li>
                <li><strong>In Progress:</strong> {in_progress} applications (draft/incomplete)</li>
            </ul>
            <p><strong>Note:</strong> Only applications with status 'Submitted' or 'Under Review' can be processed using the bulk actions.</p>
        </div>
        """
        
        self.message_user(request, mark_safe(message))
    show_review_summary.short_description = "Show review summary for selected applications"


@admin.register(ReorderNotification)
class ReorderNotificationAdmin(admin.ModelAdmin):
    """Admin interface for Reorder Notifications"""
    
    list_display = (
        'part', 'vendor', 'priority', 'status', 'current_stock', 
        'reorder_level', 'suggested_quantity', 'created_at', 'is_overdue'
    )
    list_filter = (
        'priority', 'status', 'created_at', 'acknowledged_at', 
        'order_placed_at', 'vendor'
    )
    search_fields = (
        'part__name', 'part__part_number', 'vendor__name',
        'order_reference'
    )
    readonly_fields = (
        'created_at', 'urgency_score', 'is_overdue', 'message'
    )
    
    fieldsets = (
        ('Notification Details', {
            'fields': (
                'vendor', 'part', 'priority', 'status', 'message'
            )
        }),
        ('Stock Information', {
            'fields': (
                'current_stock', 'reorder_level', 'safety_stock', 
                'suggested_quantity'
            )
        }),
        ('Order Information', {
            'fields': (
                'order_reference', 'expected_delivery'
            ),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': (
                'acknowledged_at', 'acknowledged_by', 'order_placed_at'
            ),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': (
                'created_at', 'urgency_score', 'is_overdue'
            ),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'vendor', 'part', 'acknowledged_by'
        )


# Custom admin site configuration
admin.site.site_header = "Cars Portal Business Partners Administration"
admin.site.site_title = "Business Partners Admin"
admin.site.index_title = "Welcome to Business Partners Administration"