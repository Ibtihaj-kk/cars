from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator

from .decorators import vendor_required
from .utils import get_vendor_profile
from .catalog_models import CatalogItem, CatalogItemImage


@login_required
@vendor_required
def vendor_catalog_list(request):
    """Display vendor's catalog items."""
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    # Get all catalog items for this vendor
    catalog_items = CatalogItem.objects.filter(
        vendor=business_partner
    ).prefetch_related('images').order_by('-created_at')
    
    # Pagination
    paginator = Paginator(catalog_items, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'catalog_items': page_obj,
        'page_obj': page_obj,
        'total_items': catalog_items.count(),
    }
    
    return render(request, 'vendors/catalog_list.html', context)


@login_required
@vendor_required
def vendor_catalog_detail(request, pk):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')

    business_partner = vendor_profile.business_partner
    catalog_item = get_object_or_404(
        CatalogItem.objects.prefetch_related('images'),
        pk=pk,
        vendor=business_partner,
    )

    return render(request, 'vendors/catalog_detail.html', {'catalog_item': catalog_item})


@login_required
@vendor_required
def vendor_catalog_edit(request, pk):
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')

    business_partner = vendor_profile.business_partner
    catalog_item = get_object_or_404(
        CatalogItem.objects.prefetch_related('images'),
        pk=pk,
        vendor=business_partner,
    )

    if request.method == 'POST':
        part_number = request.POST.get('part_number', '').strip()
        description = request.POST.get('description', '').strip()
        make = request.POST.get('make', '').strip()
        model = request.POST.get('model', '').strip()
        year = request.POST.get('year', '').strip()
        trim = request.POST.get('trim', '').strip() or None
        engine = request.POST.get('engine', '').strip() or None

        errors = []
        if not part_number:
            errors.append('Part number is required.')
        if not description:
            errors.append('Description is required.')
        if not make:
            errors.append('Make is required.')
        if not model:
            errors.append('Model is required.')
        if not year:
            errors.append('Year is required.')
        else:
            try:
                year_int = int(year)
                if year_int < 1900 or year_int > 2100:
                    errors.append('Please enter a valid year.')
                year = year_int
            except ValueError:
                errors.append('Year must be a number.')

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            catalog_item.part_number = part_number
            catalog_item.description = description
            catalog_item.make = make
            catalog_item.model = model
            catalog_item.year = year
            catalog_item.trim = trim
            catalog_item.engine = engine
            catalog_item.save()

            images = request.FILES.getlist('images')
            has_images = catalog_item.images.exists()
            for i, image in enumerate(images):
                CatalogItemImage.objects.create(
                    catalog_item=catalog_item,
                    image=image,
                    is_primary=(not has_images and i == 0),
                )

            messages.success(request, f'Catalog item "{catalog_item.part_number}" has been updated successfully.')
            return redirect('business_partners:vendor_catalog_detail', pk=catalog_item.pk)

    context = {
        'catalog_item': catalog_item,
        'current_year': 2025,
        'year_range': range(2025, 1979, -1),
    }
    return render(request, 'vendors/catalog_edit.html', context)


@login_required
@vendor_required
def vendor_catalog_add(request):
    """Add new catalog item."""
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    if request.method == 'POST':
        # Get form data
        part_number = request.POST.get('part_number', '').strip()
        description = request.POST.get('description', '').strip()
        make = request.POST.get('make', '').strip()
        model = request.POST.get('model', '').strip()
        year = request.POST.get('year', '').strip()
        trim = request.POST.get('trim', '').strip() or None
        engine = request.POST.get('engine', '').strip() or None
        
        # Validation
        errors = []
        if not part_number:
            errors.append('Part number is required.')
        if not description:
            errors.append('Description is required.')
        if not make:
            errors.append('Make is required.')
        if not model:
            errors.append('Model is required.')
        if not year:
            errors.append('Year is required.')
        else:
            try:
                year = int(year)
                if year < 1900 or year > 2100:
                    errors.append('Please enter a valid year.')
            except ValueError:
                errors.append('Year must be a number.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Create catalog item
            catalog_item = CatalogItem.objects.create(
                vendor=business_partner,
                part_number=part_number,
                description=description,
                make=make,
                model=model,
                year=year,
                trim=trim,
                engine=engine,
            )
            
            # Handle image uploads
            images = request.FILES.getlist('images')
            for i, image in enumerate(images):
                CatalogItemImage.objects.create(
                    catalog_item=catalog_item,
                    image=image,
                    is_primary=(i == 0)  # First image is primary
                )
            
            messages.success(request, f'Catalog item "{part_number}" has been added successfully.')
            return redirect('business_partners:vendor_catalog_list')
    
    context = {
        'current_year': 2025,
        'year_range': range(2025, 1979, -1),  # Years from 2025 to 1980
    }
    
    return render(request, 'vendors/catalog_add.html', context)


@login_required
@vendor_required
def vendor_catalog_delete(request, pk):
    """Delete a catalog item."""
    vendor_profile = get_vendor_profile(request.user)
    if not vendor_profile:
        messages.error(request, 'You do not have vendor access.')
        return redirect('home')
    
    business_partner = vendor_profile.business_partner
    
    catalog_item = get_object_or_404(
        CatalogItem,
        pk=pk,
        vendor=business_partner
    )
    
    if request.method == 'POST':
        part_number = catalog_item.part_number
        catalog_item.delete()
        messages.success(request, f'Catalog item "{part_number}" has been deleted.')
        return redirect('business_partners:vendor_catalog_list')
    
    return redirect('business_partners:vendor_catalog_list')
