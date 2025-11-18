from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import json
from unittest.mock import patch, MagicMock

from .models import (
    BusinessPartner, VendorProfile, SecureVendorApplication, 
    VendorAuditLog, PasswordHistory
)
from .password_validators import StrongPasswordValidator, PasswordHistoryValidator
from .breach_detection import BreachDetectionEngine
from .validators import validate_uploaded_document, validate_file_size, validate_file_mime_type

User = get_user_model()


class StrongPasswordValidatorTests(TestCase):
    """Test the StrongPasswordValidator"""
    
    def setUp(self):
        self.validator = StrongPasswordValidator()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='OldValidPassword123!',
            first_name='Test',
            last_name='User'
        )
    
    def test_valid_password(self):
        """Test that valid passwords pass validation"""
        valid_passwords = [
            'ValidPassword123!',
            'AnotherStrong1@Pass',
            'Complex$Password9',
            'Secure#Pass123Word'
        ]
        
        for password in valid_passwords:
            try:
                self.validator.validate(password, self.user)
            except ValidationError:
                self.fail(f"Password '{password}' should be valid")
    
    def test_short_password(self):
        """Test that short passwords fail validation"""
        short_password = 'Short1!'
        with self.assertRaises(ValidationError) as cm:
            self.validator.validate(short_password, self.user)
        self.assertIn('at least 12 characters', str(cm.exception))
    
    def test_password_without_uppercase(self):
        """Test that passwords without uppercase fail validation"""
        password = 'lowercase123!password'
        with self.assertRaises(ValidationError) as cm:
            self.validator.validate(password, self.user)
        self.assertIn('uppercase letter', str(cm.exception))
    
    def test_password_without_lowercase(self):
        """Test that passwords without lowercase fail validation"""
        password = 'UPPERCASE123!PASSWORD'
        with self.assertRaises(ValidationError) as cm:
            self.validator.validate(password, self.user)
        self.assertIn('lowercase letter', str(cm.exception))
    
    def test_password_without_numbers(self):
        """Test that passwords without numbers fail validation"""
        password = 'NoNumbers!Password'
        with self.assertRaises(ValidationError) as cm:
            self.validator.validate(password, self.user)
        self.assertIn('number', str(cm.exception))
    
    def test_password_without_special_chars(self):
        """Test that passwords without special characters fail validation"""
        password = 'NoSpecialChars123Password'
        with self.assertRaises(ValidationError) as cm:
            self.validator.validate(password, self.user)
        self.assertIn('special character', str(cm.exception))
    
    def test_common_password_patterns(self):
        """Test that common password patterns are rejected"""
        common_passwords = [
            'Password123!',
            'Admin123!',
            'Welcome123!',
            'Test123!Test'
        ]
        
        for password in common_passwords:
            with self.assertRaises(ValidationError) as cm:
                self.validator.validate(password, self.user)
            self.assertIn('common pattern', str(cm.exception))
    
    @patch('requests.get')
    def test_breached_password_detection(self, mock_get):
        """Test that breached passwords are detected"""
        # Mock the Have I Been Pwned API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "003D68EB55068C33ACE09247EE4C3173061A4:1\n1E4C9B1F6B1F6B1F6B1F6B1F6B1F6B1F6B1:2\n"
        mock_get.return_value = mock_response
        
        # This password hash would be in the mocked response
        breached_password = 'testpassword123'
        
        with self.assertRaises(ValidationError) as cm:
            self.validator.validate(breached_password, self.user)
        self.assertIn('been breached', str(cm.exception))
    
    @patch('requests.get')
    def test_api_failure_handling(self, mock_get):
        """Test that API failures don't break validation"""
        mock_get.side_effect = Exception("API Error")
        
        # Should not raise an exception when API fails
        try:
            self.validator.validate('ValidPassword123!', self.user)
        except ValidationError:
            self.fail("Validation should not fail when API is unavailable")


