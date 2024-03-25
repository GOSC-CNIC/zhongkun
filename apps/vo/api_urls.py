from django.urls import path, include
from rest_framework.routers import SimpleRouter

from vo.views import VOViewSet


app_name = 'ipam'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'vo', VOViewSet, basename='vo')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
