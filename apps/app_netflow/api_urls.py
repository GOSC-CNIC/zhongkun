from django.urls import re_path, path
from apps.app_netflow import views

app_name = "app_netflow"
urlpatterns = [
    re_path('^menu/$', views.MenuAPIView.as_view()),
    re_path('^chart/$', views.ChartAPIView.as_view()),

]