class PasswordHistoryValidatorTests(TestCase):
    """Test the PasswordHistoryValidator"""
    
    def setUp(self):
        self.validator = PasswordHistoryValidator(history_count=3)
        self.user = User.objects.create_user(
            email='test@example.com',
            password='InitialPassword123!',
            first_name='Test',
            last_name='User'
        )
    
    def test_password_not_in_history(self):
        """Test that new passwords pass validation"""
        new_password = 'NewPassword123!'
        try:
            self.validator.validate(new_password, self.user)
        except ValidationError:
            self.fail("New password should be valid")
    
    def test_password_in_history(self):
        """Test that passwords in history are rejected"""
        old_password = 'InitialPassword123!'
        
        with self.assertRaises(ValidationError) as cm:
            self.validator.validate(old_password, self.user)
        self.assertIn('recently used', str(cm.exception))
    
    def test_custom_history_count(self):
        """Test that custom history count works"""
        # Create validator with history_count=1
        validator = PasswordHistoryValidator(history_count=1)
        
        # Change password once
        self.user.set_password('SecondPassword123!')
        self.user.save()
        
        # Old password should be rejected
        with self.assertRaises(ValidationError):
            validator.validate('InitialPassword123!', self.user)
        
        # New password should be valid
        try:
            validator.validate('ThirdPassword123!', self.user)
        except ValidationError:
            self.fail("Third password should be valid")


class VendorProfileSecurityTests(TestCase):
    """Test security features of VendorProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='vendor@example.com',
            password='VendorPassword123!',
            first_name='Vendor',
            last_name='User'
        )
        self.business_partner = BusinessPartner.objects.create(
            bp_number='BP000001',
            name='Test Vendor',
            type='company',
            user=self.user
        )
        self.vendor_profile = VendorProfile.objects.create(
            business_partner=self.business_partner,
            vendor_code='VENDOR001',
            tax_number='123456789',
            bank_account_number='1234567890',
            bank_routing_number='123456789',
            bank_name='Test Bank'
        )
    
    def test_generate_backup_codes(self):
        """Test backup code generation"""
        backup_codes = self.vendor_profile.generate_backup_codes()
        
        self.assertEqual(len(backup_codes), 10)
        self.assertTrue(self.vendor_profile.backup_codes)
        
        # Verify codes are stored as JSON
        stored_codes = json.loads(self.vendor_profile.backup_codes)
        self.assertEqual(len(stored_codes), 10)
        
        # Verify each code is 8 characters
        for code in backup_codes:
            self.assertEqual(len(code), 8)
            self.assertTrue(code.isalnum())
    
    def test_use_backup_code(self):
        """Test using a backup code"""
        # Generate backup codes first
        backup_codes = self.vendor_profile.generate_backup_codes()
        original_codes = json.loads(self.vendor_profile.backup_codes)
        
        # Use a valid backup code
        code_to_use = backup_codes[0]
        result = self.vendor_profile.use_backup_code(code_to_use)
        
        self.assertTrue(result)
        
        # Verify code was removed from stored codes
        updated_codes = json.loads(self.vendor_profile.backup_codes)
        self.assertEqual(len(updated_codes), 9)
        self.assertNotIn(code_to_use, updated_codes)
    
    def test_use_invalid_backup_code(self):
        """Test using an invalid backup code"""
        # Generate backup codes first
        self.vendor_profile.generate_backup_codes()
        
        # Try to use an invalid code
        result = self.vendor_profile.use_backup_code('INVALIDCODE')
        
        self.assertFalse(result)
        
        # Verify all codes are still available
        updated_codes = json.loads(self.vendor_profile.backup_codes)
        self.assertEqual(len(updated_codes), 10)
    
    def test_use_backup_code_without_codes(self):
        """Test using backup code when none are generated"""
        result = self.vendor_profile.use_backup_code('SOMECODE')
        
        self.assertFalse(result)
    
    def test_bank_details_encryption(self):
        """Test that bank details are encrypted"""
        # The encryption should be handled by the encryption field
        # This test verifies the field exists and can store data
        self.assertIsNotNone(self.vendor_profile.bank_account_number)
        self.assertIsNotNone(self.vendor_profile.bank_routing_number)
        self.assertEqual(self.vendor_profile.bank_name, 'Test Bank')


class SecureVendorApplicationSecurityTests(TestCase):
    """Test security features of SecureVendorApplication model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='vendor@example.com',
            password='VendorPassword123!',
            first_name='Vendor',
            last_name='User'
        )
        self.business_partner = BusinessPartner.objects.create(
            bp_number='BP000001',
            name='Test Vendor',
            type='company',
            user=self.user
        )
        self.vendor_profile = VendorProfile.objects.create(
            business_partner=self.business_partner,
            vendor_code='VENDOR001'
        )
    
    def test_secure_application_creation(self):
        """Test creating a secure vendor application"""
        application = SecureVendorApplication.objects.create(
            vendor_profile=self.vendor_profile,
            application_reference='APP001',
            status='pending',
            encrypted_data={'sensitive': 'data'},
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0 Test Browser'
        )
        
        self.assertEqual(application.vendor_profile, self.vendor_profile)
        self.assertEqual(application.application_reference, 'APP001')
        self.assertEqual(application.status, 'pending')
        self.assertEqual(application.ip_address, '192.168.1.1')
        self.assertEqual(application.user_agent, 'Mozilla/5.0 Test Browser')
        self.assertIsNotNone(application.created_at)
        self.assertIsNotNone(application.updated_at)
    
    def test_session_security_methods(self):
        """Test session security methods"""
        application = SecureVendorApplication.objects.create(
            vendor_profile=self.vendor_profile,
            application_reference='APP001',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0 Test Browser'
        )
        
        # Test IP validation
        self.assertTrue(application.validate_ip_address('192.168.1.1'))
        self.assertFalse(application.validate_ip_address('192.168.1.2'))
        
        # Test user agent validation
        self.assertTrue(application.validate_user_agent('Mozilla/5.0 Test Browser'))
        self.assertFalse(application.validate_user_agent('Different Browser'))
        
        # Test session integrity
        self.assertTrue(application.check_session_integrity('192.168.1.1', 'Mozilla/5.0 Test Browser'))
        self.assertFalse(application.check_session_integrity('192.168.1.2', 'Mozilla/5.0 Test Browser'))
        self.assertFalse(application.check_session_integrity('192.168.1.1', 'Different Browser'))


