from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import get_user_model, login, logout
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
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
from parts.models import SaudiCity, CityArea

User = get_user_model()


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
        """Send verification email to the user."""
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{user.email_verification_token}/"
        
        # In a real app, you would use a template and send a proper HTML email
        subject = 'Verify your email address'
        html_message = f'''
        <html>
            <body>
                <h2>Welcome to CorporateDock!</h2>
                <p>Thank you for registering. Please click the link below to verify your email address:</p>
                <p><a href="{verification_url}">Verify Email</a></p>
                <p>This link will expire in 24 hours.</p>
                <p>If you did not register for a CorporateDock account, please ignore this email.</p>
            </body>
        </html>
        '''
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            # Log the error but don't prevent user registration
            pass


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
        # In a real app, you would verify the token here
        # For now, we'll just return success
        
        return Response({
            'message': 'Email verified successfully.'
        }, status=status.HTTP_200_OK)


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
    cities = SaudiCity.objects.filter(is_active=True).order_by('name')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        full_name = request.POST.get('full_name')
        address = request.POST.get('address')
        city_id = request.POST.get('city_id')
        city_area_id = request.POST.get('city_area_id')
        country = request.POST.get('country')
        phone = request.POST.get('phone')
        
        # Resolve city name from ID
        city_name = ""
        if city_id:
            try:
                city_obj = SaudiCity.objects.get(id=city_id)
                city_name = city_obj.name
            except SaudiCity.DoesNotExist:
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
        
        try:
            services = json.loads(services_json)
        except:
            services = []
        
        # Basic validation
        if not email or not password or not full_name:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'user/registration.html', {'cities': cities})

        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'user/registration.html', {'cities': cities})
            
        try:
            user = None
            with transaction.atomic():
                # Split full name
                names = full_name.strip().split(' ', 1)
                first_name = names[0]
                last_name = names[1] if len(names) > 1 else ''
                
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
                    user.profile.selected_services = services
                    user.profile.save()
                
            # Login
            if user:
                if not hasattr(user, 'backend'):
                     user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                
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
        context.update({
            'total_listings': user_listings.count(),
            'total_inquiries': user_inquiries.count(),
            'recent_listings': user_listings.order_by('-created_at')[:5],
            'recent_inquiries': user_inquiries.order_by('-created_at')[:5],
        })
    else:
        # Client/User context
        orders = Order.objects.filter(customer=user)
        saved_listings = SavedListing.objects.filter(user=user)
        
        total_spent = orders.aggregate(Sum('total_price'))['total_price__sum'] or 0
        
        context.update({
            'total_orders': orders.count(),
            'pending_orders_count': orders.filter(status__in=['pending', 'confirmed', 'processing']).count(),
            'total_spent': total_spent,
            'recent_orders': orders.order_by('-created_at')[:5],
            'saved_listings_count': saved_listings.count(),
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
    
    # Get cities for dropdown
    from parts.models import SaudiCity, CityArea
    cities = SaudiCity.objects.filter(is_active=True).order_by('name')
    
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
                # Keep user logged in
                login(request, user)
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
                    city_obj = SaudiCity.objects.get(id=city_id)
                    profile.city = city_obj.name
                except SaudiCity.DoesNotExist:
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
            
            profile.country = request.POST.get('country', profile.country)
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
