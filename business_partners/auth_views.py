from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.views.generic import View
from django.http import JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.db.models import Q
import pyotp
import qrcode
import io
import base64
from .models import BusinessPartner, VendorProfile
from .permissions import get_vendor_profile
from .forms import VendorLoginForm, VendorPasswordResetForm, Vendor2FAForm, VendorSettingsForm
from .rate_limiting import rate_limit_operation
from .audit_logger import VendorAuditLogger

User = get_user_model()


class VendorLoginView(View):
    """Vendor login view with 2FA support"""
    
    template_name = 'business_partners/vendor_login.html'
    
    def get(self, request):
        # If user is already authenticated, redirect them away from login page
        if request.user.is_authenticated:
            vendor_profile = get_vendor_profile(request.user)
            if vendor_profile:
                # Redirect to dashboard regardless of approval status
                # Dashboard will show pending approval message if needed
                return redirect('business_partners:vendor_dashboard')
            else:
                # Authenticated user but no vendor profile - redirect to dashboard or home
                # This prevents regular users from accessing vendor login
                if request.user.is_staff or request.user.is_superuser:
                    return redirect('/admin/')
                else:
                    # Regular authenticated user - redirect to main site or profile
                    return redirect('/')
        
        # Not authenticated - show login form
        form = VendorLoginForm()
        return render(request, self.template_name, {'form': form})
    
    @method_decorator(rate_limit_operation('login'))
    def post(self, request):
        form = VendorLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            
            # Authenticate user
            user = authenticate(request, username=email, password=password)
            
            if user is not None:
                vendor_profile = get_vendor_profile(user)
                
                if vendor_profile is None:
                    messages.error(request, 'No vendor profile found. Please complete your vendor registration.')
                else:
                    # Allow login regardless of approval status
                    # Check if 2FA is enabled
                    if vendor_profile.two_factor_enabled:
                        # Store user in session and redirect to 2FA verification
                        request.session['pre_2fa_user_id'] = user.id
                        return redirect('business_partners:vendor_2fa_verify')
                    else:
                            # Use CentralizedAuthenticationService to establish secure session with all security flags
                            from core.authentication import CentralizedAuthenticationService
                            auth_service = CentralizedAuthenticationService()
                            auth_service.establish_secure_session(request, user, backend='django.contrib.auth.backends.ModelBackend')
                            
                            messages.success(request, f'Welcome back, {user.get_full_name() or user.email}!')
                            return redirect('business_partners:vendor_dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
        
        return render(request, self.template_name, {'form': form})


class Vendor2FAVerifyView(View):
    """2FA verification view for vendors"""
    
    template_name = 'business_partners/vendor_2fa_verify.html'
    
    def get(self, request):
        # If user is already fully authenticated, redirect away from 2FA page
        if request.user.is_authenticated:
            vendor_profile = get_vendor_profile(request.user)
            if vendor_profile and vendor_profile.is_approved:
                return redirect('business_partners:vendor_dashboard')
            elif vendor_profile:
                return redirect('business_partners:vendor_registration_status')
            else:
                # Regular authenticated user
                if request.user.is_staff or request.user.is_superuser:
                    return redirect('/admin/')
                else:
                    return redirect('/')
        
        # Check if user is in pre-2FA state
        if 'pre_2fa_user_id' not in request.session:
            return redirect('business_partners:vendor_login')
        
        user_id = request.session['pre_2fa_user_id']
        try:
            user = User.objects.get(id=user_id)
            vendor_profile = get_vendor_profile(user)
            
            form = Vendor2FAForm()
            return render(request, self.template_name, {
                'form': form,
                'backup_codes_remaining': vendor_profile.backup_codes_remaining()
            })
        except (User.DoesNotExist, VendorProfile.DoesNotExist):
            return redirect('business_partners:vendor_login')
    
    @method_decorator(rate_limit_operation('login'))
    def post(self, request):
        if 'pre_2fa_user_id' not in request.session:
            return redirect('business_partners:vendor_login')
        
        form = Vendor2FAForm(request.POST)
        if form.is_valid():
            token = form.cleaned_data['token']
            user_id = request.session['pre_2fa_user_id']
            
            try:
                user = User.objects.get(id=user_id)
                vendor_profile = get_vendor_profile(user)
                
                if vendor_profile is None:
                    messages.error(request, 'Authentication error.')
                else:
                    # Verify 2FA token
                    totp = pyotp.TOTP(vendor_profile.two_factor_secret)
                    
                    if totp.verify(token, valid_window=1):
                        # Use CentralizedAuthenticationService to establish secure session
                        from core.authentication import CentralizedAuthenticationService
                        auth_service = CentralizedAuthenticationService()
                        auth_service.establish_secure_session(request, user, backend='django.contrib.auth.backends.ModelBackend')
                        
                        del request.session['pre_2fa_user_id']
                        messages.success(request, f'Welcome back, {user.get_full_name() or user.email}!')
                        return redirect('business_partners:vendor_dashboard')
                    else:
                        # Check if it's a backup code
                        if vendor_profile.use_backup_code(token):
                            from core.authentication import CentralizedAuthenticationService
                            auth_service = CentralizedAuthenticationService()
                            auth_service.establish_secure_session(request, user, backend='django.contrib.auth.backends.ModelBackend')
                            
                            del request.session['pre_2fa_user_id']
                            messages.success(request, 'Login successful using backup code.')
                            return redirect('business_partners:vendor_dashboard')
                        else:
                            messages.error(request, 'Invalid authentication code.')
                        
            except User.DoesNotExist:
                messages.error(request, 'Authentication error.')
        
        return render(request, self.template_name, {'form': form})


class Vendor2FASetupView(View):
    """2FA setup view for vendors"""
    
    template_name = 'business_partners/vendor_2fa_setup.html'
    
    @method_decorator(login_required)
    def get(self, request):
        # Already authenticated users should not access login-related pages
        # This decorator ensures only authenticated users can access this view
        # The login_required decorator will handle redirecting non-authenticated users
        vendor_profile = get_vendor_profile(request.user)
        
        if vendor_profile is None:
            messages.error(request, 'Vendor profile not found.')
            return redirect('business_partners:vendor_dashboard')
        
        if vendor_profile.two_factor_enabled:
            messages.info(request, '2FA is already enabled for your account.')
            return redirect('business_partners:vendor_profile_settings')
        
        # Generate 2FA secret
        secret = pyotp.random_base32()
        request.session['2fa_setup_secret'] = secret
        
        # Generate QR code
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=request.user.email,
            issuer_name='CarSyncro Vendor Portal'
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return render(request, self.template_name, {
            'qr_code': f'data:image/png;base64,{qr_code_base64}',
            'secret': secret,
            'manual_code': totp_uri
        })
    
    @method_decorator(login_required)
    @method_decorator(rate_limit_operation('2fa_setup'))
    def post(self, request):
        if '2fa_setup_secret' not in request.session:
            return redirect('business_partners:vendor_2fa_setup')
        
        token = request.POST.get('token')
        secret = request.session['2fa_setup_secret']
        
        totp = pyotp.TOTP(secret)
        
        if totp.verify(token, valid_window=1):
            vendor_profile = get_vendor_profile(request.user)
            
            if vendor_profile is None:
                messages.error(request, 'Vendor profile not found.')
            else:
                vendor_profile.two_factor_secret = secret
                vendor_profile.two_factor_enabled = True
                vendor_profile.save()
                
                # Generate backup codes
                backup_codes = vendor_profile.generate_backup_codes()
                
                del request.session['2fa_setup_secret']
                
                messages.success(request, 'Two-factor authentication enabled successfully!')
                return render(request, 'business_partners/vendor_2fa_backup_codes.html', {
                    'backup_codes': backup_codes
                })
        else:
            messages.error(request, 'Invalid verification code. Please try again.')
        
        return redirect('business_partners:vendor_2fa_setup')


class VendorPasswordResetRequestView(View):
    """Password reset request view for vendors"""
    
    template_name = 'business_partners/vendor_password_reset_request.html'
    
    def get(self, request):
        # If user is already authenticated, redirect them away from password reset
        if request.user.is_authenticated:
            vendor_profile = get_vendor_profile(request.user)
            if vendor_profile and vendor_profile.is_approved:
                return redirect('business_partners:vendor_dashboard')
            elif vendor_profile:
                return redirect('business_partners:vendor_registration_status')
            else:
                # Regular authenticated user
                if request.user.is_staff or request.user.is_superuser:
                    return redirect('/admin/')
                else:
                    return redirect('/')
        
        form = VendorPasswordResetForm()
        return render(request, self.template_name, {'form': form})
    
    @method_decorator(rate_limit_operation('password_reset'))
    def post(self, request):
        form = VendorPasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            try:
                user = User.objects.get(email=email)
                vendor_profile = get_vendor_profile(user)
                
                if vendor_profile is None:
                    # Don't reveal whether email exists for security
                    messages.success(request, 'If a vendor account exists with this email, password reset instructions have been sent.')
                elif not vendor_profile.is_approved:
                    messages.error(request, 'Your vendor application is still under review.')
                    return redirect('business_partners:vendor_registration_status')
                else:
                    # Generate password reset token
                    token = default_token_generator.make_token(user)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    
                    # Build reset URL
                    reset_url = request.build_absolute_uri(
                        f'/business-partners/password-reset-confirm/{uid}/{token}/'
                    )
                    
                    # Send reset email
                    subject = 'Password Reset - CarSyncro Vendor Portal'
                    html_message = render_to_string('business_partners/emails/vendor_password_reset.html', {
                        'user': user,
                        'reset_url': reset_url,
                        'site_name': 'CarSyncro Vendor Portal'
                    })
                    plain_message = strip_tags(html_message)
                    
                    send_mail(
                        subject,
                        plain_message,
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        html_message=html_message
                    )
                    
                    messages.success(request, 'Password reset instructions have been sent to your email.')
                    return redirect('business_partners:vendor_login')
                
            except User.DoesNotExist:
                # Don't reveal whether email exists for security
                messages.success(request, 'If a vendor account exists with this email, password reset instructions have been sent.')
                return redirect('business_partners:vendor_login')
        
        return render(request, self.template_name, {'form': form})


class VendorPasswordResetConfirmView(View):
    """Password reset confirmation view for vendors"""
    
    template_name = 'business_partners/vendor_password_reset_confirm.html'
    
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            return render(request, self.template_name, {
                'validlink': True,
                'uidb64': uidb64,
                'token': token
            })
        else:
            messages.error(request, 'Password reset link is invalid or has expired.')
            return redirect('business_partners:vendor_password_reset_request')
    
    @method_decorator(rate_limit_operation('password_reset_confirm'))
    def post(self, request, uidb64, token):
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, self.template_name, {
                'validlink': True,
                'uidb64': uidb64,
                'token': token
            })
        
        if len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, self.template_name, {
                'validlink': True,
                'uidb64': uidb64,
                'token': token
            })
        
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        
        if user is not None and default_token_generator.check_token(user, token):
            user.set_password(password)
            user.save()
            messages.success(request, 'Your password has been reset successfully. You can now log in with your new password.')
            return redirect('business_partners:vendor_login')
        else:
            messages.error(request, 'Password reset link is invalid or has expired.')
            return redirect('business_partners:vendor_password_reset_request')


