from django.urls import path, include
from rest_framework.routers import SimpleRouter

from apps.app_probe import views
from apps.app_probe.api_views.probe_views import ProbeViewSet

app_name = 'probes'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'probe/version', ProbeViewSet, basename='probe-version')

urlpatterns = [
    path('', include(no_slash_router.urls)),
    path('details/', views.ProbeDetailsViews.as_view(), name='probe-details'),
]
