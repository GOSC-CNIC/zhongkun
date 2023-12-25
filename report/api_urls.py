from django.urls import path, include
from rest_framework.routers import SimpleRouter

from report import report_storage_views


app_name = 'report'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'storage/bucket/stats/monthly', report_storage_views.BucketStatsMonthlyViewSet,
                         basename='report-bucket-stats-monthly')
no_slash_router.register(r'storage/stats/monthly', report_storage_views.StorageStatsMonthlyViewSet,
                         basename='report-storage-stats-monthly')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