@login_required
def vendor_logout_view(request):
    """Vendor logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login') 


@login_required
def vendor_profile_settings_view(request):
    """Vendor profile settings view"""
    try:
        vendor_profile = get_vendor_profile(request.user)
        if not vendor_profile:
            messages.error(request, 'Vendor profile not found.')
            return redirect('business_partners:vendor_dashboard')
            
        # Get the business partner associated with this vendor profile
        business_partner = vendor_profile.business_partner
        if not business_partner:
            messages.error(request, 'Business partner not found.')
            return redirect('business_partners:vendor_dashboard')
        
        context = {
            'vendor_profile': vendor_profile,
            'business_partner': business_partner,
            'backup_codes_remaining': vendor_profile.backup_codes_remaining()
        }
        
        return render(request, 'business_partners/vendor_profile_settings.html', context)
        
    except AttributeError:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_dashboard')


@login_required
def vendor_profile_view(request):
    """Vendor profile view"""
    # Handle profile picture upload if present
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        request.user.profile_picture = request.FILES['profile_picture']
        request.user.save()
        messages.success(request, 'Profile picture updated successfully.')
        return redirect('business_partners:vendor_profile')
        
    vendor_profile = get_vendor_profile(request.user)
    
    return render(request, 'vendors/profile.html', {
        'vendor_profile': vendor_profile
    })


@login_required
def vendor_profile_update_view(request):
    """Handle vendor profile personal info update"""
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        
        user = request.user
        user.first_name = first_name
        user.last_name = last_name
        user.phone_number = phone_number
        user.save()
        
        messages.success(request, 'Profile updated successfully.')
    
    return redirect('business_partners:vendor_profile')


@login_required
def vendor_password_change_view(request):
    """Handle vendor password change"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        user = request.user
        
        if not user.check_password(old_password):
            messages.error(request, 'Current password is incorrect.')
        elif new_password != confirm_password:
            messages.error(request, 'New passwords do not match.')
        elif len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        else:
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password updated successfully.')
            
    return redirect('business_partners:vendor_profile')


