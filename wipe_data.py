import os
import django
from django.conf import settings

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yallamotor_project.settings')
django.setup()

from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db import connection
from django.contrib.sessions.models import Session
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

# Import all models
# Users App
from users.models import UserProfile, User

# Business Partners App
from business_partners.models import (
    BusinessPartner, VendorProfile, VendorApplication,
    VendorPerformanceScore
)
from business_partners.document_models import (
    VendorDocument, DocumentCategory, DocumentVerificationQueue,
    DocumentAuditLog
)

# Vehicles App
from vehicles.models import (
    FuelType, TransmissionType, Brand as VehicleBrand, VehicleModel,
    VehicleCategory, VehicleSpecification, VehicleFeature,
    VehicleSpecificationFeature, VehicleMake, VehicleModelTaxonomy,
    VehicleVariant, PartCategory as VehiclePartCategory
)

# Listings App
from listings.models import (
    VehicleListing, ListingImage, SavedListing,
    ListingView, Dealer, ListingVideo, ListingStatusLog
)

# Inquiries App
from inquiries.models import (
    ListingInquiry, InquiryResponse, TestDriveRequest
)

# Reviews App
from reviews.models import (
    VehicleReview, DealerReview, SellerReview, ListingReview,
    ReviewImage, ReviewVote, ReviewComment, ReviewLog
)

# Admin Panel App
from admin_panel.models import (
    ActivityLog, AdminSetting, DashboardWidget
)
from admin_panel.messaging_models import VendorNotification

# Content App
from content.models import (
    Article, ContentCategory, Tag, Page,
    MediaGallery, MediaItem, Banner
)

# Core App
from core.models import (
    AuditLog, SystemMetric, ComplianceCheck
)

# Subscriptions App
from subscriptions.models import (
    SubscriptionPlan, UserSubscription, SubscriptionPayment,
    SubscriptionFeatureUsage
)

# Notifications App
from notifications.models import (
    Notification, NotificationPreference, DeviceToken
)

# Parts App
from parts.models import (
    Category, Brand, Part, Inventory, Order, OrderItem,
    Review, BulkUploadLog, IntegrationSource, OrderStatusHistory,
    InventoryTransaction, Cart, CartItem, DiscountCode,
    SaudiCity, CityArea, ShippingRate, OrderShipping, OrderDiscount
)

def delete_model(model_class, model_name):
    """Helper function to delete all objects of a model."""
    try:
        count = model_class.objects.count()
        if count > 0:
            print(f"Deleting {count} {model_name}...")
            model_class.objects.all().delete()
            # Verify
            if model_class.objects.exists():
                print(f"WARNING: Failed to delete all {model_name}. {model_class.objects.count()} remaining.")
            else:
                print(f"Successfully deleted all {model_name}.")
        else:
            print(f"No {model_name} to delete.")
    except Exception as e:
        print(f"Error deleting {model_name}: {e}")

