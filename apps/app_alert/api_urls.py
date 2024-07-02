from django.urls import re_path, path
from apps.app_alert import views

app_name = "app_alert"
urlpatterns = [
    # 接收告警数据
    re_path('^receiver/$', views.AlertReceiverAPIView.as_view()),
    # 查询告警列表
    re_path('^alert/$', views.AlertGenericAPIView.as_view()),
    # 查询异常告警name、cluster聚合数据
    re_path('^alert/choice/$', views.AlertChoiceAPIView.as_view()),
    # 查询工单列表、创建告警工单
    re_path('^alert/order/$', views.WorkOrderListGenericAPIView.as_view()),

    # 查询告警列表所属的服务
    re_path('^service/$', views.AlertServiceAPIView.as_view()),
    # 查询服务的管理员列表
    re_path('^service/admin/$', views.AlertServiceAdminListGenericAPIView.as_view()),

    # 查询工单解决方案历史数据
    re_path('^ticket/resolution/history/$', views.TicketResolutionHistoryListAPIView.as_view()),

    # 创建工单解决方案类型
    re_path('^ticket/category/$', views.TicketResolutionCategoryListGenericAPIView.as_view()),
    # 查询指定方案类型、修改指定方案类型、删除指定方案类型
    re_path('^ticket/category/(?P<pk>[a-z0-9]+)/$', views.TicketResolutionCategoryDetailGenericAPIView.as_view()),

    # 创建工单解决方案
    re_path('^ticket/resolution/$', views.TicketResolutionListGenericAPIView.as_view()),
    # 查询指定工单解决方案、修改指定工单解决方案、删除指定工单解决方案
    re_path('^ticket/resolution/(?P<pk>[a-z0-9]+)/$', views.TicketResolutionDetailGenericAPIView.as_view()),

    # 工单处理人
    re_path('^ticket/handler/$', views.TicketHandlerListGenericAPIView.as_view()),
    # 查询指定工单处理人、修改指定工单处理人、删除指定工单处理人
    re_path('^ticket/handler/(?P<pk>[a-z0-9]+)/$', views.TicketHandlerDetailGenericAPIView.as_view()),

    # 查询告警工单列表、创建告警工单
    re_path('^ticket/$', views.AlertTicketListGenericAPIView.as_view()),
    # 查询指定工单、修改指定工单、删除指定工单
    re_path('^ticket/(?P<pk>[a-z-0-9]+)/$', views.AlertTicketDetailGenericAPIView.as_view()),

    # 查询邮件通知记录
    re_path('^alert/notification/email/$', views.EmailNotificationAPIView.as_view()),

]
