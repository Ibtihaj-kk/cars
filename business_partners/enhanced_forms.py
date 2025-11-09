"""
Enhanced Forms for Vendor Management System
Provides comprehensive form handling for vendor workflows
"""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import models

from .models import VendorApplication, BusinessPartner
from .workflow_engine import VendorWorkflowAuditLog, VendorComplianceCheck

User = get_user_model()


class VendorApplicationReviewForm(forms.Form):
    """Form for reviewing vendor applications"""
    
    REVIEW_ACTIONS = [
        ('approve', 'Approve Application'),
        ('reject', 'Reject Application'),
        ('request_info', 'Request Additional Information'),
        ('escalate', 'Escalate for Review'),
    ]
    
    action = forms.ChoiceField(
        choices=REVIEW_ACTIONS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        label="Review Action"
    )
    
    review_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Enter your review notes and observations...'
        }),
        required=False,
        label="Review Notes"
    )
    
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'If rejecting, provide detailed reason...'
        }),
        required=False,
        label="Rejection Reason (if applicable)"
    )
    
    required_info = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Specify what additional information is needed...'
        }),
        required=False,
        label="Required Information (if requesting info)"
    )
    
    escalation_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Explain why this case needs escalation...'
        }),
        required=False,
        label="Escalation Reason (if escalating)"
    )
    
    escalation_level = forms.ChoiceField(
        choices=[(1, 'Level 1 - Senior Reviewer'), (2, 'Level 2 - Manager'), 
                (3, 'Level 3 - Director'), (4, 'Level 4 - Executive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Escalation Level"
    )
    
    def clean(self):
        """Validate form based on selected action"""
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'reject' and not cleaned_data.get('rejection_reason'):
            raise ValidationError("Rejection reason is required when rejecting an application.")
        
        if action == 'request_info' and not cleaned_data.get('required_info'):
            raise ValidationError("Required information details are needed.")
        
        if action == 'escalate' and not cleaned_data.get('escalation_reason'):
            raise ValidationError("Escalation reason is required.")
        
        return cleaned_data


class VendorComplianceOverrideForm(forms.Form):
    """Form for overriding failed compliance checks"""
    
    check_id = forms.IntegerField(
        widget=forms.HiddenInput()
    )
    
    override_reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Provide detailed justification for overriding this compliance check...'
        }),
        label="Override Reason"
    )
    
    override_evidence = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        label="Supporting Evidence (optional)"
    )
    
    def clean_override_reason(self):
        """Validate override reason"""
        reason = self.cleaned_data['override_reason']
        if len(reason) < 20:
            raise ValidationError("Override reason must be at least 20 characters long.")
        return reason


class VendorSearchForm(forms.Form):
    """Advanced search form for vendor management"""
    
    search_query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by company name, application ID, email...'
        }),
        label="Search Query"
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + [
            (status.value, status.name.replace('_', ' ').title()) 
            for status in VendorWorkflowState.VendorStatus
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Status"
    )
    
    priority = forms.ChoiceField(
        required=False,
        choices=[('', 'All Priorities'), ('1', 'Low'), ('2', 'Medium'), 
                ('3', 'High'), ('4', 'Critical'), ('5', 'Urgent')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Priority Level"
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Application Date From"
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="Application Date To"
    )
    
    performance_min = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '100',
            'step': '1'
        }),
        label="Minimum Performance Score"
    )
    
    compliance_min = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '100',
            'step': '1'
        }),
        label="Minimum Compliance Score"
    )


class VendorBulkActionForm(forms.Form):
    """Form for bulk actions on vendor applications"""
    
    BULK_ACTIONS = [
        ('approve_selected', 'Approve Selected'),
        ('reject_selected', 'Reject Selected'),
        ('request_info_selected', 'Request Info for Selected'),
        ('escalate_selected', 'Escalate Selected'),
        ('export_selected', 'Export Selected Data'),
        ('assign_reviewer', 'Assign to Reviewer'),
    ]
    
    action = forms.ChoiceField(
        choices=BULK_ACTIONS,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Bulk Action"
    )
    
    selected_vendors = forms.CharField(
        widget=forms.HiddenInput(),
        help_text="Comma-separated list of vendor application IDs"
    )
    
    bulk_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for bulk action (if applicable)...'
        }),
        label="Bulk Action Reason"
    )
    
    assign_to = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(
            groups__name__in=['Admin', 'VendorReviewer', 'SeniorReviewer']
        ).distinct(),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Assign To (if assigning reviewers)"
    )


class VendorPerformanceFilterForm(forms.Form):
    """Form for filtering vendor performance data"""
    
    date_range = forms.ChoiceField(
        choices=[
            ('7d', 'Last 7 Days'),
            ('30d', 'Last 30 Days'),
            ('90d', 'Last 90 Days'),
            ('1y', 'Last Year'),
            ('custom', 'Custom Range')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Date Range"
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="From Date"
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="To Date"
    )
    
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'All Categories')] + [
            ('electronics', 'Electronics'),
            ('automotive', 'Automotive'),
            ('industrial', 'Industrial'),
            ('consumer_goods', 'Consumer Goods'),
            ('services', 'Services')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Product Category"
    )
    
    region = forms.ChoiceField(
        required=False,
        choices=[('', 'All Regions')] + [
            ('riyadh', 'Riyadh'),
            ('jeddah', 'Jeddah'),
            ('dammam', 'Dammam'),
            ('mecca', 'Mecca'),
            ('medina', 'Medina')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Region"
    )
    
    min_performance_score = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '100',
            'step': '5'
        }),
        label="Minimum Performance Score"
    )
    
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('performance', 'Performance Score'),
            ('revenue', 'Revenue'),
            ('orders', 'Order Count'),
            ('satisfaction', 'Customer Satisfaction'),
            ('newest', 'Newest First'),
            ('oldest', 'Oldest First')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Sort By"
    )


