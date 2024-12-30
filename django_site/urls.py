"""gosc URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include, re_path
from django.conf import settings
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from baton.autodiscover import admin

from core.aai.signin import AAISignIn
from . import views
from . import admin_site
from . import check
from apps.app_alert.views import AlertReceiverAPIView

# 是否只使用大屏展示功能
screenvis_only = getattr(settings, 'SCREEN_VIS_USE_ONLY', False)
check.check_setting(screenvis_only=screenvis_only)


class BothHttpAndHttpsSchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        if not schema.schemes:
            schema.schemes = ["https", "http"]
        else:
            for s in ["https", "http"]:
                if s not in schema.schemes:
                    schema.schemes.append(s)

        return schema


schema_view = get_schema_view(
    openapi.Info(
        title=admin_site.site_header_lazy,
        default_version='v1',
    ),
    url=getattr(settings, 'SWAGGER_SCHEMA_URL', None),
    generator_class=BothHttpAndHttpsSchemaGenerator,
    public=True,
    permission_classes=[permissions.AllowAny],
)

if screenvis_only:
    urlpatterns = [
        path('api/app_screenvis/', include('apps.app_screenvis.api_urls', namespace='screenvis-api')),
        path('api/app_alert/', include('apps.app_alert.api_urls', namespace='alert-api')),
    ]
else:
    urlpatterns = [
        # api url
        path('api/', include('apps.api.urls', namespace='api')),
        path('api/', include('apps.app_vo.api_urls', namespace='vo-api')),
        path('api/', include('apps.service.api_urls', namespace='service-api')),
        path('api/', include('apps.servers.api_urls', namespace='servers-api')),
        path('api/', include('apps.app_storage.api_urls', namespace='storage-api')),
        path('api/', include('apps.app_ticket.api_urls', namespace='ticket-api')),
        path('api/', include('apps.app_order.api_urls', namespace='order-api')),
        path('api/', include('apps.app_metering.api_urls', namespace='metering-api')),
        path('api/', include('apps.app_wallet.api_urls', namespace='wallet-api')),
        path('api/app_global/', include('apps.app_global.api_urls', namespace='app-global-api')),
        path('api/report/', include('apps.app_report.api_urls', namespace='report-api')),
        path('api/monitor/', include('apps.app_monitor.api_urls', namespace='monitor-api')),
        path('api/app_net_manage/', include('apps.app_net_manage.api_urls', namespace='net_manage-api')),
        path('api/app_net_link/', include('apps.app_net_link.api_urls', namespace='net_link-api')),
        path('api/app_net_ipam/', include('apps.app_net_ipam.api_urls', namespace='net_ipam-api')),
        path('api/scan/', include('apps.app_scan.api_urls', namespace='scan-api')),
        path('api/apply/', include('apps.app_apply.api_urls', namespace='apply-api')),
        path('api/app_screenvis/', include('apps.app_screenvis.api_urls', namespace='screenvis-api')),
        path('api/app_netflow/', include('apps.app_net_flow.api_urls', namespace='netflow-api')),
        path('api/app_alert/', include('apps.app_alert.api_urls', namespace='alert-api')),
        path('api/app_probe/', include('apps.app_probe.api_urls', namespace='probe-api')),

        # views url
        path('servers/', include('apps.servers.urls', namespace='servers')),
        path('service/', include('apps.service.urls', namespace='service')),
        path('vpn/', include('apps.app_vpn.urls', namespace='vpn')),
        path('report/', include('apps.app_report.urls', namespace='report')),
        path('probe/', include('apps.app_probe.urls', namespace='probe'))
    ]

urlpatterns += [
    path('', views.home, name='index'),
    path('home/', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('accounts/', include('apps.users.urls', namespace='users')),
    path('apidocs/', login_required(schema_view.with_ui('swagger', cache_timeout=0)), name='apidocs'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='redoc'),
    path('docs/', include('docs.urls', namespace='docs')),
    path('auth/callback/aai', AAISignIn.as_view(), name='auth-callback-aai'),
    path('admin/', admin.site.urls),
    path('baton/', include('baton.urls')),
    path("i18n/", include("django.conf.urls.i18n")),
    re_path(r'api/v\d+/alerts', AlertReceiverAPIView.as_view(), name='alert-receiver'),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
                      path('__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns
