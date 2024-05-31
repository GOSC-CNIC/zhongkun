from django.urls import path, include
from rest_framework.routers import SimpleRouter

from apps.app_net_link.api_viewsets import link_views, leaseline_views, element_views, common_views


app_name = 'app_net_link'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'user/role', common_views.NetLinkUserRoleViewSet, basename='link-userrole')
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
