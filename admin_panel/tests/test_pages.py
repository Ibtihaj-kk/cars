"""
Test script to verify admin panel pages load correctly.
Run with: python manage.py test admin_panel.tests.test_pages
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from users.models import User
from parts.models import BulkUploadLog, Brand, Category
from business_partners.catalog_models import CatalogItem
from business_partners.models import BusinessPartner, BusinessPartnerRole


class AdminPanelPagesTest(TestCase):
    """Test that all admin panel pages load without errors."""
    
    def setUp(self):
        """Create admin user and login."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            email='admin@test.com',
            password='testpass123'
        )
        self.client.force_login(self.admin_user)
        
        # Create admin session data
        session = self.client.session
        now = timezone.now().isoformat()
        session['admin_session_data'] = {
            'user_id': self.admin_user.id,
            'session_key': session.session_key,
            'ip_address': '127.0.0.1',
            'user_agent': 'test',
            'created_at': now,
            'last_activity': now,
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
    
    def test_catalog_page(self):
        """Test catalog page loads."""
        response = self.client.get(reverse('admin_panel:catalog_management'))
        self.assertIn(response.status_code, [200, 302])

    def test_catalog_inventory_page(self):
        response = self.client.get(reverse('admin_panel:catalog_inventory'))
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

    def test_settings_page(self):
        response = self.client.get(reverse('admin_panel:settings'))
        self.assertIn(response.status_code, [200, 302])

    def test_setup_2fa_page(self):
        response = self.client.get(reverse('admin_panel:setup_2fa'))
        self.assertIn(response.status_code, [200, 302])

    def test_bulk_upload_template_download(self):
        response = self.client.get(reverse('admin_panel:bulk_upload_template'))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response.get("Content-Type", ""))
        content = response.content.decode("utf-8")
        self.assertIn("Category", content)
        self.assertIn("Year", content)
        self.assertIn("Make", content)
        self.assertIn("Model", content)
        self.assertIn("Trim", content)
        self.assertIn("Engine", content)

    def test_process_bulk_upload_csv(self):
        vendor = BusinessPartner.objects.create(name="Test Vendor")
        BusinessPartnerRole.objects.create(business_partner=vendor, role_type="vendor")

        csv_content = (
            "Category,Year,Make,Model,Trim,Engine\n"
            "Engine Parts,2020,Toyota,Camry,SE,2.5L\n"
        )
        upload = SimpleUploadedFile(
            "catalog.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post(reverse('admin_panel:process_bulk_upload'), {"file": upload, "processing_mode": "sync"})
        self.assertEqual(response.status_code, 302)

        item = CatalogItem.objects.get(vendor=vendor, make="Toyota", model="Camry", year=2020, trim="SE", engine="2.5L")
        self.assertEqual(item.category.name, "Engine Parts")
        self.assertTrue(item.part_number)
        self.assertTrue(item.description)
        self.assertTrue(Brand.objects.filter(name__iexact="Toyota").exists())

        log = BulkUploadLog.objects.get(file_name="catalog.csv")
        self.assertEqual(log.total_records, 1)
        self.assertEqual(log.successful_records, 1)
        self.assertEqual(log.failed_records, 0)
        self.assertEqual(log.status, "completed")

    def test_process_bulk_upload_skips_existing_make(self):
        vendor = BusinessPartner.objects.create(name="Test Vendor")
        BusinessPartnerRole.objects.create(business_partner=vendor, role_type="vendor")

        Brand.objects.create(name="Toyota")

        csv_content = (
            "Category,Year,Make,Model,Trim,Engine\n"
            "Engine Parts,2020,TOYOTA,Camry,SE,2.5L\n"
        )
        upload = SimpleUploadedFile(
            "catalog.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post(reverse('admin_panel:process_bulk_upload'), {"file": upload, "processing_mode": "sync"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Brand.objects.filter(name__iexact="Toyota").count(), 1)

    def test_process_bulk_upload_rejects_missing_category(self):
        vendor = BusinessPartner.objects.create(name="Test Vendor")
        BusinessPartnerRole.objects.create(business_partner=vendor, role_type="vendor")

        csv_content = (
            "Category,Year,Make,Model,Trim,Engine\n"
            ",2020,Toyota,Camry,SE,2.5L\n"
        )
        upload = SimpleUploadedFile(
            "catalog.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post(reverse('admin_panel:process_bulk_upload'), {"file": upload, "processing_mode": "sync"})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CatalogItem.objects.filter(vendor=vendor).exists())

        log = BulkUploadLog.objects.get(file_name="catalog.csv")
        self.assertEqual(log.status, "failed")
        self.assertIn("Category is required", log.error_log or "")
