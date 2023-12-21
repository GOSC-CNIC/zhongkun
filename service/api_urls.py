from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .viewsets import org_data_center_views, org_views


app_name = 'service'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'organization', org_views.OrganizationViewSet, basename='organization')
no_slash_router.register(r'admin/odc', org_data_center_views.AdminOrgDataCenterViewSet, basename='admin-odc')
no_slash_router.register(r'odc', org_data_center_views.OrgDataCenterViewSet, basename='odc')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
