from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class FuelType(models.Model):
    """Fuel type model (e.g., Petrol, Diesel, Electric)."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to='fuel_types/icons/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TransmissionType(models.Model):
    """Transmission type model (e.g., Automatic, Manual, CVT)."""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to='transmission_types/icons/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Brand(models.Model):
    """Vehicle brand/manufacturer model."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    logo = models.ImageField(upload_to='brands/logos/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    country_of_origin = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    founded_year = models.PositiveIntegerField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class VehicleModel(models.Model):
    """Vehicle model belonging to a brand."""
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    image = models.ImageField(upload_to='models/images/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['brand__name', 'name']
        unique_together = ['brand', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.brand.name}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.brand.name} {self.name}"


class VehicleCategory(models.Model):
    """Vehicle category (e.g., Sedan, SUV, Truck)."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.ImageField(upload_to='categories/icons/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Vehicle Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class VehicleSpecification(models.Model):
    """Vehicle specification template for a model."""
    model = models.ForeignKey(VehicleModel, on_delete=models.CASCADE, related_name='specifications')
    year = models.PositiveIntegerField()
    category = models.ForeignKey(VehicleCategory, on_delete=models.SET_NULL, null=True, blank=True)
    engine_type = models.CharField(max_length=100, blank=True, null=True)
    engine_capacity = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)  # in liters
    transmission = models.ForeignKey(TransmissionType, on_delete=models.SET_NULL, null=True, blank=True, related_name='specifications')
    fuel_type = models.ForeignKey(FuelType, on_delete=models.SET_NULL, null=True, blank=True, related_name='specifications')
    horsepower = models.PositiveIntegerField(blank=True, null=True)
    torque = models.PositiveIntegerField(blank=True, null=True)  # in Nm
    drive_type = models.CharField(max_length=50, blank=True, null=True)  # FWD, RWD, AWD
    acceleration = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)  # 0-100 km/h in seconds
    top_speed = models.PositiveIntegerField(blank=True, null=True)  # in km/h
    fuel_economy = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)  # in L/100km
    seating_capacity = models.PositiveSmallIntegerField(blank=True, null=True)
    body_style = models.CharField(max_length=50, blank=True, null=True)
    doors = models.PositiveSmallIntegerField(blank=True, null=True)
    weight = models.PositiveIntegerField(blank=True, null=True)  # in kg
    length = models.PositiveIntegerField(blank=True, null=True)  # in mm
    width = models.PositiveIntegerField(blank=True, null=True)  # in mm
    height = models.PositiveIntegerField(blank=True, null=True)  # in mm
    wheelbase = models.PositiveIntegerField(blank=True, null=True)  # in mm
    ground_clearance = models.PositiveIntegerField(blank=True, null=True)  # in mm
    trunk_capacity = models.PositiveIntegerField(blank=True, null=True)  # in liters
    fuel_tank_capacity = models.PositiveIntegerField(blank=True, null=True)  # in liters
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['model', 'year']
        ordering = ['-year']

    def __str__(self):
        return f"{self.model} {self.year}"


class VehicleFeature(models.Model):
    """Features that can be associated with vehicle specifications."""
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, blank=True, null=True)  # e.g., Safety, Comfort, Technology
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True)  # FontAwesome or similar icon name
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class VehicleSpecificationFeature(models.Model):
    """Many-to-many relationship between vehicle specifications and features."""
    specification = models.ForeignKey(VehicleSpecification, on_delete=models.CASCADE, related_name='features')
    feature = models.ForeignKey(VehicleFeature, on_delete=models.CASCADE)
    is_standard = models.BooleanField(default=True)  # True if standard, False if optional
    additional_cost = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Cost if optional
    notes = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ['specification', 'feature']

    def __str__(self):
        return f"{self.specification} - {self.feature}"


# ============================================================================
# VEHICLE TAXONOMY MODELS FOR PART COMPATIBILITY
# ============================================================================

class VehicleMake(models.Model):
    """
    Vehicle make/manufacturer model for part compatibility taxonomy.
    This is separate from Brand to provide a cleaner taxonomy structure.
    """
    name = models.CharField(max_length=100, unique=True, help_text="Make name in English")
    name_arabic = models.CharField(max_length=100, blank=True, null=True, help_text="Make name in Arabic")
    logo = models.ImageField(upload_to='vehicle_taxonomy/makes/logos/', blank=True, null=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Vehicle Make'
        verbose_name_plural = 'Vehicle Makes'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_models_count(self):
        """Return the number of models for this make."""
        return self.taxonomy_models.count()


class VehicleModelTaxonomy(models.Model):
    """
    Vehicle model for part compatibility taxonomy.
    """
    make = models.ForeignKey(VehicleMake, on_delete=models.CASCADE, related_name='taxonomy_models')
    name = models.CharField(max_length=100, help_text="Model name")
    model_code = models.CharField(max_length=50, blank=True, null=True, help_text="Internal model code")
    slug = models.SlugField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['make__name', 'name']
        unique_together = ['make', 'name']
        verbose_name = 'Vehicle Model (Taxonomy)'
        verbose_name_plural = 'Vehicle Models (Taxonomy)'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.make.name}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.make.name} {self.name}"

    def get_variants_count(self):
        """Return the number of variants for this model."""
        return self.variants.count()


class VehicleVariant(models.Model):
    """
    Vehicle variant for detailed part compatibility.
    """
    TRANSMISSION_CHOICES = [
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
        ('cvt', 'CVT'),
        ('dct', 'Dual Clutch'),
        ('amt', 'AMT'),
    ]

    FUEL_CHOICES = [
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
        ('hybrid', 'Hybrid'),
        ('electric', 'Electric'),
        ('cng', 'CNG'),
        ('lpg', 'LPG'),
    ]

    model = models.ForeignKey(VehicleModelTaxonomy, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100, help_text="Variant name (e.g., 'LX', 'EX', 'Sport')")
    year = models.PositiveIntegerField(
        validators=[MinValueValidator(1900), MaxValueValidator(2050)],
        help_text="Model year"
    )
    engine_code = models.CharField(max_length=50, blank=True, null=True, help_text="Engine code (e.g., 'K20A')")
    transmission_type = models.CharField(max_length=20, choices=TRANSMISSION_CHOICES, help_text="Transmission type")
    fuel_type = models.CharField(max_length=20, choices=FUEL_CHOICES, help_text="Fuel type")
    engine_displacement = models.DecimalField(
        max_digits=4, decimal_places=1, blank=True, null=True,
        help_text="Engine displacement in liters"
    )
    slug = models.SlugField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['model__make__name', 'model__name', '-year', 'name']
        unique_together = ['model', 'name', 'year', 'engine_code']
        verbose_name = 'Vehicle Variant'
        verbose_name_plural = 'Vehicle Variants'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.model.make.name}-{self.model.name}-{self.name}-{self.year}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.model} {self.name} ({self.year})"

    def get_full_name(self):
        """Return full vehicle name including make, model, variant, and year."""
        return f"{self.model.make.name} {self.model.name} {self.name} {self.year}"


class PartCategory(models.Model):
    """
    Hierarchical part category system for organizing automotive parts.
    """
    name = models.CharField(max_length=100, help_text="Category name in English")
    name_arabic = models.CharField(max_length=100, blank=True, null=True, help_text="Category name in Arabic")
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='subcategories',
        help_text="Parent category for hierarchical structure"
    )
    slug = models.SlugField(max_length=150, unique=True, blank=True)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, null=True, help_text="Icon class name")
    sort_order = models.PositiveIntegerField(default=0, help_text="Sort order within parent category")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['parent__name', 'sort_order', 'name']
        unique_together = ['parent', 'name']
        verbose_name = 'Part Category'
        verbose_name_plural = 'Part Categories'

    def save(self, *args, **kwargs):
        if not self.slug:
            if self.parent:
                self.slug = slugify(f"{self.parent.name}-{self.name}")
            else:
                self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        """Validate that a category cannot be its own parent."""
        if self.parent and self.parent == self:
            raise ValidationError("A category cannot be its own parent.")
        
        # Prevent circular references
        if self.parent:
            current = self.parent
            while current:
                if current == self:
                    raise ValidationError("Circular reference detected in category hierarchy.")
                current = current.parent

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def get_full_path(self):
        """Return the full hierarchical path of the category."""
        path = [self.name]
        current = self.parent
        while current:
            path.insert(0, current.name)
            current = current.parent
        return " > ".join(path)

    def get_children(self):
        """Return direct child categories."""
        return self.subcategories.filter(is_active=True)

    def get_all_descendants(self):
        """Return all descendant categories (recursive)."""
        descendants = []
        for child in self.get_children():
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants

    def is_root_category(self):
        """Check if this is a root category (no parent)."""
        return self.parent is None

    def get_level(self):
        """Return the level of this category in the hierarchy (0 for root)."""
        level = 0
        current = self.parent
        while current:
            level += 1
            current = current.parent
        return level
