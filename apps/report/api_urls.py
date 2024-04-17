from django.urls import path, include
from rest_framework.routers import SimpleRouter

from apps.report import report_storage_views
from apps.report.api_viewsets import arrear_views


app_name = 'report'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'storage/bucket/stats/monthly', report_storage_views.BucketStatsMonthlyViewSet,
                         basename='report-bucket-stats-monthly')
no_slash_router.register(r'storage/stats/monthly', report_storage_views.StorageStatsMonthlyViewSet,
                         basename='report-storage-stats-monthly')
no_slash_router.register(r'admin/arrear/server', arrear_views.ArrearServerViewSet,
                         basename='admin-report-arrear-server')
no_slash_router.register(r'admin/arrear/bucket', arrear_views.ArrearBucketViewSet,
                         basename='admin-report-arrear-bucket')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
