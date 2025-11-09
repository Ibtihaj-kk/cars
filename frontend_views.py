from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response
from listings.models import VehicleListing
from vehicles.models import VehicleCategory, VehicleModel, VehicleSpecification
from listings.filters import VehicleListingFilter
from listings.serializers import VehicleListingListSerializer
import json


def homepage_view(request):
    """
    Homepage view that renders the index.html template with dynamic data
    """
    # Get filter data for the homepage
    categories = VehicleCategory.objects.all()
    vehicle_models = VehicleModel.objects.all()
    
    # Get unique values for filters
    listings = VehicleListing.objects.filter(status='published')
    
    # Get unique cities
    cities = listings.values_list('location_city', flat=True).distinct().order_by('location_city')
    cities = [city for city in cities if city]  # Remove empty values
    
    # Get unique makes/brands
    makes = listings.values_list('make', flat=True).distinct().order_by('make')
    makes = [make for make in makes if make]  # Remove empty values
    
    # Get unique years
    years = listings.values_list('year', flat=True).distinct().order_by('-year')
    years = [year for year in years if year]  # Remove empty values
    
    # Get unique body types from VehicleCategory
    body_types = VehicleCategory.objects.filter(is_active=True)
    
    # Budget ranges (predefined)
    budget_ranges = [
        {'label': 'Under $5K', 'min': 0, 'max': 5000},
        {'label': '$5K - $10K', 'min': 5000, 'max': 10000},
        {'label': '$10K - $15K', 'min': 10000, 'max': 15000},
        {'label': '$15K - $20K', 'min': 15000, 'max': 20000},
        {'label': '$20K - $25K', 'min': 20000, 'max': 25000},
        {'label': '$25K - $30K', 'min': 25000, 'max': 30000},
        {'label': '$30K - $40K', 'min': 30000, 'max': 40000},
        {'label': '$40K - $50K', 'min': 40000, 'max': 50000},
        {'label': '$50K+', 'min': 50000, 'max': None},
    ]
    
    # Get featured listings for homepage display
    featured_listings = listings.filter(is_featured=True)[:8]
    
    context = {
        'categories': categories,
        'vehicle_models': vehicle_models,
        'cities': cities,
        'makes': makes,
        'years': years,
        'body_types': body_types,
        'budget_ranges': budget_ranges,
        'featured_listings': featured_listings,
    }
    
    return render(request, 'frontend/index.html', context)


@api_view(['GET'])
def filter_listings_api(request):
    """
    API endpoint to filter listings based on various criteria
    """
    # Apply filters using the existing VehicleListingFilter
    filterset = VehicleListingFilter(request.GET, queryset=VehicleListing.objects.filter(status='published'))
    
    if filterset.is_valid():
        queryset = filterset.qs
    else:
        queryset = VehicleListing.objects.filter(status='published')
    
    # Apply pagination
    paginator = Paginator(queryset, 12)  # 12 items per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Serialize the data
    serializer = VehicleListingListSerializer(page_obj, many=True)
    
    return Response({
        'results': serializer.data,
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })


