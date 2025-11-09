"""
Image optimization utilities for the listings app.
Provides helper functions for image processing, optimization, and format conversion.
"""

import os
from io import BytesIO
from PIL import Image as PILImage
from django.core.files.base import ContentFile
from django.conf import settings


def optimize_image_for_web(image_file, max_width=None, max_height=None, quality=None):
    """
    Optimize an image for web delivery.
    
    Args:
        image_file: Django ImageField or file-like object
        max_width: Maximum width (defaults to settings.IMAGE_MAX_WIDTH)
        max_height: Maximum height (defaults to settings.IMAGE_MAX_HEIGHT)
        quality: JPEG quality (defaults to settings.IMAGE_QUALITY)
    
    Returns:
        ContentFile: Optimized image as ContentFile
    """
    if not image_file:
        return None
    
    # Get settings with defaults
    max_width = max_width or getattr(settings, 'IMAGE_MAX_WIDTH', 1920)
    max_height = max_height or getattr(settings, 'IMAGE_MAX_HEIGHT', 1080)
    quality = quality or getattr(settings, 'IMAGE_QUALITY', 85)
    
    try:
        # Open the image
        if hasattr(image_file, 'path'):
            image = PILImage.open(image_file.path)
        else:
            image = PILImage.open(image_file)
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Resize if image is too large
        if image.width > max_width or image.height > max_height:
            image.thumbnail((max_width, max_height), PILImage.Resampling.LANCZOS)
        
        # Save optimized image
        img_io = BytesIO()
        image.save(img_io, format='JPEG', quality=quality, optimize=True)
        img_io.seek(0)
        
        return ContentFile(img_io.read())
        
    except Exception as e:
        print(f"Error optimizing image: {e}")
        return None


def create_thumbnail(image_file, size=(300, 300), quality=85):
    """
    Create a thumbnail from an image.
    
    Args:
        image_file: Django ImageField or file-like object
        size: Tuple of (width, height) for thumbnail
        quality: JPEG quality for thumbnail
    
    Returns:
        ContentFile: Thumbnail as ContentFile
    """
    if not image_file:
        return None
    
    try:
        # Open the image
        if hasattr(image_file, 'path'):
            image = PILImage.open(image_file.path)
        else:
            image = PILImage.open(image_file)
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Create thumbnail
        image.thumbnail(size, PILImage.Resampling.LANCZOS)
        
        # Save thumbnail
        thumb_io = BytesIO()
        image.save(thumb_io, format='JPEG', quality=quality, optimize=True)
        thumb_io.seek(0)
        
        return ContentFile(thumb_io.read())
        
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return None


def create_webp_version(image_file, size=None, quality=None):
    """
    Create a WebP version of an image for better compression.
    
    Args:
        image_file: Django ImageField or file-like object
        size: Optional tuple of (width, height) to resize
        quality: WebP quality (defaults to settings.WEBP_QUALITY)
    
    Returns:
        ContentFile: WebP image as ContentFile
    """
    if not image_file:
        return None
    
    # Check if WebP is enabled
    if not getattr(settings, 'ENABLE_WEBP', True):
        return None
    
    quality = quality or getattr(settings, 'WEBP_QUALITY', 80)
    
    try:
        # Open the image
        if hasattr(image_file, 'path'):
            image = PILImage.open(image_file.path)
        else:
            image = PILImage.open(image_file)
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Resize if size is specified
        if size:
            image.thumbnail(size, PILImage.Resampling.LANCZOS)
        
        # Save as WebP
        webp_io = BytesIO()
        image.save(webp_io, format='WebP', quality=quality, optimize=True)
        webp_io.seek(0)
        
        return ContentFile(webp_io.read())
        
    except Exception as e:
        print(f"Error creating WebP version: {e}")
        return None


def get_image_dimensions(image_file):
    """
    Get the dimensions of an image.
    
    Args:
        image_file: Django ImageField or file-like object
    
    Returns:
        tuple: (width, height) or (None, None) if error
    """
    if not image_file:
        return None, None
    
    try:
        if hasattr(image_file, 'path'):
            image = PILImage.open(image_file.path)
        else:
            image = PILImage.open(image_file)
        
        return image.width, image.height
        
    except Exception as e:
        print(f"Error getting image dimensions: {e}")
        return None, None


def get_image_file_size(image_file):
    """
    Get the file size of an image in bytes.
    
    Args:
        image_file: Django ImageField or file-like object
    
    Returns:
        int: File size in bytes or None if error
    """
    if not image_file:
        return None
    
    try:
        if hasattr(image_file, 'size'):
            return image_file.size
        elif hasattr(image_file, 'path'):
            return os.path.getsize(image_file.path)
        else:
            # For file-like objects, seek to end to get size
            current_pos = image_file.tell()
            image_file.seek(0, 2)  # Seek to end
            size = image_file.tell()
            image_file.seek(current_pos)  # Restore position
            return size
            
    except Exception as e:
        print(f"Error getting image file size: {e}")
        return None


def generate_optimized_filename(original_filename, suffix="", extension=None):
    """
    Generate an optimized filename for processed images.
    
    Args:
        original_filename: Original filename
        suffix: Suffix to add (e.g., "_thumb", "_optimized")
        extension: New extension (e.g., "webp", "jpg")
    
    Returns:
        str: New filename
    """
    name, ext = os.path.splitext(os.path.basename(original_filename))
    
    if extension:
        ext = f".{extension}"
    
    return f"{name}{suffix}{ext}"


def is_image_format_supported(filename):
    """
    Check if an image format is supported for optimization.
    
    Args:
        filename: Image filename
    
    Returns:
        bool: True if supported, False otherwise
    """
    supported_formats = ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff']
    _, ext = os.path.splitext(filename.lower())
    return ext in supported_formats


def calculate_compression_ratio(original_size, compressed_size):
    """
    Calculate the compression ratio between original and compressed image.
    
    Args:
        original_size: Original file size in bytes
        compressed_size: Compressed file size in bytes
    
    Returns:
        float: Compression ratio (e.g., 0.5 means 50% compression)
    """
    if not original_size or not compressed_size:
        return 0.0
    
    return 1.0 - (compressed_size / original_size)