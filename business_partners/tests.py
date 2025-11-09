from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import BusinessPartner, BusinessPartnerRole, ContactInfo

User = get_user_model()


class BusinessPartnerCRUDTests(TestCase):
    """Test CRUD operations for BusinessPartner model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_create_business_partner(self):
        """Test creating a business partner"""
        partner = BusinessPartner.objects.create(
            bp_number='BP000001',
            name='Test Business Partner',
            type='company',
            legal_identifier='123456789',
            status='active',
            user=self.user
        )
        self.assertEqual(partner.name, 'Test Business Partner')
        self.assertEqual(partner.bp_number, 'BP000001')
        self.assertEqual(partner.type, 'company')
        self.assertEqual(partner.status, 'active')
        self.assertEqual(partner.user, self.user)
        self.assertIsNotNone(partner.created_at)
        self.assertIsNotNone(partner.updated_at)
    
    def test_read_business_partner(self):
        """Test reading business partner data"""
        partner = BusinessPartner.objects.create(
            bp_number='BP000001',
            name='Test Business Partner',
            type='company',
            user=self.user
        )
        retrieved_partner = BusinessPartner.objects.get(pk=partner.pk)
        self.assertEqual(retrieved_partner.name, partner.name)
        self.assertEqual(retrieved_partner.bp_number, partner.bp_number)
    
    def test_update_business_partner(self):
        """Test updating business partner data"""
        partner = BusinessPartner.objects.create(
            bp_number='BP000001',
            name='Test Business Partner',
            type='company',
            user=self.user
        )
        partner.name = 'Updated Business Partner'
        partner.status = 'inactive'
        partner.save()
        
        updated_partner = BusinessPartner.objects.get(pk=partner.pk)
        self.assertEqual(updated_partner.name, 'Updated Business Partner')
        self.assertEqual(updated_partner.status, 'inactive')
    
    def test_delete_business_partner(self):
        """Test deleting a business partner"""
        partner = BusinessPartner.objects.create(
            bp_number='BP000001',
            name='Test Business Partner',
            type='company',
            user=self.user
        )
        partner_id = partner.pk
        partner.delete()
        
        with self.assertRaises(BusinessPartner.DoesNotExist):
            BusinessPartner.objects.get(pk=partner_id)


class BusinessPartnerRoleCRUDTests(TestCase):
    """Test CRUD operations for BusinessPartnerRole model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.business_partner = BusinessPartner.objects.create(
            bp_number='BP000001',
            name='Test Business Partner',
            type='company',
            user=self.user
        )
    
    def test_create_business_partner_role(self):
        """Test creating a business partner role"""
        role = BusinessPartnerRole.objects.create(
            business_partner=self.business_partner,
            role_type='vendor'
        )
        self.assertEqual(role.business_partner, self.business_partner)
        self.assertEqual(role.role_type, 'vendor')
    
    def test_read_business_partner_role(self):
        """Test reading business partner role data"""
        role = BusinessPartnerRole.objects.create(
            business_partner=self.business_partner,
            role_type='vendor'
        )
        retrieved_role = BusinessPartnerRole.objects.get(pk=role.pk)
        self.assertEqual(retrieved_role.business_partner, self.business_partner)
        self.assertEqual(retrieved_role.role_type, 'vendor')
    
    def test_update_business_partner_role(self):
        """Test updating business partner role"""
        role = BusinessPartnerRole.objects.create(
            business_partner=self.business_partner,
            role_type='vendor'
        )
        role.role_type = 'customer'
        role.save()
        
        updated_role = BusinessPartnerRole.objects.get(pk=role.pk)
        self.assertEqual(updated_role.role_type, 'customer')
    
    def test_delete_business_partner_role(self):
        """Test deleting a business partner role"""
        role = BusinessPartnerRole.objects.create(
            business_partner=self.business_partner,
            role_type='vendor'
        )
        role_id = role.pk
        role.delete()
        
        with self.assertRaises(BusinessPartnerRole.DoesNotExist):
            BusinessPartnerRole.objects.get(pk=role_id)


