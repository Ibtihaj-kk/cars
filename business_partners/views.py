"""
Multi-step vendor registration views with comprehensive workflow management.
Handles the complete vendor onboarding process with step-by-step validation.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import View, TemplateView
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.conf import settings
import json

from .models import VendorApplication
from .forms import (
    VendorApplicationStep1Form, VendorApplicationStep2Form,
    VendorApplicationStep3Form, VendorApplicationStep4Form,
    VendorApplicationSubmissionForm, VendorApplicationReviewForm
)


class VendorRegistrationMixin:
    """Mixin for vendor registration views with common functionality"""
    
    def get_or_create_application(self, user):
        """Get existing application or create new one"""
        if user.is_authenticated:
            application, created = VendorApplication.objects.get_or_create(
                user=user,
                status__in=['draft', 'business_details_completed', 
                           'contact_info_completed', 'bank_details_completed',
                           'requires_changes'],
                defaults={'status': 'draft', 'current_step': 1}
            )
        else:
            # For anonymous users, create a temporary session-based application
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            
            # Try to get existing application for this session
            application = VendorApplication.objects.filter(
                session_key=session_key,
                status__in=['draft', 'business_details_completed', 
                           'contact_info_completed', 'bank_details_completed',
                           'requires_changes']
            ).first()
            
            if not application:
                # Create new application for anonymous user
                application = VendorApplication.objects.create(
                    session_key=session_key,
                    status='draft',
                    current_step=1
                )
        
        return application
    
    def get_step_url(self, step):
        """Get URL for specific step"""
        step_urls = {
            1: 'vendor_registration_step1',
            2: 'vendor_registration_step2', 
            3: 'vendor_registration_step3',
            4: 'vendor_registration_step4',
            'review': 'vendor_registration_review',
            'submit': 'vendor_registration_submit'
        }
        return reverse(f'business_partners:{step_urls.get(step, "vendor_registration_step1")}')
    
    def check_step_access(self, application, requested_step):
        """Check if user can access the requested step"""
        if requested_step == 1:
            return True
        elif requested_step == 2:
            return application.is_step_completed(1)
        elif requested_step == 3:
            return application.is_step_completed(2)
        elif requested_step == 4:
            return application.is_step_completed(3)
        return False


class VendorRegistrationStartView(VendorRegistrationMixin, TemplateView):
    """Landing page for vendor registration"""
    template_name = 'business_partners/vendor_registration_start.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Handle anonymous users
        if not self.request.user.is_authenticated:
            # Check for existing session-based application
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            
            application = VendorApplication.objects.filter(
                session_key=session_key,
                status__in=['draft', 'business_details_completed', 
                           'contact_info_completed', 'bank_details_completed',
                           'requires_changes']
            ).first()
            
            context['existing_application'] = application
            context['next_step_url'] = self.get_step_url(application.current_step if application else 1)
            context['requires_login'] = False  # No login required for anonymous users
            return context
        
        # Check if user already has an application
        try:
            application = VendorApplication.objects.get(
                user=self.request.user,
                status__in=['draft', 'business_details_completed', 
                           'contact_info_completed', 'bank_details_completed',
                           'requires_changes']
            )
            context['existing_application'] = application
            context['next_step_url'] = self.get_step_url(application.current_step)
        except VendorApplication.DoesNotExist:
            context['existing_application'] = None
            context['next_step_url'] = self.get_step_url(1)
        
        # Check if user already has approved application
        approved_application = VendorApplication.objects.filter(
            user=self.request.user,
            status='approved'
        ).first()
        
        if approved_application:
            context['approved_application'] = approved_application
        
        return context


class VendorRegistrationStep1View(VendorRegistrationMixin, View):
    """Step 1: Business Details"""
    template_name = 'business_partners/vendor_registration_step1.html'
    
    def get(self, request):
        application = self.get_or_create_application(request.user)
        
        # Check if user can access this step
        if not self.check_step_access(application, 1):
            messages.error(request, 'Please complete previous steps first.')
            return redirect(self.get_step_url(application.current_step))
        
        form = VendorApplicationStep1Form(instance=application, user=request.user if request.user.is_authenticated else None)
        
        context = {
            'form': form,
            'application': application,
            'current_step': 1,
            'total_steps': 4,
            'step_title': 'Business Details',
            'next_step_url': self.get_step_url(2),
            'completion_percentage': application.get_completion_percentage(),
            'user_authenticated': request.user.is_authenticated
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        application = self.get_or_create_application(request.user)
        form = VendorApplicationStep1Form(
            request.POST, request.FILES, 
            instance=application, user=request.user if request.user.is_authenticated else None
        )
        
        if form.is_valid():
            application = form.save()
            messages.success(request, 'Business details saved successfully!')
            
            # Redirect to next step if this step is completed
            if application.is_step_completed(1):
                return redirect(self.get_step_url(2))
            else:
                return redirect(self.get_step_url(1))
        
        context = {
            'form': form,
            'application': application,
            'current_step': 1,
            'total_steps': 4,
            'step_title': 'Business Details',
            'next_step_url': self.get_step_url(2),
            'completion_percentage': application.get_completion_percentage(),
            'user_authenticated': request.user.is_authenticated
        }
        
        return render(request, self.template_name, context)


class VendorRegistrationStep2View(VendorRegistrationMixin, View):
    """Step 2: Contact Information"""
    template_name = 'business_partners/vendor_registration_step2.html'
    
    def get(self, request):
        application = self.get_or_create_application(request.user)
        
        # Check if user can access this step
        if not self.check_step_access(application, 2):
            messages.error(request, 'Please complete Step 1 first.')
            return redirect(self.get_step_url(1))
        
        form = VendorApplicationStep2Form(instance=application, user=request.user if request.user.is_authenticated else None)
        
        context = {
            'form': form,
            'application': application,
            'current_step': 2,
            'total_steps': 4,
            'step_title': 'Contact Information',
            'prev_step_url': self.get_step_url(1),
            'next_step_url': self.get_step_url(3),
            'completion_percentage': application.get_completion_percentage(),
            'user_authenticated': request.user.is_authenticated
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        application = self.get_or_create_application(request.user)
        form = VendorApplicationStep2Form(
            request.POST, instance=application, user=request.user if request.user.is_authenticated else None
        )
        
        if form.is_valid():
            application = form.save()
            messages.success(request, 'Contact information saved successfully!')
            
            # Redirect to next step if this step is completed
            if application.is_step_completed(2):
                return redirect(self.get_step_url(3))
            else:
                return redirect(self.get_step_url(2))
        
        context = {
            'form': form,
            'application': application,
            'current_step': 2,
            'total_steps': 4,
            'step_title': 'Contact Information',
            'prev_step_url': self.get_step_url(1),
            'next_step_url': self.get_step_url(3),
            'completion_percentage': application.get_completion_percentage(),
            'user_authenticated': request.user.is_authenticated
        }
        
        return render(request, self.template_name, context)


class VendorRegistrationStep3View(VendorRegistrationMixin, View):
    """Step 3: Bank Details"""
    template_name = 'business_partners/vendor_registration_step3.html'
    
    def get(self, request):
        application = self.get_or_create_application(request.user)
        
        # Check if user can access this step
        if not self.check_step_access(application, 3):
            messages.error(request, 'Please complete previous steps first.')
            return redirect(self.get_step_url(application.current_step))
        
        form = VendorApplicationStep3Form(instance=application, user=request.user if request.user.is_authenticated else None)
        
        context = {
            'form': form,
            'application': application,
            'current_step': 3,
            'total_steps': 4,
            'step_title': 'Bank Details',
            'prev_step_url': self.get_step_url(2),
            'next_step_url': self.get_step_url(4),
            'completion_percentage': application.get_completion_percentage(),
            'user_authenticated': request.user.is_authenticated
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        application = self.get_or_create_application(request.user)
        form = VendorApplicationStep3Form(
            request.POST, request.FILES,
            instance=application, user=request.user if request.user.is_authenticated else None
        )
        
        if form.is_valid():
            application = form.save()
            messages.success(request, 'Bank details saved successfully!')
            
            # Redirect to next step if this step is completed
            if application.is_step_completed(3):
                return redirect(self.get_step_url(4))
            else:
                return redirect(self.get_step_url(3))
        
        context = {
            'form': form,
            'application': application,
            'current_step': 3,
            'total_steps': 4,
            'step_title': 'Bank Details',
            'prev_step_url': self.get_step_url(2),
            'next_step_url': self.get_step_url(4),
            'completion_percentage': application.get_completion_percentage(),
            'user_authenticated': request.user.is_authenticated
        }
        
        return render(request, self.template_name, context)


class VendorRegistrationStep4View(VendorRegistrationMixin, View):
    """Step 4: Additional Information (Optional)"""
    template_name = 'business_partners/vendor_registration_step4.html'
    
    def get(self, request):
        application = self.get_or_create_application(request.user)
        
        # Check if user can access this step
        if not self.check_step_access(application, 4):
            messages.error(request, 'Please complete previous steps first.')
            return redirect(self.get_step_url(application.current_step))
        
        form = VendorApplicationStep4Form(instance=application, user=request.user if request.user.is_authenticated else None)
        
        context = {
            'form': form,
            'application': application,
            'current_step': 4,
            'total_steps': 4,
            'step_title': 'Additional Information',
            'prev_step_url': self.get_step_url(3),
            'next_step_url': self.get_step_url('review'),
            'completion_percentage': application.get_completion_percentage(),
            'can_submit': application.can_submit(),
            'user_authenticated': request.user.is_authenticated
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        application = self.get_or_create_application(request.user)
        form = VendorApplicationStep4Form(
            request.POST, instance=application, user=request.user if request.user.is_authenticated else None
        )
        
        if form.is_valid():
            application = form.save()
            messages.success(request, 'Additional information saved successfully!')
            
            # Redirect to review page
            return redirect(self.get_step_url('review'))
        
        context = {
            'form': form,
            'application': application,
            'current_step': 4,
            'total_steps': 4,
            'step_title': 'Additional Information',
            'prev_step_url': self.get_step_url(3),
            'next_step_url': self.get_step_url('review'),
            'completion_percentage': application.get_completion_percentage(),
            'can_submit': application.can_submit(),
            'user_authenticated': request.user.is_authenticated
        }
        
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class VendorRegistrationReviewView(VendorRegistrationMixin, View):
    """Review all information before submission"""
    template_name = 'business_partners/vendor_registration_review.html'
    
    def get(self, request):
        try:
            application = VendorApplication.objects.get(
                user=request.user,
                status__in=['draft', 'business_details_completed', 
                           'contact_info_completed', 'bank_details_completed',
                           'ready_for_submission', 'requires_changes']
            )
        except VendorApplication.DoesNotExist:
            messages.error(request, 'No application found. Please start the registration process.')
            return redirect('vendor_registration_start')
        
        # Check if application can be submitted
        if not application.can_submit():
            messages.error(request, 'Please complete all required steps before review.')
            return redirect(self.get_step_url(application.current_step))
        
        context = {
            'application': application,
            'step_title': 'Review & Submit',
            'completion_percentage': application.get_completion_percentage(),
            'can_submit': application.can_submit()
        }
        
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class VendorRegistrationSubmitView(VendorRegistrationMixin, View):
    """Final submission with terms acceptance"""
    template_name = 'business_partners/vendor_registration_submit.html'
    
    def get(self, request):
        try:
            application = VendorApplication.objects.get(
                user=request.user,
                status__in=['draft', 'business_details_completed', 
                           'contact_info_completed', 'bank_details_completed',
                           'ready_for_submission', 'requires_changes']
            )
        except VendorApplication.DoesNotExist:
            messages.error(request, 'No application found.')
            return redirect('vendor_registration_start')
        
        if not application.can_submit():
            messages.error(request, 'Application is not ready for submission.')
            return redirect(self.get_step_url('review'))
        
        form = VendorApplicationSubmissionForm(application=application)
        
        context = {
            'form': form,
            'application': application,
            'step_title': 'Submit Application'
        }
        
        return render(request, self.template_name, context)
    
    def post(self, request):
        try:
            application = VendorApplication.objects.get(
                user=request.user,
                status__in=['draft', 'business_details_completed', 
                           'contact_info_completed', 'bank_details_completed',
                           'ready_for_submission', 'requires_changes']
            )
        except VendorApplication.DoesNotExist:
            messages.error(request, 'No application found.')
            return redirect('vendor_registration_start')
        
        form = VendorApplicationSubmissionForm(
            request.POST, application=application
        )
        
        if form.is_valid():
            if application.submit_for_review():
                messages.success(
                    request, 
                    f'Application {application.application_id} submitted successfully! '
                    'You will receive an email notification once it has been reviewed.'
                )
                return redirect('vendor_registration_status')
            else:
                messages.error(request, 'Unable to submit application. Please try again.')
        
        context = {
            'form': form,
            'application': application,
            'step_title': 'Submit Application'
        }
        
        return render(request, self.template_name, context)


@method_decorator(login_required, name='dispatch')
class VendorRegistrationStatusView(TemplateView):
    """View application status"""
    template_name = 'business_partners/vendor_registration_status.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all applications for the user
        applications = VendorApplication.objects.filter(
            user=self.request.user
        ).order_by('-created_at')
        
        context['applications'] = applications
        
        # Get current active application
        current_application = applications.filter(
            status__in=['draft', 'business_details_completed', 
                       'contact_info_completed', 'bank_details_completed',
                       'submitted', 'under_review', 'requires_changes']
        ).first()
        
        context['current_application'] = current_application
        
        return context


class VendorRegistrationSubmittedView(TemplateView):
    """View for displaying application submission confirmation"""
    template_name = 'business_partners/vendor_registration_submitted.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the most recent submitted application for the user (or create a demo one)
        if self.request.user.is_authenticated:
            application = VendorApplication.objects.filter(
                user=self.request.user,
                status='submitted'
            ).order_by('-submitted_at').first()
        else:
            # Create a demo application for testing
            from datetime import datetime
            application = type('obj', (object,), {
                'application_id': 'DEMO-APP-12345',
                'company_name': 'Demo Business LLC',
                'business_type': 'corporation',
                'business_email': 'demo@business.com',
                'created_at': datetime.now(),
                'submitted_at': datetime.now(),
                'status': 'submitted'
            })()
        
        if not application:
            # If no submitted application found, redirect to status page
            from django.shortcuts import redirect
            return redirect('vendor_registration_status')
        
        context['application'] = application
        
        # Calculate estimated review time
        from datetime import timedelta
        from django.utils import timezone
        
        estimated_review_date = application.submitted_at + timedelta(days=3)
        context['estimated_review_date'] = estimated_review_date
        
        # Next steps timeline
        context['next_steps'] = [
            {
                'step': 'Document Verification',
                'description': 'Our team will verify all submitted documents and information',
                'duration': '1-2 business days',
                'icon': 'fas fa-file-alt'
            },
            {
                'step': 'Business Verification',
                'description': 'We will conduct business verification and reference checks',
                'duration': '1 business day',
                'icon': 'fas fa-building'
            },
            {
                'step': 'Final Review',
                'description': 'Final review and approval decision will be made',
                'duration': '1 business day',
                'icon': 'fas fa-check-circle'
            },
            {
                'step': 'Account Activation',
                'description': 'You will receive login credentials and can start selling',
                'duration': 'Immediate',
                'icon': 'fas fa-rocket'
            }
        ]
        
        return context


# AJAX endpoints for dynamic functionality
@login_required
@require_http_methods(["POST"])
def validate_iban_ajax(request):
    """AJAX endpoint to validate IBAN"""
    iban = request.POST.get('iban', '').strip().upper()
    
    if not iban:
        return JsonResponse({'valid': False, 'message': 'IBAN is required'})
    
    # Use the same validation logic from the form
    from .forms import VendorApplicationStep3Form
    form = VendorApplicationStep3Form()
    
    try:
        validated_iban = form.clean_iban.__func__(form, iban)
        return JsonResponse({
            'valid': True, 
            'message': 'Valid IBAN',
            'formatted_iban': validated_iban
        })
    except Exception as e:
        return JsonResponse({'valid': False, 'message': str(e)})


@login_required
@require_http_methods(["GET"])
def application_progress_ajax(request):
    """AJAX endpoint to get application progress"""
    try:
        application = VendorApplication.objects.get(
            user=request.user,
            status__in=['draft', 'business_details_completed', 
                       'contact_info_completed', 'bank_details_completed',
                       'requires_changes']
        )
        
        return JsonResponse({
            'exists': True,
            'current_step': application.current_step,
            'status': application.status,
            'completion_percentage': application.get_completion_percentage(),
            'can_submit': application.can_submit(),
            'application_id': application.application_id
        })
    except VendorApplication.DoesNotExist:
        return JsonResponse({'exists': False})


# Admin views for reviewing applications
@login_required
def admin_vendor_applications(request):
    """Admin view to list and manage vendor applications"""
    if not request.user.is_staff:
        raise PermissionDenied
    
    applications = VendorApplication.objects.all().order_by('-created_at')
    
    # Filter by status if provided
    status_filter = request.GET.get('status')
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    context = {
        'applications': applications,
        'status_filter': status_filter,
        'status_choices': VendorApplication.APPLICATION_STATUS
    }
    
    return render(request, 'business_partners/admin_vendor_applications.html', context)


@login_required
def admin_review_application(request, application_id):
    """Admin view to review a specific vendor application"""
    if not request.user.is_staff:
        raise PermissionDenied
    
    application = get_object_or_404(VendorApplication, application_id=application_id)
    
    if request.method == 'POST':
        form = VendorApplicationReviewForm(request.POST, instance=application)
        if form.is_valid():
            action = form.cleaned_data['action']
            notes = form.cleaned_data.get('review_notes', '')
            reason = form.cleaned_data.get('rejection_reason', '')
            
            if action == 'approve':
                business_partner = application.approve(request.user, notes)
                messages.success(
                    request, 
                    f'Application {application.application_id} approved successfully! '
                    f'Business Partner {business_partner.bp_number} created.'
                )
            elif action == 'reject':
                application.reject(request.user, reason, notes)
                messages.success(
                    request, 
                    f'Application {application.application_id} rejected.'
                )
            elif action == 'request_changes':
                application.request_changes(request.user, reason, notes)
                messages.success(
                    request, 
                    f'Changes requested for application {application.application_id}.'
                )
            
            return redirect('admin_vendor_applications')
    else:
        form = VendorApplicationReviewForm(instance=application)
    
    context = {
        'application': application,
        'form': form
    }
    
    return render(request, 'business_partners/admin_review_application.html', context)