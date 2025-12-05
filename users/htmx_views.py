"""
HTMX Views for Users Module
Server-side rendered views for user authentication and profile management
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.contrib.auth.models import User

from parts.models import Order


# =====================
# AUTHENTICATION
# =====================

@require_http_methods(["GET"])
def login_form_htmx(request):
    """
    HTMX endpoint for login form
    Returns login form HTML fragment
    """
    return render(request, 'users/htmx/login_form.html')


@require_http_methods(["POST"])
def login_submit_htmx(request):
    """
    HTMX endpoint to handle login
    Returns success/error HTML fragment
    """
    username = request.POST.get('username')
    password = request.POST.get('password')

    user = authenticate(request, username=username, password=password)

    if user is not None:
        login(request, user)
        context = {
            'message': 'Login successful',
            'redirect_url': request.POST.get('next', '/'),
        }
        return render(request, 'users/htmx/login_success.html', context)
    else:
        context = {
            'error': 'Invalid username or password',
        }
        return render(request, 'users/htmx/login_error.html', context)


@require_http_methods(["POST"])
def logout_htmx(request):
    """
    HTMX endpoint for logout
    Returns logout confirmation HTML fragment
    """
    logout(request)

    context = {
        'message': 'You have been logged out',
    }

    return render(request, 'users/htmx/logout_success.html', context)


# =====================
# REGISTRATION
# =====================

@require_http_methods(["GET"])
def register_form_htmx(request):
    """
    HTMX endpoint for registration form
    Returns registration form HTML fragment
    """
    return render(request, 'users/htmx/register_form.html')


@require_http_methods(["POST"])
def register_submit_htmx(request):
    """
    HTMX endpoint to handle registration
    Returns success/error HTML fragment
    """
    username = request.POST.get('username')
    email = request.POST.get('email')
    password = request.POST.get('password')
    password_confirm = request.POST.get('password_confirm')
    first_name = request.POST.get('first_name', '')
    last_name = request.POST.get('last_name', '')

    # Validation
    if password != password_confirm:
        context = {'error': 'Passwords do not match'}
        return render(request, 'users/htmx/register_error.html', context)

    if User.objects.filter(username=username).exists():
        context = {'error': 'Username already exists'}
        return render(request, 'users/htmx/register_error.html', context)

    if User.objects.filter(email=email).exists():
        context = {'error': 'Email already registered'}
        return render(request, 'users/htmx/register_error.html', context)

    # Create user
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name
    )

    # Auto login
    login(request, user)

    context = {
        'message': 'Registration successful',
        'user': user,
    }

    return render(request, 'users/htmx/register_success.html', context)


# =====================
# USER PROFILE
# =====================

@login_required
@require_http_methods(["GET"])
def user_profile_htmx(request):
    """
    HTMX endpoint for user profile
    Returns profile HTML fragment
    """
    user = request.user

    # Get user statistics
    total_orders = Order.objects.filter(user=user).count()
    total_spent = sum(
        order.total_amount
        for order in Order.objects.filter(user=user)
    )

    context = {
        'user': user,
        'total_orders': total_orders,
        'total_spent': total_spent,
    }

    return render(request, 'users/htmx/profile.html', context)


@login_required
@require_http_methods(["GET"])
def user_profile_edit_htmx(request):
    """
    HTMX endpoint for edit profile form
    Returns edit form HTML fragment
    """
    context = {
        'user': request.user,
    }

    return render(request, 'users/htmx/profile_edit_form.html', context)


@login_required
@require_http_methods(["POST"])
def user_profile_update_htmx(request):
    """
    HTMX endpoint to update user profile
    Returns updated profile HTML fragment
    """
    user = request.user

    user.first_name = request.POST.get('first_name', '')
    user.last_name = request.POST.get('last_name', '')
    user.email = request.POST.get('email', user.email)
    user.save()

    context = {
        'user': user,
        'message': 'Profile updated successfully',
    }

    return render(request, 'users/htmx/profile.html', context)


# =====================
# USER DASHBOARD
# =====================

@login_required
@require_http_methods(["GET"])
def user_dashboard_htmx(request):
    """
    HTMX endpoint for user dashboard
    Returns dashboard HTML fragment
    """
    user = request.user

    # Recent orders
    recent_orders = Order.objects.filter(
        user=user
    ).order_by('-created_at')[:5]

    # Statistics
    total_orders = Order.objects.filter(user=user).count()
    pending_orders = Order.objects.filter(user=user, status='pending').count()
    completed_orders = Order.objects.filter(user=user, status='completed').count()

    context = {
        'user': user,
        'recent_orders': recent_orders,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'completed_orders': completed_orders,
    }

    return render(request, 'users/htmx/dashboard.html', context)


# =====================
# USER ORDERS
# =====================

@login_required
@require_http_methods(["GET"])
def user_orders_htmx(request):
    """
    HTMX endpoint for user orders list
    Returns orders HTML fragment
    """
    status_filter = request.GET.get('status', 'all')

    orders = Order.objects.filter(user=request.user).prefetch_related('items__part')

    if status_filter != 'all':
        orders = orders.filter(status=status_filter)

    orders = orders.order_by('-created_at')

    context = {
        'orders': orders,
        'status_filter': status_filter,
    }

    return render(request, 'users/htmx/orders_list.html', context)


@login_required
@require_http_methods(["GET"])
def user_order_detail_htmx(request, order_id):
    """
    HTMX endpoint for user order detail
    Returns order detail HTML fragment
    """
    order = get_object_or_404(
        Order.objects.prefetch_related('items__part'),
        id=order_id,
        user=request.user
    )

    context = {
        'order': order,
    }

    return render(request, 'users/htmx/order_detail.html', context)


# =====================
# PASSWORD MANAGEMENT
# =====================

@login_required
@require_http_methods(["GET"])
def change_password_form_htmx(request):
    """
    HTMX endpoint for change password form
    Returns form HTML fragment
    """
    return render(request, 'users/htmx/change_password_form.html')


@login_required
@require_http_methods(["POST"])
def change_password_submit_htmx(request):
    """
    HTMX endpoint to change password
    Returns success/error HTML fragment
    """
    user = request.user
    old_password = request.POST.get('old_password')
    new_password = request.POST.get('new_password')
    confirm_password = request.POST.get('confirm_password')

    # Validation
    if not user.check_password(old_password):
        context = {'error': 'Current password is incorrect'}
        return render(request, 'users/htmx/password_error.html', context)

    if new_password != confirm_password:
        context = {'error': 'New passwords do not match'}
        return render(request, 'users/htmx/password_error.html', context)

    if len(new_password) < 8:
        context = {'error': 'Password must be at least 8 characters'}
        return render(request, 'users/htmx/password_error.html', context)

    # Update password
    user.set_password(new_password)
    user.save()

    # Re-login user
    login(request, user)

    context = {
        'message': 'Password changed successfully',
    }

    return render(request, 'users/htmx/password_success.html', context)


# =====================
# ACCOUNT SETTINGS
# =====================

@login_required
@require_http_methods(["GET"])
def account_settings_htmx(request):
    """
    HTMX endpoint for account settings
    Returns settings HTML fragment
    """
    context = {
        'user': request.user,
    }

    return render(request, 'users/htmx/account_settings.html', context)


@login_required
@require_http_methods(["POST"])
def update_email_preferences_htmx(request):
    """
    HTMX endpoint to update email preferences
    Returns updated preferences HTML fragment
    """
    # In a real app, you'd have a UserProfile model with email preferences
    # For now, just return success

    context = {
        'message': 'Email preferences updated',
    }

    return render(request, 'users/htmx/preferences_success.html', context)


@login_required
@require_http_methods(["POST"])
def deactivate_account_htmx(request):
    """
    HTMX endpoint to deactivate account
    Returns confirmation HTML fragment
    """
    user = request.user
    user.is_active = False
    user.save()

    logout(request)

    context = {
        'message': 'Your account has been deactivated',
    }

    return render(request, 'users/htmx/account_deactivated.html', context)
