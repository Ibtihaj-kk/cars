"""
Admin authentication views for Cars Portal admin panel.
Provides secure login/logout with comprehensive logging and 2FA support.
"""
import logging
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.conf import settings
from datetime import timedelta
import pyotp
import qrcode
import io
import base64

from .utils import log_activity, get_client_ip
from .models import ActivityLogType
from .decorators import admin_required
from users.models import User, UserRole

logger = logging.getLogger('security')


@csrf_protect
@never_cache
@require_http_methods(["GET", "POST"])
def admin_login_view(request):
    """
    Admin panel login view with enhanced security features.
    """
    # Redirect if already authenticated admin
    if request.user.is_authenticated and _is_admin_user(request.user):
        return redirect('admin_panel:dashboard')
    
    if request.method == 'POST':
        return _handle_login_post(request)
    
    # GET request - show login form
    context = {
        'next': request.GET.get('next', ''),
        'login_attempts': request.session.get('admin_login_attempts', 0),
        'max_attempts': getattr(settings, 'ADMIN_MAX_LOGIN_ATTEMPTS', 5),
    }
    
    return render(request, 'admin_panel/auth/login.html', context)


def _handle_login_post(request):
    """Handle POST request for admin login."""
    email = request.POST.get('email', '').strip().lower()
    password = request.POST.get('password', '')
    otp_code = request.POST.get('otp_code', '').strip()
    remember_me = request.POST.get('remember_me') == 'on'
    next_url = request.POST.get('next', '')
    
    # Basic validation
    if not email or not password:
        messages.error(request, 'Email and password are required.')
        return redirect('admin_panel:login')
    
    # Check login attempts
    login_attempts = request.session.get('admin_login_attempts', 0)
    max_attempts = getattr(settings, 'ADMIN_MAX_LOGIN_ATTEMPTS', 5)
    
    if login_attempts >= max_attempts:
        # Log brute force attempt
        logger.warning(
            f"Admin login blocked due to too many attempts from IP {get_client_ip(request)} "
            f"for email {email}"
        )
        
        messages.error(request, 'Too many login attempts. Please try again later.')
        return redirect('admin_panel:login')
    
    # Authenticate user
    user = authenticate(request, username=email, password=password)
    
    if user is None:
        # Invalid credentials
        request.session['admin_login_attempts'] = login_attempts + 1
        
        # Log failed login attempt
        log_activity(
            user=None,
            action_type=ActivityLogType.LOGIN,
            description=f"Failed admin login attempt for email: {email}",
            request=request,
            data={
                'email': email,
                'reason': 'invalid_credentials',
                'attempt_number': login_attempts + 1
            }
        )
        
        messages.error(request, 'Invalid email or password.')
        return redirect('admin_panel:login')
    
    # Check if user is admin
    if not _is_admin_user(user):
        request.session['admin_login_attempts'] = login_attempts + 1
        
        # Log unauthorized access attempt
        log_activity(
            user=user,
            action_type=ActivityLogType.LOGIN,
            description="Non-admin user attempted to access admin panel",
            request=request,
            data={
                'email': email,
                'user_role': getattr(user, 'role', 'unknown'),
                'reason': 'insufficient_privileges'
            }
        )
        
        messages.error(request, 'You do not have permission to access the admin panel.')
        return redirect('admin_panel:login')
    
    # Check 2FA if enabled
    if user.is_2fa_enabled:
        if not otp_code:
            # Store user ID in session for 2FA verification
            request.session['admin_2fa_user_id'] = user.id
            request.session['admin_2fa_timestamp'] = timezone.now().isoformat()
            
            context = {
                'require_2fa': True,
                'email': email,
                'next': next_url,
            }
            return render(request, 'admin_panel/auth/login.html', context)
        
        # Verify OTP
        if not _verify_otp(user, otp_code):
            request.session['admin_login_attempts'] = login_attempts + 1
            
            # Log failed 2FA attempt
            log_activity(
                user=user,
                action_type=ActivityLogType.LOGIN,
                description="Failed 2FA verification for admin login",
                request=request,
                data={
                    'email': email,
                    'reason': 'invalid_2fa_code'
                }
            )
            
            messages.error(request, 'Invalid 2FA code.')
            return redirect('admin_panel:login')
    
    # Successful authentication - log in user
    login(request, user)
    
    # Clear login attempts
    request.session.pop('admin_login_attempts', None)
    request.session.pop('admin_2fa_user_id', None)
    request.session.pop('admin_2fa_timestamp', None)
    
    # Set session timeout
    if not remember_me:
        request.session.set_expiry(getattr(settings, 'ADMIN_SESSION_TIMEOUT', 30) * 60)
    
    # Initialize admin session data
    request.session['admin_login_time'] = timezone.now().isoformat()
    request.session['admin_last_activity'] = timezone.now().isoformat()
    request.session['admin_session_ips'] = [get_client_ip(request)]
    
    # Log successful login
    log_activity(
        user=user,
        action_type=ActivityLogType.LOGIN,
        description="Successful admin panel login",
        request=request,
        data={
            'remember_me': remember_me,
            'session_timeout': not remember_me
        }
    )
    
    messages.success(request, f'Welcome back, {user.first_name or user.email}!')
    
    # Redirect to next URL or dashboard
    if next_url and next_url.startswith('/admin-panel/'):
        return redirect(next_url)
    
    return redirect('admin_panel:dashboard')


