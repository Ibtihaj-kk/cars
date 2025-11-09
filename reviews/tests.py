"""
Tests for the enhanced review system.
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from vehicles.models import VehicleModel, Brand
from listings.models import VehicleListing
from .models import VehicleReview, DealerReview, SellerReview, ListingReview, ReviewLog
from .moderation import ReviewModerationService, ReviewQualityAnalyzer

User = get_user_model()


class ReviewModerationTestCase(TestCase):
    """Test cases for review moderation system."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        # Create test brand and vehicle model
        self.brand = Brand.objects.create(name='Test Brand')
        self.vehicle_model = VehicleModel.objects.create(
            brand=self.brand,
            name='Test Model'
        )
    
    def test_high_quality_review_approved(self):
        """Test that high-quality reviews are automatically approved."""
        review = VehicleReview.objects.create(
            user=self.user,
            vehicle_model=self.vehicle_model,
            year=2020,
            title='Excellent vehicle with great performance',
            content='I have been driving this car for 6 months now and I am extremely satisfied with its performance. The fuel efficiency is outstanding, averaging 15km/l in city driving. The build quality feels solid and the interior is comfortable for long drives. The only minor issue I noticed is that the air conditioning takes a bit longer to cool down in extreme heat, but overall this is an excellent vehicle that I would highly recommend to anyone looking for a reliable and efficient car.',
            overall_rating=5,
            pros='Great fuel efficiency, comfortable interior, reliable',
            cons='AC takes time to cool in extreme heat',
            status='pending'
        )
        
        moderation_results = ReviewModerationService.moderate_review(review)
        
        self.assertEqual(moderation_results['status'], 'approved')
        self.assertGreaterEqual(moderation_results['score'], 70)
        self.assertNotIn('severe_violation', moderation_results['flags'])
    
    def test_low_quality_review_rejected(self):
        """Test that low-quality reviews are rejected."""
        review = VehicleReview.objects.create(
            user=self.user,
            vehicle_model=self.vehicle_model,
            year=2021,
            title='bad',
            content='this car is terrible and awful and the worst thing ever spam spam spam contact me at 1234567890',
            overall_rating=1,
            status='pending'
        )
        
        moderation_results = ReviewModerationService.moderate_review(review)
        
        self.assertEqual(moderation_results['status'], 'rejected')
        self.assertLess(moderation_results['score'], 30)
        self.assertIn('severe_violation', moderation_results['flags'])
    
    def test_spam_detection(self):
        """Test spam detection in reviews."""
        review = VehicleReview.objects.create(
            user=self.user,
            vehicle_model=self.vehicle_model,
            year=2022,
            title='Buy now! Limited time offer!',
            content='Visit our website www.example.com for amazing deals! Click here for discount! Act now!',
            overall_rating=5,
            status='pending'
        )
        
        moderation_results = ReviewModerationService.moderate_review(review)
        
        self.assertIn('likely_spam', moderation_results['flags'])
        self.assertEqual(moderation_results['status'], 'rejected')
    
    def test_inappropriate_content_detection(self):
        """Test detection of inappropriate content."""
        review = VehicleReview.objects.create(
            user=self.user,
            vehicle_model=self.vehicle_model,
            year=2019,
            title='This is terrible',
            content='This car is f*cking awful and the dealer is a liar and cheat. Contact me at test@email.com',
            overall_rating=1,
            status='pending'
        )
        
        moderation_results = ReviewModerationService.moderate_review(review)
        
        self.assertIn('inappropriate_language', moderation_results['flags'])
        self.assertIn('personal_info_sharing', moderation_results['flags'])
        self.assertEqual(moderation_results['status'], 'rejected')


