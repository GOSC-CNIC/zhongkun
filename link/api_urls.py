from django.urls import path, include
from rest_framework.routers import SimpleRouter

from link.viewsets import (
    leaseline_views, fibercable_views, distriframe_views,
    connectorbox_views, link_views, opticalfiber_views,
    distriframeport_views, linkorg_views, linkuserrole_views,
    element_views
)


app_name = 'link'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'leaseline', leaseline_views.LeaseLineViewSet, basename='link-leaseline')
no_slash_router.register(r'fibercable', fibercable_views.FiberCableViewSet, basename='link-fibercable')
no_slash_router.register(r'distributionframe', distriframe_views.DistriFrameViewSet,
                         basename='link-distributionframe')
no_slash_router.register(r'connectorbox', connectorbox_views.ConnectorBoxViewSet, basename='link-connectorbox')
no_slash_router.register(r'link', link_views.LinkViewSet, basename='link-link')
no_slash_router.register(r'opticalfiber', opticalfiber_views.OpticalFiberViewSet, basename='link-opticalfiber')
no_slash_router.register(r'distriframeport', distriframeport_views.DistriFramePortViewSet,
                         basename='link-distriframeport')
no_slash_router.register(r'linkorg', linkorg_views.LinkOrgViewSet, basename='link-linkorg')
no_slash_router.register(r'user/role', linkuserrole_views.LinkUserRoleViewSet, basename='link-userrole')
no_slash_router.register(r'element', element_views.ElementViewSet, basename='link-element')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
