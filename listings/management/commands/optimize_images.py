"""
Django management command to optimize existing images in the database.
This command will generate thumbnails and WebP versions for existing images.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db import models
from listings.models import ListingImage
import time


class Command(BaseCommand):
    help = 'Optimize existing images by generating thumbnails and WebP versions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of images to process in each batch (default: 10)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration of existing thumbnails and WebP versions'
        )
        parser.add_argument(
            '--listing-id',
            type=int,
            help='Process images for a specific listing ID only'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        force = options['force']
        listing_id = options['listing_id']

        # Build queryset
        queryset = ListingImage.objects.select_related('listing')
        
        if listing_id:
            queryset = queryset.filter(listing_id=listing_id)
            
        if not force:
            # Only process images that don't have all thumbnails generated
            queryset = queryset.filter(
                models.Q(thumbnail__isnull=True) |
                models.Q(thumbnail_small__isnull=True) |
                models.Q(thumbnail_medium__isnull=True) |
                models.Q(image_webp__isnull=True) |
                models.Q(thumbnail_webp__isnull=True)
            )

        total_images = queryset.count()
        
        if total_images == 0:
            self.stdout.write(
                self.style.SUCCESS('No images need optimization.')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'Found {total_images} images to optimize.')
        )

        processed = 0
        errors = 0
        
        # Process images in batches
        for i in range(0, total_images, batch_size):
            batch = queryset[i:i + batch_size]
            
            for image in batch:
                try:
                    with transaction.atomic():
                        self.stdout.write(f'Processing image {processed + 1}/{total_images}: {image.image.name}')
                        
                        # Force regeneration if requested
                        if force:
                            # Clear existing thumbnails
                            if image.thumbnail:
                                image.thumbnail.delete(save=False)
                            if image.thumbnail_small:
                                image.thumbnail_small.delete(save=False)
                            if image.thumbnail_medium:
                                image.thumbnail_medium.delete(save=False)
                            if image.image_webp:
                                image.image_webp.delete(save=False)
                            if image.thumbnail_webp:
                                image.thumbnail_webp.delete(save=False)
                        
                        # Generate all thumbnails and optimizations
                        image._generate_all_thumbnails()
                        
                        processed += 1
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Optimized: {image.image.name}')
                        )
                        
                except Exception as e:
                    errors += 1
                    self.stdout.write(
                        self.style.ERROR(f'✗ Error processing {image.image.name}: {str(e)}')
                    )
                    continue
            
            # Small delay between batches to avoid overwhelming the system
            if i + batch_size < total_images:
                time.sleep(0.5)
                
        # Summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(f'Optimization complete!')
        )
        self.stdout.write(f'Total processed: {processed}')
        self.stdout.write(f'Errors: {errors}')
        
        if errors > 0:
            self.stdout.write(
                self.style.WARNING(f'Some images failed to process. Check the error messages above.')
            )