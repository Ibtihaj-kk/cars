"""
Tasks for the Parts module.
Handles background processing for CSV imports, API imports, and cache management.
"""

import uuid
from typing import Any, Callable

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import csv
import io
import requests
from decimal import Decimal
import logging
from django.db.utils import OperationalError

from .models import Part, Category, Brand, BulkUploadLog, IntegrationSource, Cart
from .cache import warm_cache, invalidate_part_cache, get_cached_popular_parts
from users.models import User

logger = logging.getLogger(__name__)

class MaxRetriesExceededError(Exception):
    pass


class _EagerResult:
    def __init__(self, result: Any = None):
        self.id = uuid.uuid4().hex
        self.result = result


class _EagerTask:
    def __init__(self, func: Callable[..., Any], *, bind: bool):
        self._func = func
        self._bind = bind
        self.__name__ = getattr(func, "__name__", self.__class__.__name__)
        self.__qualname__ = getattr(func, "__qualname__", self.__class__.__name__)
        self.__module__ = getattr(func, "__module__", __name__)
        self.__doc__ = getattr(func, "__doc__", None)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._call(*args, **kwargs)

    def delay(self, *args: Any, **kwargs: Any) -> _EagerResult:
        return _EagerResult(self._call(*args, **kwargs))

    def _call(self, *args: Any, **kwargs: Any) -> Any:
        if not self._bind:
            return self._func(*args, **kwargs)

        class _TaskContext:
            def retry(self, exc=None, countdown=None, max_retries=None):
                raise MaxRetriesExceededError(str(exc) if exc else "Retry requested")

        return self._func(_TaskContext(), *args, **kwargs)


def shared_task(*dargs, **dkwargs):
    bind = bool(dkwargs.get("bind", False))

    if dargs and callable(dargs[0]) and not dkwargs:
        return _EagerTask(dargs[0], bind=False)

    def decorator(func):
        return _EagerTask(func, bind=bind)

    return decorator


