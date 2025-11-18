from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
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
from .forms import VendorLoginForm, VendorPasswordResetForm, Vendor2FAForm
from .rate_limiting import rate_limit_operation
from .audit_logger import VendorAuditLogger

User = get_user_model()


class VendorLoginView(View):
    """Vendor login view with 2FA support"""
    
    template_name = 'business_partners/vendor_login.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            vendor_profile = get_vendor_profile(request.user)
            if vendor_profile and vendor_profile.is_approved:
                return redirect('business_partners:vendor_dashboard')
            elif vendor_profile:
                return redirect('business_partners:vendor_registration_status')
        
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
                    messages.error(request, 'Invalid vendor credentials.')
                elif not vendor_profile.is_approved:
                    messages.error(request, 'Your vendor application is still under review. Please wait for approval.')
                    return redirect('business_partners:vendor_registration_status')
                else:
                    # Check if 2FA is enabled
                    if vendor_profile.two_factor_enabled:
                        # Store user in session and redirect to 2FA verification
                        request.session['pre_2fa_user_id'] = user.id
                        return redirect('business_partners:vendor_2fa_verify')
                    else:
                        # Login directly
                        login(request, user)
                        messages.success(request, f'Welcome back, {user.get_full_name() or user.email}!')
                        return redirect('business_partners:vendor_dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
        
        return render(request, self.template_name, {'form': form})


class Vendor2FAVerifyView(View):
    """2FA verification view for vendors"""
    
    template_name = 'business_partners/vendor_2fa_verify.html'
    
    def get(self, request):
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
                        # Login user
                        login(request, user)
                        del request.session['pre_2fa_user_id']
                        messages.success(request, f'Welcome back, {user.get_full_name() or user.email}!')
                        return redirect('business_partners:vendor_dashboard')
                    else:
                        # Check if it's a backup code
                        if vendor_profile.use_backup_code(token):
                            login(request, user)
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
            issuer_name='Cars Portal Vendor Portal'
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
                    subject = 'Password Reset - Cars Portal Vendor Portal'
                    html_message = render_to_string('business_partners/emails/vendor_password_reset.html', {
                        'user': user,
                        'reset_url': reset_url,
                        'site_name': 'Cars Portal Vendor Portal'
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
    return redirect('business_partners:vendor_login')


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