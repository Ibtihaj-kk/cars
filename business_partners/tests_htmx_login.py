from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import JsonResponse
import json
from unittest.mock import patch, MagicMock

from .htmx_views import vendor_login_status_htmx
from .models import VendorProfile

User = get_user_model()

class VendorLoginStatusTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )
        self.factory = RequestFactory()

    def test_unauthenticated_user(self):
        request = self.factory.get('/business-partners/htmx/login/status/')
        request.user = AnonymousUser()
        
        # Add session
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        response = vendor_login_status_htmx(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['is_authenticated'])
        self.assertEqual(data['status'], 'pending')

    def test_authenticated_user_no_profile(self):
        request = self.factory.get('/business-partners/htmx/login/status/')
        request.user = self.user
        
        # Add session
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        with patch('business_partners.permissions.get_vendor_profile') as mock_get_profile:
            mock_get_profile.return_value = None
            
            response = vendor_login_status_htmx(request)
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['is_authenticated'])
            self.assertFalse(data['is_vendor'])
            self.assertEqual(data['redirect_url'], '/')

    def test_authenticated_vendor_approved(self):
        request = self.factory.get('/business-partners/htmx/login/status/')
        request.user = self.user
        
        # Add session
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        # Mock VendorProfile
        mock_profile = MagicMock()
        mock_profile.approval_state = 'APPROVED'
        
        with patch('business_partners.permissions.get_vendor_profile') as mock_get_profile:
            mock_get_profile.return_value = mock_profile
            
            response = vendor_login_status_htmx(request)
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['is_authenticated'])
            self.assertTrue(data['is_vendor'])
            self.assertEqual(data['vendor_status'], 'APPROVED')
            self.assertTrue(data['is_approved'])
            self.assertEqual(data['redirect_url'], '/business-partners/vendor/dashboard/')

    def test_login_error_in_session(self):
        request = self.factory.get('/business-partners/htmx/login/status/')
        request.user = AnonymousUser()
        
        # Add session with error
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session['login_error'] = 'Invalid credentials'
        request.session.save()
        
        response = vendor_login_status_htmx(request)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['status'], 'error')
        self.assertEqual(data['message'], 'Invalid credentials')
