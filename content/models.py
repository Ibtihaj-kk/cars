from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
from vehicles.models import Brand, VehicleModel


class ContentStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    PUBLISHED = 'published', 'Published'
    ARCHIVED = 'archived', 'Archived'
    SCHEDULED = 'scheduled', 'Scheduled'


class ContentCategory(models.Model):
    """Categories for content organization."""
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Content Category'
        verbose_name_plural = 'Content Categories'
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Tag(models.Model):
    """Tags for content labeling."""
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=60, unique=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Article(models.Model):
    """Model for blog articles and news."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField()
    excerpt = models.TextField(blank=True, null=True, help_text='Short summary of the article')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='articles')
    featured_image = models.ImageField(upload_to='content/articles/', blank=True, null=True)
    categories = models.ManyToManyField(ContentCategory, related_name='articles')
    tags = models.ManyToManyField(Tag, related_name='articles', blank=True)
    status = models.CharField(max_length=20, choices=ContentStatus.choices, default=ContentStatus.DRAFT)
    
    # SEO fields
    meta_title = models.CharField(max_length=100, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    
    # Related vehicles
    related_brands = models.ManyToManyField(Brand, related_name='articles', blank=True)
    related_vehicle_models = models.ManyToManyField(VehicleModel, related_name='articles', blank=True)
    
    # Publishing details
    is_featured = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['published_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Set published_at when status changes to published
        if self.status == ContentStatus.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)


class Page(models.Model):
    """Model for static pages like About Us, Terms, etc."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True)
    content = models.TextField()
    featured_image = models.ImageField(upload_to='content/pages/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=ContentStatus.choices, default=ContentStatus.DRAFT)
    
    # SEO fields
    meta_title = models.CharField(max_length=100, blank=True, null=True)
    meta_description = models.TextField(blank=True, null=True)
    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    
    # Page settings
    order = models.PositiveIntegerField(default=0)
    show_in_menu = models.BooleanField(default=False)
    show_in_footer = models.BooleanField(default=False)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['order', 'title']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Set published_at when status changes to published
        if self.status == ContentStatus.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)


class MediaGallery(models.Model):
    """Model for media galleries (images, videos)."""
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=300, unique=True)
    description = models.TextField(blank=True, null=True)
    cover_image = models.ImageField(upload_to='content/galleries/covers/', blank=True, null=True)
    
    # Related content
    categories = models.ManyToManyField(ContentCategory, related_name='galleries', blank=True)
    tags = models.ManyToManyField(Tag, related_name='galleries', blank=True)
    related_brands = models.ManyToManyField(Brand, related_name='galleries', blank=True)
    related_vehicle_models = models.ManyToManyField(VehicleModel, related_name='galleries', blank=True)
    
    status = models.CharField(max_length=20, choices=ContentStatus.choices, default=ContentStatus.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Media Gallery'
        verbose_name_plural = 'Media Galleries'
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        
        # Set published_at when status changes to published
        if self.status == ContentStatus.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)


class MediaItem(models.Model):
    """Individual media items in galleries."""
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
    ]
    
    gallery = models.ForeignKey(MediaGallery, on_delete=models.CASCADE, related_name='items')
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    media_type = models.CharField(max_length=20, choices=MEDIA_TYPE_CHOICES, default='image')
    file = models.FileField(upload_to='content/media/')
    thumbnail = models.ImageField(upload_to='content/media/thumbnails/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # For videos
    video_url = models.URLField(blank=True, null=True, help_text='URL for embedded videos (YouTube, Vimeo, etc.)')
    duration = models.PositiveIntegerField(blank=True, null=True, help_text='Duration in seconds')
    
    class Meta:
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return self.title or f"Media item {self.id}"


class Banner(models.Model):
    """Model for promotional banners and sliders."""
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True, null=True)
    image = models.ImageField(upload_to='content/banners/')
    mobile_image = models.ImageField(upload_to='content/banners/mobile/', blank=True, null=True, 
                                    help_text='Optimized image for mobile devices')
    link_url = models.URLField(blank=True, null=True)
    button_text = models.CharField(max_length=50, blank=True, null=True)
    position = models.CharField(max_length=50, help_text='Banner position (e.g., home_top, sidebar)')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['position', 'order']
    
    def __str__(self):
        return f"{self.title} ({self.position})"
    
    @property
    def is_scheduled(self):
        now = timezone.now()
        if self.start_date and self.start_date > now:
            return True
        if self.end_date and self.end_date < now:
            return False
        return True