class VendorRevenueFilterForm(forms.Form):
    """Form for filtering vendor revenue data"""
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="From Date"
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="To Date"
    )
    
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'All Categories')] + [
            ('electronics', 'Electronics'),
            ('automotive', 'Automotive'),
            ('industrial', 'Industrial'),
            ('consumer_goods', 'Consumer Goods'),
            ('services', 'Services')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Product Category"
    )
    
    region = forms.ChoiceField(
        required=False,
        choices=[('', 'All Regions')] + [
            ('riyadh', 'Riyadh'),
            ('jeddah', 'Jeddah'),
            ('dammam', 'Dammam'),
            ('mecca', 'Mecca'),
            ('medina', 'Medina')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Region"
    )
    
    min_revenue = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'step': '1000'
        }),
        label="Minimum Revenue"
    )
    
    group_by = forms.ChoiceField(
        required=False,
        choices=[
            ('vendor', 'By Vendor'),
            ('category', 'By Category'),
            ('region', 'By Region'),
            ('month', 'By Month'),
            ('week', 'By Week')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Group By"
    )


class VendorComplianceCheckForm(forms.Form):
    """Form for running vendor compliance checks"""
    
    CHECK_TYPES = [
        ('all', 'Run All Checks'),
        ('document_verification', 'Document Verification'),
        ('business_license', 'Business License Validation'),
        ('tax_id_verification', 'Tax ID Verification'),
        ('bank_account_validation', 'Bank Account Validation'),
        ('reference_check', 'Reference Check'),
        ('performance_review', 'Performance Review'),
        ('policy_compliance', 'Policy Compliance'),
    ]
    
    check_type = forms.ChoiceField(
        choices=CHECK_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Compliance Check Type"
    )
    
    priority = forms.ChoiceField(
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Check Priority"
    )
    
    auto_override_threshold = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '100',
            'step': '5'
        }),
        label="Auto-Override Threshold (%)"
    )


class VendorNotificationSettingsForm(forms.Form):
    """Form for vendor notification settings"""
    
    email_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Enable Email Notifications"
    )
    
    sms_notifications = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Enable SMS Notifications"
    )
    
    notification_frequency = forms.ChoiceField(
        choices=[
            ('immediate', 'Immediate'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Notification Frequency"
    )
    
    stock_alert_threshold = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '100'
        }),
        label="Stock Alert Threshold (%)"
    )
    
    performance_alert_threshold = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '100',
            'step': '5'
        }),
        label="Performance Alert Threshold (%)"
    )


class VendorExportForm(forms.Form):
    """Form for exporting vendor data"""
    
    EXPORT_FORMATS = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
        ('json', 'JSON')
    ]
    
    EXPORT_TYPES = [
        ('applications', 'Vendor Applications'),
        ('performance', 'Performance Data'),
        ('revenue', 'Revenue Data'),
        ('compliance', 'Compliance Reports'),
        ('audit_logs', 'Audit Logs')
    ]
    
    export_format = forms.ChoiceField(
        choices=EXPORT_FORMATS,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Export Format"
    )
    
    export_type = forms.ChoiceField(
        choices=EXPORT_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Export Type"
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="From Date"
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label="To Date"
    )
    
    include_inactive = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Include Inactive Vendors"
    )


class VendorEscalationMatrixForm(forms.Form):
    """Form for configuring vendor escalation matrix"""
    
    escalation_level = forms.ChoiceField(
        choices=[(1, 'Level 1'), (2, 'Level 2'), (3, 'Level 3'), (4, 'Level 4')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Escalation Level"
    )
    
    escalation_trigger = forms.ChoiceField(
        choices=[
            ('performance_drop', 'Performance Score Drop Below Threshold'),
            ('compliance_failure', 'Compliance Check Failure'),
            ('customer_complaint', 'Customer Complaint'),
            ('order_dispute', 'Order Dispute'),
            ('policy_violation', 'Policy Violation'),
            ('manual_review', 'Manual Review Required')
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Escalation Trigger"
    )
    
    threshold_value = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '0',
            'max': '100',
            'step': '5'
        }),
        label="Threshold Value (%)"
    )
    
    auto_escalate = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="Enable Auto-Escalation"
    )
    
    notification_recipients = forms.ModelMultipleChoiceField(
        required=False,
        queryset=User.objects.filter(
            groups__name__in=['Admin', 'VendorManager', 'SeniorReviewer']
        ).distinct(),
        widget=forms.CheckboxSelectMultiple(),
        label="Notification Recipients"
    )