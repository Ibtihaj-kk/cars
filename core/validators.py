import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_phone_number(value):
    """Validate that the value is a valid phone number.
    
    Args:
        value: Phone number string
        
    Raises:
        ValidationError: If the phone number is invalid
    """
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', value)
    
    # Check if the phone number has a valid length
    if len(digits_only) < 8 or len(digits_only) > 15:
        raise ValidationError(
            _('Phone number must be between 8 and 15 digits.'),
            code='invalid_phone_number'
        )


def validate_file_size(max_size_mb):
    """Create a validator that checks if a file is within the specified size limit.
    
    Args:
        max_size_mb: Maximum file size in megabytes
        
    Returns:
        A validator function
    """
    max_size_bytes = max_size_mb * 1024 * 1024
    
    def validator(value):
        if value.size > max_size_bytes:
            raise ValidationError(
                _(f'File size cannot exceed {max_size_mb} MB.'),
                code='file_too_large'
            )
    
    return validator


def validate_image_dimensions(min_width=None, min_height=None, max_width=None, max_height=None):
    """Create a validator that checks if an image has valid dimensions.
    
    Args:
        min_width: Minimum width in pixels
        min_height: Minimum height in pixels
        max_width: Maximum width in pixels
        max_height: Maximum height in pixels
        
    Returns:
        A validator function
    """
    def validator(image):
        # Check if the file is an image
        if not hasattr(image, 'width') or not hasattr(image, 'height'):
            # Try to open the image to get its dimensions
            from PIL import Image
            try:
                img = Image.open(image)
                width, height = img.size
            except Exception:
                raise ValidationError(
                    _('Invalid image file.'),
                    code='invalid_image'
                )
        else:
            width, height = image.width, image.height
        
        # Check minimum dimensions
        if min_width is not None and width < min_width:
            raise ValidationError(
                _(f'Image width must be at least {min_width} pixels.'),
                code='image_too_narrow'
            )
        
        if min_height is not None and height < min_height:
            raise ValidationError(
                _(f'Image height must be at least {min_height} pixels.'),
                code='image_too_short'
            )
        
        # Check maximum dimensions
        if max_width is not None and width > max_width:
            raise ValidationError(
                _(f'Image width cannot exceed {max_width} pixels.'),
                code='image_too_wide'
            )
        
        if max_height is not None and height > max_height:
            raise ValidationError(
                _(f'Image height cannot exceed {max_height} pixels.'),
                code='image_too_tall'
            )
    
    return validator