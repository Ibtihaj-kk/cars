from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from .audit_logging import AuditLogger
from .models import AuditLog

User = get_user_model()

class AuditLoggerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )
        self.factory = RequestFactory()

    def test_log_authentication_success(self):
        request = self.factory.get('/')
        request.user = self.user
        
        log = AuditLogger.log_authentication_success(
            user=self.user,
            primary_role='vendor',
            client_ip='127.0.0.1',
            request=request
        )
        
        self.assertIsNotNone(log)
        self.assertEqual(log.action_type, 'AUTH_SUCCESS')
        self.assertEqual(log.user, self.user)
        self.assertTrue(log.success)
        self.assertEqual(log.additional_data.get('primary_role'), 'vendor')

    def test_log_authentication_failure(self):
        request = self.factory.post('/login')
        
        log = AuditLogger.log_authentication_failure(
            email='wrong@example.com',
            client_ip='127.0.0.1',
            request=request
        )
        
        self.assertIsNotNone(log)
        self.assertEqual(log.action_type, 'AUTH_FAILURE')
        self.assertFalse(log.success)
        self.assertEqual(log.object_repr, 'wrong@example.com')

    def test_log_access_denied(self):
        request = self.factory.get('/restricted')
        request.user = self.user
        
        log = AuditLogger.log_access_denied(
            user=self.user,
            primary_role='vendor',
            client_ip='127.0.0.1',
            request=request
        )
        
        self.assertIsNotNone(log)
        self.assertEqual(log.action_type, 'ACCESS_DENIED')
        self.assertEqual(log.user, self.user)
        self.assertFalse(log.success)
        self.assertEqual(log.additional_data.get('primary_role'), 'vendor')
