from django.urls import path, include
from rest_framework.routers import SimpleRouter

from apps.app_netbox.api_viewsets import (
    common_views, ip_record_views, ipv4_views, ipv6_views,
    link_views, leaseline_views, element_views
)


app_name = 'netbox'


no_slash_router = SimpleRouter(trailing_slash=False)
# 公共
no_slash_router.register(r'user/role', common_views.NetBoxUserRoleViewSet, basename='netbox-userrole')
no_slash_router.register(r'org-obj', common_views.OrgObjViewSet, basename='org-obj')
no_slash_router.register(r'contacts', common_views.ContactPersonViewSet, basename='contacts')

# ipam
no_slash_router.register(r'ipam/ipv4range', ipv4_views.IPv4RangeViewSet, basename='ipam-ipv4range')
no_slash_router.register(r'ipam/ipv4address', ipv4_views.IPv4AddressViewSet, basename='ipam-ipv4address')
no_slash_router.register(r'ipam/record/ipv4range', ip_record_views.IPv4RangeRecordViewSet, basename='record-ipv4range')
no_slash_router.register(r'ipam/ipv6range', ipv6_views.IPv6RangeViewSet, basename='ipam-ipv6range')

# link
no_slash_router.register(r'link/link', link_views.LinkViewSet, basename='link-link')
no_slash_router.register(r'link/leaseline', leaseline_views.LeaseLineViewSet, basename='link-leaseline')
no_slash_router.register(r'link/fibercable', element_views.FiberCableViewSet, basename='link-fibercable')
no_slash_router.register(r'link/distributionframe', element_views.DistriFrameViewSet,
                         basename='link-distributionframe')
no_slash_router.register(r'link/connectorbox', element_views.ConnectorBoxViewSet, basename='link-connectorbox')
no_slash_router.register(r'link/opticalfiber', element_views.OpticalFiberViewSet, basename='link-opticalfiber')
no_slash_router.register(r'link/distriframeport', element_views.DistriFramePortViewSet,
                         basename='link-distriframeport')
no_slash_router.register(r'link/element', element_views.ElementViewSet, basename='link-element')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
