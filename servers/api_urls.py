from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .apiviews import flavor_views


app_name = 'servers'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'flavor', flavor_views.FlavorViewSet, basename='flavor')
no_slash_router.register(r'admin/flavor', flavor_views.AdminFlavorViewSet, basename='admin-flavor')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