@login_required
@require_http_methods(["GET", "POST"])
def admin_logout_view(request):
    """
    Admin panel logout view with session cleanup.
    """
    if request.method == 'POST':
        return _handle_logout_post(request)
    
    # GET request - show logout confirmation
    return render(request, 'admin_panel/auth/logout.html')


def _handle_logout_post(request):
    """Handle POST request for admin logout."""
    user = request.user
    
    # Log logout
    log_activity(
        user=user,
        action_type=ActivityLogType.LOGOUT,
        description="Admin panel logout",
        request=request,
        data={
            'session_duration': _calculate_session_duration(request),
            'logout_type': 'manual'
        }
    )
    
    # Clear admin session data
    admin_session_keys = [
        'admin_login_time',
        'admin_last_activity', 
        'admin_session_ips',
        'admin_2fa_user_id',
        'admin_2fa_timestamp'
    ]
    
    for key in admin_session_keys:
        request.session.pop(key, None)
    
    # Logout user
    logout(request)
    
    messages.success(request, 'You have been successfully logged out.')
    return redirect('admin_panel:login')


@admin_required(min_role='staff')
def setup_2fa_view(request):
    """
    Setup 2FA for admin users.
    """
    user = request.user
    
    if request.method == 'POST':
        return _handle_2fa_setup_post(request)
    
    # Generate QR code for 2FA setup
    if not user.otp_secret:
        user.otp_secret = pyotp.random_base32()
        user.save()
    
    # Generate QR code
    totp = pyotp.TOTP(user.otp_secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="Cars Portal Admin"
    )
    
    # Create QR code image
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_code_data = base64.b64encode(buffer.getvalue()).decode()
    
    context = {
        'qr_code_data': qr_code_data,
        'secret_key': user.otp_secret,
        'is_2fa_enabled': user.is_2fa_enabled,
    }
    
    return render(request, 'admin_panel/auth/setup_2fa.html', context)


def _handle_2fa_setup_post(request):
    """Handle 2FA setup POST request."""
    user = request.user
    otp_code = request.POST.get('otp_code', '').strip()
    
    if not otp_code:
        messages.error(request, 'Please enter the 2FA code.')
        return redirect('admin_panel:setup_2fa')
    
    # Verify OTP code
    if _verify_otp(user, otp_code):
        user.is_2fa_enabled = True
        user.save()
        
        # Log 2FA setup
        log_activity(
            user=user,
            action_type=ActivityLogType.OTHER,
            description="2FA enabled for admin account",
            request=request
        )
        
        messages.success(request, '2FA has been successfully enabled for your account.')
        return redirect('admin_panel:dashboard')
    else:
        messages.error(request, 'Invalid 2FA code. Please try again.')
        return redirect('admin_panel:setup_2fa')


@admin_required(min_role='staff')
@require_http_methods(["POST"])
def disable_2fa_view(request):
    """
    Disable 2FA for admin users.
    """
    user = request.user
    password = request.POST.get('password', '')
    
    # Verify password before disabling 2FA
    if not user.check_password(password):
        messages.error(request, 'Invalid password.')
        return redirect('admin_panel:setup_2fa')
    
    # Disable 2FA
    user.is_2fa_enabled = False
    user.otp_secret = None
    user.save()
    
    # Log 2FA disable
    log_activity(
        user=user,
        action_type=ActivityLogType.OTHER,
        description="2FA disabled for admin account",
        request=request
    )
    
    messages.warning(request, '2FA has been disabled for your account.')
    return redirect('admin_panel:setup_2fa')


# Helper functions

def _is_admin_user(user):
    """Check if user has admin privileges."""
    return (
        user.is_authenticated and 
        (user.is_staff or user.is_superuser or 
         getattr(user, 'role', None) in [UserRole.ADMIN, UserRole.STAFF]) and
        not getattr(user, 'is_banned', False) and 
        not getattr(user, 'is_suspended', False) and 
        not getattr(user, 'is_deleted', False)
    )


def _verify_otp(user, otp_code):
    """Verify OTP code for 2FA."""
    if not user.otp_secret:
        return False
    
    totp = pyotp.TOTP(user.otp_secret)
    return totp.verify(otp_code, valid_window=1)


def _calculate_session_duration(request):
    """Calculate admin session duration."""
    login_time_str = request.session.get('admin_login_time')
    if not login_time_str:
        return None
    
    try:
        login_time = timezone.datetime.fromisoformat(login_time_str)
        duration = timezone.now() - login_time
        return str(duration)
    except (ValueError, TypeError):
        return None