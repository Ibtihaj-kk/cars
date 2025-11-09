"""
Django management command for bulk moderation of reviews.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from reviews.models import VehicleReview, DealerReview, SellerReview, ListingReview, ReviewLog
from reviews.moderation import ReviewModerationService, ReviewQualityAnalyzer


class Command(BaseCommand):
    help = 'Moderate existing reviews using the automated moderation system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--review-type',
            type=str,
            choices=['vehicle', 'dealer', 'seller', 'listing', 'all'],
            default='all',
            help='Type of reviews to moderate (default: all)'
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=['pending', 'approved', 'rejected', 'all'],
            default='pending',
            help='Status of reviews to moderate (default: pending)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of reviews to process in each batch (default: 100)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to show what would be done'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-moderation of already moderated reviews'
        )

    def handle(self, *args, **options):
        review_type = options['review_type']
        status_filter = options['status']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(
            self.style.SUCCESS(f'Starting review moderation...')
        )
        self.stdout.write(f'Review type: {review_type}')
        self.stdout.write(f'Status filter: {status_filter}')
        self.stdout.write(f'Batch size: {batch_size}')
        self.stdout.write(f'Dry run: {dry_run}')
        self.stdout.write(f'Force re-moderation: {force}')
        self.stdout.write('-' * 50)

        # Get review models to process
        models_to_process = []
        if review_type in ['vehicle', 'all']:
            models_to_process.append(('VehicleReview', VehicleReview))
        if review_type in ['dealer', 'all']:
            models_to_process.append(('DealerReview', DealerReview))
        if review_type in ['seller', 'all']:
            models_to_process.append(('SellerReview', SellerReview))
        if review_type in ['listing', 'all']:
            models_to_process.append(('ListingReview', ListingReview))

        total_processed = 0
        total_updated = 0

        for model_name, model_class in models_to_process:
            self.stdout.write(f'\nProcessing {model_name}...')
            
            # Build queryset
            queryset = model_class.objects.all()
            if status_filter != 'all':
                queryset = queryset.filter(status=status_filter)
            
            # If not forcing, skip reviews that have been moderated recently
            if not force:
                from django.utils import timezone
                from datetime import timedelta
                recent_cutoff = timezone.now() - timedelta(days=1)
                
                # Get reviews that have moderation logs
                moderated_review_ids = ReviewLog.objects.filter(
                    action='MODERATE',
                    created_at__gte=recent_cutoff,
                    content_type__model=model_name.lower()
                ).values_list('object_id', flat=True)
                
                queryset = queryset.exclude(id__in=moderated_review_ids)

            total_count = queryset.count()
            self.stdout.write(f'Found {total_count} {model_name} reviews to process')

            if total_count == 0:
                continue

            # Process in batches
            processed_count = 0
            updated_count = 0

            for offset in range(0, total_count, batch_size):
                batch = queryset[offset:offset + batch_size]
                
                with transaction.atomic():
                    for review in batch:
                        try:
                            # Perform moderation
                            moderation_results = ReviewModerationService.moderate_review(review)
                            
                            # Check if status would change
                            old_status = review.status
                            new_status = moderation_results['status']
                            
                            if old_status != new_status or force:
                                if not dry_run:
                                    # Update review status
                                    review.status = new_status
                                    review.save()
                                    
                                    # Log moderation action
                                    ReviewModerationService.log_moderation_action(
                                        review, moderation_results
                                    )
                                
                                updated_count += 1
                                self.stdout.write(
                                    f'  {review.id}: {old_status} -> {new_status} '
                                    f'(score: {moderation_results["score"]}, '
                                    f'flags: {", ".join(moderation_results["flags"]) or "none"})'
                                )
                            
                            processed_count += 1
                            
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f'Error processing review {review.id}: {str(e)}')
                            )
                
                # Progress update
                self.stdout.write(f'Processed {processed_count}/{total_count} {model_name} reviews...')

            self.stdout.write(
                self.style.SUCCESS(f'Completed {model_name}: {updated_count} reviews updated')
            )
            
            total_processed += processed_count
            total_updated += updated_count

        # Final summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(
            self.style.SUCCESS(f'Moderation completed!')
        )
        self.stdout.write(f'Total reviews processed: {total_processed}')
        self.stdout.write(f'Total reviews updated: {total_updated}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('This was a dry run - no changes were made')
            )


class QualityAnalysisCommand(BaseCommand):
    """Command for analyzing review quality across the platform."""
    
    help = 'Analyze review quality and generate insights'

    def add_arguments(self, parser):
        parser.add_argument(
            '--review-type',
            type=str,
            choices=['vehicle', 'dealer', 'seller', 'listing', 'all'],
            default='all',
            help='Type of reviews to analyze (default: all)'
        )
        parser.add_argument(
            '--output-format',
            type=str,
            choices=['summary', 'detailed', 'csv'],
            default='summary',
            help='Output format (default: summary)'
        )

    def handle(self, *args, **options):
        review_type = options['review_type']
        output_format = options['output_format']

        self.stdout.write(
            self.style.SUCCESS(f'Starting quality analysis...')
        )

        # Get review models to analyze
        models_to_analyze = []
        if review_type in ['vehicle', 'all']:
            models_to_analyze.append(('VehicleReview', VehicleReview))
        if review_type in ['dealer', 'all']:
            models_to_analyze.append(('DealerReview', DealerReview))
        if review_type in ['seller', 'all']:
            models_to_analyze.append(('SellerReview', SellerReview))
        if review_type in ['listing', 'all']:
            models_to_analyze.append(('ListingReview', ListingReview))

        overall_stats = {
            'total_reviews': 0,
            'quality_scores': [],
            'readability_scores': [],
            'helpfulness_scores': [],
            'completeness_scores': []
        }

        for model_name, model_class in models_to_analyze:
            self.stdout.write(f'\nAnalyzing {model_name}...')
            
            reviews = model_class.objects.filter(status='approved')
            count = reviews.count()
            
            if count == 0:
                self.stdout.write(f'No approved {model_name} reviews found')
                continue

            model_stats = {
                'count': count,
                'quality_scores': [],
                'readability_scores': [],
                'helpfulness_scores': [],
                'completeness_scores': []
            }

            # Analyze sample of reviews (max 1000 for performance)
            sample_size = min(count, 1000)
            sample_reviews = reviews.order_by('?')[:sample_size]

            for review in sample_reviews:
                analysis = ReviewQualityAnalyzer.analyze_review_quality(review)
                
                model_stats['quality_scores'].append(analysis['quality_score'])
                model_stats['readability_scores'].append(analysis['readability_score'])
                model_stats['helpfulness_scores'].append(analysis['helpfulness_score'])
                model_stats['completeness_scores'].append(analysis['completeness_score'])

            # Calculate averages
            avg_quality = sum(model_stats['quality_scores']) / len(model_stats['quality_scores'])
            avg_readability = sum(model_stats['readability_scores']) / len(model_stats['readability_scores'])
            avg_helpfulness = sum(model_stats['helpfulness_scores']) / len(model_stats['helpfulness_scores'])
            avg_completeness = sum(model_stats['completeness_scores']) / len(model_stats['completeness_scores'])

            self.stdout.write(f'  Total reviews: {count}')
            self.stdout.write(f'  Sample analyzed: {sample_size}')
            self.stdout.write(f'  Average quality score: {avg_quality:.1f}/100')
            self.stdout.write(f'  Average readability: {avg_readability:.1f}/100')
            self.stdout.write(f'  Average helpfulness: {avg_helpfulness:.1f}/100')
            self.stdout.write(f'  Average completeness: {avg_completeness:.1f}/100')

            # Add to overall stats
            overall_stats['total_reviews'] += count
            overall_stats['quality_scores'].extend(model_stats['quality_scores'])
            overall_stats['readability_scores'].extend(model_stats['readability_scores'])
            overall_stats['helpfulness_scores'].extend(model_stats['helpfulness_scores'])
            overall_stats['completeness_scores'].extend(model_stats['completeness_scores'])

        # Overall summary
        if overall_stats['quality_scores']:
            self.stdout.write('\n' + '=' * 50)
            self.stdout.write(self.style.SUCCESS('OVERALL PLATFORM QUALITY ANALYSIS'))
            self.stdout.write('=' * 50)
            
            avg_quality = sum(overall_stats['quality_scores']) / len(overall_stats['quality_scores'])
            avg_readability = sum(overall_stats['readability_scores']) / len(overall_stats['readability_scores'])
            avg_helpfulness = sum(overall_stats['helpfulness_scores']) / len(overall_stats['helpfulness_scores'])
            avg_completeness = sum(overall_stats['completeness_scores']) / len(overall_stats['completeness_scores'])

            self.stdout.write(f'Total reviews analyzed: {len(overall_stats["quality_scores"])}')
            self.stdout.write(f'Platform average quality score: {avg_quality:.1f}/100')
            self.stdout.write(f'Platform average readability: {avg_readability:.1f}/100')
            self.stdout.write(f'Platform average helpfulness: {avg_helpfulness:.1f}/100')
            self.stdout.write(f'Platform average completeness: {avg_completeness:.1f}/100')

            # Quality distribution
            high_quality = len([s for s in overall_stats['quality_scores'] if s >= 80])
            medium_quality = len([s for s in overall_stats['quality_scores'] if 60 <= s < 80])
            low_quality = len([s for s in overall_stats['quality_scores'] if s < 60])

            self.stdout.write(f'\nQuality Distribution:')
            self.stdout.write(f'  High quality (80+): {high_quality} ({high_quality/len(overall_stats["quality_scores"])*100:.1f}%)')
            self.stdout.write(f'  Medium quality (60-79): {medium_quality} ({medium_quality/len(overall_stats["quality_scores"])*100:.1f}%)')
            self.stdout.write(f'  Low quality (<60): {low_quality} ({low_quality/len(overall_stats["quality_scores"])*100:.1f}%)')