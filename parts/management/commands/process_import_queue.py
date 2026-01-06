"""
Management command to process queued bulk imports from the database.
This provides a Celery-free alternative for background processing.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.files.storage import default_storage
from parts.models import BulkUploadLog
from business_partners.models import BusinessPartner
from business_partners.vendor_views import process_import_file
import os

class Command(BaseCommand):
    help = 'Process queued bulk import files from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=10,
            help='Maximum number of queued imports to process (default: 10)',
        )
        parser.add_argument(
            '--chunk-size',
            type=int,
            default=5000,
            help='Chunk size for processing (default: 5000)',
        )

    def handle(self, *args, **options):
        limit = options['limit']
        chunk_size = options['chunk_size']
        
        # Get queued imports for database processing
        queued_imports = BulkUploadLog.objects.filter(
            status='queued',
            processing_mode='async_db'
        ).order_by('uploaded_at')[:limit]
        
        if not queued_imports:
            self.stdout.write('No queued imports found for processing.')
            return
        
        self.stdout.write(f'Processing {len(queued_imports)} queued imports...')
        
        processed_count = 0
        success_count = 0
        
        for upload_log in queued_imports:
            try:
                self.stdout.write(f'Processing import: {upload_log.file_name} (ID: {upload_log.id})')
                
                # Extract storage path from success_message
                storage_path = None
                if upload_log.success_message and upload_log.success_message.startswith('Database queue: '):
                    storage_path = upload_log.success_message.replace('Database queue: ', '')
                
                if not storage_path or not default_storage.exists(storage_path):
                    upload_log.status = 'failed'
                    upload_log.error_log = 'Stored file not found or invalid storage path'
                    upload_log.completed_at = timezone.now()
                    upload_log.save()
                    self.stdout.write(self.style.ERROR(f'File not found for import {upload_log.id}'))
                    continue
                
                # Get business partner from user
                business_partner = BusinessPartner.objects.filter(user=upload_log.user).first()
                if not business_partner:
                    upload_log.status = 'failed'
                    upload_log.error_log = 'Business partner not found for user'
                    upload_log.completed_at = timezone.now()
                    upload_log.save()
                    self.stdout.write(self.style.ERROR(f'Business partner not found for user {upload_log.user.id}'))
                    continue
                
                # Update status to processing
                upload_log.status = 'processing'
                upload_log.success_message = 'Processing via database queue'
                upload_log.save()
                
                # Process the file
                with default_storage.open(storage_path, 'rb') as import_file:
                    results = process_import_file(
                        import_file=import_file,
                        business_partner=business_partner,
                        import_status='published',  # Default status
                        update_existing=False,      # Default to not update existing
                        validate_only=False,
                        upload_log_id=upload_log.id,
                        chunk_size=chunk_size,
                    )
                
                # Update results
                total = results.get('total_rows', 0)
                created = results.get('created_count', 0)
                updated = results.get('updated_count', 0)
                errors = results.get('error_count', 0)
                
                upload_log.total_records = total
                upload_log.successful_records = created + updated
                upload_log.failed_records = errors
                upload_log.status = 'completed' if errors == 0 else 'partial'
                upload_log.success_message = f'Database processing complete: {created} created, {updated} updated, {errors} errors'
                upload_log.completed_at = timezone.now()
                upload_log.save()
                
                # Clean up stored file
                try:
                    default_storage.delete(storage_path)
                except Exception:
                    pass
                
                self.stdout.write(self.style.SUCCESS(
                    f'Completed: {upload_log.file_name} - '
                    f'{created} created, {updated} updated, {errors} errors'
                ))
                success_count += 1
                
            except Exception as e:
                # Handle any processing errors
                upload_log.status = 'failed'
                upload_log.error_log = f'Database queue processing failed: {str(e)}'
                upload_log.completed_at = timezone.now()
                upload_log.save()
                
                self.stdout.write(self.style.ERROR(
                    f'Failed to process {upload_log.file_name}: {str(e)}'
                ))
                
            finally:
                processed_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Processing complete: {success_count} successful, '
            f'{processed_count - success_count} failed out of {processed_count} total'
        ))