class ContactInfoCRUDTests(TestCase):
    """Test CRUD operations for ContactInfo model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.business_partner = BusinessPartner.objects.create(
            bp_number='BP000001',
            name='Test Business Partner',
            type='company',
            user=self.user
        )
    
    def test_create_contact_info(self):
        """Test creating contact information"""
        contact = ContactInfo.objects.create(
            business_partner=self.business_partner,
            contact_type='email',
            value='test@example.com',
            is_primary=True
        )
        self.assertEqual(contact.business_partner, self.business_partner)
        self.assertEqual(contact.contact_type, 'email')
        self.assertEqual(contact.value, 'test@example.com')
        self.assertTrue(contact.is_primary)
    
    def test_read_contact_info(self):
        """Test reading contact information"""
        contact = ContactInfo.objects.create(
            business_partner=self.business_partner,
            contact_type='phone',
            value='+1234567890',
            is_primary=False
        )
        retrieved_contact = ContactInfo.objects.get(pk=contact.pk)
        self.assertEqual(retrieved_contact.contact_type, 'phone')
        self.assertEqual(retrieved_contact.value, '+1234567890')
    
    def test_update_contact_info(self):
        """Test updating contact information"""
        contact = ContactInfo.objects.create(
            business_partner=self.business_partner,
            contact_type='email',
            value='old@example.com',
            is_primary=False
        )
        contact.value = 'new@example.com'
        contact.is_primary = True
        contact.save()
        
        updated_contact = ContactInfo.objects.get(pk=contact.pk)
        self.assertEqual(updated_contact.value, 'new@example.com')
        self.assertTrue(updated_contact.is_primary)
    
    def test_delete_contact_info(self):
        """Test deleting contact information"""
        contact = ContactInfo.objects.create(
            business_partner=self.business_partner,
            contact_type='email',
            value='test@example.com',
            is_primary=True
        )
        contact_id = contact.pk
        contact.delete()
        
        with self.assertRaises(ContactInfo.DoesNotExist):
            ContactInfo.objects.get(pk=contact_id)


class BusinessPartnerMethodTests(TestCase):
    """Test additional methods of BusinessPartner model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.business_partner = BusinessPartner.objects.create(
            bp_number='BP000001',
            name='Test Business Partner',
            type='company',
            user=self.user
        )
    
    def test_auto_generate_bp_number(self):
        """Test auto-generation of BP number when not provided"""
        partner = BusinessPartner.objects.create(
            name='Auto BP Partner',
            type='company',
            user=self.user
        )
        self.assertTrue(partner.bp_number.startswith('BP'))
        self.assertEqual(len(partner.bp_number), 8)
    
    def test_auto_generate_slug(self):
        """Test auto-generation of slug"""
        # Use a unique name to avoid conflicts with existing test data
        unique_name = 'Unique Test Partner for Slug'
        partner = BusinessPartner.objects.create(
            bp_number='BP000002',
            name=unique_name,
            type='company',
            user=self.user
        )
        from django.utils.text import slugify
        expected_slug = slugify(unique_name)
        self.assertEqual(partner.slug, expected_slug)
    
    def test_business_partner_roles(self):
        """Test business partner role methods"""
        # Test role creation
        role = BusinessPartnerRole.objects.create(
            business_partner=self.business_partner,
            role_type='vendor'
        )
        
        self.assertTrue(self.business_partner.has_role('vendor'))
        self.assertTrue(self.business_partner.is_vendor())
        self.assertFalse(self.business_partner.is_customer())
        self.assertFalse(self.business_partner.is_prospect())
    
    def test_string_representation(self):
        """Test string representation of business partner"""
        expected_str = f"{self.business_partner.bp_number} - {self.business_partner.name}"
        self.assertEqual(str(self.business_partner), expected_str)


class ContactInfoMethodTests(TestCase):
    """Test additional methods of ContactInfo model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.business_partner = BusinessPartner.objects.create(
            bp_number='BP000001',
            name='Test Business Partner',
            type='company',
            user=self.user
        )
    
    def test_contact_info_primary_constraint(self):
        """Test that only one primary contact per type per business partner"""
        ContactInfo.objects.create(
            business_partner=self.business_partner,
            contact_type='email',
            value='primary@example.com',
            is_primary=True
        )
        
        # Create another primary email - should make the first one non-primary
        contact2 = ContactInfo.objects.create(
            business_partner=self.business_partner,
            contact_type='email',
            value='newprimary@example.com',
            is_primary=True
        )
        
        # Refresh first contact from DB
        first_contact = ContactInfo.objects.get(value='primary@example.com')
        self.assertFalse(first_contact.is_primary)
        self.assertTrue(contact2.is_primary)
    
    def test_string_representation(self):
        """Test string representation of contact information"""
        contact = ContactInfo.objects.create(
            business_partner=self.business_partner,
            contact_type='email',
            value='test@example.com',
            is_primary=True
        )
        expected_str = f"{self.business_partner.name} - Email: test@example.com"
        self.assertEqual(str(contact), expected_str)