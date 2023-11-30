from django.urls import path, include
from rest_framework.routers import SimpleRouter

from ipam.viewsets import ipv4_views, org_obj_views, record_views, ipv6_views


app_name = 'ipam'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'ipv4range', ipv4_views.IPv4RangeViewSet, basename='ipam-ipv4range')
no_slash_router.register(r'user/role', ipv4_views.IPAMUserRoleViewSet, basename='ipam-userrole')
no_slash_router.register(r'org-obj', org_obj_views.OrgObjViewSet, basename='org-obj')
no_slash_router.register(r'record/ipv4range', record_views.IPv4RangeRecordViewSet, basename='record-ipv4range')
no_slash_router.register(r'ipv6range', ipv6_views.IPv6RangeViewSet, basename='ipam-ipv6range')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