def process_catalog_bulk_upload_file(file_obj, file_name, *, upload_log_id=None):
    import io
    import uuid
    from django.db import IntegrityError, transaction

    from business_partners.catalog_models import CatalogItem
    from business_partners.models import BusinessPartner
    from .models import Category, Brand, BulkUploadLog

    def normalize_header(value):
        value = (value or "").strip().lower()
        return "".join(ch for ch in value if ch.isalnum())

    def normalize_value(value):
        return (value or "").strip()

    def normalize_catalog_part(value: str) -> str:
        return "".join(ch for ch in (value or "").strip().upper() if ch.isalnum())

    def build_catalog_part_number(category, make: str, model: str | None, year: int | None) -> str:
        cat = normalize_catalog_part(getattr(category, "name", ""))[:10] if category else "CAT"
        mk = normalize_catalog_part(make)[:10] or "MAKE"
        mdl = normalize_catalog_part(model or "")[:10] or "MODEL"
        yr = str(year) if year else "NA"
        suffix = uuid.uuid4().hex[:6].upper()
        return f"{cat}-{yr}-{mk}-{mdl}-{suffix}"[:100]

    def build_catalog_description(
        category, make: str, model: str | None, year: int | None, trim: str | None, engine: str | None
    ) -> str:
        cat = getattr(category, "name", None) or "Catalog item"
        vehicle_parts = [make, (model or "").strip()]
        vehicle = " ".join([p for p in vehicle_parts if p]).strip()
        if year:
            vehicle = f"{vehicle} ({year})" if vehicle else f"({year})"
        base = f"{cat} for {vehicle or make}"
        extra = []
        if trim:
            extra.append(f"Trim: {trim}")
        if engine:
            extra.append(f"Engine: {engine}")
        if extra:
            return f"{base}\n" + "\n".join(extra)
        return base

    vendor = (
        BusinessPartner.objects.filter(roles__role_type="vendor")
        .distinct()
        .order_by("id")
        .first()
    )
    if not vendor:
        raise ValueError("At least one vendor must exist to add catalog items.")

    header_map = {
        "category": "category",
        "year": "year",
        "make": "make",
        "brand": "make",
        "model": "model",
        "trim": "trim",
        "engine": "engine",
    }

    required_fields = ["category"]

    def build_row_dict(headers, values):
        row = {}
        for idx, header in enumerate(headers):
            key = header_map.get(normalize_header(header))
            if not key:
                continue
            row[key] = "" if idx >= len(values) or values[idx] is None else str(values[idx]).strip()
        return row

    def process_rows(headers, row_values_iter):
        header_keys = {}
        for header in headers:
            normalized = normalize_header(header)
            canonical = header_map.get(normalized)
            if canonical and canonical not in header_keys:
                header_keys[canonical] = header

        missing = [field for field in required_fields if field not in header_keys]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")

        total_records = 0
        successful_records = 0
        errors = []

        with transaction.atomic():
            for row_index, values in enumerate(row_values_iter, start=2):
                if not any(v is not None and str(v).strip() for v in values):
                    continue

                total_records += 1
                row = build_row_dict(headers, values)

                category_value = normalize_value(row.get("category"))
                year_value_raw = normalize_value(row.get("year"))
                make_value_raw = normalize_value(row.get("make"))
                model_value = normalize_value(row.get("model")) or None
                trim_value = normalize_value(row.get("trim")) or None
                engine_value = normalize_value(row.get("engine")) or None

                if not category_value:
                    errors.append(f"Row {row_index}: Category is required.")
                    continue

                year_value = None
                if year_value_raw:
                    try:
                        year_int = int(float(year_value_raw))
                        if year_int < 1900 or year_int > 2100:
                            errors.append(f"Row {row_index}: Please enter a valid year.")
                            continue
                        year_value = year_int
                    except ValueError:
                        errors.append(f"Row {row_index}: Year must be a number.")
                        continue

                make_value = make_value_raw or "Unknown"
                if make_value_raw:
                    existing_make = Brand.objects.filter(name__iexact=make_value_raw).first()
                    if existing_make:
                        make_value = existing_make.name
                    else:
                        try:
                            created_make = Brand.objects.create(name=make_value_raw, is_active=True)
                            make_value = created_make.name
                        except IntegrityError:
                            existing_make = Brand.objects.filter(name__iexact=make_value_raw).first()
                            if existing_make:
                                make_value = existing_make.name

                try:
                    category = None
                    try:
                        category_id = int(category_value)
                        category = Category.objects.get(pk=category_id)
                    except (TypeError, ValueError):
                        category, _ = Category.objects.get_or_create(name=category_value)
                    except Category.DoesNotExist:
                        category, _ = Category.objects.get_or_create(name=category_value)

                    part_number = build_catalog_part_number(category, make_value, model_value, year_value)
                    description = build_catalog_description(
                        category, make_value, model_value, year_value, trim_value, engine_value
                    )

                    CatalogItem.objects.update_or_create(
                        vendor=vendor,
                        category=category,
                        make=make_value,
                        model=model_value,
                        year=year_value,
                        trim=trim_value,
                        engine=engine_value,
                        defaults={
                            "part_number": part_number,
                            "description": description,
                        },
                    )
                    successful_records += 1
                except Exception as exc:
                    errors.append(f"Row {row_index}: {str(exc)}")

        failed_records = total_records - successful_records

        if upload_log_id:
            BulkUploadLog.objects.filter(id=upload_log_id).update(
                total_records=total_records,
                successful_records=successful_records,
                failed_records=failed_records,
            )

        return total_records, successful_records, failed_records, errors

    file_name_lower = (file_name or "").lower()

    if file_name_lower.endswith(".csv"):
        file_obj.seek(0)
        raw = file_obj.read()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("utf-8")

        reader = csv.reader(io.StringIO(text))
        headers = next(reader, None)
        if not headers:
            raise ValueError("Empty CSV file")
        return process_rows(headers, reader)

    if file_name_lower.endswith(".xlsx"):
        import openpyxl

        file_obj.seek(0)
        workbook = openpyxl.load_workbook(file_obj, read_only=True, data_only=True)
        sheet = workbook.active
        rows_iter = sheet.iter_rows(values_only=True)
        headers = next(rows_iter, None)
        if not headers:
            raise ValueError("Empty Excel file")
        headers = ["" if h is None else str(h) for h in headers]
        return process_rows(headers, rows_iter)

    if file_name_lower.endswith(".xls"):
        raise ValueError("XLS files are not supported. Please save as .xlsx.")

    raise ValueError("Unsupported file type. Please upload a CSV or XLSX file.")


