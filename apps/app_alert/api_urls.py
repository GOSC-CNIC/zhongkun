from django.urls import re_path, path
from apps.app_alert import views

app_name = "app_alert"
urlpatterns = [
    re_path('^receiver/$', views.AlertReceiverAPIView.as_view()),  # 接收告警数据
    re_path('^alert/$', views.AlertGenericAPIView.as_view()),  # 查询告警列表
    re_path('^alert/choice/$', views.AlertChoiceAPIView.as_view()),  # 查询异常告警name、cluster聚合数据
    re_path('^alert/order/$', views.WorkOrderListGenericAPIView.as_view()),  # 查询工单列表、创建告警工单
    re_path('^alert/notification/email/$', views.EmailNotificationAPIView.as_view()),  # 查询邮件通知记录

]