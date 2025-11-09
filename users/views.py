from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
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
                <h2>Welcome to Cars Portal!</h2>
                <p>Thank you for registering. Please click the link below to verify your email address:</p>
                <p><a href="{verification_url}">Verify Email</a></p>
                <p>This link will expire in 24 hours.</p>
                <p>If you did not register for a Cars Portal account, please ignore this email.</p>
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
            print(f"Error sending verification email: {e}")


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token view that uses our serializer."""
    serializer_class = CustomTokenObtainPairSerializer


class VerifyOTPView(generics.GenericAPIView):
    """View for OTP verification."""
    serializer_class = VerifyOTPSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        # Clear OTP after successful verification
        user.otp_secret = None
        user.otp_created_at = None
        user.otp_attempts = 0
        user.save(update_fields=['otp_secret', 'otp_created_at', 'otp_attempts'])
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        })


class EmailVerificationView(generics.GenericAPIView):
    """View for email verification."""
    serializer_class = EmailVerificationSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        user.verify_email()
        
        return Response({
            'message': 'Email verified successfully.'
        })


class PasswordResetRequestView(generics.GenericAPIView):
    """View for password reset request."""
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = User.objects.get(email=email)
            # Generate token
            token = user.generate_email_verification_token()
            
            # Send reset email
            self.send_reset_email(user, token)
            
            return Response({
                'message': 'Password reset email sent.'
            })
        except User.DoesNotExist:
            # Don't reveal that the user doesn't exist
            return Response({
                'message': 'Password reset email sent if the email exists.'
            })
    
    def send_reset_email(self, user, token):
        """Send password reset email to the user."""
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}/"
        
        subject = 'Reset your password'
        html_message = f'''
        <html>
            <body>
                <h2>Password Reset</h2>
                <p>You requested a password reset. Please click the link below to reset your password:</p>
                <p><a href="{reset_url}">Reset Password</a></p>
                <p>This link will expire in 24 hours.</p>
                <p>If you did not request a password reset, please ignore this email.</p>
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
            # Log the error
            print(f"Error sending reset email: {e}")


class PasswordResetConfirmView(generics.GenericAPIView):
    """View for password reset confirmation."""
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        password = serializer.validated_data['password']
        
        # Set new password
        user.set_password(password)
        
        # Clear token
        user.email_verification_token = None
        user.email_verification_sent_at = None
        
        user.save()
        
        return Response({
            'message': 'Password reset successfully.'
        })


class UserViewSet(viewsets.ModelViewSet):
    """ViewSet for user operations."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsActiveUser]
    
    def get_queryset(self):
        """Return users based on role permissions."""
        if self.request.user.role == User.UserRole.ADMIN:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsOwnerOrAdmin]
        elif self.action == 'create':
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Return the current user's profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='change-password')
    def change_password(self, request):
        """Change user's password."""
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'Password changed successfully.'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def enable_2fa(self, request):
        """Enable 2FA for the user."""
        user = request.user
        
        if user.is_2fa_enabled:
            return Response({'message': '2FA is already enabled.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate OTP
        otp = user.generate_otp()
        user.is_2fa_enabled = True
        user.save(update_fields=['is_2fa_enabled'])
        
        # In a real app, send OTP via email or SMS here
        try:
            subject = 'Your 2FA Setup Code'
            message = f'Your verification code is: {otp}. It will expire in 10 minutes.'
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            # Log the error
            print(f"Error sending 2FA setup email: {e}")
        
        return Response({
            'message': '2FA enabled successfully. Please verify with the OTP sent to your email.'
        })
    
    @action(detail=False, methods=['post'])
    def disable_2fa(self, request):
        """Disable 2FA for the user."""
        user = request.user
        
        if not user.is_2fa_enabled:
            return Response({'message': '2FA is not enabled.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.is_2fa_enabled = False
        user.otp_secret = None
        user.otp_created_at = None
        user.otp_attempts = 0
        user.save()
        
        return Response({'message': '2FA disabled successfully.'})
    
    @action(detail=False, methods=['post'])
    def upload_profile_picture(self, request):
        """Upload a profile picture."""
        if 'profile_picture' not in request.FILES:
            return Response({'profile_picture': ['No file was submitted.']}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        user.profile_picture = request.FILES['profile_picture']
        user.save()
        
        return Response({
            'message': 'Profile picture uploaded successfully.',
            'profile_picture': request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None
        })
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Blacklist the refresh token to logout."""
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminUserViewSet(viewsets.ModelViewSet):
    """Admin viewset for comprehensive user management."""
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated, CanManageUsers]
    
    def get_queryset(self):
        """Return all users including soft-deleted ones for admins."""
        return User.objects.all_with_deleted()
    
    @action(detail=True, methods=['post'])
    def ban(self, request, pk=None):
        """Ban a user."""
        user = self.get_object()
        serializer = BanUserSerializer(data=request.data)
        
        if serializer.is_valid():
            reason = serializer.validated_data['reason']
            until = serializer.validated_data.get('until')
            
            user.ban(reason=reason, until=until, banned_by=request.user)
            UserAuditLog.log_action(
                user=user, 
                action='ban', 
                performed_by=request.user,
                details={'reason': reason, 'until': until.isoformat() if until else None},
                request=request
            )
            
            return Response({'message': f'User {user.email} has been banned.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def unban(self, request, pk=None):
        """Unban a user."""
        user = self.get_object()
        
        if not user.is_banned:
            return Response({'error': 'User is not banned.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.unban()
        UserAuditLog.log_action(
            user=user, 
            action='unban', 
            performed_by=request.user,
            request=request
        )
        
        return Response({'message': f'User {user.email} has been unbanned.'})
    
    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend a user."""
        user = self.get_object()
        serializer = SuspendUserSerializer(data=request.data)
        
        if serializer.is_valid():
            reason = serializer.validated_data['reason']
            until = serializer.validated_data.get('until')
            
            user.suspend(reason=reason, until=until, suspended_by=request.user)
            UserAuditLog.log_action(
                user=user, 
                action='suspend', 
                performed_by=request.user,
                details={'reason': reason, 'until': until.isoformat() if until else None},
                request=request
            )
            
            return Response({'message': f'User {user.email} has been suspended.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def unsuspend(self, request, pk=None):
        """Unsuspend a user."""
        user = self.get_object()
        
        if not user.is_suspended:
            return Response({'error': 'User is not suspended.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.unsuspend()
        UserAuditLog.log_action(
            user=user, 
            action='unsuspend', 
            performed_by=request.user,
            request=request
        )
        
        return Response({'message': f'User {user.email} has been unsuspended.'})
    
    @action(detail=True, methods=['delete'])
    def soft_delete(self, request, pk=None):
        """Soft delete a user."""
        user = self.get_object()
        
        if user.is_deleted:
            return Response({'error': 'User is already deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.soft_delete(deleted_by=request.user)
        UserAuditLog.log_action(
            user=user, 
            action='delete', 
            performed_by=request.user,
            request=request
        )
        
        return Response({'message': f'User {user.email} has been soft deleted.'})
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted user."""
        user = self.get_object()
        
        if not user.is_deleted:
            return Response({'error': 'User is not deleted.'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.restore()
        UserAuditLog.log_action(
            user=user, 
            action='restore', 
            performed_by=request.user,
            request=request
        )
        
        return Response({'message': f'User {user.email} has been restored.'})
    
    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        """Change a user's role."""
        user = self.get_object()
        serializer = RoleChangeSerializer(data=request.data)
        
        if serializer.is_valid():
            old_role = user.role
            new_role = serializer.validated_data['role']
            
            user.role = new_role
            user.save(update_fields=['role'])
            
            UserAuditLog.log_action(
                user=user, 
                action='role_change', 
                performed_by=request.user,
                details={'old_role': old_role, 'new_role': new_role},
                request=request
            )
            
            return Response({'message': f'User {user.email} role changed from {old_role} to {new_role}.'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def deleted_users(self, request):
        """Get all soft-deleted users."""
        deleted_users = User.objects.deleted_only()
        serializer = self.get_serializer(deleted_users, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def banned_users(self, request):
        """Get all banned users."""
        banned_users = User.objects.all_with_deleted().filter(is_banned=True)
        serializer = self.get_serializer(banned_users, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def suspended_users(self, request):
        """Get all suspended users."""
        suspended_users = User.objects.all_with_deleted().filter(is_suspended=True)
        serializer = self.get_serializer(suspended_users, many=True)
        return Response(serializer.data)


class UserAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing user audit logs."""
    queryset = UserAuditLog.objects.all()
    serializer_class = UserAuditLogSerializer
    permission_classes = [IsAuthenticated, CanViewAuditLogs]
    
    def get_queryset(self):
        """Filter audit logs by user if specified."""
        queryset = UserAuditLog.objects.all()
        user_id = self.request.query_params.get('user_id')
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        return queryset


class ProfileUpdateView(generics.UpdateAPIView):
    """View for updating user profile information."""
    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated, IsActiveUser]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Send verification email if email was changed
        if 'email' in request.data and request.data['email'] != instance.email:
            self.send_verification_email(serializer.instance)
        
        return Response({
            'message': 'Profile updated successfully.',
            'user': UserSerializer(serializer.instance, context=self.get_serializer_context()).data,
            'email_verification_required': not serializer.instance.is_verified
        }, status=status.HTTP_200_OK)
    
    def send_verification_email(self, user):
        """Send verification email to the user."""
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{user.email_verification_token}/"
        
        subject = 'Verify your new email address'
        html_message = f'''
        <html>
            <body>
                <h2>Email Address Change - Cars Portal</h2>
                <p>You have updated your email address. Please click the link below to verify your new email:</p>
                <p><a href="{verification_url}">Verify New Email</a></p>
                <p>This link will expire in 24 hours.</p>
                <p>If you did not make this change, please contact support immediately.</p>
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
            print(f"Error sending verification email: {e}")


class DashboardView(generics.GenericAPIView):
    """Role-based dashboard API that returns user-specific data."""
    permission_classes = [IsAuthenticated, IsActiveUser]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        
        # Import models here to avoid circular imports
        from listings.models import VehicleListing, SavedListing
        from inquiries.models import ListingInquiry
        
        if user.role == UserRole.ADMIN:
            # Admin dashboard data
            data = {
                'role': 'admin',
                'total_users': User.objects.count(),
                'total_dealers': User.objects.filter(role=UserRole.SELLER).count(),
                'total_clients': User.objects.filter(role=UserRole.USER).count(),
                'total_listings': VehicleListing.objects.count(),
                'published_listings': VehicleListing.objects.filter(status='published').count(),
                'pending_listings': VehicleListing.objects.filter(status='pending_review').count(),
                'total_inquiries': ListingInquiry.objects.count(),
                'new_inquiries': ListingInquiry.objects.filter(status='new').count(),
                'recent_users': UserSerializer(
                    User.objects.order_by('-date_joined')[:5], 
                    many=True, 
                    context={'request': request}
                ).data,
                'recent_listings': self.get_recent_listings_data(VehicleListing.objects.order_by('-created_at')[:5]),
            }
        elif user.role == UserRole.SELLER:
            # Dealer dashboard data
            user_listings = VehicleListing.objects.filter(user=user)
            user_inquiries = ListingInquiry.objects.filter(listing__user=user)
            
            data = {
                'role': 'dealer',
                'total_listings': user_listings.count(),
                'published_listings': user_listings.filter(status='published').count(),
                'pending_listings': user_listings.filter(status='pending_review').count(),
                'draft_listings': user_listings.filter(status='draft').count(),
                'total_inquiries': user_inquiries.count(),
                'new_inquiries': user_inquiries.filter(status='new').count(),
                'viewed_inquiries': user_inquiries.filter(status='viewed').count(),
                'replied_inquiries': user_inquiries.filter(status='replied').count(),
                'saved_by_users': SavedListing.objects.filter(listing__user=user).count(),
                'recent_listings': self.get_recent_listings_data(user_listings.order_by('-created_at')[:5]),
                'recent_inquiries': self.get_recent_inquiries_data(user_inquiries.order_by('-created_at')[:5]),
            }
        else:
            # Regular user dashboard data
            user_saved_listings = SavedListing.objects.filter(user=user)
            user_inquiries = ListingInquiry.objects.filter(user=user)
            
            data = {
                'role': 'user',
                'saved_listings_count': user_saved_listings.count(),
                'inquiries_sent': user_inquiries.count(),
                'inquiries_replied': user_inquiries.filter(status='replied').count(),
                'saved_listings': self.get_saved_listings_data(user_saved_listings[:5]),
                'recent_inquiries': self.get_recent_inquiries_data(user_inquiries.order_by('-created_at')[:5]),
            }
        
        return Response(data, status=status.HTTP_200_OK)
    
    def get_recent_listings_data(self, listings):
        """Get simplified listing data for dashboard."""
        return [{
            'id': listing.id,
            'title': listing.title,
            'price': listing.price,
            'status': listing.status,
            'created_at': listing.created_at,
            'views_count': getattr(listing, 'views_count', 0)
        } for listing in listings]
    
    def get_recent_inquiries_data(self, inquiries):
        """Get simplified inquiry data for dashboard."""
        return [{
            'id': inquiry.id,
            'listing_title': inquiry.listing.title,
            'name': inquiry.name,
            'status': inquiry.status,
            'created_at': inquiry.created_at,
            'inquiry_type': inquiry.inquiry_type
        } for inquiry in inquiries]
    
    def get_saved_listings_data(self, saved_listings):
        """Get simplified saved listing data for dashboard."""
        return [{
            'id': saved.listing.id,
            'title': saved.listing.title,
            'price': saved.listing.price,
            'saved_at': saved.created_at,
            'status': saved.listing.status
        } for saved in saved_listings]