@shared_task(bind=True, soft_time_limit=3600, time_limit=7200)
def process_vendor_parts_import(
    self,
    upload_log_id,
    storage_path,
    business_partner_id,
    import_status='published',
    update_existing=False,
    chunk_size=5000,
):
    from django.core.files.storage import default_storage
    from django.utils import timezone
    from business_partners.models import BusinessPartner
    from business_partners.vendor_views import process_import_file

    upload_log = BulkUploadLog.objects.filter(id=upload_log_id).first()
    if not upload_log:
        return {'success': False, 'error': 'Upload log not found'}

    upload_log.status = 'processing'
    upload_log.success_message = 'Processing'
    upload_log.save(update_fields=['status', 'success_message'])

    business_partner = BusinessPartner.objects.filter(id=business_partner_id).first()
    if not business_partner:
        upload_log.status = 'failed'
        upload_log.error_log = 'Vendor not found'
        upload_log.completed_at = timezone.now()
        upload_log.save(update_fields=['status', 'error_log', 'completed_at'])
        return {'success': False, 'error': 'Vendor not found'}

    try:
        with default_storage.open(storage_path, 'rb') as f:
            results = process_import_file(
                f,
                business_partner,
                import_status,
                update_existing,
                validate_only=False,
                upload_log_id=upload_log.id,
                chunk_size=chunk_size,
            )

        total = int(results.get('total_rows') or 0)
        created = int(results.get('created_count') or 0)
        updated = int(results.get('updated_count') or 0)
        errors = results.get('errors') or []
        warnings = results.get('warnings') or []

        upload_log.total_records = total
        upload_log.successful_records = created + updated
        upload_log.failed_records = int(results.get('error_count') or 0)
        upload_log.status = 'completed' if upload_log.failed_records == 0 else 'partial'
        upload_log.success_message = f'Created: {created}, Updated: {updated}'
        upload_log.error_log = '\n'.join([*errors[:500], *warnings[:200]]) if (errors or warnings) else None
        upload_log.completed_at = timezone.now()
        upload_log.save(
            update_fields=[
                'total_records',
                'successful_records',
                'failed_records',
                'status',
                'success_message',
                'error_log',
                'completed_at',
            ]
        )

        try:
            warm_cache()
        except Exception:
            pass

        return {
            'success': True,
            'total_rows': total,
            'created_count': created,
            'updated_count': updated,
            'error_count': upload_log.failed_records,
        }
    except OperationalError as e:
        try:
            upload_log.status = 'processing'
            upload_log.error_log = str(e)
            upload_log.save(update_fields=['status', 'error_log'])
        except Exception:
            pass
        try:
            upload_log.status = 'failed'
            upload_log.error_log = str(e)
            upload_log.completed_at = timezone.now()
            upload_log.save(update_fields=['status', 'error_log', 'completed_at'])
        except Exception:
            pass
        return {'success': False, 'error': str(e)}
    except Exception as e:
        upload_log.status = 'failed'
        upload_log.error_log = str(e)
        upload_log.completed_at = timezone.now()
        upload_log.save(update_fields=['status', 'error_log', 'completed_at'])
        return {'success': False, 'error': str(e)}
    finally:
        try:
            default_storage.delete(storage_path)
        except Exception:
            pass


@shared_task(bind=True, soft_time_limit=3600, time_limit=7200)
def process_catalog_parts_import(self, upload_log_id, storage_path):
    from django.core.files.storage import default_storage
    from django.utils import timezone

    upload_log = BulkUploadLog.objects.filter(id=upload_log_id).first()
    if not upload_log:
        return {'success': False, 'error': 'Upload log not found'}

    upload_log.status = 'processing'
    upload_log.success_message = 'Processing'
    upload_log.save(update_fields=['status', 'success_message'])

    try:
        with default_storage.open(storage_path, 'rb') as f:
            total, successful, failed, errors = process_catalog_bulk_upload_file(
                f,
                upload_log.file_name,
                upload_log_id=upload_log.id,
            )

        upload_log.total_records = total
        upload_log.successful_records = successful
        upload_log.failed_records = failed
        upload_log.completed_at = timezone.now()
        upload_log.error_log = "\n".join(errors) if errors else ""
        if failed:
            upload_log.status = "failed"
            upload_log.success_message = ""
        else:
            upload_log.status = "completed"
            upload_log.success_message = f"Successfully processed {successful} records."
        upload_log.save(
            update_fields=[
                'total_records',
                'successful_records',
                'failed_records',
                'status',
                'success_message',
                'error_log',
                'completed_at',
            ]
        )

        try:
            warm_cache()
        except Exception:
            pass

        return {
            'success': failed == 0,
            'total_records': total,
            'successful_records': successful,
            'failed_records': failed,
        }
    except Exception as e:
        upload_log.status = 'failed'
        upload_log.error_log = str(e)
        upload_log.completed_at = timezone.now()
        upload_log.save(update_fields=['status', 'error_log', 'completed_at'])
        return {'success': False, 'error': str(e)}
    finally:
        try:
            default_storage.delete(storage_path)
        except Exception:
            pass


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
        
        subject = f'CarSyncro - {import_type.upper()} Import Completed'
        
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
