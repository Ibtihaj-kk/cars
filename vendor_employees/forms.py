from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import models
from .models import VendorRole, VendorPagePermission, VendorLocation, StorageLocation


User = get_user_model()


# Common styles for form fields
INPUT_CLASSES = 'mt-1 block w-full h-12 px-4 rounded-xl border-2 border-gray-200 bg-white shadow-sm focus:ring-4 focus:ring-black/5 focus:border-black sm:text-sm transition-all outline-none placeholder:text-gray-400 text-gray-900'
TEXTAREA_CLASSES = 'mt-1 block w-full px-4 py-3 rounded-xl border-2 border-gray-200 bg-white shadow-sm focus:ring-4 focus:ring-black/5 focus:border-black sm:text-sm transition-all outline-none placeholder:text-gray-400 text-gray-900'
CHECKBOX_CLASSES = 'h-5 w-5 rounded-md border-2 border-gray-300 text-black focus:ring-0 focus:ring-offset-0 transition-all cursor-pointer hover:border-black checked:bg-black checked:border-black'
SELECT_CLASSES = 'mt-1 block w-full h-12 px-4 rounded-xl border-2 border-gray-200 bg-white shadow-sm focus:ring-4 focus:ring-black/5 focus:border-black sm:text-sm transition-all outline-none cursor-pointer appearance-none text-gray-900'
MULTI_SELECT_CLASSES = 'mt-1 block w-full h-32 px-4 py-2 rounded-xl border-2 border-gray-200 bg-white shadow-sm focus:ring-4 focus:ring-black/5 focus:border-black sm:text-sm transition-all outline-none cursor-pointer text-gray-900'


class VendorLocationForm(forms.ModelForm):
    class Meta:
        model = VendorLocation
        fields = ['name', 'address', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'address': forms.Textarea(attrs={'class': TEXTAREA_CLASSES, 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES})
        }


class StorageLocationForm(forms.ModelForm):
    class Meta:
        model = StorageLocation
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'description': forms.Textarea(attrs={'class': TEXTAREA_CLASSES, 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES})
        }


class EmployeeInviteForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': INPUT_CLASSES}))
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    role = forms.ModelChoiceField(
        queryset=VendorRole.objects.none(),
        widget=forms.Select(attrs={'class': SELECT_CLASSES})
    )
    locations = forms.ModelMultipleChoiceField(
        queryset=VendorLocation.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': MULTI_SELECT_CLASSES})
    )

    def __init__(self, vendor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = VendorRole.objects.filter(vendor=vendor, is_active=True)
        self.fields['locations'].queryset = VendorLocation.objects.filter(vendor=vendor, is_active=True)


class EmployeeUpdateForm(forms.Form):
    role = forms.ModelChoiceField(
        queryset=VendorRole.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': SELECT_CLASSES})
    )
    locations = forms.ModelMultipleChoiceField(
        queryset=VendorLocation.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': MULTI_SELECT_CLASSES})
    )
    is_active = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES})
    )

    def __init__(self, vendor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = VendorRole.objects.filter(vendor=vendor, is_active=True)
        self.fields['locations'].queryset = VendorLocation.objects.filter(vendor=vendor, is_active=True)


class InvitationAcceptForm(forms.Form):
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': INPUT_CLASSES}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': INPUT_CLASSES}))
    password_confirm = forms.CharField(widget=forms.PasswordInput(attrs={'class': INPUT_CLASSES}))

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')

        if password and password_confirm and password != password_confirm:
            raise ValidationError("Passwords do not match.")
        return cleaned_data


class RoleForm(forms.ModelForm):
    class Meta:
        model = VendorRole
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASSES}),
            'description': forms.Textarea(attrs={'class': TEXTAREA_CLASSES, 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': CHECKBOX_CLASSES})
        }


class RolePermissionForm(forms.Form):
    permissions = forms.ModelMultipleChoiceField(
        queryset=VendorPagePermission.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, vendor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['permissions'].queryset = VendorPagePermission.objects.filter(
            is_active=True
        ).filter(models.Q(vendor__isnull=True) | models.Q(vendor=vendor))
