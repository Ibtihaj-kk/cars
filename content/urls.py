from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'content'

router = DefaultRouter()
router.register(r'categories', views.ContentCategoryViewSet, basename='category')
router.register(r'tags', views.TagViewSet, basename='tag')
router.register(r'articles', views.ArticleViewSet, basename='article')
router.register(r'pages', views.PageViewSet, basename='page')
router.register(r'galleries', views.MediaGalleryViewSet, basename='gallery')
router.register(r'media-items', views.MediaItemViewSet, basename='media-item')
router.register(r'banners', views.BannerViewSet, basename='banner')

urlpatterns = [
    path('api/', include(router.urls)),
]