from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ListingInquiryViewSet, 
    InquiryResponseViewSet, 
    TestDriveRequestViewSet,
    ReceivedInquiriesView,
    UnauthenticatedInquiryCreateView
)

app_name = 'inquiries'

router = DefaultRouter()
router.register(r'inquiries', ListingInquiryViewSet, basename='inquiries')
router.register(r'responses', InquiryResponseViewSet, basename='responses')
router.register(r'test-drives', TestDriveRequestViewSet, basename='test-drives')

urlpatterns = [
    path('', include(router.urls)),
    path('received/', ReceivedInquiriesView.as_view(), name='received-inquiries'),
    path('create/', UnauthenticatedInquiryCreateView.as_view(), name='unauthenticated-inquiry-create'),
]