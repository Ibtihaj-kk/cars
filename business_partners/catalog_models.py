from django.db import models
from django.conf import settings


class CatalogItem(models.Model):
    """
    Standalone catalog item model for vendors.
    Contains only the essential fields for catalog display.
    """
    
    vendor = models.ForeignKey(
        'business_partners.BusinessPartner',
        on_delete=models.CASCADE,
        related_name='catalog_items',
        help_text="Vendor who owns this catalog item"
    )

    category = models.ForeignKey(
        'parts.Category',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vendor_catalog_items',
        help_text="Category for this catalog item"
    )
    
    part_number = models.CharField(
        max_length=100,
        help_text="Part number / SKU"
    )
    
    description = models.TextField(
        help_text="Parts description"
    )
    
    make = models.CharField(
        max_length=100,
        help_text="Vehicle make (e.g., Toyota, Honda)"
    )
    
    model = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Vehicle model (e.g., Camry, Civic)"
    )
    
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Vehicle year"
    )
    
    trim = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Vehicle trim (optional)"
    )
    
    engine = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Engine specification (optional)"
    )

    # Location fields for access control
    plant = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Plant / City location"
    )
    
    storage_location = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Storage location / Area"
    )
    
    warehouse_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Warehouse identifier"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Catalog Item'
        verbose_name_plural = 'Catalog Items'
    
    def __str__(self):
        vehicle = " ".join([p for p in [self.make, self.model] if p]).strip()
        if self.year:
            vehicle = f"{vehicle} ({self.year})" if vehicle else f"({self.year})"
        if self.category_id:
            return f"{self.category.name} - {vehicle or self.make}"
        return vehicle or self.make
    
    def get_primary_image(self):
        """Get the primary image or first image"""
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary
        return self.images.first()


class CatalogItemImage(models.Model):
    """
    Images for catalog items.
    Supports multiple images per catalog item.
    """
    
    catalog_item = models.ForeignKey(
        CatalogItem,
        on_delete=models.CASCADE,
        related_name='images',
        help_text="Parent catalog item"
    )
    
    image = models.ImageField(
        upload_to='catalog_images/',
        help_text="Catalog item image"
    )
    
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary display image"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_primary', 'created_at']
        verbose_name = 'Catalog Item Image'
        verbose_name_plural = 'Catalog Item Images'
    
    def __str__(self):
        return f"Image for {self.catalog_item.part_number}"
    
    def save(self, *args, **kwargs):
        # If this is marked as primary, unmark other images for this item
        if self.is_primary:
            CatalogItemImage.objects.filter(
                catalog_item=self.catalog_item,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
