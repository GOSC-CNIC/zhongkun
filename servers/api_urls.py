from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .apiviews import flavor_views, views, disk_views, server_views


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


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
