"""
Celery tasks for the Parts module.
Handles background processing for CSV imports, API imports, and cache management.
"""

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import csv
import io
import requests
from decimal import Decimal
import logging

from .models import Part, Category, Brand, BulkUploadLog, IntegrationSource, Cart
from .cache import warm_cache, invalidate_part_cache, get_cached_popular_parts
from users.models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_csv_import(self, file_content, user_id, upload_log_id):
    """
    Process CSV file import in the background.
    """
    try:
        upload_log = BulkUploadLog.objects.get(id=upload_log_id)
        upload_log.status = 'processing'
        upload_log.save()
        
        user = User.objects.get(id=user_id)
        
        # Parse CSV content
        csv_file = io.StringIO(file_content)
        reader = csv.DictReader(csv_file)
        
        success_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):
            try:
                # Validate required fields
                required_fields = ['name', 'sku', 'price', 'category', 'brand']
                missing_fields = [field for field in required_fields if not row.get(field)]
                
                if missing_fields:
                    error_msg = f"Row {row_num}: Missing required fields: {', '.join(missing_fields)}"
                    errors.append(error_msg)
                    error_count += 1
                    continue
                
                # Get or create category
                category_name = row['category'].strip()
                category, _ = Category.objects.get_or_create(
                    name=category_name,
                    defaults={'description': f'Auto-created category for {category_name}'}
                )
                
                # Get or create brand
                brand_name = row['brand'].strip()
                brand, _ = Brand.objects.get_or_create(
                    name=brand_name,
                    defaults={'is_active': True}
                )
                
                # Create or update part
                part_data = {
                    'name': row['name'].strip(),
                    'description': row.get('description', '').strip(),
                    'category': category,
                    'brand': brand,
                    'price': Decimal(str(row['price'])),
                    'quantity': int(row.get('quantity', 0)),
                    'weight': Decimal(str(row['weight'])) if row.get('weight') else None,
                    'dimensions': row.get('dimensions', '').strip(),
                    'warranty_period': int(row['warranty_period']) if row.get('warranty_period') else None,
                    'is_active': row.get('is_active', 'true').lower() == 'true',
                    'is_featured': row.get('is_featured', 'false').lower() == 'true',
                }
                
                # Set dealer for non-admin users
                if user.role != 'admin':
                    part_data['dealer'] = user
                
                # Check if part exists by SKU
                sku = row['sku'].strip()
                existing_part = Part.objects.filter(sku=sku).first()
                
                if existing_part:
                    # Update existing part
                    for key, value in part_data.items():
                        setattr(existing_part, key, value)
                    existing_part.save()
                else:
                    # Create new part
                    part_data['sku'] = sku
                    Part.objects.create(**part_data)
                
                success_count += 1
                
            except Exception as e:
                error_msg = f"Row {row_num}: {str(e)}"
                errors.append(error_msg)
                error_count += 1
                logger.error(f"CSV import error for row {row_num}: {e}")
        
        # Update upload log
        upload_log.status = 'completed' if error_count == 0 else 'completed_with_errors'
        upload_log.success_count = success_count
        upload_log.error_count = error_count
        upload_log.error_details = '\n'.join(errors) if errors else None
        upload_log.completed_at = timezone.now()
        upload_log.save()
        
        # Send notification email
        send_import_notification_email.delay(user_id, upload_log_id, 'csv')
        
        # Invalidate relevant caches
        warm_cache()
        
        return {
            'success': True,
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors[:10]  # Limit errors in response
        }
        
    except Exception as e:
        logger.error(f"CSV import task failed: {e}")
        
        # Update upload log with error
        try:
            upload_log = BulkUploadLog.objects.get(id=upload_log_id)
            upload_log.status = 'failed'
            upload_log.error_details = str(e)
            upload_log.completed_at = timezone.now()
            upload_log.save()
        except:
            pass
        
        return {'success': False, 'error': str(e)}


