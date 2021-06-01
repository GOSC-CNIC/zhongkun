from django.urls import path, include

from rest_framework.routers import SimpleRouter

from . import views


app_name = 'api'

router = SimpleRouter()
router.register(r'server', views.ServersViewSet, basename='servers')
router.register(r'server-archive', views.ServerArchiveViewSet, basename='server-archive')
router.register(r'image', views.ImageViewSet, basename='images')
router.register(r'network', views.NetworkViewSet, basename='networks')
router.register(r'vpn', views.VPNViewSet, basename='vpn')
router.register(r'flavor', views.FlavorViewSet, basename='flavor')
router.register(r'u-quota', views.UserQuotaViewSet, basename='user-quota')
router.register(r'service', views.ServiceViewSet, basename='service')
router.register(r'registry', views.DataCenterViewSet, basename='registry')
router.register(r'apply/quota', views.UserQuotaApplyViewSet, basename='apply-quota')
router.register(r'user', views.UserViewSet, basename='user')
router.register(r'apply/service', views.ApplyVmServiceViewSet, basename='apply-service')

no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'media', views.MediaViewSet, basename='media')


urlpatterns = [
    path('', include(router.urls)),
    path('', include(no_slash_router.urls)),
]
