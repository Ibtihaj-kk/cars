from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from .models import VendorProfile
from .permissions import get_vendor_profile

User = get_user_model()


class VendorLoginForm(forms.Form):
    """Vendor login form with email and password fields"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'required': True
        }),
        label='Email Address',
        help_text='Enter the email address associated with your vendor account'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your password',
            'required': True
        }),
        label='Password',
        help_text='Enter your password'
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Remember me',
        help_text='Keep me logged in for 30 days'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            try:
                user = User.objects.get(email=email)
                vendor_profile = get_vendor_profile(user)
                
                if not vendor_profile.is_approved:
                    raise forms.ValidationError(
                        'Your vendor application is still under review. You will receive an email once approved.',
                        code='not_approved'
                    )
                    
                if vendor_profile.two_factor_enabled:
                    cleaned_data['requires_2fa'] = True
                    cleaned_data['user'] = user
                
            except (User.DoesNotExist, VendorProfile.DoesNotExist):
                raise forms.ValidationError(
                    'Invalid email or password',
                    code='invalid_login'
                )
                
        return cleaned_data


class Vendor2FAForm(forms.Form):
    """2FA verification form"""
    
    token = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit code',
            'required': True,
            'autocomplete': 'off',
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric'
        }),
        label='Authentication Code',
        help_text='Enter the 6-digit code from your authenticator app or a backup code'
    )
    
    def clean_token(self):
        token = self.cleaned_data['token'].strip()
        if not token.isdigit():
            raise forms.ValidationError('Please enter a valid 6-digit code.')
        return token


class VendorPasswordResetForm(forms.Form):
    """Password reset request form"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'required': True
        }),
        label='Email Address',
        help_text='Enter the email address associated with your vendor account'
    )
    
    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            user = User.objects.get(email=email)
            get_vendor_profile(user)
        except User.DoesNotExist:
            # Don't reveal whether email exists for security
            pass
        except VendorProfile.DoesNotExist:
            # Don't reveal whether user is a vendor for security
            pass
        return email


class VendorPasswordChangeForm(forms.Form):
    """Password change form"""
    
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your current password',
            'required': True
        }),
        label='Current Password',
        help_text='Enter your current password'
    )
    
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new password',
            'required': True
        }),
        label='New Password',
        help_text='Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, and one number'
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm new password',
            'required': True
        }),
        label='Confirm New Password',
        help_text='Enter the same password as above'
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_current_password(self):
        current_password = self.cleaned_data['current_password']
        if not self.user.check_password(current_password):
            raise forms.ValidationError('Your current password is incorrect.')
        return current_password
    
    def clean_new_password(self):
        new_password = self.cleaned_data['new_password']
        
        if len(new_password) < 8:
            raise forms.ValidationError('Password must be at least 8 characters long.')
        
        # Check for complexity
        if not any(c.isupper() for c in new_password):
            raise forms.ValidationError('Password must contain at least one uppercase letter.')
        
        if not any(c.islower() for c in new_password):
            raise forms.ValidationError('Password must contain at least one lowercase letter.')
        
        if not any(c.isdigit() for c in new_password):
            raise forms.ValidationError('Password must contain at least one number.')
        
        return new_password
    
    def clean_confirm_password(self):
        confirm_password = self.cleaned_data['confirm_password']
        if 'new_password' in self.cleaned_data:
            if confirm_password != self.cleaned_data['new_password']:
                raise forms.ValidationError('Passwords do not match.')
        return confirm_password
    
    def save(self):
        self.user.set_password(self.cleaned_data['new_password'])
        self.user.save()
        return self.user


class VendorProfileUpdateForm(forms.Form):
    """Vendor profile update form"""
    
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        }),
        label='First Name'
    )
    
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        }),
        label='Last Name'
    )
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+1234567890'
        }),
        label='Phone Number'
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        
        # Set initial values
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        
        try:
            vendor_profile = get_vendor_profile(user)
            self.fields['phone'].initial = vendor_profile.business_phone
        except VendorProfile.DoesNotExist:
            pass
    
    def save(self):
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.save()
        
        try:
            vendor_profile = get_vendor_profile(self.user)
            vendor_profile.business_phone = self.cleaned_data['phone']
            vendor_profile.save()
        except VendorProfile.DoesNotExist:
            pass
        
        return self.user