class ReviewQualityAnalyzerTestCase(TestCase):
    """Test cases for review quality analyzer."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.brand = Brand.objects.create(name='Test Brand')
        self.vehicle_model = VehicleModel.objects.create(
            brand=self.brand,
            name='Test Model'
        )
    
    def test_quality_analysis_comprehensive_review(self):
        """Test quality analysis for a comprehensive review."""
        review = VehicleReview.objects.create(
            user=self.user,
            vehicle_model=self.vehicle_model,
            year=2018,
            title='Detailed review after 6 months of ownership',
            content='After owning this vehicle for six months, I can provide a comprehensive review. The performance has been excellent with smooth acceleration and responsive handling. Fuel efficiency averages 14km/l in mixed driving conditions. The interior is well-designed with comfortable seating and intuitive controls. Build quality feels solid with no rattles or issues so far. The infotainment system is user-friendly and connects seamlessly with smartphones.',
            overall_rating=4,
            pros='Excellent performance, good fuel efficiency, comfortable interior, solid build quality',
            cons='Infotainment could be more responsive, road noise at highway speeds',
            status='approved'
        )
        
        analysis = ReviewQualityAnalyzer.analyze_review_quality(review)
        
        self.assertGreaterEqual(analysis['quality_score'], 70)
        self.assertGreaterEqual(analysis['completeness_score'], 80)
        self.assertGreaterEqual(analysis['helpfulness_score'], 70)
        self.assertIn('Provides both pros and cons', analysis['insights'])
    
    def test_quality_analysis_incomplete_review(self):
        """Test quality analysis for an incomplete review."""
        review = VehicleReview.objects.create(
            user=self.user,
            vehicle_model=self.vehicle_model,
            year=2017,
            title='',  # Missing title
            content='ok car',  # Very short
            overall_rating=3,
            status='approved'
        )
        
        analysis = ReviewQualityAnalyzer.analyze_review_quality(review)
        
        self.assertLess(analysis['quality_score'], 50)
        self.assertLess(analysis['completeness_score'], 60)  # Should be 55 (30 for content + 25 for rating)
        self.assertIn('Missing title', analysis['insights'])


class ReviewAPITestCase(APITestCase):
    """Test cases for review API endpoints."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.brand = Brand.objects.create(name='Test Brand')
        self.vehicle_model = VehicleModel.objects.create(
            brand=self.brand,
            name='Test Model'
        )
        
        # Create a dealer user for dealer reviews
        self.dealer = User.objects.create_user(
            email='dealer@example.com',
            password='testpass123',
            first_name='John',
            last_name='Dealer',
            role='seller'
        )
        
        # Create a listing for listing reviews
        self.listing = VehicleListing.objects.create(
            user=self.user,
            title='Test Listing',
            description='Test description',
            price=50000,
            year=2023,
            make='Test Make',
            model='Test Model',
            kilometers=10000,
            fuel_type='gasoline',
            condition='used',
            transmission='automatic',
            location_city='Dubai'
        )
    
    def test_create_vehicle_review_with_moderation(self):
        """Test creating a vehicle review with automatic moderation."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'vehicle_model': self.vehicle_model.id,
            'year': 2023,
            'title': 'Great car with excellent performance',
            'content': 'I have been driving this car for several months and I am very satisfied with its performance. The fuel efficiency is good and the build quality is solid. I would recommend this car to others looking for a reliable vehicle.',
            'overall_rating': 5,
            'pros': 'Good fuel efficiency, solid build quality',
            'cons': 'None so far'
        }
        
        response = self.client.post('/api/reviews/vehicle-reviews/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that review was created and moderated
        review = VehicleReview.objects.get(id=response.data['id'])
        self.assertEqual(review.status, 'approved')  # Should be auto-approved
        
        # Check that moderation log was created
        self.assertTrue(
            ReviewLog.objects.filter(
                object_id=review.id,
                action='MODERATE'
            ).exists()
        )
    
    def test_create_seller_review(self):
        """Test creating a seller review."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'seller': self.user.id,  # Review the same user (for testing)
            'title': 'Excellent seller experience',
            'content': 'The seller was very responsive and professional throughout the transaction. Communication was clear and timely. The vehicle was exactly as described and the handover process was smooth.',
            'overall_rating': 5,
            'communication_rating': 5,
            'reliability_rating': 5,
            'responsiveness_rating': 5,
            'pros': 'Professional, responsive, honest',
            'cons': 'None',
            'is_verified_transaction': True
        }
        
        response = self.client.post('/api/reviews/seller-reviews/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that review was created
        review = SellerReview.objects.get(id=response.data['id'])
        self.assertEqual(review.seller, self.user)
        self.assertEqual(review.overall_rating, 5)
    
    def test_create_listing_review(self):
        """Test creating a listing review."""
        self.client.force_authenticate(user=self.user)
        
        data = {
            'listing': self.listing.id,
            'title': 'Vehicle exactly as described',
            'content': 'The vehicle was in excellent condition as advertised. All features worked perfectly and the description was accurate. Great value for money.',
            'overall_rating': 5,
            'condition_rating': 5,
            'value_rating': 4,
            'description_accuracy_rating': 5,
            'pros': 'Accurate description, good condition',
            'cons': 'Slightly overpriced',
            'is_verified_purchase': True
        }
        
        response = self.client.post('/api/reviews/listing-reviews/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check that review was created
        review = ListingReview.objects.get(id=response.data['id'])
        self.assertEqual(review.listing, self.listing)
        self.assertEqual(review.overall_rating, 5)
    
    def test_quality_analysis_endpoint(self):
        """Test the quality analysis endpoint."""
        self.client.force_authenticate(user=self.user)
        
        # Create a review
        review = VehicleReview.objects.create(
            user=self.user,
            vehicle_model=self.vehicle_model,
            year=2016,
            title='Comprehensive review',
            content='This is a detailed review with specific examples and thorough analysis of the vehicle performance.',
            overall_rating=4,
            pros='Good performance',
            cons='Minor issues',
            status='approved'
        )
        
        response = self.client.get(f'/api/reviews/vehicle-reviews/{review.id}/quality_analysis/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('quality_score', response.data)
        self.assertIn('readability_score', response.data)
        self.assertIn('helpfulness_score', response.data)
        self.assertIn('completeness_score', response.data)
        self.assertIn('insights', response.data)
    
    def test_review_stats_endpoint(self):
        """Test the review statistics endpoint."""
        self.client.force_authenticate(user=self.user)
        
        # Create some reviews
        for i in range(3):
            VehicleReview.objects.create(
                user=self.user,
                vehicle_model=self.vehicle_model,
                year=2015 + i,  # Use years 2015, 2016, 2017
                title=f'Review {i+1}',
                content=f'This is review number {i+1}',
                overall_rating=4 + (i % 2),  # Ratings of 4, 5, 4
                status='approved'
            )
        
        response = self.client.get(f'/api/reviews/vehicle-reviews/stats/?vehicle_model={self.vehicle_model.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_reviews'], 3)
        self.assertAlmostEqual(response.data['average_ratings']['avg_overall'], 4.33, places=1)


class ReviewLogTestCase(TestCase):
    """Test cases for review logging system."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        
        self.brand = Brand.objects.create(name='Test Brand')
        self.vehicle_model = VehicleModel.objects.create(
            brand=self.brand,
            name='Test Model'
        )
    
    def test_review_log_creation(self):
        """Test that review logs are created properly."""
        review = VehicleReview.objects.create(
            user=self.user,
            vehicle_model=self.vehicle_model,
            year=2014,
            title='Test Review',
            content='This is a test review',
            overall_rating=4,
            status='pending'
        )
        
        # Log an action
        ReviewLog.log_action(
            user=self.user,
            content_object=review,
            action='CREATE',
            description='Review created',
            ip_address='127.0.0.1',
            user_agent='Test Agent'
        )
        
        # Check that log was created
        log = ReviewLog.objects.get(object_id=review.id, action='CREATE')
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.description, 'Review created')
        self.assertEqual(log.ip_address, '127.0.0.1')
        self.assertEqual(log.user_agent, 'Test Agent')
    
    def test_moderation_logging(self):
        """Test that moderation actions are logged."""
        review = VehicleReview.objects.create(
            user=self.user,
            vehicle_model=self.vehicle_model,
            year=2013,
            title='Test Review',
            content='This is a test review for moderation',
            overall_rating=4,
            status='pending'
        )
        
        # Perform moderation
        moderation_results = ReviewModerationService.moderate_review(review)
        ReviewModerationService.log_moderation_action(review, moderation_results, self.user)
        
        # Check that moderation log was created
        log = ReviewLog.objects.get(object_id=review.id, action='MODERATE')
        self.assertEqual(log.user, self.user)
        self.assertIn('Automated moderation', log.description)
        self.assertIn('moderation_status', log.new_data)
        self.assertIn('moderation_score', log.new_data)
