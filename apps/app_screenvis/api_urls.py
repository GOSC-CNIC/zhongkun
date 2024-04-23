from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .api_views import ceph_views, common_views, host_views, tidb_views, service_views


app_name = 'screenvis'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'configs', common_views.ConfigsViewSet, basename='configs')
no_slash_router.register(r'datacenter', common_views.DataCenterViewSet, basename='datacenter')
no_slash_router.register(r'ceph', ceph_views.MetricCephViewSet, basename='ceph')
no_slash_router.register(r'host', host_views.MetricHostViewSet, basename='host')
no_slash_router.register(r'tidb', tidb_views.MetricTiDBViewSet, basename='tidb')
no_slash_router.register(r'service/server/stats', service_views.ServerServiceViewSet,
                         basename='server-stats')
no_slash_router.register(r'service/vpn/stats', service_views.VPNServiceViewSet,
                         basename='vpn-stats')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