@shared_task(bind=True)
def process_api_import(self, integration_source_id, user_id):
    """
    Process API import in the background.
    """
    try:
        integration_source = IntegrationSource.objects.get(id=integration_source_id)
        user = User.objects.get(id=user_id)
        
        # Create upload log
        upload_log = BulkUploadLog.objects.create(
            user=user,
            import_type='api',
            source_name=integration_source.name,
            status='processing'
        )
        
        # Prepare authentication
        headers = {'Content-Type': 'application/json'}
        auth = None
        
        if integration_source.auth_type == 'api_key':
            headers['Authorization'] = f'Bearer {integration_source.api_key}'
        elif integration_source.auth_type == 'basic':
            # For basic auth, api_key should contain username:password
            import base64
            encoded_credentials = base64.b64encode(integration_source.api_key.encode()).decode()
            headers['Authorization'] = f'Basic {encoded_credentials}'
        
        # Make API request
        response = requests.get(
            integration_source.api_url,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        # Process API data
        api_data = response.json()
        success_count, error_count, errors = process_api_data(api_data, user, integration_source)
        
        # Update upload log
        upload_log.status = 'completed' if error_count == 0 else 'completed_with_errors'
        upload_log.success_count = success_count
        upload_log.error_count = error_count
        upload_log.error_details = '\n'.join(errors) if errors else None
        upload_log.completed_at = timezone.now()
        upload_log.save()
        
        # Send notification email
        send_import_notification_email.delay(user_id, upload_log.id, 'api')
        
        # Invalidate relevant caches
        warm_cache()
        
        return {
            'success': True,
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors[:10]
        }
        
    except Exception as e:
        logger.error(f"API import task failed: {e}")
        
        # Update upload log with error
        try:
            upload_log.status = 'failed'
            upload_log.error_details = str(e)
            upload_log.completed_at = timezone.now()
            upload_log.save()
        except:
            pass
        
        return {'success': False, 'error': str(e)}


def process_api_data(api_data, user, integration_source):
    """
    Process API response data and create/update parts.
    """
    success_count = 0
    error_count = 0
    errors = []
    
    # Handle different API response formats
    if isinstance(api_data, dict):
        if 'data' in api_data:
            parts_data = api_data['data']
        elif 'products' in api_data:
            parts_data = api_data['products']
        elif 'items' in api_data:
            parts_data = api_data['items']
        else:
            parts_data = [api_data]  # Single item
    else:
        parts_data = api_data  # Assume it's a list
    
    for item_data in parts_data:
        try:
            # Extract part data with flexible field mapping
            name = (
                item_data.get('name') or 
                item_data.get('title') or 
                item_data.get('product_name')
            )
            
            sku = (
                item_data.get('sku') or 
                item_data.get('product_id') or 
                item_data.get('id')
            )
            
            price_value = (
                item_data.get('price') or 
                item_data.get('cost') or 
                item_data.get('price_value')
            )
            
            # Validate required fields
            if not all([name, sku, price_value]):
                error_msg = f"Missing required fields for item: {item_data}"
                errors.append(error_msg)
                error_count += 1
                continue
            
            # Get or create category
            category_name = item_data.get('category', 'Imported Parts')
            category, _ = Category.objects.get_or_create(
                name=category_name,
                defaults={'description': f'Auto-created category for {category_name}'}
            )
            
            # Get or create brand
            brand_name = item_data.get('brand', 'Generic')
            brand, _ = Brand.objects.get_or_create(
                name=brand_name,
                defaults={'is_active': True}
            )
            
            # Create or update part
            part_data = {
                'name': name,
                'description': item_data.get('description', ''),
                'category': category,
                'brand': brand,
                'price': Decimal(str(price_value)),
                'quantity': int(item_data.get('quantity', 0)),
                'weight': Decimal(str(item_data['weight'])) if item_data.get('weight') else None,
                'dimensions': item_data.get('dimensions', ''),
                'warranty_period': int(item_data['warranty_period']) if item_data.get('warranty_period') else None,
                'is_active': True,
                'is_featured': False,
            }
            
            # Set dealer for non-admin users
            if user.role != 'admin':
                part_data['dealer'] = user
            
            # Check if part exists by SKU
            existing_part = Part.objects.filter(sku=str(sku)).first()
            
            if existing_part:
                # Update existing part
                for key, value in part_data.items():
                    setattr(existing_part, key, value)
                existing_part.save()
            else:
                # Create new part
                part_data['sku'] = str(sku)
                Part.objects.create(**part_data)
            
            success_count += 1
            
        except Exception as e:
            error_msg = f"Error processing item {item_data.get('sku', 'unknown')}: {str(e)}"
            errors.append(error_msg)
            error_count += 1
            logger.error(f"API data processing error: {e}")
    
    return success_count, error_count, errors


@shared_task
def send_import_notification_email(user_id, upload_log_id, import_type):
    """
    Send email notification about import completion.
    """
    try:
        user = User.objects.get(id=user_id)
        upload_log = BulkUploadLog.objects.get(id=upload_log_id)
        
        subject = f'Cars Portal - {import_type.upper()} Import Completed'
        
        if upload_log.status == 'completed':
            message = f"""
            Your {import_type.upper()} import has been completed successfully!
            
            Results:
            - Successfully imported: {upload_log.success_count} parts
            - Errors: {upload_log.error_count}
            
            Import completed at: {upload_log.completed_at}
            """
        else:
            message = f"""
            Your {import_type.upper()} import has been completed with some errors.
            
            Results:
            - Successfully imported: {upload_log.success_count} parts
            - Errors: {upload_log.error_count}
            
            Error details:
            {upload_log.error_details or 'No specific error details available.'}
            
            Import completed at: {upload_log.completed_at}
            """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
    except Exception as e:
        logger.error(f"Failed to send import notification email: {e}")


@shared_task
def warm_cache_task():
    """
    Warm up the cache with commonly accessed data.
    """
    try:
        warm_cache()
        logger.info("Cache warmed successfully")
    except Exception as e:
        logger.error(f"Failed to warm cache: {e}")


@shared_task
def cleanup_expired_carts():
    """
    Clean up expired anonymous carts.
    """
    try:
        # Delete carts older than 30 days for anonymous users
        cutoff_date = timezone.now() - timedelta(days=30)
        expired_carts = Cart.objects.filter(
            user__isnull=True,
            created_at__lt=cutoff_date
        )
        
        count = expired_carts.count()
        expired_carts.delete()
        
        logger.info(f"Cleaned up {count} expired anonymous carts")
        return f"Cleaned up {count} expired carts"
        
    except Exception as e:
        logger.error(f"Failed to cleanup expired carts: {e}")
        return f"Error: {str(e)}"


@shared_task
def update_popular_parts_cache():
    """
    Update the popular parts cache based on recent activity.
    """
    try:
        # This will refresh the popular parts cache
        get_cached_popular_parts(limit=10)
        logger.info("Popular parts cache updated successfully")
    except Exception as e:
        logger.error(f"Failed to update popular parts cache: {e}")


@shared_task
def bulk_update_part_prices(part_ids, price_adjustment_percent):
    """
    Bulk update part prices with a percentage adjustment.
    """
    try:
        updated_count = 0
        
        for part_id in part_ids:
            try:
                part = Part.objects.get(id=part_id)
                adjustment_factor = Decimal(str(1 + (price_adjustment_percent / 100)))
                part.price = part.price * adjustment_factor
                part.save()
                
                # Invalidate cache for this part
                invalidate_part_cache(part_id)
                updated_count += 1
                
            except Part.DoesNotExist:
                logger.warning(f"Part with ID {part_id} not found")
                continue
            except Exception as e:
                logger.error(f"Failed to update price for part {part_id}: {e}")
                continue
        
        logger.info(f"Bulk updated prices for {updated_count} parts")
        return f"Updated {updated_count} parts"
        
    except Exception as e:
        logger.error(f"Bulk price update failed: {e}")
        return f"Error: {str(e)}"