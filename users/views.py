from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from rest_framework import viewsets, permissions, status, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import (
    IsOwnerOrAdmin, IsAdminOrStaff, IsAdmin, IsSeller, IsBuyer, 
    IsSellerOrAdmin, IsActiveUser, CanManageUsers, CanViewAuditLogs
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import json
from django.contrib.auth.decorators import login_required

from .models import UserProfile, UserRole, UserAuditLog
from .serializers import (
    UserSerializer, 
    UserRegistrationSerializer,
    UserUpdateSerializer,
    PasswordChangeSerializer,
    UserProfileSerializer,
    CustomTokenObtainPairSerializer,
    VerifyOTPSerializer,
    EmailVerificationSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    AdminUserSerializer,
    UserAuditLogSerializer,
    BanUserSerializer,
    SuspendUserSerializer,
    RoleChangeSerializer,
    ProfileUpdateSerializer
)
from core.permissions import IsAdminUser, IsOwnerOrAdmin
from parts.models import City, CityArea

User = get_user_model()


class LoginView(auth_views.LoginView):
    """
    Custom LoginView that uses CentralizedAuthenticationService
    to ensure robust session establishment.
    """
    def form_valid(self, form):
        """Security-enhanced session establishment on successful login."""
        user = form.get_user()
        
        # Use CentralizedAuthenticationService for robust session establishment
        from core.authentication import CentralizedAuthenticationService
        auth_service = CentralizedAuthenticationService()
        
        # Establish session with all security flags
        auth_service.establish_secure_session(
            self.request, 
            user, 
            remember_me=form.cleaned_data.get('remember_me', False),
            backend=user.backend if hasattr(user, 'backend') else 'django.contrib.auth.backends.ModelBackend'
        )
        
        # Perform standard redirect
        return redirect(self.get_success_url())


class UserRegistrationView(generics.CreateAPIView):
    """View for user registration."""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Send verification email
        self.send_verification_email(user)
        
        # Generate tokens for the user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user, context=self.get_serializer_context()).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'User registered successfully. Please verify your email.'
        }, status=status.HTTP_201_CREATED)
    
    def send_verification_email(self, user):
        """Send verification email to the user using centralized email service."""
        # Skip if user doesn't require email verification (e.g., vendor employees)
        if not getattr(user, 'requires_email_verification', True):
            return None

        from django.urls import reverse
        
        # Build absolute URL using reverse and request or SITE_URL
        try:
            path = reverse('users:verify-email', kwargs={'token': user.email_verification_token})
            verification_url = f"{settings.FRONTEND_URL}{path}"
        except:
            # Fallback
            verification_url = f"{settings.FRONTEND_URL}/api/users/verify-email/{user.email_verification_token}/"
        
        try:
            from core.email_service.orchestrator import send_email
            
            email_id = send_email(
                email_type='verification',
                to_email=user.email,
                subject='Verify Your Email Address - CarSyncro',
                template_name='email_verification',
                context={
                    'user_name': user.first_name or user.email,
                    'verification_url': verification_url,
                    'expiration_hours': 24
                },
                priority='high'
            )
            
            # Log successful email queuing
            import logging
            logger = logging.getLogger('email_notifications')
            logger.info(f"Verification email queued for {user.email} with ID: {email_id}")
            
        except Exception as e:
            # Log the error but don't prevent user registration
            import logging
            logger = logging.getLogger('email_notifications')
            logger.error(f"Failed to queue verification email for {user.email}: {e}")
            
            # Fallback to direct sending if orchestrator fails
            try:
                subject = 'Verify your email address'
                html_message = f'''
                <html>
                    <body>
                        <h2>Welcome to CarSyncro!</h2>
                        <p>Thank you for registering. Please click the link below to verify your email address:</p>
                        <p><a href="{verification_url}">Verify Email</a></p>
                        <p>This link will expire in 24 hours.</p>
                        <p>If you did not register for a CarSyncro account, please ignore this email.</p>
                    </body>
                </html>
                '''
                plain_message = strip_tags(html_message)
                
                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                    fail_silently=False,
                )
            except Exception as fallback_error:
                logger.error(f"Fallback email sending also failed for {user.email}: {fallback_error}")


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom view for token generation."""
    serializer_class = CustomTokenObtainPairSerializer


class VerifyOTPView(generics.GenericAPIView):
    """View for OTP verification."""
    serializer_class = VerifyOTPSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # In a real app, you would verify the OTP here
        # For now, we'll just return success
        
        return Response({
            'message': 'OTP verified successfully.'
        }, status=status.HTTP_200_OK)


class EmailVerificationView(generics.GenericAPIView):
    """View for email verification."""
    serializer_class = EmailVerificationSerializer
    permission_classes = [AllowAny]
    
    def get(self, request, token, *args, **kwargs):
        """Handle email verification via GET request (clicking the link in email)."""
        from core.email_service.handlers.verification_handler import EmailVerificationHandler
        from django.shortcuts import redirect
        from django.contrib import messages
        from django.urls import reverse
        
        handler = EmailVerificationHandler()
        user = handler.verify_email_token(token)
        
        if user:
            messages.success(request, 'Your email has been successfully verified! You can now log in.')
            
            # Check if user is a vendor to redirect to vendor login
            try:
                if hasattr(user, 'vendor_profiles') and user.vendor_profiles.exists():
                    return redirect('business_partners:vendor_login')
            except:
                pass
                
            return redirect('login')
        else:
            messages.error(request, 'The verification link is invalid or has expired.')
            # Try to redirect to vendor login if possible, else default login
            return redirect('login')


class PasswordResetRequestView(generics.GenericAPIView):
    """View for password reset request."""
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        # In a real app, you would generate a token and send a reset email
        
        return Response({
            'message': 'If an account exists with this email, a password reset link has been sent.'
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    """View for password reset confirmation."""
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # In a real app, you would verify the token and reset the password
        
        return Response({
            'message': 'Password has been reset successfully.'
        }, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for viewing and editing user instances.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users can only see their own profile unless they are admins
        user = self.request.user
        if user.is_staff or user.role == UserRole.ADMIN:
            return User.objects.all()
        return User.objects.filter(id=user.id)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'change_password':
            return PasswordChangeSerializer
        return UserSerializer
    
    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        user = request.user
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password updated successfully.'}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get', 'patch'], url_path='profile')
    def profile(self, request):
        user = request.user
        
        if request.method == 'GET':
            # Create profile if it doesn't exist
            if not hasattr(user, 'profile'):
                UserProfile.objects.create(user=user)
            
            serializer = UserProfileSerializer(user.profile)
            return Response(serializer.data)
        
        elif request.method == 'PATCH':
            # Create profile if it doesn't exist
            if not hasattr(user, 'profile'):
                UserProfile.objects.create(user=user)
                
            serializer = UserProfileSerializer(user.profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for admin to manage users.
    """
    queryset = User.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, CanManageUsers]
    filterset_fields = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'phone_number']
    ordering_fields = ['date_joined', 'last_login', 'email']
    
    @action(detail=True, methods=['post'], serializer_class=BanUserSerializer)
    def ban(self, request, pk=None):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            reason = serializer.validated_data.get('reason', '')
            user.is_active = False
            user.save()
            
            # Log the action
            UserAuditLog.objects.create(
                actor=request.user,
                target=user,
                action='BAN',
                details={'reason': reason},
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response({'message': f'User {user.email} has been banned.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], serializer_class=SuspendUserSerializer)
    def suspend(self, request, pk=None):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            duration_days = serializer.validated_data['duration_days']
            reason = serializer.validated_data.get('reason', '')
            
            # Logic for suspension (e.g., setting a suspension end date)
            # For now, we'll just deactivate the user
            user.is_active = False
            user.save()
            
            # Log the action
            UserAuditLog.objects.create(
                actor=request.user,
                target=user,
                action='SUSPEND',
                details={'duration_days': duration_days, 'reason': reason},
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response({'message': f'User {user.email} has been suspended for {duration_days} days.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        user = self.get_object()
        user.is_active = True
        user.save()
        
        # Log the action
        UserAuditLog.objects.create(
            actor=request.user,
            target=user,
            action='ACTIVATE',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return Response({'message': f'User {user.email} has been activated.'})
    
    @action(detail=True, methods=['post'], serializer_class=RoleChangeSerializer)
    def change_role(self, request, pk=None):
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            new_role = serializer.validated_data['role']
            old_role = user.role
            
            user.role = new_role
            user.save()
            
            # Log the action
            UserAuditLog.objects.create(
                actor=request.user,
                target=user,
                action='CHANGE_ROLE',
                details={'old_role': old_role, 'new_role': new_role},
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return Response({'message': f'User role changed to {new_role}.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing audit logs.
    """
    queryset = UserAuditLog.objects.all()
    serializer_class = UserAuditLogSerializer
    permission_classes = [IsAuthenticated, CanViewAuditLogs]
    filterset_fields = ['action', 'actor', 'target']
    ordering_fields = ['timestamp']


class ProfileUpdateView(generics.UpdateAPIView):
    """
    View for users to update their own profile.
    """
    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        user = self.request.user
        if not hasattr(user, 'profile'):
            UserProfile.objects.create(user=user)
        return user.profile


class DashboardView(generics.RetrieveAPIView):
    """
    View for user dashboard data.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        
        data = {
            'user': UserSerializer(user).data,
            'role': user.role,
        }
        
        # Add role-specific data
        if user.role == UserRole.BUYER:
            # Add buyer specific data (e.g., recent orders, wishlist)
            pass
        elif user.role == UserRole.SELLER:
            # Add seller specific data (e.g., sales, products)
            pass
        elif user.role == UserRole.ADMIN:
            # Add admin specific data (e.g., user stats, system health)
            data['total_users'] = User.objects.count()
            data['active_users'] = User.objects.filter(is_active=True).count()
        
        return Response(data)

# ==========================================
# Template Views
# ==========================================

def register_page(request):
    # If user is already authenticated, redirect them away
    if request.user.is_authenticated:
        return redirect('users:user-dashboard')

    # Add message if present in query params
    msg = request.GET.get('msg')
    if msg:
        messages.info(request, msg)

    # Get cities for dropdown
    from parts.models import City
    cities = City.objects.filter(is_active=True).order_by('name')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        address = request.POST.get('address')
        city_id = request.POST.get('city_id')
        city_area_id = request.POST.get('city_area_id')
        country = request.POST.get('country')
        phone = request.POST.get('phone')
        terms_accepted = bool(request.POST.get('terms_accepted'))
        
        # Resolve city name from ID
        city_name = ""
        if city_id:
            try:
                city_obj = City.objects.get(id=city_id)
                city_name = city_obj.name
            except City.DoesNotExist:
                pass
        
        # Resolve city area name from ID
        city_area_name = ""
        if city_area_id:
            try:
                area_obj = CityArea.objects.get(id=city_area_id)
                city_area_name = area_obj.name
            except CityArea.DoesNotExist:
                pass

        # New fields
        postal_code = request.POST.get('postal_code')
        national_id = request.POST.get('national_id')
        tax_id = request.POST.get('tax_id')
        role_value = request.POST.get('role', 'client')
        services_json = request.POST.get('services', '[]')
        
        # Name fields
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        
        try:
            services = json.loads(services_json)
        except:
            services = []
        
        # Basic validation
        if not email or not password or not first_name or not last_name:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'user/registration.html', {'cities': cities})

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'user/registration.html', {'cities': cities})

        if not terms_accepted:
            messages.error(request, 'Please accept the Terms & Conditions to continue.')
            return render(request, 'user/registration.html', {'cities': cities})

        try:
            from django.contrib.auth.password_validation import validate_password
            from django.core.exceptions import ValidationError
            validate_password(password)
        except Exception as e:
            try:
                if isinstance(e, ValidationError):
                    messages.error(request, " ".join(e.messages))
                else:
                    messages.error(request, 'Password does not meet the required rules.')
            except Exception:
                messages.error(request, 'Password does not meet the required rules.')
            return render(request, 'user/registration.html', {'cities': cities})

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'user/registration.html', {'cities': cities})
            
        try:
            user = None
            with transaction.atomic():
                # Determine role
                role = UserRole.SELLER if role_value == 'seller' else UserRole.CLIENT

                # Create User
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number=phone,
                    role=role
                )
                
                # Get currency based on country
                from business_partners.utils import get_currency_for_country
                currency = get_currency_for_country(country)

                # Create Profile (if not exists)
                if not hasattr(user, 'profile'):
                    UserProfile.objects.create(
                        user=user,
                        address=address,
                        city=city_name,
                        city_area=city_area_name,
                        country=country,
                        postal_code=postal_code,
                        national_id=national_id,
                        tax_id=tax_id,
                        preferred_currency=currency,
                        selected_services=services
                    )
                else:
                    # Update existing profile
                    user.profile.address = address
                    user.profile.city = city_name
                    user.profile.city_area = city_area_name
                    user.profile.country = country
                    user.profile.postal_code = postal_code
                    user.profile.national_id = national_id
                    user.profile.tax_id = tax_id
                    user.profile.preferred_currency = currency
                    user.profile.selected_services = services
                    user.profile.save()

                # Handle Vendor/Seller specific logic
                if role == UserRole.SELLER:
                    from business_partners.models import BusinessPartner, VendorProfile, VendorApplication, BusinessPartnerRole
                    
                    # 1. Handle Vendor Application
                    # Check for existing anonymous application in session
                    # Ensure session exists to get key
                    if not request.session.session_key:
                        request.session.create()
                    session_key = request.session.session_key
                    
                    vendor_app = None
                    if session_key:
                        # Find the most recent anonymous application for this session
                        # We prefer one that has some data (e.g. company_name) over an empty draft
                        candidates = VendorApplication.objects.filter(session_key=session_key, user__isnull=True).order_by('-updated_at')
                        
                        # Try to find one with company name first
                        for app in candidates:
                            if app.company_name:
                                vendor_app = app
                                break
                        
                        # If no app with data, take the most recent one (even if draft)
                        if not vendor_app and candidates.exists():
                            vendor_app = candidates.first()
                    
                    if vendor_app:
                        # Link anonymous application to new user
                        vendor_app.user = user
                        # Only update status if it's still in draft or early stages
                        if vendor_app.status in ['draft', 'business_details_completed']:
                            vendor_app.status = 'business_details_completed'
                        vendor_app.save()
                    else:
                        # Check if an application was just created for this email (to avoid duplicates)
                        # searching by email is a fallback
                        existing_app = VendorApplication.objects.filter(business_email=email, user__isnull=True).order_by('-created_at').first()
                        if existing_app:
                             existing_app.user = user
                             if existing_app.status in ['draft', 'business_details_completed']:
                                existing_app.status = 'business_details_completed'
                             existing_app.save()
                             vendor_app = existing_app
                        else:
                            # Create new application if none exists
                            vendor_app = VendorApplication.objects.create(
                                user=user,
                                status='business_details_completed',
                                company_name=user.profile.company_name or f"{first_name} {last_name}",
                                business_email=email,
                                contact_person_name=f"{first_name} {last_name}",
                                business_phone=phone,
                                street_address=address,
                                city=city_name,
                                country=country,
                                postal_code=postal_code
                            )
                    
                    # 2. Create Business Partner (which generates BP number)
                    # Check if BP already exists
                    if not BusinessPartner.objects.filter(user=user).exists():
                        # Create BP - BP Number is auto-generated in save()
                        bp = BusinessPartner(
                            user=user,
                            name=vendor_app.company_name or f"{first_name} {last_name}",
                            type='company',
                            status='active',
                            created_by=user
                        )
                        bp.save()
                        
                        # Add Vendor Role
                        BusinessPartnerRole.objects.create(business_partner=bp, role_type='vendor')
                        
                        # Create Vendor Profile
                        if not hasattr(bp, 'vendor_profile'):
                            VendorProfile.objects.create(
                                business_partner=bp,
                                user=user,
                                preferred_currency=currency,
                                registration_date=timezone.now().date(),
                                contact_person_name=f"{first_name} {last_name}",
                                is_approved=False # Explicitly set approval status
                            )
                
            # Login
            if user:
                if not hasattr(user, 'backend'):
                     user.backend = 'django.contrib.auth.backends.ModelBackend'
                
                # Use CentralizedAuthenticationService for robust session establishment
                from core.authentication import CentralizedAuthenticationService
                auth_service = CentralizedAuthenticationService()
                auth_service.establish_secure_session(request, user, backend=user.backend)
                
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('users:user-dashboard')
                
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'user/registration.html', {'cities': cities})
            
    return render(request, 'user/registration.html', {'cities': cities})


@login_required
def user_dashboard(request):
    """Render user dashboard with context data."""
    user = request.user
    
    # Import models locally
    from listings.models import VehicleListing, SavedListing
    from inquiries.models import ListingInquiry
    from parts.models import Order
    from finance.models import Wallet
    from django.contrib.contenttypes.models import ContentType
    
    # Common context
    context = {
        'user': user,
        'profile': getattr(user, 'profile', None),
    }
    
    if user.role == UserRole.ADMIN:
        # Admin context
        context.update({
            'total_users': User.objects.count(),
            'total_listings': VehicleListing.objects.count(),
            'total_inquiries': ListingInquiry.objects.count(),
        })
    elif user.role == UserRole.SELLER:
        # Seller context
        user_listings = VehicleListing.objects.filter(user=user)
        user_inquiries = ListingInquiry.objects.filter(listing__user=user)
        
        # Get or create vendor wallet
        from business_partners.models import BusinessPartner
        vendor = BusinessPartner.objects.filter(user=user).first()
        wallet = None
        if vendor:
            vendor_ct = ContentType.objects.get_for_model(vendor)
            wallet, _ = Wallet.objects.get_or_create(
                owner_content_type=vendor_ct,
                owner_id=vendor.id,
                defaults={'currency': 'USD'}
            )
            
        context.update({
            'total_listings': user_listings.count(),
            'total_inquiries': user_inquiries.count(),
            'recent_listings': user_listings.order_by('-created_at')[:5],
            'recent_inquiries': user_inquiries.order_by('-created_at')[:5],
            'wallet': wallet,
        })
    else:
        # Client/User context
        # Ensure currency profile exists
        from business_partners.models import BusinessPartner, BusinessPartnerRole, CustomerProfile
        from business_partners.utils import get_currency_for_country
        
        # Check if user has country in their profile
        profile = getattr(user, 'profile', None)
        if profile and profile.country:
            # Check if BusinessPartner exists
            if not BusinessPartner.objects.filter(user=user).exists():
                currency = get_currency_for_country(profile.country)
                bp = BusinessPartner.objects.create(
                    user=user,
                    name=user.get_full_name() or user.email,
                    type='individual',
                    status='active',
                    created_by=user
                )
                BusinessPartnerRole.objects.create(business_partner=bp, role_type='customer')
                CustomerProfile.objects.create(
                    business_partner=bp,
                    preferred_currency=currency
                )
            # If BP exists but no CustomerProfile or incorrect currency
            else:
                bp = BusinessPartner.objects.filter(user=user).first()
                if bp:
                    currency = get_currency_for_country(profile.country)
                    if not hasattr(bp, 'customer_profile'):
                        CustomerProfile.objects.create(
                            business_partner=bp,
                            preferred_currency=currency
                        )
                    elif bp.customer_profile.preferred_currency != currency:
                        bp.customer_profile.preferred_currency = currency
                        bp.customer_profile.save()

        orders = Order.objects.filter(customer=user)
        saved_listings = SavedListing.objects.filter(user=user)
        
        total_spent = orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        # Get or create user wallet
        user_ct = ContentType.objects.get_for_model(user)
        wallet, _ = Wallet.objects.get_or_create(
            owner_content_type=user_ct,
            owner_id=user.id,
            defaults={'currency': 'USD'}
        )
        
        context.update({
            'total_orders': orders.count(),
            'pending_orders_count': orders.filter(status__in=['pending', 'confirmed', 'processing']).count(),
            'total_spent': total_spent,
            'recent_orders': orders.order_by('-created_at')[:5],
            'saved_listings_count': saved_listings.count(),
            'wallet': wallet,
        })
        
    return render(request, 'user/user_dashboard.html', context)


@login_required
def user_profile(request):
    """Render and handle user profile updates."""
    user = request.user
    
    # Ensure profile exists
    if not hasattr(user, 'profile'):
        UserProfile.objects.create(user=user)
    
    profile = user.profile
    
    # Check if we need to set preferred currency for new profile
    if hasattr(profile, 'country') and profile.country and not hasattr(profile, 'preferred_currency'):
        # This assumes UserProfile model has been updated to have preferred_currency
        # If not, we might need to rely on CustomerProfile
        pass
        
    # Ensure CustomerProfile exists for currency preference
    from business_partners.models import BusinessPartner, BusinessPartnerRole, CustomerProfile
    from business_partners.utils import get_currency_for_country
    
    # Try to find existing business partner for this user
    bp = BusinessPartner.objects.filter(user=user, roles__role_type='customer').first()
    
    if not bp:
        # Check if user has country in their profile
        country = getattr(profile, 'country', None)
        currency = get_currency_for_country(country) if country else 'USD'
        
        # Create BusinessPartner for customer if it doesn't exist
        # This is needed because currency preference is stored in CustomerProfile
        if not BusinessPartner.objects.filter(user=user).exists():
            bp = BusinessPartner.objects.create(
                user=user,
                name=user.get_full_name() or user.email,
                type='individual',
                status='active',
                created_by=user
            )
            BusinessPartnerRole.objects.create(business_partner=bp, role_type='customer')
            
            CustomerProfile.objects.create(
                business_partner=bp,
                preferred_currency=currency
            )
    
    # Get cities for dropdown
    from parts.models import City, CityArea
    cities = City.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'change_password':
            current_password = request.POST.get('current_password')
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if not user.check_password(current_password):
                messages.error(request, 'Incorrect current password.')
            elif new_password != confirm_password:
                messages.error(request, 'New passwords do not match.')
            elif len(new_password) < 8:
                messages.error(request, 'Password must be at least 8 characters long.')
            else:
                user.set_password(new_password)
                user.save()
                # Keep user logged in with robust session setup
                from core.authentication import CentralizedAuthenticationService
                auth_service = CentralizedAuthenticationService()
                auth_service.establish_secure_session(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Password updated successfully.')
                
            return redirect('users:user-profile')
            
        else:
            # Update User fields
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.phone_number = request.POST.get('phone', user.phone_number)
            user.save()
            
            # Update Profile fields
            profile.address = request.POST.get('address', profile.address)
            
            # Handle City (ID or Name)
            city_id = request.POST.get('city_id')
            if city_id:
                try:
                    city_obj = City.objects.get(id=city_id)
                    profile.city = city_obj.name
                except City.DoesNotExist:
                    pass
            else:
                # Fallback to text input if needed or just keep existing
                city_name = request.POST.get('city')
                if city_name:
                    profile.city = city_name
            
            # Handle City Area
            city_area_id = request.POST.get('city_area_id')
            if city_area_id:
                try:
                    area_obj = CityArea.objects.get(id=city_area_id)
                    profile.city_area = area_obj.name
                except CityArea.DoesNotExist:
                    pass
            else:
                city_area_name = request.POST.get('city_area')
                if city_area_name:
                    profile.city_area = city_area_name
            
            # Handle country update
            new_country = request.POST.get('country')
            if new_country and new_country != profile.country:
                profile.country = new_country
                
                # Update currency if country changed
                from business_partners.models import BusinessPartner, CustomerProfile
                from business_partners.utils import get_currency_for_country
                
                currency = get_currency_for_country(new_country)
                
                # Find or create customer profile to update currency
                bp = BusinessPartner.objects.filter(user=user, roles__role_type='customer').first()
                if bp:
                    if hasattr(bp, 'customer_profile'):
                        bp.customer_profile.preferred_currency = currency
                        bp.customer_profile.save()
                    else:
                        CustomerProfile.objects.create(
                            business_partner=bp,
                            preferred_currency=currency
                        )
            elif new_country is not None:
                profile.country = new_country
            profile.postal_code = request.POST.get('postal_code', profile.postal_code)
            profile.national_id = request.POST.get('national_id', profile.national_id)
            profile.tax_id = request.POST.get('tax_id', profile.tax_id)
            profile.bio = request.POST.get('bio', profile.bio)
            profile.save()
            
            messages.success(request, 'Profile updated successfully.')
            return redirect('users:user-profile')
        
    context = {
        'user': user,
        'profile': profile,
        'cities': cities
    }
    return render(request, 'user/profile.html', context)


@login_required
def user_orders(request):
    """Render user orders list."""
    from parts.models import Order
    from django.core.paginator import Paginator
    
    user = request.user
    orders_list = Order.objects.filter(customer=user).select_related('customer').prefetch_related(
        'items__part__brand', 
        'status_history'
    ).order_by('-created_at')
    
    paginator = Paginator(orders_list, 10)  # Show 10 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'user': user,
        'orders': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'user/orders_list.html', context)

@login_required
def logout_view(request):
    """Logout user and redirect to home."""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')

@require_GET
def check_email_availability(request):
    """Check if email is available for registration."""
    email = request.GET.get('email', '').strip()
    
    if not email:
        return JsonResponse({'available': False, 'error': 'Email is required'}, status=400)
    
    # Check if user exists
    exists = User.objects.filter(email__iexact=email).exists()
    
    return JsonResponse({
        'available': not exists,
        'message': 'Email is available' if not exists else 'Email is already registered'
    })
