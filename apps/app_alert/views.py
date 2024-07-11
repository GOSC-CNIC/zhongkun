import time
from rest_framework.generics import GenericAPIView
from django.utils.translation import gettext_lazy
from apps.app_alert.filters import AlertFilterBackend
from apps.app_alert.models import AlertModel
from apps.app_alert.models import ResolvedAlertModel
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from apps.app_alert.handlers.receiver import AlertReceiver
from apps.app_alert.pagination import LimitOffsetPage
from apps.app_alert.pagination import CustomAlertCursorPagination
from django_filters.rest_framework import DjangoFilterBackend
from apps.app_alert.handlers.handlers import AlertChoiceHandler
from apps.app_alert.serializers import NotificationModelSerializer
from apps.app_alert.models import EmailNotification
from django.db.models import Q
from apps.app_alert.handlers.handlers import EmailNotificationCleaner
from apps.app_alert.permission import ReceiverPermission
from apps.app_alert.handlers.handlers import UserMonitorUnit
from apps.app_alert.serializers import AlertModelSerializer
from collections import OrderedDict
from rest_framework.permissions import IsAuthenticated
from core.aai.authentication import CreateUserJWTAuthentication
from rest_framework.authentication import BasicAuthentication, SessionAuthentication


# Create your views here.
class AlertReceiverAPIView(APIView):
    permission_classes = [ReceiverPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('接收异常告警'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def post(self, request):
        """
        接收异常告警

            http code 200：
            {
                "status": "success"
            }
        """
        r = AlertReceiver(request.data)
        r.start()
        return Response({"status": "success"})


class AlertGenericAPIView(APIView):
    permission_classes = [IsAuthenticated, ]
    authentication_classes = [CreateUserJWTAuthentication, BasicAuthentication, SessionAuthentication, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询告警列表'),
        manual_parameters=[
            openapi.Parameter(name='id',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='告警ID'),
            openapi.Parameter(name='start__gte',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='开始时间大于'),
            openapi.Parameter(name='start__lte',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='开始时间小于'),
            openapi.Parameter(name='end__gte',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='结束时间大于'),
            openapi.Parameter(name='end__lte',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='结束时间小于'),
            openapi.Parameter(name='instance',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='主机'),
            openapi.Parameter(name='port',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='端口'),
            openapi.Parameter(name='severity',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              enum=["critical", "error", "warning"],
                              description='等级'),
            openapi.Parameter(name='status',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              enum=["firing", "resolved"],
                              description='状态'),
            openapi.Parameter(name='name',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='名称'),
            openapi.Parameter(name='type',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              enum=["log", "metric", "webmonitor"],
                              description='类型'),
            openapi.Parameter(name='cluster',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='来源'),
            openapi.Parameter(name='cursor',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='游标'),
            openapi.Parameter(name='page_size',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='查询条目数'),

        ],
        responses={
            200: ""
        }
    )
    def get(self, request):
        """
            查询告警列表

                    http code 200：
                    {
                        "count": 525,
                        "next": null,
                        "previous": null,
                        "results": [
                            {
                                "id": "1aedaac26b56b61d644573", # ID
                                "fingerprint": "e7c69c516fd0a3360", # 指纹
                                "instance": "127.0.0.1", # 主机
                                "port": "", # 端口
                                "severity": "critical", # 等级
                                "summary": "the message including error tips in plenty of logs", # 摘要
                                "description": "source: mail_log level: error content xxxxxxxxxxxx", # 详情
                                "start": 1701738777, # 开始时间
                                "end": 1701740316, # 结束时间
                                "count": 18, # 累计
                                "creation": 1701738778,  # 创建时间
                                "modification": 1701739716,  # 修改时间
                                "alertname": "mail_log_error", # 名称
                                "monitor_cluster": "mail_log", # 来源
                                "alert_type": "log", # 类型
                                "timestamp": 1701738777, # 等于开始时间
                                "startsAt": "2023-12-05T09:12:57", # 等于开始时间
                                "status": "firing", #  # 状态,
                                "order":{ # 工单信息
                                      "id": "fasfkasjgasdlg",  # 工单id
                                      "status": "已完成", # 工单状态
                                      "remark": "已经解决，是xxxx故障",  # 备注
                                      "creation": "2024-01-17T13:21:58.985281", # 创建时间
                                      "creator_email": "user@cnic.cn",# 创建人邮箱
                                      "creator_name": "姓名" # 创建人姓名
                                    }
                            }]
                    }
                """

        # 进行中告警和已恢复告警
        queryset_list = [AlertModel.objects.all(), ResolvedAlertModel.objects.all()]
        queryset_list = self.filter_queryset(queryset_list)
        page_data_list, previous_link, next_link, total_count = CustomAlertCursorPagination().paginate_queryset(
            queryset_list, request, self)
        serializer = AlertModelSerializer(page_data_list, many=True)
        return Response(OrderedDict([
            ('count', total_count),
            ('previous', previous_link),
            ('next', next_link),
            ('results', serializer.data)
        ]))

    def filter_queryset(self, queryset_list):
        # 通过用户权限过滤queryset
        queryset_list = self.filter_by_user_permission(queryset_list=queryset_list)
        # 通过请求参数过滤queryset
        queryset_list = self.filter_by_request_params(queryset_list=queryset_list)
        return queryset_list

    def filter_by_request_params(self, queryset_list):
        filtered_queryset_list = []
        for queryset in queryset_list:
            queryset = AlertFilterBackend().filter_queryset(self.request, queryset, self)
            filtered_queryset_list.append(queryset)
        return filtered_queryset_list

    def filter_by_user_permission(self, queryset_list):
        if self.request.user.is_superuser:
            return queryset_list
        user_units = UserMonitorUnit(self.request)
        filtered_queryset_list = []
        for queryset in queryset_list:
            qs = queryset.filter(Q(cluster__in=user_units.clusters) | Q(fingerprint__in=user_units.url_hash_list))
            filtered_queryset_list.append(qs)
        return filtered_queryset_list


class AlertChoiceAPIView(APIView):
    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询异常告警可选项'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request):
        """
                查询异常告警可选项（需要使用JWT）

                    http code 200：
                    {
                        "name": [   # 名称
                            "HostHighCpuLoad",
                            "HostOutOfMemory",
                        ],
                        "cluster": [  # 来源
                            "cluster1",
                            "cluster2",
                        ]
                    }
                """
        result = AlertChoiceHandler(request).get()
        return Response(result)




class EmailNotificationAPIView(GenericAPIView):
    queryset = EmailNotification.objects.all()
    serializer_class = NotificationModelSerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = LimitOffsetPage

    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询当前用户的告警通知记录'),
        manual_parameters=[
            openapi.Parameter(name='start',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='开始时间戳(秒)'),
            openapi.Parameter(name='end',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='结束时间戳(秒)'),
            openapi.Parameter(name='severity',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              enum=["critical", "error", "warning"],
                              description='等级'),
        ],
        responses={
        }
    )
    def get(self, request):
        """
                查询当前用户的告警通知记录（需要使用JWT）

                    http code 200：
                    {
                        "count": 53,
                        "next": null,
                        "previous": null,
                        "results": [
                            {
                                "id": "a4e51186b93ed60f6", # 通知ID
                                "alert": {
                                    "id": "209ff403eed3615", # 异常ID
                                    "fingerprint": "4c22db2cad8a6467c32372", # 指纹
                                    "name": "webPageNotAvailable", # 名称
                                    "type": "webmonitor", # 类型
                                    "instance": "", # 主机
                                    "port": "", # 端口
                                    "cluster": "webMonitor", # 来源
                                    "severity": "error",  # 等级
                                    "summary": "webPage is not availabe (instance https://test20231031.cn/)", # 摘要
                                    "description": "WebPage https://test20231031.cn/ is  not availabe xxxxxxx",  # 详情
                                    "start": 1699852484, # 开始时间
                                    "end": 1701656984, # 结束时间
                                    "count": 112967, # 累计
                                    "first_notification": 1700126640, # 首次通知时间
                                    "last_notification": 1701648000, # 最近通知时间
                                    "creation": 1700017995,  # 创建时间
                                    "modification": 1701657014,  # 修改时间
                                    "status": "resolved" # 状态
                                },
                                "email": "xxx@cnic.cn", # 通知邮箱
                                "timestamp": 1701648000 # 通知时间
                            }]
                    }
                """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            ret = self.get_paginated_response(EmailNotificationCleaner().start(serializer.data))
            return ret
        serializer = self.get_serializer(queryset, many=True)
        return Response(EmailNotificationCleaner().start(serializer.data))

    def filter_queryset(self, queryset):
        timestamp = int(time.time())
        params = self.request.query_params
        start = params.get("start") or timestamp - 30 * 12 * 86400
        end = params.get("end") or timestamp
        queryset = queryset.filter(timestamp__gte=start, timestamp__lte=end)
        severity = params.get("severity")
        if severity:
            queryset = queryset.filter(Q(alert__in=AlertModel.objects.filter(severity=severity)) | Q(
                alert__in=ResolvedAlertModel.objects.filter(severity=severity)))
        return queryset

    def get_queryset(self):
        if not self.request:
            return EmailNotification.objects.none()
        return self.queryset.filter(email=self.request.user.username)