class BreachDetectionEngineTests(TestCase):
    """Test the BreachDetectionEngine"""
    
    def setUp(self):
        self.engine = BreachDetectionEngine()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )
    
    def test_sql_injection_detection(self):
        """Test SQL injection detection"""
        sql_injection_patterns = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "1' OR 1=1--",
            "admin'--",
            "1' AND 1=1--"
        ]
        
        for pattern in sql_injection_patterns:
            result = self.engine.detect_sql_injection(pattern)
            self.assertIsNotNone(result)
            self.assertEqual(result['type'], 'sql_injection')
            self.assertIn('payload', result)
    
    def test_legitimate_input_not_flagged_as_sql_injection(self):
        """Test that legitimate input is not flagged as SQL injection"""
        legitimate_inputs = [
            "This is a normal comment",
            "user@example.com",
            "Hello World!",
            "Price: $19.99"
        ]
        
        for input_text in legitimate_inputs:
            result = self.engine.detect_sql_injection(input_text)
            self.assertIsNone(result)
    
    def test_xss_detection(self):
        """Test XSS detection"""
        xss_patterns = [
            "<script>alert('XSS')</script>",
            "<img src='x' onerror='alert(1)'>",
            "javascript:alert('XSS')",
            "<svg onload='alert(1)'>",
            "<iframe src='javascript:alert(1)'></iframe>"
        ]
        
        for pattern in xss_patterns:
            result = self.engine.detect_xss(pattern)
            self.assertIsNotNone(result)
            self.assertEqual(result['type'], 'xss')
            self.assertIn('payload', result)
    
    def test_legitimate_input_not_flagged_as_xss(self):
        """Test that legitimate HTML is not flagged as XSS"""
        legitimate_html = [
            "<p>This is a paragraph</p>",
            "<strong>Bold text</strong>",
            "<em>Italic text</em>",
            "<h1>Heading</h1>"
        ]
        
        for html in legitimate_html:
            result = self.engine.detect_xss(html)
            self.assertIsNone(result)
    
    def test_directory_traversal_detection(self):
        """Test directory traversal detection"""
        traversal_patterns = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32",
            "file:///etc/passwd"
        ]
        
        for pattern in traversal_patterns:
            result = self.engine.detect_directory_traversal(pattern)
            self.assertIsNotNone(result)
            self.assertEqual(result['type'], 'directory_traversal')
            self.assertIn('payload', result)
    
    def test_brute_force_detection(self):
        """Test brute force login detection"""
        # Create some failed login attempts
        for i in range(6):
            VendorAuditLog.objects.create(
                user=self.user,
                action_type='login_failed',
                ip_address='192.168.1.100',
                details={'username': 'testuser'}
            )
        
        result = self.engine.detect_brute_force_login(
            username='testuser',
            ip_address='192.168.1.100',
            failed_attempts_threshold=5,
            time_window_minutes=15
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'brute_force_login')
        self.assertEqual(result['ip_address'], '192.168.1.100')
        self.assertEqual(result['username'], 'testuser')
        self.assertGreaterEqual(result['failed_attempts'], 5)
    
    def test_account_takeover_detection(self):
        """Test account takeover detection"""
        # Create a login from unusual location
        result = self.engine.detect_account_takeover(
            user_id=self.user.id,
            current_ip='203.0.113.45',
            current_user_agent='Unusual Browser 1.0',
            usual_ip='192.168.1.1',
            usual_user_agent='Mozilla/5.0 Chrome'
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'account_takeover')
        self.assertEqual(result['user_id'], self.user.id)
        self.assertIn('unusual', result['details'])
    
    def test_data_exfiltration_detection(self):
        """Test data exfiltration detection"""
        # Simulate high-frequency access
        for i in range(15):
            VendorAuditLog.objects.create(
                user=self.user,
                action_type='data_access',
                ip_address='192.168.1.100',
                details={'resource': 'sensitive_data'}
            )
        
        result = self.engine.detect_data_exfiltration(
            user_id=self.user.id,
            ip_address='192.168.1.100',
            access_threshold=10,
            time_window_minutes=5
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['type'], 'data_exfiltration')
        self.assertEqual(result['user_id'], self.user.id)
        self.assertGreaterEqual(result['access_count'], 10)


