from django.urls import path, include
from rest_framework.routers import SimpleRouter

from apps.app_net_manage.api_viewsets import org2_views


app_name = 'app_net_manage'


no_slash_router = SimpleRouter(trailing_slash=False)
# 公共
no_slash_router.register(r'user/role', org2_views.NetManageUserRoleViewSet, basename='userrole')
no_slash_router.register(r'org-obj', org2_views.OrgObjViewSet, basename='org-obj')
no_slash_router.register(r'contacts', org2_views.ContactPersonViewSet, basename='contacts')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
