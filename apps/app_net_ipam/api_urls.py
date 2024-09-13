from django.urls import path, include
from rest_framework.routers import SimpleRouter

from apps.app_net_ipam.api_viewsets import (
    common_views, ip_record_views, ipv4_views, ipv6_views
)


app_name = 'app_net_ipam'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'user/role', common_views.NetIPamUserRoleViewSet, basename='ipam-userrole')
no_slash_router.register(r'ipam/ipv4range', ipv4_views.IPv4RangeViewSet, basename='ipam-ipv4range')
no_slash_router.register(r'ipam/ipv4address', ipv4_views.IPv4AddressViewSet, basename='ipam-ipv4address')
no_slash_router.register(r'ipam/record/ipv4range', ip_record_views.IPv4RangeRecordViewSet, basename='record-ipv4range')
no_slash_router.register(r'ipam/ipv6range', ipv6_views.IPv6RangeViewSet, basename='ipam-ipv6range')
no_slash_router.register(r'ipam/record/ipv6range', ip_record_views.IPv6RangeRecordViewSet, basename='record-ipv6range')
no_slash_router.register(r'ipam/ipv4supernet', ipv4_views.IPv4SupernetViewSet, basename='ipam-ipv4supernet')
no_slash_router.register(r'ipam/external/ipv4range', ipv4_views.ExternalIPv4RangeViewSet,
                         basename='ipam-external-ipv4range')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
