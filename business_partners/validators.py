"""
File upload validators for security.
"""
import magic
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
import hashlib


# Allowed MIME types
ALLOWED_DOCUMENT_TYPES = [
    'application/pdf',
    'image/jpeg',
    'image/png',
]

# Allowed extensions
ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png']

# Maximum file size (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

# Suspicious file signatures
SUSPICIOUS_SIGNATURES = {
    b'PK': 'ZIP archive (potential Office document)',
    b'Rar!': 'RAR archive',
    b'7z\xbc\xaf\x27\x1c': '7z archive',
    b'\x1f\x8b': 'GZIP archive',
}

# Dangerous file extensions (case insensitive)
DANGEROUS_EXTENSIONS = [
    'exe', 'scr', 'bat', 'cmd', 'com', 'pif', 'vbs', 'js', 'jar',
    'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'tar.gz',
    'docm', 'xlsm', 'pptm', 'dotm', 'xltm', 'potm', 'ppam',
    'ade', 'adp', 'app', 'asp', 'bas', 'cer', 'chm', 'crt',
    'cpl', 'dll', 'drv', 'hlp', 'hta', 'inf', 'ins', 'isp',
    'jse', 'lnk', 'mdb', 'mde', 'msc', 'msi', 'msp', 'mst',
    'ops', 'pcd', 'pif', 'reg', 'sct', 'shb', 'shs', 'url',
    'vb', 'vbe', 'vbs', 'wsc', 'wsf', 'wsh'
]


def validate_file_size(file):
    """Validate file size"""
    if file.size > MAX_FILE_SIZE:
        raise ValidationError(
            f'File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.0f}MB. '
            f'Your file is {file.size / (1024*1024):.1f}MB.'
        )


def validate_file_mime_type(file):
    """
    Validate actual file MIME type (not just extension).
    Prevents malicious files disguised with safe extensions.
    """
    # Read first 1KB to determine type
    file.seek(0)
    file_head = file.read(1024)
    file.seek(0)
    
    # Detect MIME type
    mime_type = magic.from_buffer(file_head, mime=True)
    
    if mime_type not in ALLOWED_DOCUMENT_TYPES:
        raise ValidationError(
            f'File type not allowed: {mime_type}. '
            f'Allowed types: {", ".join(ALLOWED_DOCUMENT_TYPES)}'
        )


def validate_file_content(file):
    """
    Validate file content for malicious patterns.
    Basic check for executable content and scripts.
    """
    file.seek(0)
    content = file.read(8192)  # Read first 8KB
    file.seek(0)
    
    # Check for executable signatures
    dangerous_patterns = [
        b'MZ',  # Windows executable
        b'#!/bin',  # Shell script
        b'<?php',  # PHP script
        b'<script',  # JavaScript (in non-HTML files)
    ]
    
    for pattern in dangerous_patterns:
        if pattern in content:
            raise ValidationError(
                'File contains potentially dangerous content and cannot be uploaded.'
            )


def validate_filename(filename):
    """Validate filename for path traversal attempts"""
    if '..' in filename or '/' in filename or '\\' in filename:
        raise ValidationError(
            'Invalid filename. Filename cannot contain path separators.'
        )
    
    # Check for suspicious patterns
    if filename.startswith('.') or filename.endswith('.'):
        raise ValidationError(
            'Invalid filename. Filename cannot start or end with a dot.'
        )
    
    # Validate extension
    file_extension = filename.split('.')[-1].lower() if '.' in filename else ''
    if file_extension in DANGEROUS_EXTENSIONS:
        raise ValidationError(
            f'File extension ".{file_extension}" is not allowed for security reasons.'
        )


def validate_file_signature(file):
    """
    Validate file signature against suspicious patterns.
    Detects archives and other potentially dangerous formats.
    """
    file.seek(0)
    file_head = file.read(16)  # Read first 16 bytes
    file.seek(0)
    
    for signature, description in SUSPICIOUS_SIGNATURES.items():
        if file_head.startswith(signature):
            raise ValidationError(
                f'File appears to be a {description}. Only PDF, JPG, and PNG files are allowed.'
            )


def validate_image_dimensions(file):
    """
    Validate image dimensions to prevent DoS attacks with oversized images.
    Only applies to image files.
    """
    from PIL import Image
    
    try:
        # Check if it's an image file
        file.seek(0)
        image = Image.open(file)
        file.seek(0)
        
        width, height = image.size
        max_dimension = 4096  # Maximum 4096x4096 pixels
        
        if width > max_dimension or height > max_dimension:
            raise ValidationError(
                f'Image dimensions too large. Maximum size is {max_dimension}x{max_dimension} pixels. '
                f'Your image is {width}x{height} pixels.'
            )
            
        # Check for potential DoS attacks with extreme aspect ratios
        aspect_ratio = max(width, height) / min(width, height) if min(width, height) > 0 else 0
        if aspect_ratio > 20:  # Very wide or very tall images
            raise ValidationError(
                'Image aspect ratio is too extreme. This may indicate a malformed file.'
            )
            
    except ImportError:
        # PIL not available, skip image validation
        pass
    except Exception:
        # Not a valid image file, skip image validation
        pass


def calculate_file_hash(file):
    """Calculate SHA256 hash of file for integrity checking"""
    sha256 = hashlib.sha256()
    file.seek(0)
    
    for chunk in iter(lambda: file.read(4096), b''):
        sha256.update(chunk)
    
    file.seek(0)
    return sha256.hexdigest()


# Combined validator function
def validate_uploaded_document(file, user=None):
    """
    Comprehensive document validation.
    Apply this to all file upload fields.
    
    Args:
        file: The uploaded file to validate
        user: Optional user object for audit logging
    """
    try:
        validate_filename(file.name)
        validate_file_size(file)
        validate_file_signature(file)
        validate_file_mime_type(file)
        validate_file_content(file)
        validate_image_dimensions(file)
        
        # Calculate and store hash
        file_hash = calculate_file_hash(file)
        file.content_hash = file_hash  # Store on file object for later use
        
        # Log successful validation for audit purposes
        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            from .audit_logger import VendorAuditLogger
            VendorAuditLogger.log_file_upload_validation(
                user=user,
                filename=file.name,
                file_size=file.size,
                file_hash=file_hash,
                validation_result='success'
            )
            
    except ValidationError as e:
        # Log failed validation for audit purposes
        if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
            from .audit_logger import VendorAuditLogger
            VendorAuditLogger.log_file_upload_validation(
                user=user,
                filename=file.name,
                file_size=getattr(file, 'size', 0),
                file_hash=None,
                validation_result='failed',
                error_message=str(e)
            )
        raise