@login_required
def vendor_settings_view(request):
    """Vendor business settings view"""
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile or not vendor_profile.business_partner:
        messages.error(request, 'Vendor profile not found.')
        return redirect('business_partners:vendor_dashboard')
        
    business_partner = vendor_profile.business_partner
    
    # Get documents from VendorDocument model (collected during registration)
    from business_partners.document_models import VendorDocument
    registration_documents = VendorDocument.objects.filter(
        business_partner=business_partner,
        status='verified'
    ).select_related('category')
    
    # Create a dictionary of registration documents for easy access
    registration_docs_dict = {}
    for doc in registration_documents:
        category_name = doc.category.name.lower().replace(' ', '_')
        registration_docs_dict[category_name] = doc
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'remove_logo':
            if business_partner.logo:
                business_partner.logo.delete()
                business_partner.save()
                messages.success(request, 'Logo removed successfully.')
            return redirect('business_partners:vendor_settings')
            
        form = VendorSettingsForm(request.POST, request.FILES, business_partner=business_partner)
        if form.is_valid():
            form.save()
            messages.success(request, 'Business settings updated successfully.')
            return redirect('business_partners:vendor_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = VendorSettingsForm(business_partner=business_partner)
    
    return render(request, 'vendors/settings.html', {
        'form': form,
        'vendor': business_partner,
        'vendor_profile': vendor_profile,
        'registration_documents': registration_docs_dict
    })
