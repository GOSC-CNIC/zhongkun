from django.urls import re_path, path
from apps.app_net_flow import views

app_name = "app_net_flow"
urlpatterns = [
    re_path('^role/$', views.GlobalUserRoleAPIView.as_view(), name='user-role'),  # 当前用户的角色
    re_path('^menu/$', views.MenuListGenericAPIView.as_view(), name='menu-list'),
    re_path('^menu/(?P<pk>[a-z0-9]+)/$', views.MenuDetailGenericAPIView.as_view(), name='menu-detail'),
    re_path('^chart/traffic/$', views.TrafficAPIView.as_view()),
    re_path('^port/$', views.PortListGenericAPIView.as_view()),

    re_path('^chart/$', views.Menu2ChartListGenericAPIView.as_view()),
    re_path('^chart/(?P<pk>[a-z0-9]+)/$', views.Menu2ChartDetailGenericAPIView.as_view()),
    re_path('^group/member/$', views.Menu2MemberListGenericAPIView.as_view()),
    re_path('^group/member/(?P<pk>[a-z0-9]+)/$', views.Menu2MemberDetailGenericAPIView.as_view()),
    re_path('^administrator/$', views.GlobalAdministratorListGenericAPIView.as_view(), name='administrator-list'),
    re_path('^administrator/(?P<pk>[a-z0-9]+)/$', views.GlobalAdministratorDetailGenericAPIView.as_view()),
]
