from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .apiviews import views
from .apiviews import (
    monitor_views, service_quota_views,
    stats_quota_views,
)

app_name = 'api'

router = SimpleRouter()
router.register(r'server', views.ServersViewSet, basename='servers')
router.register(r'server-archive', views.ServerArchiveViewSet, basename='server-archive')
router.register(r'image', views.ImageViewSet, basename='images')
router.register(r'network', views.NetworkViewSet, basename='networks')
router.register(r'vpn', views.VPNViewSet, basename='vpn')
router.register(r'flavor', views.FlavorViewSet, basename='flavor')
router.register(r'quota', views.QuotaViewSet, basename='quota')
router.register(r'service', views.ServiceViewSet, basename='service')
router.register(r'registry', views.DataCenterViewSet, basename='registry')
router.register(r'apply/quota', views.UserQuotaApplyViewSet, basename='apply-quota')
router.register(r'user', views.UserViewSet, basename='user')
router.register(r'apply/service', views.ApplyVmServiceViewSet, basename='apply-service')
router.register(r'apply/organization', views.ApplyOrganizationViewSet, basename='apply-organization')
router.register(r'vo', views.VOViewSet, basename='vo')
router.register(r'quota-activity', views.QuotaActivityViewSet, basename='quota-activity')


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'media', views.MediaViewSet, basename='media')
no_slash_router.register(r'server', views.ServersViewSet, basename='servers')
no_slash_router.register(r'server-archive', views.ServerArchiveViewSet, basename='server-archive')
no_slash_router.register(r'image', views.ImageViewSet, basename='images')
no_slash_router.register(r'network', views.NetworkViewSet, basename='networks')
no_slash_router.register(r'vpn', views.VPNViewSet, basename='vpn')
no_slash_router.register(r'flavor', views.FlavorViewSet, basename='flavor')
no_slash_router.register(r'quota', views.QuotaViewSet, basename='quota')
no_slash_router.register(r'service', views.ServiceViewSet, basename='service')
no_slash_router.register(r'registry', views.DataCenterViewSet, basename='registry')
no_slash_router.register(r'apply/quota', views.UserQuotaApplyViewSet, basename='apply-quota')
no_slash_router.register(r'user', views.UserViewSet, basename='user')
no_slash_router.register(r'apply/service', views.ApplyVmServiceViewSet, basename='apply-service')
no_slash_router.register(r'apply/organization', views.ApplyOrganizationViewSet, basename='apply-organization')
no_slash_router.register(r'vo', views.VOViewSet, basename='vo')
no_slash_router.register(r'quota-activity', views.QuotaActivityViewSet, basename='quota-activity')
no_slash_router.register(r'monitor/ceph/query', monitor_views.MonitorCephQueryViewSet, basename='monitor-ceph-query')
no_slash_router.register(r'monitor/server/query', monitor_views.MonitorServerQueryViewSet,
                         basename='monitor-server-query')
no_slash_router.register(r'vms/service/p-quota', service_quota_views.ServivePrivateQuotaViewSet,
                         basename='vms-service-p-quota')
no_slash_router.register(r'vms/service/s-quota', service_quota_views.ServiveShareQuotaViewSet,
                         basename='vms-service-s-quota')
no_slash_router.register(r'stats/quota', stats_quota_views.StatsQuotaViewSet,
                         basename='vms-stats-quota')


urlpatterns = [
    path('', include(router.urls)),
    path('', include(no_slash_router.urls)),
]