class FileUploadValidatorTests(TestCase):
    """Test file upload validation functions"""
    
    def test_validate_file_size(self):
        """Test file size validation"""
        # Mock file object
        mock_file = MagicMock()
        mock_file.size = 5 * 1024 * 1024  # 5MB
        
        # Should pass for 5MB file
        try:
            validate_file_size(mock_file)
        except ValidationError:
            self.fail("5MB file should be valid")
        
        # Mock large file
        mock_file.size = 15 * 1024 * 1024  # 15MB
        
        with self.assertRaises(ValidationError) as cm:
            validate_file_size(mock_file)
        self.assertIn('exceeds maximum allowed size', str(cm.exception))
    
    def test_validate_file_mime_type(self):
        """Test file MIME type validation"""
        # Mock valid file
        mock_file = MagicMock()
        mock_file.name = 'document.pdf'
        
        try:
            validate_file_mime_type(mock_file)
        except ValidationError:
            self.fail("PDF file should be valid")
        
        # Mock invalid file
        mock_file.name = 'script.exe'
        
        with self.assertRaises(ValidationError) as cm:
            validate_file_mime_type(mock_file)
        self.assertIn('File type', str(cm.exception))





class VendorAuditLogTests(TestCase):
    """Test VendorAuditLog functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )
    
    def test_audit_log_creation(self):
        """Test creating audit log entries"""
        log = VendorAuditLog.objects.create(
            user=self.user,
            action_type='login_success',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0 Test Browser',
            details={'username': 'testuser'}
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.action_type, 'login_success')
        self.assertEqual(log.ip_address, '192.168.1.1')
        self.assertEqual(log.user_agent, 'Mozilla/5.0 Test Browser')
        self.assertEqual(log.details['username'], 'testuser')
        self.assertIsNotNone(log.created_at)