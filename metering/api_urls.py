from django.urls import path, include
from rest_framework.routers import SimpleRouter

from metering.apiviews import metering_views, storage_metering_views, monitor_metering_views


app_name = 'metering'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'metering/server', metering_views.MeteringServerViewSet, basename='metering-server')
no_slash_router.register(r'metering/disk', metering_views.MeteringDiskViewSet, basename='metering-disk')
no_slash_router.register(r'statement/server', metering_views.StatementServerViewSet, basename='statement-server')
no_slash_router.register(r'statement/disk', metering_views.StatementDiskViewSet, basename='statement-disk')
no_slash_router.register(
    r'metering/storage', storage_metering_views.MeteringStorageViewSet, basename='metering-storage')
no_slash_router.register(
    r'metering/admin/storage', storage_metering_views.AdminMeteringStorageViewSet, basename='admin-metering-storage')
no_slash_router.register(
    r'statement/storage', storage_metering_views.StatementStorageViewSet, basename='statement-storage')
no_slash_router.register(
    r'metering/monitor/site', monitor_metering_views.MeteringMonitorSiteViewSet, basename='metering-monitor-site')
no_slash_router.register(
    r'statement/monitor/site', monitor_metering_views.StatementMonitorSiteViewSet, basename='statement-monitor-site')

no_slash_router.register(
    r'admin/metering/server/statistics', metering_views.AdminMeteringServerStatisticsViewSet,
    basename='admin-metering-server-statistics')
no_slash_router.register(
    r'admin/metering/storage/statistics', storage_metering_views.AdminMeteringStorageStatisticsViewSet,
    basename='admin-metering-storage-statistics')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
