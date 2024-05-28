from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .apiviews import views
from .apiviews import (
    user_views, email_views,
    portal_views
)


app_name = 'api'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'media', views.MediaViewSet, basename='media')
no_slash_router.register(r'vpn', views.VPNViewSet, basename='vpn')
no_slash_router.register(r'registry', views.DataCenterViewSet, basename='registry')
no_slash_router.register(r'user', user_views.UserViewSet, basename='user')
no_slash_router.register(r'email', email_views.EmailViewSet, basename='email')
no_slash_router.register(
    r'admin/user/statistics', user_views.AdminUserStatisticsViewSet, basename='admin-user-statistics')

no_slash_router.register(r'portal/service', portal_views.PortalServiceViewSet, basename='portal-service')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
