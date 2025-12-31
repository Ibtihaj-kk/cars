"""
Test script to verify admin panel pages load correctly.
Run with: python manage.py test admin_panel.tests.test_pages
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from decimal import Decimal
from users.models import User
from parts.models import Part, BulkUploadLog, Category, Brand


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
        self.assertIn("Part Number", content)
        self.assertIn("Material Description", content)
        self.assertIn("Safety Stock", content)
        self.assertIn("Reorder Point", content)
        self.assertIn("Manufacturer Part Number", content)
        self.assertIn("OEM Number", content)
        self.assertIn("Image URL", content)

    def test_process_bulk_upload_csv(self):
        Category.objects.create(name="Engine Parts")
        Brand.objects.create(name="Toyota")

        csv_content = (
            "Part Number,Material Description,Category,Brand,Price,Base Unit,Quantity,Safety Stock,Reorder Point,Active,Featured,Gross Weight,Net Weight,Dimensions,Arabic Description,Manufacturer Part Number,OEM Number,Image URL\n"
            "PN-123,Oil Filter,Engine Parts,Toyota,25.00,EA,10,2.000,5.000,true,false,0.500,0.450,10x10x10,فلتر زيت,MFG-12345,OEM-98765,https://example.com/image.jpg\n"
        )
        upload = SimpleUploadedFile(
            "parts.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post(reverse('admin_panel:process_bulk_upload'), {"file": upload})
        self.assertEqual(response.status_code, 302)

        part = Part.objects.get(parts_number="PN-123")
        self.assertEqual(part.material_description, "Oil Filter")
        self.assertEqual(part.price, 25)
        self.assertEqual(part.quantity, 10)
        self.assertEqual(part.base_unit_of_measure, "EA")
        self.assertEqual(part.safety_stock, Decimal("2.000"))
        self.assertEqual(part.reorder_point, Decimal("5.000"))
        self.assertTrue(part.is_active)
        self.assertFalse(part.is_featured)
        self.assertEqual(part.gross_weight, Decimal("0.500"))
        self.assertEqual(part.net_weight, Decimal("0.450"))
        self.assertEqual(part.size_dimensions, "10x10x10")
        self.assertEqual(part.material_description_ar, "فلتر زيت")
        self.assertEqual(part.manufacturer_part_number, "MFG-12345")
        self.assertEqual(part.manufacturer_oem_number, "OEM-98765")
        self.assertEqual(part.image_url, "https://example.com/image.jpg")
        self.assertEqual(part.inventory.stock, 10)
        self.assertEqual(part.inventory.reorder_level, 5)

        log = BulkUploadLog.objects.get(file_name="parts.csv")
        self.assertEqual(log.total_records, 1)
        self.assertEqual(log.successful_records, 1)
        self.assertEqual(log.failed_records, 0)
        self.assertEqual(log.status, "completed")

    def test_process_bulk_upload_rejects_missing_brand_or_category(self):
        Category.objects.create(name="Engine Parts")

        csv_content = (
            "Part Number,Material Description,Category,Brand,Price,Base Unit,Quantity,Safety Stock,Reorder Point,Active,Featured,Gross Weight,Net Weight,Dimensions,Arabic Description,Manufacturer Part Number,OEM Number,Image URL\n"
            "PN-999,Oil Filter,Engine Parts,NotARealBrand,25.00,EA,10,2.000,5.000,true,false,0.500,0.450,10x10x10,فلتر زيت,MFG-12345,OEM-98765,https://example.com/image.jpg\n"
        )
        upload = SimpleUploadedFile(
            "parts.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post(reverse('admin_panel:process_bulk_upload'), {"file": upload})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Part.objects.filter(parts_number="PN-999").exists())

        log = BulkUploadLog.objects.get(file_name="parts.csv")
        self.assertEqual(log.status, "failed")
        self.assertIn("Brand not found", log.error_log or "")

    def test_process_bulk_upload_rejects_mismatched_category_and_brand(self):
        Category.objects.create(name="Transmission")
        Brand.objects.create(name="Honda")

        csv_content = (
            "Part Number,Material Description,Category,Brand,Price,Base Unit,Quantity,Safety Stock,Reorder Point,Active,Featured,Gross Weight,Net Weight,Dimensions,Arabic Description,Manufacturer Part Number,OEM Number,Image URL\n"
            "PN-555,Oil Filter,cat,brnd,25.00,EA,10,2.000,5.000,true,false,0.500,0.450,10x10x10,فلتر زيت,MFG-12345,OEM-98765,https://example.com/image.jpg\n"
        )
        upload = SimpleUploadedFile(
            "parts.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )
        response = self.client.post(reverse('admin_panel:process_bulk_upload'), {"file": upload})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Part.objects.filter(parts_number="PN-555").exists())

        log = BulkUploadLog.objects.get(file_name="parts.csv")
        self.assertEqual(log.status, "failed")
        self.assertIn("Category not found", log.error_log or "")
        self.assertIn("Brand not found", log.error_log or "")
