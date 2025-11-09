from django import forms
from django.core.validators import FileExtensionValidator
from .document_models import VendorDocument, DocumentCategory, DocumentVerificationQueue
from business_partners.models import VendorApplication, BusinessPartner


class VendorDocumentUploadForm(forms.ModelForm):
    """Form for uploading vendor documents"""
    
    class Meta:
        model = VendorDocument
        fields = ['category', 'title', 'description', 'file', 'issue_date', 'expiry_date']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Document title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief description of the document'}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf,.jpg,.jpeg,.png,.doc,.docx'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.vendor_application = kwargs.pop('vendor_application', None)
        self.business_partner = kwargs.pop('business_partner', None)
        super().__init__(*args, **kwargs)
        
        # Filter categories based on vendor type and requirements
        queryset = DocumentCategory.objects.all()
        if self.vendor_application:
            # Show required categories first
            queryset = queryset.order_by('-required', 'name')
        
        self.fields['category'].queryset = queryset
        self.fields['category'].empty_label = "Select document category"
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Validate file size (10MB limit)
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must not exceed 10MB")
            
            # Validate file extension based on category
            category = self.cleaned_data.get('category')
            if category:
                allowed_extensions = category.get_allowed_extensions_list()
                file_extension = file.name.split('.')[-1].lower()
                if file_extension not in allowed_extensions:
                    raise forms.ValidationError(
                        f"File type '{file_extension}' not allowed. Allowed types: {', '.join(allowed_extensions)}"
                    )
        return file
    
    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        issue_date = self.cleaned_data.get('issue_date')
        
        if expiry_date and issue_date and expiry_date <= issue_date:
            raise forms.ValidationError("Expiry date must be after issue date")
        
        return expiry_date
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set the appropriate relationship
        if self.vendor_application:
            instance.vendor_application = self.vendor_application
        elif self.business_partner:
            instance.business_partner = self.business_partner
        
        if commit:
            instance.save()
        
        return instance


class VendorDocumentVerificationForm(forms.ModelForm):
    """Form for verifying vendor documents"""
    
    ACTION_CHOICES = [
        ('verify', 'Verify Document'),
        ('reject', 'Reject Document'),
        ('request_renewal', 'Request Renewal'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='verify'
    )
    
    verification_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Verification notes'}),
        required=False
    )
    
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason for rejection'}),
        required=False
    )
    
    class Meta:
        model = VendorDocument
        fields = []
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'reject' and not cleaned_data.get('rejection_reason'):
            raise forms.ValidationError("Rejection reason is required when rejecting a document")
        
        return cleaned_data
    
    def save(self, user, commit=True):
        action = self.cleaned_data['action']
        
        if action == 'verify':
            self.instance.verify(
                user=user,
                notes=self.cleaned_data.get('verification_notes')
            )
        elif action == 'reject':
            self.instance.reject(
                user=user,
                reason=self.cleaned_data.get('rejection_reason', '')
            )
        elif action == 'request_renewal':
            self.instance.mark_needs_renewal()
        
        return self.instance


class DocumentVerificationQueueForm(forms.ModelForm):
    """Form for managing document verification queue"""
    
    class Meta:
        model = DocumentVerificationQueue
        fields = ['priority', 'assigned_to', 'notes']
        widgets = {
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limit assigned_to to staff users with appropriate permissions
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_staff=True,
            is_active=True
        ).order_by('first_name', 'last_name')
        self.fields['assigned_to'].empty_label = "Unassigned"


class VendorDocumentSearchForm(forms.Form):
    """Form for searching vendor documents"""
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('pending', 'Pending Review'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('needs_renewal', 'Needs Renewal'),
    ]
    
    PRIORITY_CHOICES = [
        ('', 'All Priorities'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    search_query = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by title, description, or document number'
        })
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    category = forms.ModelChoiceField(
        queryset=DocumentCategory.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    vendor_application = forms.ModelChoiceField(
        queryset=VendorApplication.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    business_partner = forms.ModelChoiceField(
        queryset=BusinessPartner.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    expiry_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    expiry_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    uploaded_date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    uploaded_date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter vendor applications and business partners based on user permissions
        if self.user and not self.user.is_staff:
            # Non-staff users can only see their own documents
            self.fields['vendor_application'].queryset = VendorApplication.objects.filter(
                user=self.user
            )
            self.fields['business_partner'].queryset = BusinessPartner.objects.filter(
                user=self.user
            )
        
        # Set empty labels
        self.fields['category'].empty_label = "All Categories"
        self.fields['vendor_application'].empty_label = "All Applications"
        self.fields['business_partner'].empty_label = "All Vendors"


class BulkDocumentActionForm(forms.Form):
    """Form for bulk actions on documents"""
    
    ACTION_CHOICES = [
        ('verify', 'Verify Selected'),
        ('reject', 'Reject Selected'),
        ('request_renewal', 'Request Renewal'),
        ('assign_priority', 'Assign Priority'),
        ('export', 'Export Selected'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    document_ids = forms.ModelMultipleChoiceField(
        queryset=VendorDocument.objects.none(),
        widget=forms.MultipleHiddenInput()
    )
    
    priority = forms.ChoiceField(
        choices=DocumentVerificationQueue.PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    rejection_reason = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )
    
    verification_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set queryset for document_ids based on user permissions
        if user and user.is_staff:
            self.fields['document_ids'].queryset = VendorDocument.objects.all()
        else:
            # Non-staff users should not have access to bulk actions
            self.fields['document_ids'].queryset = VendorDocument.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'reject' and not cleaned_data.get('rejection_reason'):
            raise forms.ValidationError("Rejection reason is required when rejecting documents")
        
        if action == 'assign_priority' and not cleaned_data.get('priority'):
            raise forms.ValidationError("Priority is required when assigning priority")
        
        return cleaned_data