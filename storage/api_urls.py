from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .apiviews import storage_views, bucket_views


app_name = 'servers'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'admin/storage/bucket', bucket_views.AdminBucketViewSet, basename='admin-bucket')
no_slash_router.register(
    r'admin/storage/statistics', storage_views.StorageStatisticsViewSet, basename='admin-storage-statistics')
no_slash_router.register(r'storage/service', storage_views.ObjectsServiceViewSet, basename='storage-service')
no_slash_router.register(r'storage/bucket', bucket_views.BucketViewSet, basename='bucket')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
