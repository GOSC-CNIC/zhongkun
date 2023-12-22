from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .apiviews import flavor_views, views


app_name = 'servers'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'flavor', flavor_views.FlavorViewSet, basename='flavor')
no_slash_router.register(r'admin/flavor', flavor_views.AdminFlavorViewSet, basename='admin-flavor')
no_slash_router.register(r'image', views.ImageViewSet, basename='images')
no_slash_router.register(r'network', views.NetworkViewSet, basename='networks')
no_slash_router.register(r'azone', views.AvailabilityZoneViewSet, basename='availability-zone')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
