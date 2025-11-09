from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.db.models import Q, Count, Case, When, IntegerField
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from datetime import timedelta
import mimetypes

from .document_models import VendorDocument, DocumentCategory, DocumentVerificationQueue, DocumentAuditLog
from .document_forms import (
    VendorDocumentUploadForm, 
    VendorDocumentVerificationForm,
    VendorDocumentSearchForm,
    DocumentVerificationQueueForm,
    BulkDocumentActionForm
)
from business_partners.models import VendorApplication, BusinessPartner


class VendorDocumentUploadView(LoginRequiredMixin, CreateView):
    """View for uploading vendor documents"""
    
    model = VendorDocument
    form_class = VendorDocumentUploadForm
    template_name = 'business_partners/vendor_document_upload.html'
    success_url = reverse_lazy('business_partners:vendor_documents_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        
        # Determine which relationship to use based on context
        if hasattr(self.request.user, 'vendor_application'):
            kwargs['vendor_application'] = self.request.user.vendor_application
        elif hasattr(self.request.user, 'business_partner'):
            kwargs['business_partner'] = self.request.user.business_partner
        
        return kwargs
    
    def form_valid(self, form):
        # Set the uploaded_by field
        form.instance.uploaded_by = self.request.user
        
        response = super().form_valid(form)
        
        # Log the upload action
        DocumentAuditLog.log_action(
            document=form.instance,
            action='uploaded',
            user=self.request.user,
            details=f"Document uploaded: {form.instance.title}"
        )
        
        # Add to verification queue if verification is required
        if form.instance.category.verification_required and form.instance.status == 'pending':
            DocumentVerificationQueue.objects.create(
                document=form.instance,
                priority='medium'  # Default priority
            )
        
        messages.success(self.request, f"Document '{form.instance.title}' uploaded successfully and is pending review.")
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Upload Document'
        context['required_documents'] = DocumentCategory.objects.filter(required=True)
        return context


class VendorDocumentsListView(LoginRequiredMixin, ListView):
    """List view for vendor documents"""
    
    model = VendorDocument
    template_name = 'business_partners/vendor_documents_list.html'
    context_object_name = 'documents'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = VendorDocument.objects.select_related(
            'category', 'vendor_application', 'business_partner', 'uploaded_by'
        ).prefetch_related('verification_queue')
        
        # Filter based on user permissions
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(vendor_application__user=self.request.user) |
                Q(business_partner__user=self.request.user)
            )
        
        # Apply search filters
        self.search_form = VendorDocumentSearchForm(self.request.GET, user=self.request.user)
        if self.search_form.is_valid():
            search_query = self.search_form.cleaned_data.get('search_query')
            status = self.search_form.cleaned_data.get('status')
            category = self.search_form.cleaned_data.get('category')
            vendor_application = self.search_form.cleaned_data.get('vendor_application')
            business_partner = self.search_form.cleaned_data.get('business_partner')
            priority = self.search_form.cleaned_data.get('priority')
            expiry_date_from = self.search_form.cleaned_data.get('expiry_date_from')
            expiry_date_to = self.search_form.cleaned_data.get('expiry_date_to')
            uploaded_date_from = self.search_form.cleaned_data.get('uploaded_date_from')
            uploaded_date_to = self.search_form.cleaned_data.get('uploaded_date_to')
            
            if search_query:
                queryset = queryset.filter(
                    Q(title__icontains=search_query) |
                    Q(description__icontains=search_query) |
                    Q(document_number__icontains=search_query)
                )
            
            if status:
                queryset = queryset.filter(status=status)
            
            if category:
                queryset = queryset.filter(category=category)
            
            if vendor_application:
                queryset = queryset.filter(vendor_application=vendor_application)
            
            if business_partner:
                queryset = queryset.filter(business_partner=business_partner)
            
            if priority:
                queryset = queryset.filter(verification_queue__priority=priority)
            
            if expiry_date_from:
                queryset = queryset.filter(expiry_date__gte=expiry_date_from)
            
            if expiry_date_to:
                queryset = queryset.filter(expiry_date__lte=expiry_date_to)
            
            if uploaded_date_from:
                queryset = queryset.filter(uploaded_at__date__gte=uploaded_date_from)
            
            if uploaded_date_to:
                queryset = queryset.filter(uploaded_at__date__lte=uploaded_date_to)
        
        return queryset.order_by('-uploaded_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Vendor Documents'
        context['search_form'] = self.search_form
        context['document_categories'] = DocumentCategory.objects.all()
        
        # Add statistics for staff users
        if self.request.user.is_staff:
            context['stats'] = {
                'total_pending': VendorDocument.objects.filter(status='pending').count(),
                'total_verified': VendorDocument.objects.filter(status='verified').count(),
                'total_rejected': VendorDocument.objects.filter(status='rejected').count(),
                'expiring_soon': VendorDocument.objects.filter(
                    expiry_date__lte=timezone.now().date() + timedelta(days=30),
                    status='verified'
                ).count(),
            }
        
        return context


class VendorDocumentDetailView(LoginRequiredMixin, DetailView):
    """Detail view for vendor documents"""
    
    model = VendorDocument
    template_name = 'business_partners/vendor_document_detail.html'
    context_object_name = 'document'
    
    def get_queryset(self):
        queryset = VendorDocument.objects.select_related(
            'category', 'vendor_application', 'business_partner', 'uploaded_by',
            'verified_by', 'rejected_by'
        ).prefetch_related('audit_logs', 'verification_queue')
        
        # Filter based on user permissions
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(vendor_application__user=self.request.user) |
                Q(business_partner__user=self.request.user)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Document: {self.object.title}"
        
        # Add audit logs
        context['audit_logs'] = self.object.audit_logs.select_related('performed_by')[:10]
        
        # Add verification form for staff users
        if self.request.user.is_staff and self.object.status == 'pending':
            context['verification_form'] = VendorDocumentVerificationForm()
        
        # Log document view
        DocumentAuditLog.log_action(
            document=self.object,
            action='viewed',
            user=self.request.user,
            details=f"Document viewed by {self.request.user.get_full_name() or self.request.user.username}"
        )
        
        return context


@login_required
@permission_required('business_partners.can_verify_documents', raise_exception=True)
def verify_document(request, pk):
    """View for verifying/rejecting documents"""
    
    document = get_object_or_404(VendorDocument, pk=pk)
    
    if request.method == 'POST':
        form = VendorDocumentVerificationForm(request.POST, instance=document)
        if form.is_valid():
            form.save(user=request.user)
            
            # Log the verification action
            action = form.cleaned_data['action']
            DocumentAuditLog.log_action(
                document=document,
                action=action.replace('_', ''),
                user=request.user,
                details=f"Document {action}ed by {request.user.get_full_name() or request.user.username}"
            )
            
            # Complete verification queue entry if exists
            if hasattr(document, 'verification_queue'):
                document.verification_queue.complete_verification()
            
            messages.success(request, f"Document '{document.title}' has been {action}ed successfully.")
            return redirect('business_partners:vendor_document_detail', pk=document.pk)
    else:
        form = VendorDocumentVerificationForm(instance=document)
    
    context = {
        'form': form,
        'document': document,
        'page_title': f'Verify Document: {document.title}',
    }
    
    return render(request, 'business_partners/verify_document.html', context)


class DocumentVerificationQueueView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """View for managing document verification queue"""
    
    model = DocumentVerificationQueue
    template_name = 'business_partners/document_verification_queue.html'
    context_object_name = 'queue_items'
    permission_required = 'business_partners.can_verify_documents'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = DocumentVerificationQueue.objects.select_related(
            'document', 'document__category', 'document__vendor_application',
            'document__business_partner', 'assigned_to'
        ).filter(completed_at__isnull=True)
        
        # Filter by assigned user if specified
        assigned_to = self.request.GET.get('assigned_to')
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # Filter by priority if specified
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        return queryset.order_by('-priority', 'created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Document Verification Queue'
        
        # Add queue statistics
        context['queue_stats'] = {
            'total_pending': queryset.filter(assigned_to__isnull=True).count(),
            'assigned_to_me': queryset.filter(assigned_to=self.request.user).count(),
            'urgent_items': queryset.filter(priority='urgent').count(),
            'high_priority': queryset.filter(priority='high').count(),
        }
        
        return context


@login_required
@permission_required('business_partners.can_verify_documents', raise_exception=True)
def assign_document_verification(request, pk):
    """Assign document verification to a user"""
    
    queue_item = get_object_or_404(DocumentVerificationQueue, pk=pk)
    
    if request.method == 'POST':
        form = DocumentVerificationQueueForm(request.POST, instance=queue_item)
        if form.is_valid():
            if form.cleaned_data.get('assigned_to'):
                queue_item.assign_to_user(form.cleaned_data['assigned_to'])
                messages.success(request, f"Document verification assigned to {form.cleaned_data['assigned_to'].get_full_name() or form.cleaned_data['assigned_to'].username}")
            else:
                queue_item.assigned_to = None
                queue_item.assigned_at = None
                queue_item.save()
                messages.success(request, "Document verification unassigned")
            
            return redirect('business_partners:document_verification_queue')
    else:
        form = DocumentVerificationQueueForm(instance=queue_item)
    
    context = {
        'form': form,
        'queue_item': queue_item,
        'page_title': f'Assign Verification: {queue_item.document.title}',
    }
    
    return render(request, 'business_partners/assign_document_verification.html', context)


@login_required
def download_document(request, pk):
    """Secure document download view"""
    
    document = get_object_or_404(VendorDocument, pk=pk)
    
    # Check permissions
    if not request.user.is_staff:
        if not (
            (document.vendor_application and document.vendor_application.user == request.user) or
            (document.business_partner and document.business_partner.user == request.user)
        ):
            return HttpResponse("Permission denied", status=403)
    
    if not document.file:
        return HttpResponse("Document file not found", status=404)
    
    # Log the download action
    DocumentAuditLog.log_action(
        document=document,
        action='downloaded',
        user=request.user,
        details=f"Document downloaded by {request.user.get_full_name() or request.user.username}",
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    # Serve the file
    response = HttpResponse(document.file.read(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{document.file.name.split("/")[-1]}"'
    return response


@login_required
@permission_required('business_partners.can_verify_documents', raise_exception=True)
def bulk_document_actions(request):
    """Handle bulk actions on documents"""
    
    if request.method == 'POST':
        form = BulkDocumentActionForm(request.POST, user=request.user)
        if form.is_valid():
            action = form.cleaned_data['action']
            documents = form.cleaned_data['document_ids']
            
            success_count = 0
            error_count = 0
            
            for document in documents:
                try:
                    if action == 'verify':
                        document.verify(
                            user=request.user,
                            notes=form.cleaned_data.get('verification_notes', '')
                        )
                    elif action == 'reject':
                        document.reject(
                            user=request.user,
                            reason=form.cleaned_data.get('rejection_reason', '')
                        )
                    elif action == 'request_renewal':
                        document.mark_needs_renewal()
                    elif action == 'assign_priority':
                        if hasattr(document, 'verification_queue'):
                            document.verification_queue.priority = form.cleaned_data['priority']
                            document.verification_queue.save()
                    
                    success_count += 1
                    
                except Exception as e:
                    error_count += 1
                    # Log error but continue with other documents
                    continue
            
            if action == 'export':
                # Handle export separately
                return export_documents(documents)
            
            messages.success(
                request,
                f"Bulk action completed: {success_count} documents processed successfully, {error_count} errors."
            )
            return redirect('business_partners:vendor_documents_list')
    else:
        return redirect('business_partners:vendor_documents_list')


def export_documents(documents):
    """Export selected documents as CSV"""
    import csv
    from io import StringIO
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Document Number', 'Title', 'Category', 'Vendor/Application',
        'Status', 'Uploaded By', 'Uploaded At', 'Verified By', 'Verified At',
        'Expiry Date', 'File Size (MB)'
    ])
    
    # Write data
    for document in documents:
        writer.writerow([
            document.document_number,
            document.title,
            document.category.name,
            str(document.business_partner or document.vendor_application),
            document.get_status_display(),
            document.uploaded_by.get_full_name() if document.uploaded_by else '',
            document.uploaded_at.strftime('%Y-%m-%d %H:%M:%S'),
            document.verified_by.get_full_name() if document.verified_by else '',
            document.verified_at.strftime('%Y-%m-%d %H:%M:%S') if document.verified_at else '',
            document.expiry_date.strftime('%Y-%m-%d') if document.expiry_date else '',
            document.file_size_mb
        ])
    
    # Create response
    response = HttpResponse(output.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="vendor_documents_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    return response