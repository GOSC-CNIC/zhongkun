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
router.register(r'p-quota', views.ServicePrivateQuotaViewSet, basename='private-quota')


urlpatterns = [
    path('', include(router.urls)),
    path(r'jwt/', views.JWTObtainPairView.as_view(), name='jwt-token'),
    path(r'jwt-refresh/', views.JWTRefreshView.as_view(), name='jwt-refresh'),
    path(r'jwt-verify/', views.JWTVerifyView.as_view(), name='jwt-verify'),
]
