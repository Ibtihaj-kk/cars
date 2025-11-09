"""
Review moderation system with quality control and automated filtering.
"""
import re
from typing import Dict, List, Tuple
from django.conf import settings
from django.utils import timezone
from .models import ReviewLog


class ReviewModerationService:
    """Service for automated review moderation and quality control."""
    
    # Profanity and inappropriate content patterns
    PROFANITY_PATTERNS = [
        r'\b(spam|fake|scam|fraud|cheat|lie|liar|terrible|awful|worst|hate|stupid|idiot)\b',
        r'\b(f[*@#$%]ck|sh[*@#$%]t|d[*@#$%]mn|b[*@#$%]tch|a[*@#$%]s)\b',
        r'\b(contact\s+me|call\s+me|email\s+me|whatsapp|telegram)\b',
        r'\b(\d{10,}|[\w\.-]+@[\w\.-]+\.\w+)\b',  # Phone numbers and emails
    ]
    
    # Spam indicators
    SPAM_PATTERNS = [
        r'(buy\s+now|click\s+here|visit\s+our|check\s+out)',
        r'(discount|offer|deal|sale|promotion)',
        r'(www\.|http|\.com|\.net|\.org)',
        r'(urgent|limited\s+time|act\s+now)',
    ]
    
    # Quality indicators
    MIN_REVIEW_LENGTH = 20
    MAX_REVIEW_LENGTH = 2000
    MIN_TITLE_LENGTH = 5
    MAX_TITLE_LENGTH = 100
    
    @classmethod
    def moderate_review(cls, review) -> Dict:
        """
        Perform comprehensive moderation on a review.
        
        Returns:
            Dict with moderation results including status, flags, and recommendations.
        """
        results = {
            'status': 'approved',  # approved, pending, rejected
            'flags': [],
            'score': 100,  # Quality score out of 100
            'recommendations': [],
            'auto_actions': []
        }
        
        # Check content quality
        quality_results = cls._check_content_quality(review)
        results['score'] -= quality_results['penalty']
        results['flags'].extend(quality_results['flags'])
        results['recommendations'].extend(quality_results['recommendations'])
        
        # Check for inappropriate content
        content_results = cls._check_inappropriate_content(review)
        results['score'] -= content_results['penalty']
        results['flags'].extend(content_results['flags'])
        
        # Check for spam
        spam_results = cls._check_spam_indicators(review)
        results['score'] -= spam_results['penalty']
        results['flags'].extend(spam_results['flags'])
        
        # Check user behavior
        behavior_results = cls._check_user_behavior(review)
        results['score'] -= behavior_results['penalty']
        results['flags'].extend(behavior_results['flags'])
        
        # Determine final status based on score and flags
        if results['score'] < 30 or 'severe_violation' in results['flags']:
            results['status'] = 'rejected'
            results['auto_actions'].append('auto_reject')
        elif results['score'] < 60 or 'moderate_violation' in results['flags']:
            results['status'] = 'pending'
            results['auto_actions'].append('require_manual_review')
        
        return results
    
    @classmethod
    def _check_content_quality(cls, review) -> Dict:
        """Check review content quality."""
        results = {'penalty': 0, 'flags': [], 'recommendations': []}
        
        # Check review text length
        review_text = getattr(review, 'content', '') or ''
        if len(review_text) < cls.MIN_REVIEW_LENGTH:
            results['penalty'] += 20
            results['flags'].append('too_short')
            results['recommendations'].append('Review text is too short. Please provide more details.')
        elif len(review_text) > cls.MAX_REVIEW_LENGTH:
            results['penalty'] += 10
            results['flags'].append('too_long')
            results['recommendations'].append('Review text is too long. Please be more concise.')
        
        # Check title length
        title = getattr(review, 'title', '') or ''
        if len(title) < cls.MIN_TITLE_LENGTH:
            results['penalty'] += 10
            results['flags'].append('title_too_short')
            results['recommendations'].append('Title is too short. Please provide a descriptive title.')
        elif len(title) > cls.MAX_TITLE_LENGTH:
            results['penalty'] += 5
            results['flags'].append('title_too_long')
            results['recommendations'].append('Title is too long. Please shorten it.')
        
        # Check for repeated characters or words
        if re.search(r'(.)\1{4,}', review_text):  # 5+ repeated characters
            results['penalty'] += 15
            results['flags'].append('repeated_characters')
        
        if re.search(r'\b(\w+)\s+\1\s+\1\b', review_text):  # Repeated words
            results['penalty'] += 10
            results['flags'].append('repeated_words')
        
        # Check for all caps (shouting)
        if len(review_text) > 20 and review_text.isupper():
            results['penalty'] += 15
            results['flags'].append('all_caps')
            results['recommendations'].append('Please avoid writing in all capital letters.')
        
        # Check rating consistency
        overall_rating = getattr(review, 'overall_rating', 0)
        if overall_rating:
            # Check if detailed ratings are consistent with overall rating
            detailed_ratings = []
            for field in ['performance_rating', 'comfort_rating', 'reliability_rating',
                         'value_rating', 'fuel_economy_rating']:
                rating = getattr(review, field, None)
                if rating:
                    detailed_ratings.append(rating)
            
            if detailed_ratings:
                avg_detailed = sum(detailed_ratings) / len(detailed_ratings)
                if abs(overall_rating - avg_detailed) > 1.5:
                    results['penalty'] += 10
                    results['flags'].append('rating_inconsistency')
                    results['recommendations'].append('Overall rating seems inconsistent with detailed ratings.')
        
        return results
    
    @classmethod
    def _check_inappropriate_content(cls, review) -> Dict:
        """Check for inappropriate content."""
        results = {'penalty': 0, 'flags': []}
        
        text_to_check = f"{getattr(review, 'title', '')} {getattr(review, 'content', '')} {getattr(review, 'pros', '')} {getattr(review, 'cons', '')}"
        text_to_check = text_to_check.lower()
        
        # Check for profanity and inappropriate language
        for pattern in cls.PROFANITY_PATTERNS:
            if re.search(pattern, text_to_check, re.IGNORECASE):
                results['penalty'] += 30
                results['flags'].append('inappropriate_language')
                break
        
        # Check for personal information sharing
        if re.search(r'\b(\d{10,}|[\w\.-]+@[\w\.-]+\.\w+)\b', text_to_check):
            results['penalty'] += 25
            results['flags'].append('personal_info_sharing')
        
        # Check for external links or promotional content
        if re.search(r'(www\.|http|\.com|\.net|\.org)', text_to_check):
            results['penalty'] += 20
            results['flags'].append('external_links')
        
        # Severe violations
        if results['penalty'] >= 30:
            results['flags'].append('severe_violation')
        elif results['penalty'] >= 15:
            results['flags'].append('moderate_violation')
        
        return results
    
    @classmethod
    def _check_spam_indicators(cls, review) -> Dict:
        """Check for spam indicators."""
        results = {'penalty': 0, 'flags': []}
        
        text_to_check = f"{getattr(review, 'title', '')} {getattr(review, 'content', '')} {getattr(review, 'pros', '')} {getattr(review, 'cons', '')}"
        text_to_check = text_to_check.lower()
        
        spam_score = 0
        for pattern in cls.SPAM_PATTERNS:
            matches = len(re.findall(pattern, text_to_check, re.IGNORECASE))
            spam_score += matches * 5
        
        if spam_score >= 15:
            results['penalty'] += 40
            results['flags'].append('likely_spam')
            results['flags'].append('severe_violation')
        elif spam_score >= 10:
            results['penalty'] += 20
            results['flags'].append('possible_spam')
            results['flags'].append('moderate_violation')
        
        return results
    
    @classmethod
    def _check_user_behavior(cls, review) -> Dict:
        """Check user behavior patterns."""
        results = {'penalty': 0, 'flags': []}
        
        user = getattr(review, 'user', None)
        if not user:
            return results
        
        # Check review frequency (prevent spam)
        from django.utils import timezone
        from datetime import timedelta
        
        recent_reviews = cls._get_user_recent_reviews(user, hours=24)
        if recent_reviews >= 5:
            results['penalty'] += 25
            results['flags'].append('excessive_posting')
            results['flags'].append('moderate_violation')
        
        # Check for duplicate content
        if cls._check_duplicate_content(review):
            results['penalty'] += 30
            results['flags'].append('duplicate_content')
            results['flags'].append('severe_violation')
        
        # Check account age
        account_age = timezone.now() - user.date_joined
        if account_age.days < 1:
            results['penalty'] += 10
            results['flags'].append('new_account')
        
        return results
    
    @classmethod
    def _get_user_recent_reviews(cls, user, hours=24) -> int:
        """Get count of user's recent reviews."""
        from django.utils import timezone
        from datetime import timedelta
        from .models import VehicleReview, DealerReview, SellerReview, ListingReview
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        count = 0
        for model in [VehicleReview, DealerReview, SellerReview, ListingReview]:
            count += model.objects.filter(
                user=user,
                created_at__gte=cutoff_time
            ).count()
        
        return count
    
    @classmethod
    def _check_duplicate_content(cls, review) -> bool:
        """Check if review content is duplicate."""
        from .models import VehicleReview, DealerReview, SellerReview, ListingReview
        
        review_text = getattr(review, 'content', '') or ''
        if len(review_text) < 50:  # Too short to be meaningful duplicate check
            return False
        
        # Check for exact or near-exact duplicates
        for model in [VehicleReview, DealerReview, SellerReview, ListingReview]:
            existing_reviews = model.objects.filter(
                user=review.user
            ).exclude(id=getattr(review, 'id', None))
            
            for existing in existing_reviews:
                existing_text = getattr(existing, 'content', '') or ''
                if cls._calculate_similarity(review_text, existing_text) > 0.8:
                    return True
        
        return False
    
    @classmethod
    def _calculate_similarity(cls, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (simple implementation)."""
        if not text1 or not text2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    @classmethod
    def log_moderation_action(cls, review, moderation_results, user=None):
        """Log moderation action for audit trail."""
        ReviewLog.log_action(
            user=user,
            content_object=review,
            action='MODERATE',
            description=f"Automated moderation: {moderation_results['status']} (score: {moderation_results['score']})",
            new_data={
                'moderation_status': moderation_results['status'],
                'moderation_score': moderation_results['score'],
                'moderation_flags': moderation_results['flags'],
                'auto_actions': moderation_results['auto_actions']
            }
        )


class ReviewQualityAnalyzer:
    """Analyzer for review quality metrics and insights."""
    
    @classmethod
    def analyze_review_quality(cls, review) -> Dict:
        """Analyze overall review quality."""
        analysis = {
            'quality_score': 0,
            'readability_score': 0,
            'helpfulness_score': 0,
            'completeness_score': 0,
            'insights': []
        }
        
        # Analyze readability
        readability = cls._analyze_readability(review)
        analysis['readability_score'] = readability['score']
        analysis['insights'].extend(readability['insights'])
        
        # Analyze helpfulness
        helpfulness = cls._analyze_helpfulness(review)
        analysis['helpfulness_score'] = helpfulness['score']
        analysis['insights'].extend(helpfulness['insights'])
        
        # Analyze completeness
        completeness = cls._analyze_completeness(review)
        analysis['completeness_score'] = completeness['score']
        analysis['insights'].extend(completeness['insights'])
        
        # Calculate overall quality score
        analysis['quality_score'] = (
            analysis['readability_score'] * 0.3 +
            analysis['helpfulness_score'] * 0.4 +
            analysis['completeness_score'] * 0.3
        )
        
        return analysis
    
    @classmethod
    def _analyze_readability(cls, review) -> Dict:
        """Analyze review readability."""
        results = {'score': 50, 'insights': []}
        
        review_text = getattr(review, 'content', '') or ''
        
        if not review_text:
            results['score'] = 0
            results['insights'].append('No review text provided')
            return results
        
        # Sentence count and average length
        sentences = re.split(r'[.!?]+', review_text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)
            
            if 10 <= avg_sentence_length <= 20:
                results['score'] += 20
                results['insights'].append('Good sentence length for readability')
            elif avg_sentence_length < 5:
                results['score'] -= 10
                results['insights'].append('Sentences are too short')
            elif avg_sentence_length > 30:
                results['score'] -= 15
                results['insights'].append('Sentences are too long')
        
        # Paragraph structure
        paragraphs = review_text.split('\n\n')
        if len(paragraphs) > 1:
            results['score'] += 10
            results['insights'].append('Well-structured with paragraphs')
        
        # Grammar and punctuation (basic check)
        if re.search(r'[.!?]', review_text):
            results['score'] += 10
        else:
            results['score'] -= 10
            results['insights'].append('Missing proper punctuation')
        
        return results
    
    @classmethod
    def _analyze_helpfulness(cls, review) -> Dict:
        """Analyze review helpfulness."""
        results = {'score': 50, 'insights': []}
        
        # Check for specific details
        review_text = getattr(review, 'content', '') or ''
        pros = getattr(review, 'pros', '') or ''
        cons = getattr(review, 'cons', '') or ''
        
        # Pros and cons provided
        if pros and cons:
            results['score'] += 20
            results['insights'].append('Provides both pros and cons')
        elif pros or cons:
            results['score'] += 10
            results['insights'].append('Provides either pros or cons')
        
        # Specific details and examples
        detail_indicators = [
            r'\b(because|since|due to|reason|example|specifically|particularly)\b',
            r'\b(experience|used|tried|tested|compared)\b',
            r'\b(quality|performance|service|delivery|communication)\b'
        ]
        
        detail_score = 0
        for pattern in detail_indicators:
            if re.search(pattern, review_text, re.IGNORECASE):
                detail_score += 5
        
        results['score'] += min(detail_score, 20)
        if detail_score >= 15:
            results['insights'].append('Contains specific details and examples')
        
        # Length indicates thoroughness
        if len(review_text) >= 100:
            results['score'] += 10
            results['insights'].append('Comprehensive review length')
        
        return results
    
    @classmethod
    def _analyze_completeness(cls, review) -> Dict:
        """Analyze review completeness."""
        results = {'score': 0, 'insights': []}
        
        # Check required fields
        if getattr(review, 'title', ''):
            results['score'] += 20
        else:
            results['insights'].append('Missing title')
        
        if getattr(review, 'content', ''):
            results['score'] += 30
        else:
            results['insights'].append('Missing review text')
        
        if getattr(review, 'overall_rating', 0):
            results['score'] += 25
        else:
            results['insights'].append('Missing overall rating')
        
        # Check optional but valuable fields
        optional_fields = ['pros', 'cons']
        filled_optional = sum(1 for field in optional_fields if getattr(review, field, ''))
        results['score'] += (filled_optional / len(optional_fields)) * 15
        
        # Check detailed ratings
        detailed_rating_fields = []
        if hasattr(review, 'communication_rating'):
            detailed_rating_fields.extend(['communication_rating', 'reliability_rating', 'responsiveness_rating'])
        if hasattr(review, 'condition_rating'):
            detailed_rating_fields.extend(['condition_rating', 'value_rating', 'description_accuracy_rating'])
        
        if detailed_rating_fields:
            filled_detailed = sum(1 for field in detailed_rating_fields if getattr(review, field, 0))
            results['score'] += (filled_detailed / len(detailed_rating_fields)) * 10
        
        if results['score'] >= 90:
            results['insights'].append('Very complete review')
        elif results['score'] >= 70:
            results['insights'].append('Mostly complete review')
        elif results['score'] < 50:
            results['insights'].append('Incomplete review - missing important information')
        
        return results