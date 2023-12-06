from django.urls import path, include
from rest_framework.routers import SimpleRouter

from monitor import monitor_views, log_views


app_name = 'monitor'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'unit/ceph', monitor_views.MonitorUnitCephViewSet, basename='unit-ceph')
no_slash_router.register(r'unit/server', monitor_views.MonitorUnitServerViewSet, basename='unit-server')
no_slash_router.register(r'unit/tidb', monitor_views.MonitorUnitTiDBViewSet, basename='unit-tidb')
no_slash_router.register(r'ceph/query', monitor_views.MonitorCephQueryViewSet, basename='ceph-query')
no_slash_router.register(r'server/query', monitor_views.MonitorServerQueryViewSet,
                         basename='server-query')
no_slash_router.register(r'video-meeting/query', monitor_views.MonitorVideoMeetingQueryViewSet,
                         basename='video-meeting-query')
no_slash_router.register(r'website', monitor_views.MonitorWebsiteViewSet,
                         basename='website')
no_slash_router.register(r'website-task', monitor_views.MonitorWebsiteTaskViewSet,
                         basename='website-task')
no_slash_router.register(r'tidb/query', monitor_views.MonitorTiDBQueryViewSet, basename='tidb-query')
no_slash_router.register(r'log/site', log_views.LogSiteViewSet, basename='log-site')
no_slash_router.register(r'admin/email', monitor_views.UnitAdminEmailViewSet, basename='unit-admin-email')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
