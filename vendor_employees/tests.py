from django.test import TestCase
from django.urls import reverse

from business_partners.models import BusinessPartner
from users.models import User
from .models import VendorEmployee, VendorPagePermission, VendorRole, VendorRolePermission, VendorLocation


class VendorEmployeeAccessTests(TestCase):
    def setUp(self):
        self.vendor_user = User.objects.create_user(email='vendor@example.com', password='password123')
        self.vendor = BusinessPartner.objects.create(
            bp_number='BP000001',
            name='Vendor A',
            status='active',
            user=self.vendor_user
        )
        self.vendor_user_b = User.objects.create_user(email='vendorb@example.com', password='password123')
        self.vendor_b = BusinessPartner.objects.create(
            bp_number='BP000002',
            name='Vendor B',
            status='active',
            user=self.vendor_user_b
        )
        self.permission_employees = VendorPagePermission.objects.create(
            code='employees',
            name='Employees',
            category='Team Management'
        )
        self.permission_locations = VendorPagePermission.objects.create(
            code='locations',
            name='Locations',
            category='Team Management'
        )
        self.role = VendorRole.objects.create(
            vendor=self.vendor,
            name='Manager',
            is_active=True
        )
        VendorRolePermission.objects.create(
            role=self.role, 
            permission=self.permission_employees,
            can_view=True,
            can_create=True,
            can_edit=True,
            can_delete=True
        )
        VendorRolePermission.objects.create(
            role=self.role, 
            permission=self.permission_locations,
            can_view=True,
            can_create=True,
            can_edit=True,
            can_delete=True
        )
        self.employee_user = User.objects.create_user(email='employee@example.com', password='password123')
        self.employee = VendorEmployee.objects.create(
            user=self.employee_user,
            vendor=self.vendor,
            role=self.role,
            is_active=True
        )
        self.location = VendorLocation.objects.create(
            vendor=self.vendor,
            name='Warehouse A',
            is_active=True
        )
        self.role_b = VendorRole.objects.create(
            vendor=self.vendor_b,
            name='Manager B',
            is_active=True
        )
        VendorRolePermission.objects.create(
            role=self.role_b, 
            permission=self.permission_employees,
            can_view=True
        )
        self.employee_user_b = User.objects.create_user(email='employee_b@example.com', password='password123')
        self.employee_b = VendorEmployee.objects.create(
            user=self.employee_user_b,
            vendor=self.vendor_b,
            role=self.role_b,
            is_active=True
        )
        self.location_b = VendorLocation.objects.create(
            vendor=self.vendor_b,
            name='Warehouse B',
            is_active=True
        )

    def test_master_vendor_can_view_employees(self):
        self.client.force_login(self.vendor_user)
        response = self.client.get(reverse('vendor_employees:employee_list'))
        self.assertEqual(response.status_code, 200)

    def test_vendor_employee_with_permission_can_view(self):
        self.client.force_login(self.employee_user)
        response = self.client.get(reverse('vendor_employees:employee_list'))
        self.assertEqual(response.status_code, 200)

    def test_vendor_employee_without_permission_denied(self):
        role = VendorRole.objects.create(vendor=self.vendor, name='Limited', is_active=True)
        user = User.objects.create_user(email='viewer@example.com', password='password123')
        VendorEmployee.objects.create(user=user, vendor=self.vendor, role=role, is_active=True)
        self.client.force_login(user)
        response = self.client.get(reverse('vendor_employees:employee_list'))
        self.assertEqual(response.status_code, 403)

    def test_vendor_isolation_on_employee_update(self):
        self.client.force_login(self.employee_user_b)
        response = self.client.get(reverse('vendor_employees:employee_update', args=[self.employee.id]))
        self.assertEqual(response.status_code, 404)

    def test_location_list_view(self):
        self.client.force_login(self.vendor_user)
        response = self.client.get(reverse('vendor_employees:location_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Warehouse A')
        self.assertNotContains(response, 'Warehouse B')

    def test_location_create(self):
        self.client.force_login(self.vendor_user)
        response = self.client.post(reverse('vendor_employees:location_create'), {
            'name': 'New Warehouse',
            'address': '123 Street',
            'is_active': True
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(VendorLocation.objects.filter(name='New Warehouse', vendor=self.vendor).exists())

    def test_location_edit_isolation(self):
        self.client.force_login(self.employee_user_b)
        response = self.client.get(reverse('vendor_employees:location_edit', args=[self.location.id]))
        # User B doesn't have access to this location (wrong vendor), so 404 is expected
        self.assertEqual(response.status_code, 404)



    def test_employee_invite_with_location(self):
        self.client.force_login(self.vendor_user)
        response = self.client.post(reverse('vendor_employees:employee_invite'), {
            'email': 'new_employee@example.com',
            'first_name': 'New',
            'last_name': 'Employee',
            'role': self.role.id,
            'location': self.location.id
        })
        self.assertEqual(response.status_code, 302)
        
        # Check if employee was created
        new_employee = VendorEmployee.objects.get(user__email='new_employee@example.com')
        self.assertEqual(new_employee.location, self.location)
        self.assertEqual(new_employee.role, self.role)
        
        # Check if invitation email was queued
        from core.email_service.models import EmailQueue
        self.assertTrue(EmailQueue.objects.filter(to_email='new_employee@example.com', email_type='employee_invitation').exists())

    def test_accept_invitation_flow(self):
        # Create an invited user
        invited_user = User.objects.create(email='invited@example.com', is_active=True)
        invited_user.set_unusable_password()
        invited_user.save()
        
        VendorEmployee.objects.create(
            user=invited_user,
            vendor=self.vendor,
            role=self.role,
            is_active=True
        )
        
        # Generate token and uid
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        
        token = default_token_generator.make_token(invited_user)
        uid = urlsafe_base64_encode(force_bytes(invited_user.pk))
        
        accept_url = reverse('vendor_employees:accept_invitation', args=[uid, token])
        
        # GET request to see the form
        response = self.client.get(accept_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Join Vendor A')
        
        # POST request to set password
        response = self.client.post(accept_url, {
            'first_name': 'Invited',
            'last_name': 'User',
            'password': 'newpassword123',
            'password_confirm': 'newpassword123'
        })
        
        # Should redirect to dashboard
        self.assertEqual(response.status_code, 302)
        
        # Check if user is updated and logged in
        invited_user.refresh_from_db()
        self.assertEqual(invited_user.first_name, 'Invited')
        self.assertTrue(invited_user.check_password('newpassword123'))

