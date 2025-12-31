from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
import uuid

from .decorators import vendor_required
from .utils import get_vendor_profile
from .catalog_models import CatalogItem, CatalogItemImage
from parts.models import Category


def _normalize_part(s: str) -> str:
    return ''.join(ch for ch in (s or '').strip().upper() if ch.isalnum())


def _build_part_number(category: Category | None, make: str, model: str | None, year: int | None) -> str:
    cat = _normalize_part(category.name)[:10] if category else 'CAT'
    mk = _normalize_part(make)[:10] or 'MAKE'
    mdl = _normalize_part(model or '')[:10] or 'MODEL'
    yr = str(year) if year else 'NA'
    suffix = uuid.uuid4().hex[:6].upper()
    return f"{cat}-{yr}-{mk}-{mdl}-{suffix}"[:100]


def _build_description(category: Category | None, make: str, model: str | None, year: int | None, trim: str | None, engine: str | None) -> str:
    cat = category.name if category else 'Catalog item'
    vehicle_parts = [make, (model or '').strip()]
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
    ).select_related('category').prefetch_related('images').order_by('-created_at')
    
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
        CatalogItem.objects.select_related('category').prefetch_related('images'),
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
        CatalogItem.objects.select_related('category').prefetch_related('images'),
        pk=pk,
        vendor=business_partner,
    )

    if request.method == 'POST':
        category_id = (request.POST.get('category') or '').strip()
        make = request.POST.get('make', '').strip()
        model = request.POST.get('model', '').strip() or None
        year = request.POST.get('year', '').strip()
        trim = request.POST.get('trim', '').strip() or None
        engine = request.POST.get('engine', '').strip() or None

        errors = []
        category = None
        if not category_id:
            errors.append('Category is required.')
        else:
            try:
                category = Category.objects.get(pk=category_id)
            except Category.DoesNotExist:
                errors.append('Please select a valid category.')
        if not make:
            errors.append('Make is required.')
        if year:
            try:
                year_int = int(year)
                if year_int < 1900 or year_int > 2100:
                    errors.append('Please enter a valid year.')
                year = year_int
            except ValueError:
                errors.append('Year must be a number.')
        else:
            year = None

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            catalog_item.category = category
            catalog_item.make = make
            catalog_item.model = model
            catalog_item.year = year
            catalog_item.trim = trim
            catalog_item.engine = engine
            catalog_item.part_number = _build_part_number(category, make, model, year)
            catalog_item.description = _build_description(category, make, model, year, trim, engine)
            catalog_item.save()

            messages.success(request, 'Catalog item has been updated successfully.')
            return redirect('business_partners:vendor_catalog_detail', pk=catalog_item.pk)

    context = {
        'catalog_item': catalog_item,
        'current_year': 2025,
        'year_range': range(2025, 1979, -1),
        'categories': Category.objects.all().order_by('name'),
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
        category_id = (request.POST.get('category') or '').strip()
        make = request.POST.get('make', '').strip()
        model = request.POST.get('model', '').strip() or None
        year = request.POST.get('year', '').strip()
        trim = request.POST.get('trim', '').strip() or None
        engine = request.POST.get('engine', '').strip() or None
        
        # Validation
        errors = []
        category = None
        if not category_id:
            errors.append('Category is required.')
        else:
            try:
                category = Category.objects.get(pk=category_id)
            except Category.DoesNotExist:
                errors.append('Please select a valid category.')
        if not make:
            errors.append('Make is required.')
        if year:
            try:
                year_int = int(year)
                if year_int < 1900 or year_int > 2100:
                    errors.append('Please enter a valid year.')
                year = year_int
            except ValueError:
                errors.append('Year must be a number.')
        else:
            year = None
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Create catalog item
            catalog_item = CatalogItem.objects.create(
                vendor=business_partner,
                category=category,
                make=make,
                model=model,
                year=year,
                trim=trim,
                engine=engine,
                part_number=_build_part_number(category, make, model, year),
                description=_build_description(category, make, model, year, trim, engine),
            )

            messages.success(request, 'Catalog item has been added successfully.')
            return redirect('business_partners:vendor_catalog_management')
    
    context = {
        'current_year': 2025,
        'year_range': range(2025, 1979, -1),  # Years from 2025 to 1980
        'categories': Category.objects.all().order_by('name'),
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