def search_listings_view(request):
    """
    View to handle search and filtering of listings
    """
    # Get search parameters
    search_query = request.GET.get('search', '')
    category = request.GET.get('category', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    make = request.GET.get('make', '')
    model = request.GET.get('model', '')
    city = request.GET.get('city', '')
    year = request.GET.get('year', '')
    body_type = request.GET.get('body_type', '')
    
    # Start with active listings
    listings = VehicleListing.objects.filter(status='published')
    
    # Apply search filters
    if search_query:
        listings = listings.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(make__icontains=search_query) |
            Q(model__icontains=search_query)
        )
    
    if category:
        # Filter by body_type category
        listings = listings.filter(body_type__name__icontains=category)
    
    if min_price:
        listings = listings.filter(price__gte=min_price)
    
    if max_price:
        listings = listings.filter(price__lte=max_price)
    
    if make:
        listings = listings.filter(make__icontains=make)
    
    if model:
        listings = listings.filter(model__icontains=model)
    
    if city:
        listings = listings.filter(location_city__icontains=city)
    
    if year:
        listings = listings.filter(year=year)
    
    if body_type:
        # Filter by body_type using the new body_type field
        listings = listings.filter(body_type__name__icontains=body_type)
    
    # Apply pagination
    paginator = Paginator(listings, 12)  # 12 items per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Get filter data for the template
    categories = VehicleCategory.objects.all()
    all_listings = VehicleListing.objects.filter(status='published')
    cities = all_listings.values_list('location_city', flat=True).distinct().order_by('location_city')
    makes = all_listings.values_list('make', flat=True).distinct().order_by('make')
    years = all_listings.values_list('year', flat=True).distinct().order_by('-year')
    body_types = VehicleCategory.objects.filter(is_active=True).values_list('name', flat=True)
    
    context = {
        'listings': page_obj,
        'search_query': search_query,
        'categories': categories,
        'cities': [city for city in cities if city],
        'makes': [make for make in makes if make],
        'years': [year for year in years if year],
        'body_types': [body_type for body_type in body_types if body_type],
        'current_filters': {
            'category': category,
            'min_price': min_price,
            'max_price': max_price,
            'make': make,
            'model': model,
            'city': city,
            'year': year,
            'body_type': body_type,
        }
    }
    
    return render(request, 'frontend/search_results.html', context)


def car_detail_view(request, slug):
    """
    Car detail view that renders the car-details.html template with dynamic data
    """
    from django.shortcuts import get_object_or_404
    
    # Get the car listing by slug
    car = get_object_or_404(
        VehicleListing.objects.select_related('user').prefetch_related('images'),
        slug=slug,
        status='published'
    )
    
    # Increment view count
    car.views_count += 1
    car.save(update_fields=['views_count'])
    
    # Get similar cars (same make or model)
    similar_cars = VehicleListing.objects.filter(
        status='published'
    ).filter(
        Q(make=car.make) | Q(model=car.model)
    ).exclude(id=car.id)[:6]
    
    context = {
        'car': car,
        'similar_cars': similar_cars,
    }
    
    return render(request, 'frontend/car-details.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def schedule_test_drive_view(request):
    """
    Handle test drive scheduling form submission
    """
    try:
        # Get form data
        vehicle_id = request.POST.get('vehicle_id')
        vehicle_title = request.POST.get('vehicle_title')
        customer_name = request.POST.get('customer_name')
        customer_email = request.POST.get('customer_email')
        customer_phone = request.POST.get('customer_phone')
        preferred_date = request.POST.get('preferred_date')
        preferred_time = request.POST.get('preferred_time')
        message = request.POST.get('message', '')
        
        # Validate required fields
        if not all([vehicle_id, customer_name, customer_email, customer_phone, preferred_date, preferred_time]):
            return JsonResponse({
                'success': False,
                'message': 'Please fill in all required fields.'
            }, status=400)
        
        # Verify the vehicle exists
        try:
            vehicle = get_object_or_404(VehicleListing, id=vehicle_id, status='published')
        except:
            return JsonResponse({
                'success': False,
                'message': 'Vehicle not found.'
            }, status=404)
        
        # Here you would typically save the test drive request to a database
        # For now, we'll just return a success response
        # You can create a TestDriveRequest model later if needed
        
        # Log the test drive request (you can replace this with database save)
        print(f"Test Drive Request:")
        print(f"Vehicle: {vehicle_title} (ID: {vehicle_id})")
        print(f"Customer: {customer_name}")
        print(f"Email: {customer_email}")
        print(f"Phone: {customer_phone}")
        print(f"Preferred Date: {preferred_date}")
        print(f"Preferred Time: {preferred_time}")
        print(f"Message: {message}")
        
        return JsonResponse({
            'success': True,
            'message': f'Thank you {customer_name}! Your test drive request for {vehicle_title} has been submitted successfully. We will contact you soon to confirm the appointment.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while processing your request. Please try again.'
        }, status=500)