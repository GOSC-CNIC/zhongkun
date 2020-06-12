from django.urls import path, include

from rest_framework.routers import SimpleRouter

from . import views


app_name = 'api'

router = SimpleRouter()
router.register(r'server', views.ServersViewSet, basename='servers')
router.register(r'image', views.ImageViewSet, basename='images')
router.register(r'network', views.NetworkViewSet, basename='networks')
router.register(r'vpn', views.VPNViewSet, basename='vpn')
router.register(r'flavor', views.FlavorViewSet, basename='flavor')


urlpatterns = [
    path('', include(router.urls)),
]
