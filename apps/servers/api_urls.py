from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .apiviews import (
    flavor_views, views, disk_views, server_views, service_views, snapshot_views, price_views, stats_views,
    res_order_deliver_task_views
)


app_name = 'servers'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'flavor', flavor_views.FlavorViewSet, basename='flavor')
no_slash_router.register(r'admin/flavor', flavor_views.AdminFlavorViewSet, basename='admin-flavor')
no_slash_router.register(r'image', views.ImageViewSet, basename='images')
no_slash_router.register(r'network', views.NetworkViewSet, basename='networks')
no_slash_router.register(r'azone', views.AvailabilityZoneViewSet, basename='availability-zone')
no_slash_router.register(r'disk', disk_views.DisksViewSet, basename='disks')
no_slash_router.register(r'server', server_views.ServersViewSet, basename='servers')
no_slash_router.register(r'server-archive', server_views.ServerArchiveViewSet, basename='server-archive')

no_slash_router.register(r'service', service_views.ServiceViewSet, basename='service')
no_slash_router.register(r'vms/service/p-quota', service_views.ServivePrivateQuotaViewSet,
                         basename='vms-service-p-quota')
no_slash_router.register(r'vms/service/s-quota', service_views.ServiveShareQuotaViewSet,
                         basename='vms-service-s-quota')

no_slash_router.register(r'app_servers/snapshot', snapshot_views.ServerSnapshotViewSet, basename='server-snapshot')
no_slash_router.register(r'app_servers/describe-price/snapshot', price_views.SnapshotPriceViewSet,
                         basename='snapshot-describe-price')
no_slash_router.register(r'app_servers/stats', stats_views.StatsViewSet, basename='stats')
no_slash_router.register(r'app_servers/res-order-deliver/task',
                         res_order_deliver_task_views.ResOdDeliverTaskViewSet, basename='res-order-deliver-task')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