def wipe_data():
    print("Starting data wipe process...")
    
    # --- Inquiries App Deletions (Leaf nodes relying on Listings/Users) ---
    delete_model(TestDriveRequest, "TestDriveRequests")
    delete_model(InquiryResponse, "InquiryResponses")
    delete_model(ListingInquiry, "ListingInquiries")
    
    # --- Reviews App Deletions ---
    delete_model(ReviewLog, "ReviewLogs")
    delete_model(ReviewComment, "ReviewComments")
    delete_model(ReviewVote, "ReviewVotes")
    delete_model(ReviewImage, "ReviewImages")
    delete_model(VehicleReview, "VehicleReviews")
    delete_model(DealerReview, "DealerReviews")
    delete_model(SellerReview, "SellerReviews")
    delete_model(ListingReview, "ListingReviews")
    
    # --- Listings App Deletions (Relies on Vehicles, Users, Dealers) ---
    delete_model(ListingStatusLog, "ListingStatusLogs")
    delete_model(ListingView, "ListingViews")
    delete_model(SavedListing, "SavedListings")
    delete_model(ListingImage, "ListingImages")
    delete_model(ListingVideo, "ListingVideos")
    delete_model(VehicleListing, "VehicleListings")
    delete_model(Dealer, "Dealers")
    
    # --- Parts App Deletions ---
    # Delete child models first
    delete_model(InventoryTransaction, "InventoryTransactions")
    delete_model(OrderStatusHistory, "OrderStatusHistories")
    delete_model(OrderShipping, "OrderShippings")
    delete_model(OrderDiscount, "OrderDiscounts")
    delete_model(OrderItem, "OrderItems")
    
    # Delete Orders and Carts
    delete_model(Order, "Orders")
    delete_model(CartItem, "CartItems")
    delete_model(Cart, "Carts")
    
    # Delete Reviews and Logs
    delete_model(Review, "Parts Reviews")
    delete_model(BulkUploadLog, "BulkUploadLogs")
    delete_model(IntegrationSource, "IntegrationSources")
    
    # Delete Inventory and Parts
    delete_model(Inventory, "Inventories")
    delete_model(Part, "Parts")
    
    # Delete Taxonomy and Locations
    delete_model(Brand, "Parts Brands")
    delete_model(Category, "Parts Categories")
    delete_model(ShippingRate, "ShippingRates")
    delete_model(CityArea, "CityAreas")
    delete_model(SaudiCity, "SaudiCities")
    delete_model(DiscountCode, "DiscountCodes")
    
    # --- Vehicles App Deletions ---
    delete_model(VehicleSpecificationFeature, "VehicleSpecificationFeatures")
    delete_model(VehicleSpecification, "VehicleSpecifications")
    delete_model(VehicleFeature, "VehicleFeatures")
    delete_model(VehicleVariant, "VehicleVariants")
    delete_model(VehicleModelTaxonomy, "VehicleModelTaxonomies")
    delete_model(VehicleMake, "VehicleMakes")
    delete_model(VehicleModel, "VehicleModels")
    delete_model(VehicleBrand, "VehicleBrands")
    delete_model(VehicleCategory, "VehicleCategories")
    delete_model(FuelType, "FuelTypes")
    delete_model(TransmissionType, "TransmissionTypes")
    delete_model(VehiclePartCategory, "VehiclePartCategories")
    
    # --- Business Partners App Deletions ---
    # Delete document-related models first (leaf nodes)
    delete_model(DocumentAuditLog, "DocumentAuditLogs")
    delete_model(DocumentVerificationQueue, "DocumentVerificationQueues")
    delete_model(DocumentCategory, "DocumentCategories")
    delete_model(VendorDocument, "VendorDocuments")
    
    delete_model(VendorNotification, "VendorNotifications")
    delete_model(VendorPerformanceScore, "VendorPerformanceScores")
    delete_model(VendorApplication, "VendorApplications")
    delete_model(VendorProfile, "VendorProfiles")
    delete_model(BusinessPartner, "BusinessPartners")
    
    # --- Admin Panel App Deletions ---
    delete_model(ActivityLog, "ActivityLogs")
    delete_model(DashboardWidget, "DashboardWidgets")
    delete_model(AdminSetting, "AdminSettings")
    
    # --- Content App Deletions ---
    delete_model(MediaItem, "MediaItems")
    delete_model(MediaGallery, "MediaGalleries")
    delete_model(Banner, "Banners")
    delete_model(Article, "Articles")
    delete_model(ContentCategory, "ContentCategories")
    delete_model(Tag, "Tags")
    delete_model(Page, "Pages")
    
    # --- Core App Deletions ---
    delete_model(AuditLog, "AuditLogs")
    delete_model(SystemMetric, "SystemMetrics")
    delete_model(ComplianceCheck, "ComplianceChecks")
    
    # --- Notifications App Deletions (Depends on Users) ---
    delete_model(DeviceToken, "DeviceTokens")
    delete_model(NotificationPreference, "NotificationPreferences")
    delete_model(Notification, "Notifications")
    
    # --- Subscriptions App Deletions (Depends on Users) ---
    delete_model(SubscriptionFeatureUsage, "SubscriptionFeatureUsages")
    delete_model(SubscriptionPayment, "SubscriptionPayments")
    delete_model(UserSubscription, "UserSubscriptions")
    delete_model(SubscriptionPlan, "SubscriptionPlans")
    
    # --- Django JWT Token Deletions ---
    delete_model(BlacklistedToken, "BlacklistedTokens")
    delete_model(OutstandingToken, "OutstandingTokens")
    
    # --- Django Session Deletions ---
    delete_model(Session, "Sessions")
    
    # --- Users Deletion (The Root) ---
    delete_model(UserProfile, "UserProfiles")
    
    try:
        # Check if we can use custom manager method or standard delete
        if hasattr(User.objects, 'all_with_deleted'):
            qs = User.objects.all_with_deleted()
        else:
            qs = User.objects.all()
        
        count = qs.count()
        if count > 0:
            print(f"Deleting {count} Users...")
            # We need to exclude superusers if we want to keep admin access, 
            # but the request is to wipe all data.
            # Assuming we want to keep at least one superuser or wipe EVERYTHING.
            # "remove all the tables data" implies EVERYTHING.
            qs.delete()
            if User.objects.exists():
                 print(f"WARNING: Failed to delete all Users. {User.objects.count()} remaining.")
            else:
                 print("Successfully deleted all Users.")
        else:
            print("No Users to delete.")
    except Exception as e:
        print(f"Error deleting Users: {e}")

    # --- Cleanup Orphaned Data ---
    print("Cleaning up any orphaned M2M tables...")
    with connection.cursor() as cursor:
        # Helper to truncate table if exists
        def truncate_table(table_name):
            try:
                cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE;")
                print(f"Truncated {table_name}")
            except Exception:
                pass # Table might not exist or other error

        # Manually truncate known M2M tables if needed
        # Most should be handled by CASCADE
        pass

    print("Clearing cache...")
    try:
        cache.clear()
        print("Cache cleared.")
    except Exception as e:
        print(f"Error clearing cache: {e}")
    
    print("Data wipe completed.")

if __name__ == '__main__':
    wipe_data()
