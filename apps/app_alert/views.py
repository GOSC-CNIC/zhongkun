import copy
import time
from rest_framework.generics import GenericAPIView
from django.utils.translation import gettext_lazy
from apps.app_alert.filters import FiringAlterFilter, ResolvedAlterFilter, AlertFilterBackend, WorkOrderFilter
from apps.app_alert.models import AlertModel
from apps.app_alert.models import ResolvedAlertModel
from apps.app_alert.models import AlertWorkOrder
from apps.app_alert.models import AlertLifetimeModel
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from apps.app_alert.handlers.receiver import AlertReceiver
from apps.app_alert.serializers import ResolvedAlertModelSerializer
from apps.app_alert.pagination import AlertCustomLimitOffset
from apps.app_alert.pagination import LimitOffsetPage
from django_filters.rest_framework import DjangoFilterBackend
from apps.app_alert.handlers.handlers import AlertQuerysetFilter
from itertools import chain
from apps.app_alert.handlers.handlers import AlertCleaner
from apps.app_alert.handlers.handlers import AlertChoiceHandler
from rest_framework.mixins import CreateModelMixin
from apps.app_alert.serializers import WorkOrderSerializer
from apps.app_alert.serializers import NotificationModelSerializer
from apps.app_alert.filters import WorkOrderFilter
from rest_framework import status as status_code
from rest_framework.exceptions import PermissionDenied
from apps.app_alert.utils.utils import hash_md5
from django.http import QueryDict
from apps.app_alert.models import EmailNotification
from django.db.models import Q
from apps.app_alert.handlers.handlers import EmailNotificationCleaner
from apps.app_alert.permission import ReceiverPermission
from apps.app_alert.handlers.handlers import UserMonitorUnit
from apps.app_alert.utils.utils import DateUtils


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


class AlertAPIView(GenericAPIView):
    queryset_list = [AlertModel.objects.all(), ResolvedAlertModel.objects.all()]  # firing + resolved
    serializer_class = ResolvedAlertModelSerializer
    filterset_classes = [FiringAlterFilter, ResolvedAlterFilter]  # 对应两个filter
    pagination_class = AlertCustomLimitOffset  # 重写分页器
    filterset_class = ResolvedAlterFilter
    filter_backends = [DjangoFilterBackend]  # apidoc params

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
            openapi.Parameter(name='offset',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_STRING,
                              required=False,
                              description='查询偏移量'),
            openapi.Parameter(name='limit',
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
                查询异常告警（需要使用JWT）

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
        queryset = self.filter_queryset(self.queryset_list)  # 两个 model 过滤后进行合并
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(AlertCleaner().clean(serializer.data))
        serializer = self.get_serializer(queryset, many=True)
        return Response(AlertCleaner().clean(serializer.data))

    def filter_queryset(self, queryset_list):
        queryset_list = AlertQuerysetFilter(request=self.request).filter()
        filtered_queryset_list = []
        for queryset in queryset_list:
            queryset = AlertFilterBackend().filter_queryset(self.request, queryset, self)
            filtered_queryset_list.append(queryset)
        self._filtered_queryset_list = filtered_queryset_list
        return chain(*filtered_queryset_list)

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, '_paginator'):
            self._paginator = self.pagination_class(self._filtered_queryset_list)  # 传入过滤后的queryset列表，计算总数
        return self._paginator

    def paginate_queryset(self, queryset):
        if self.paginator is None:
            return None
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_queryset(self):
        """
        覆盖原方法
        """
        pass


class AlertChoiceAPIView(APIView):
    # permission_classes = [IsAuthenticated, ]

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
        return Response(AlertChoiceHandler(request).get())


class WorkOrderListGenericAPIView(GenericAPIView, CreateModelMixin):
    queryset = AlertWorkOrder.objects.all()
    serializer_class = WorkOrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = WorkOrderFilter
    pagination_class = LimitOffsetPage

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询告警工单列表'),
        manual_parameters=[
        ],
        responses={
        }
    )
    def get(self, request):
        """
        查询告警工单列表
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建告警工单'),
        manual_parameters=[
        ],
        responses={
        }
    )
    def post(self, request, *args, **kwargs):
        """
            创建告警工单

                http code 200：
                    {
                      "id": "xxx",
                      "status": "无需处理",
                      "remark": "测试",
                      "creation": "2024-01-26T11:03:37.402077",
                      "modification": "2024-01-26T11:03:37.402077",
                      "alert": "xxx",
                      "creator": "xxx"
                    }
        """
        params = self.pretreatment(request)
        serializers = []
        for param in params:
            serializer = self.get_serializer(data=param)
            serializer.is_valid(raise_exception=True)
            serializers.append(serializer)

        timestamp = DateUtils.timestamp()

        for serializer in serializers:
            self.perform_create(serializer, timestamp=timestamp)
        return Response({"status": "success"}, status=status_code.HTTP_201_CREATED)

    def perform_create(self, serializer, **kwargs):
        alert = serializer.validated_data.get("alert")
        user_monitor_units = UserMonitorUnit(self.request)
        if alert.fingerprint not in user_monitor_units.url_hash_list and alert.cluster not in user_monitor_units.clusters and not self.request.user.is_superuser:
            raise PermissionDenied()
        order = serializer.save(
            creator=self.request.user,
            creation=kwargs.get('timestamp'),
            modification=kwargs.get('timestamp'),
        )
        lifecycle = AlertLifetimeModel.objects.filter(id=order.alert.id).first()
        if lifecycle and not lifecycle.end:
            lifecycle.end = order.creation
            lifecycle.status = AlertLifetimeModel.Status.WORK_ORDER.value
            lifecycle.save()

    def pretreatment(self, request):
        """
        创建工单 参数预处理
        """
        request_data = dict(request.data)
        alerts = request_data.pop("alert", [])
        if isinstance(alerts, str):
            alerts = [alerts]
        collect = hash_md5(str(sorted(alerts)))
        params = []
        for alert in alerts:
            data = QueryDict(mutable=True)
            for k, v in request_data.items():
                v = v[0] if isinstance(v, list) else v
                data[k] = v
            data["alert"] = alert
            data["collect"] = collect
            params.append(data)
        return params


class EmailNotificationAPIView(GenericAPIView):
    queryset = EmailNotification.objects.all()
    serializer_class = NotificationModelSerializer
    filter_backends = [DjangoFilterBackend]
    pagination_class = LimitOffsetPage

    # permission_classes = [IsAuthenticated, ]

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
        return self.queryset.filter(email=self.request.user.email)
