"""
Custom validators for listings app.
"""
from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from django.utils.translation import gettext_lazy
import os

# Safe translation function that handles None cases
def _(message):
    """Safe translation function that handles None cases."""
    try:
        result = gettext_lazy(message)
        return result if result is not None else message
    except Exception:
        return message

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False


@deconstructible
class FileSizeValidator:
    """Validate file size."""
    
    def __init__(self, max_size_mb):
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def __call__(self, value):
        if value.size > self.max_size_bytes:
            raise ValidationError(
                _('File size cannot exceed %(max_size)s MB. Current size: %(current_size).2f MB'),
                params={
                    'max_size': self.max_size_mb,
                    'current_size': value.size / (1024 * 1024)
                }
            )
    
    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.max_size_mb == other.max_size_mb
        )


@deconstructible
class FileTypeValidator:
    """Validate file type using python-magic."""
    
    def __init__(self, allowed_types):
        self.allowed_types = allowed_types
    
    def __call__(self, value):
        if not HAS_MAGIC:
            # Fallback to basic file extension validation if python-magic is not available
            import mimetypes
            file_type, _ = mimetypes.guess_type(value.name)
            if file_type and file_type not in self.allowed_types:
                raise ValidationError(
                    _('File type "%(file_type)s" is not allowed. Allowed types: %(allowed_types)s'),
                    params={
                        'file_type': file_type,
                        'allowed_types': ', '.join(self.allowed_types)
                    }
                )
            return
        
        try:
            # Get file type using python-magic
            file_type = magic.from_buffer(value.read(1024), mime=True)
            value.seek(0)  # Reset file pointer
            
            if file_type not in self.allowed_types:
                raise ValidationError(
                    _('File type "%(file_type)s" is not allowed. Allowed types: %(allowed_types)s'),
                    params={
                        'file_type': file_type,
                        'allowed_types': ', '.join(self.allowed_types)
                    }
                )
        except Exception as e:
            raise ValidationError(_('Could not validate file type: %(error)s'), params={'error': str(e)})
    
    def __eq__(self, other):
        return (
            isinstance(other, self.__class__) and
            self.allowed_types == other.allowed_types
        )


# Predefined validators
validate_image_size = FileSizeValidator(10)  # 10MB for images
validate_video_size = FileSizeValidator(100)  # 100MB for videos

validate_image_type = FileTypeValidator([
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif'
])

validate_video_type = FileTypeValidator([
    'video/mp4',
    'video/quicktime',
    'video/x-msvideo',
    'video/webm'
])


def validate_image_dimensions(value):
    """Validate image dimensions."""
    try:
        from PIL import Image
        img = Image.open(value)
        width, height = img.size
        
        # Minimum dimensions
        if width < 400 or height < 300:
            raise ValidationError(
                _('Image dimensions too small. Minimum: 400x300 pixels. Current: %(width)sx%(height)s'),
                params={'width': width, 'height': height}
            )
        
        # Maximum dimensions
        if width > 4000 or height > 3000:
            raise ValidationError(
                _('Image dimensions too large. Maximum: 4000x3000 pixels. Current: %(width)sx%(height)s'),
                params={'width': width, 'height': height}
            )
            
    except Exception as e:
        raise ValidationError(_('Could not validate image dimensions: %(error)s'), params={'error': str(e)})