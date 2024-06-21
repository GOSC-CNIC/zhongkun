from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .api_views import common_views


app_name = 'app_global'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'sales-info', common_views.SalesCustomerServiceViewSet, basename='sales-info')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
