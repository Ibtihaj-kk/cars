"""
Cloud storage configuration for vehicle listings media files.
"""
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os


class MediaStorage(S3Boto3Storage):
    """Custom S3 storage for media files."""
    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'carsportal-media')
    location = 'media'
    default_acl = 'public-read'
    file_overwrite = False
    custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', None)


class StaticStorage(S3Boto3Storage):
    """Custom S3 storage for static files."""
    bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'carsportal-static')
    location = 'static'
    default_acl = 'public-read'


class CloudinaryStorage:
    """Cloudinary storage wrapper."""
    
    def __init__(self):
        cloudinary.config(
            cloud_name=getattr(settings, 'CLOUDINARY_CLOUD_NAME', ''),
            api_key=getattr(settings, 'CLOUDINARY_API_KEY', ''),
            api_secret=getattr(settings, 'CLOUDINARY_API_SECRET', ''),
            secure=True
        )
    
    def upload_image(self, file, folder='listings/images', **options):
        """Upload image to Cloudinary."""
        default_options = {
            'folder': folder,
            'resource_type': 'image',
            'format': 'auto',
            'quality': 'auto:good',
            'fetch_format': 'auto',
            'flags': 'progressive',
            'transformation': [
                {'width': 1920, 'height': 1080, 'crop': 'limit'},
                {'quality': 'auto:good'}
            ]
        }
        default_options.update(options)
        
        try:
            result = cloudinary.uploader.upload(file, **default_options)
            return result
        except Exception as e:
            raise Exception(f"Failed to upload image to Cloudinary: {str(e)}")
    
    def upload_video(self, file, folder='listings/videos', **options):
        """Upload video to Cloudinary."""
        default_options = {
            'folder': folder,
            'resource_type': 'video',
            'format': 'auto',
            'quality': 'auto',
            'transformation': [
                {'width': 1280, 'height': 720, 'crop': 'limit', 'quality': 'auto'}
            ]
        }
        default_options.update(options)
        
        try:
            result = cloudinary.uploader.upload(file, **default_options)
            return result
        except Exception as e:
            raise Exception(f"Failed to upload video to Cloudinary: {str(e)}")
    
    def generate_thumbnail(self, public_id, **options):
        """Generate thumbnail for video."""
        default_options = {
            'resource_type': 'video',
            'format': 'jpg',
            'transformation': [
                {'width': 300, 'height': 200, 'crop': 'fill'},
                {'quality': 'auto:good'}
            ]
        }
        default_options.update(options)
        
        return cloudinary.CloudinaryImage(public_id).build_url(**default_options)
    
    def delete_file(self, public_id, resource_type='image'):
        """Delete file from Cloudinary."""
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
            return result.get('result') == 'ok'
        except Exception as e:
            print(f"Failed to delete file from Cloudinary: {str(e)}")
            return False


def get_storage_backend():
    """Get the configured storage backend."""
    storage_backend = getattr(settings, 'MEDIA_STORAGE_BACKEND', 'local')
    
    if storage_backend == 's3':
        return MediaStorage()
    elif storage_backend == 'cloudinary':
        return CloudinaryStorage()
    else:
        return default_storage


def optimize_image(image_file, max_width=1920, max_height=1080, quality=85):
    """Optimize image file."""
    try:
        from PIL import Image
        
        # Open image
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Resize if larger than max dimensions
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Save optimized image
        from io import BytesIO
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        return ContentFile(output.read())
        
    except Exception as e:
        print(f"Error optimizing image: {str(e)}")
        return image_file


def generate_responsive_images(image_file, sizes=[400, 800, 1200, 1920]):
    """Generate responsive image sizes."""
    responsive_images = {}
    
    try:
        from PIL import Image
        
        img = Image.open(image_file)
        original_width, original_height = img.size
        aspect_ratio = original_height / original_width
        
        for size in sizes:
            if size <= original_width:
                new_height = int(size * aspect_ratio)
                resized_img = img.copy()
                resized_img.thumbnail((size, new_height), Image.Resampling.LANCZOS)
                
                # Save resized image
                from io import BytesIO
                output = BytesIO()
                resized_img.save(output, format='JPEG', quality=85, optimize=True)
                output.seek(0)
                
                responsive_images[f'{size}w'] = ContentFile(output.read())
        
        return responsive_images
        
    except Exception as e:
        print(f"Error generating responsive images: {str(e)}")
        return {}