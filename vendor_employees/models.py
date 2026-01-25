from django.conf import settings
from django.db import models
from business_partners.models import BusinessPartner


class VendorPagePermission(models.Model):
    code = models.CharField(max_length=150)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=100, blank=True)
    vendor = models.ForeignKey(
        BusinessPartner,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='page_permissions'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('vendor', 'code')]
        indexes = [
            models.Index(fields=['vendor', 'code']),
            models.Index(fields=['code', 'is_active'])
        ]
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.code} - {self.name}"


class VendorRole(models.Model):
    vendor = models.ForeignKey(
        BusinessPartner,
        on_delete=models.CASCADE,
        related_name='employee_roles'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_vendor_roles'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    permissions = models.ManyToManyField(
        VendorPagePermission,
        through='VendorRolePermission',
        blank=True
    )

    class Meta:
        unique_together = [('vendor', 'name')]
        indexes = [
            models.Index(fields=['vendor', 'is_active'])
        ]
        ordering = ['name']

    def __str__(self):
        return f"{self.vendor.name} - {self.name}"


class VendorRolePermission(models.Model):
    role = models.ForeignKey(VendorRole, on_delete=models.CASCADE)
    permission = models.ForeignKey(VendorPagePermission, on_delete=models.CASCADE)
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('role', 'permission')]
        indexes = [
            models.Index(fields=['role', 'permission'])
        ]


class VendorLocation(models.Model):
    vendor = models.ForeignKey(
        BusinessPartner,
        on_delete=models.CASCADE,
        related_name='locations'
    )
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('vendor', 'name')]
        ordering = ['name']

    def __str__(self):
        return f"{self.vendor.name} - {self.name}"


class StorageLocation(models.Model):
    plant = models.ForeignKey(
        VendorLocation,
        on_delete=models.CASCADE,
        related_name='storage_locations'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('plant', 'name')]
        ordering = ['plant', 'name']

    def __str__(self):
        return f"{self.plant.name} - {self.name}"


class VendorEmployee(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vendor_employee'
    )
    vendor = models.ForeignKey(
        BusinessPartner,
        on_delete=models.CASCADE,
        related_name='employees'
    )
    role = models.ForeignKey(
        VendorRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )
    locations = models.ManyToManyField(
        VendorLocation,
        blank=True,
        related_name='employees'
    )
    # Keeping old field for backward compatibility during migration, but should be deprecated
    location = models.ForeignKey(
        VendorLocation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employee_legacy'
    )
    is_active = models.BooleanField(default=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invited_vendor_employees'
    )
    invitation_accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['vendor', 'is_active']),
            models.Index(fields=['user', 'is_active'])
        ]

    def __str__(self):
        return f"{self.user.email} - {self.vendor.name}"
