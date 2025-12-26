"""
Test script to verify admin panel pages load correctly.
Run with: python manage.py test admin_panel.tests.test_pages
"""
from django.test import TestCase, Client
from django.urls import reverse
from users.models import User


class AdminPanelPagesTest(TestCase):
    """Test that all admin panel pages load without errors."""
    
    def setUp(self):
        """Create admin user and login."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='testpass123'
        )
        self.client.login(username='admin@test.com', password='testpass123')
        
        # Create admin session data
        session = self.client.session
        session['admin_session_data'] = {
            'user_id': self.admin_user.id,
            'session_key': session.session_key,
            'ip_address': '127.0.0.1',
            'user_agent': 'test',
            'created_at': '2024-01-01T00:00:00',
            'last_activity': '2024-01-01T00:00:00',
            'is_active': True,
        }
        session.save()
    
    def test_dashboard(self):
        """Test dashboard page loads."""
        response = self.client.get(reverse('admin_panel:dashboard'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_users_page(self):
        """Test users management page loads."""
        response = self.client.get(reverse('admin_panel:users'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_parts_page(self):
        """Test parts catalog page loads."""
        response = self.client.get(reverse('admin_panel:parts'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_orders_page(self):
        """Test orders page loads."""
        response = self.client.get(reverse('admin_panel:orders'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_categories_page(self):
        """Test categories page loads."""
        response = self.client.get(reverse('admin_panel:categories'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_inventory_page(self):
        """Test inventory page loads."""
        response = self.client.get(reverse('admin_panel:inventory'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_reviews_page(self):
        """Test reviews page loads."""
        response = self.client.get(reverse('admin_panel:reviews'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_invoices_page(self):
        """Test invoices page loads."""
        response = self.client.get(reverse('admin_panel:invoices'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_taxes_page(self):
        """Test taxes page loads."""
        response = self.client.get(reverse('admin_panel:taxes'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_partners_page(self):
        """Test business partners page loads."""
        response = self.client.get(reverse('admin_panel:partners'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_bulk_upload_page(self):
        """Test bulk upload page loads."""
        response = self.client.get(reverse('admin_panel:bulk_upload'))
        self.assertIn(response.status_code, [200, 302])
    
    def test_roles_page(self):
        """Test roles/permissions page loads."""
        response = self.client.get(reverse('admin_panel:roles'))
        self.assertIn(response.status_code, [200, 302])
