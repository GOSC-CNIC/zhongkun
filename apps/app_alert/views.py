import copy
import json
import time
from rest_framework.generics import GenericAPIView
from django.utils.translation import gettext_lazy
from apps.app_alert.filters import AlertFilterBackend
from apps.app_alert.models import AlertModel
from apps.app_alert.models import ResolvedAlertModel
from apps.app_alert.models import AlertWorkOrder
from apps.app_alert.models import TicketResolutionCategory
from apps.app_alert.models import TicketResolution
from apps.app_alert.models import AlertTicket
from rest_framework.views import APIView
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from apps.app_alert.handlers.receiver import AlertReceiver
from apps.app_alert.pagination import LimitOffsetPage
from apps.app_alert.pagination import CustomAlertCursorPagination
from django_filters.rest_framework import DjangoFilterBackend
from apps.app_alert.handlers.handlers import AlertChoiceHandler
from rest_framework.mixins import CreateModelMixin
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin
from rest_framework.mixins import DestroyModelMixin
from apps.app_alert.serializers import WorkOrderSerializer
from apps.app_alert.serializers import NotificationModelSerializer
from apps.app_alert.serializers import TicketResolutionCategorySerializer
from apps.app_alert.serializers import TicketResolutionCategoryRelationSerializer
from apps.app_alert.serializers import BelongedServiceSerializer
from apps.app_alert.serializers import TicketResolutionSerializer
from apps.app_alert.serializers import AlertTicketSerializer
from apps.app_alert.filters import WorkOrderFilter
from apps.app_alert.filters import TicketResolutionCategoryFilter
from apps.app_alert.filters import TicketResolutionFilter
from apps.app_alert.filters import AlertTicketFilter
from rest_framework import status as status_code
from rest_framework.exceptions import PermissionDenied
from apps.app_alert.models import EmailNotification
from django.db.models import Q
from apps.app_alert.handlers.handlers import EmailNotificationCleaner
from apps.app_alert.permission import ReceiverPermission
from apps.app_alert.handlers.handlers import UserMonitorUnit
from apps.app_alert.utils.utils import DateUtils
from django.db.utils import IntegrityError
from django.forms.models import model_to_dict
from apps.app_alert.utils import errors
from apps.app_alert.serializers import AlertModelSerializer
from collections import OrderedDict
from rest_framework.permissions import IsAuthenticated
from core.aai.authentication import CreateUserJWTAuthentication
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from apps.app_alert.handlers.ticket import has_service_permission
from apps.app_alert.models import ServiceAdminUser
from apps.app_alert.serializers import ServiceAdminUserSerializer
from apps.app_alert.filters import ServiceAdminUserFilter
from apps.app_alert.handlers.handlers import move_to_resolved


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


class TicketResolutionHistoryListAPIView(GenericAPIView, ListModelMixin):
    """
    查询告警工单解决方案历史数据
    """
    queryset = TicketResolutionCategory.objects.all()
    serializer_class = TicketResolutionCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TicketResolutionCategoryFilter
    pagination_class = LimitOffsetPage
    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询告警工单解决方案历史数据'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request, *args, **kwargs):
        if not has_service_permission(service_name=request.query_params.get('service'), user=request.user):
            raise PermissionDenied()
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = TicketResolutionCategoryRelationSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TicketResolutionCategoryRelationSerializer(queryset, many=True)
        return Response(serializer.data)


class TicketResolutionCategoryListGenericAPIView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    创建告警工单 解决方案类型
    """
    queryset = TicketResolutionCategory.objects.all()
    serializer_class = TicketResolutionCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TicketResolutionCategoryFilter
    pagination_class = LimitOffsetPage
    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建工单解决方案类型'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status_code.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        service_name = serializer.validated_data.get('service')
        if not has_service_permission(service_name=service_name, user=self.request.user):
            raise PermissionDenied()
        serializer.save()


class TicketResolutionCategoryDetailGenericAPIView(
    GenericAPIView,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin
):
    """
    告警工单 解决方案 类型
    """
    queryset = TicketResolutionCategory.objects.all()
    serializer_class = TicketResolutionCategorySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TicketResolutionCategoryFilter
    pagination_class = LimitOffsetPage
    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询指定工单解决方案类型'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_service_permission(service_name=instance.service, user=request.user):
            raise PermissionDenied()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改指定工单解决方案类型'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def put(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        if not has_service_permission(service_name=instance.service, user=request.user):
            raise PermissionDenied()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除指定工单解决方案类型'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_service_permission(service_name=instance.service, user=request.user):
            raise PermissionDenied()
        self.perform_destroy(instance)
        return Response(status=status_code.HTTP_204_NO_CONTENT)


class TicketResolutionListGenericAPIView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    告警工单 解决方案
    列表查询，创建
    """
    queryset = TicketResolution.objects.all()
    serializer_class = TicketResolutionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TicketResolutionFilter
    pagination_class = LimitOffsetPage
    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建工单解决方案'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status_code.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        category = serializer.validated_data.get('category')
        if not has_service_permission(service_name=category.service, user=self.request.user):
            raise PermissionDenied()
        serializer.save()


class TicketResolutionDetailGenericAPIView(
    GenericAPIView,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin
):
    """
    告警工单 解决方案
    """
    queryset = TicketResolution.objects.all()
    serializer_class = TicketResolutionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = TicketResolutionFilter
    pagination_class = LimitOffsetPage
    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询指定工单解决方案'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_service_permission(service_name=instance.category.service, user=request.user):
            raise PermissionDenied()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改指定工单解决方案'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def put(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        if not has_service_permission(service_name=instance.category.service, user=request.user):
            raise PermissionDenied()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除指定工单解决方案'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        if not has_service_permission(service_name=instance.category.service, user=request.user):
            raise PermissionDenied()
        self.perform_destroy(instance)
        return Response(status=status_code.HTTP_204_NO_CONTENT)


class AlertTicketListGenericAPIView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    查询工单列表
    创建新的工单
    """
    queryset = AlertTicket.objects.all()
    serializer_class = AlertTicketSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AlertTicketFilter
    pagination_class = LimitOffsetPage
    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询告警工单列表'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def filter_queryset(self, queryset):
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)
        user = self.request.user
        service_admin_queryset = ServiceAdminUser.objects.filter(userprofile=user)
        service_list = list()
        for obj in service_admin_queryset:
            service = obj.service
            service_list.append(service.name_en)
        return queryset.filter(service__in=service_list)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建告警工单'),
        # manual_parameters=[
        # ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['service', 'alerts'],
            properties={
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='工单标题'),
                'description': openapi.Schema(type=openapi.TYPE_STRING, description='工单描述'),
                'severity': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='严重程度，critical(严重),high(高),normal(一般),low(低),verylow(很低)'),
                'status': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='工单状态，open(打开), progress(处理中), closed(结束)'),
                'assigned_to': openapi.Schema(type=openapi.TYPE_STRING, description='处理人id'),
                'resolution': openapi.Schema(type=openapi.TYPE_STRING, description='解决方案id'),
                'service': openapi.Schema(type=openapi.TYPE_STRING, description='所属的服务名称'),
                'alerts': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Items(type=openapi.TYPE_STRING),
                    description='关联的告警'

                )
            },
        ),
        responses={
            200: ""
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        service_serializer = BelongedServiceSerializer(data=self.request.data)
        service_serializer.is_valid(raise_exception=True)
        service = service_serializer.data.get('alerts')
        # 用户权限验证
        if not has_service_permission(service_name=service.name_en, user=self.request.user):
            raise PermissionDenied()

        # 告警是否已经存在工单
        alert_object_list = list()
        for alert in self.request.data.get('alerts'):
            obj = AlertModel.objects.filter(id=alert).first()
            if not obj:
                raise errors.InvalidArgument(f'invalid alert:{alert}')
            if obj.ticket:
                raise errors.InvalidArgument(f'work order already exists')
            alert_object_list.append(obj)
        # 保存工单
        ticket = serializer.save(
            submitter=self.request.user,
            service=service.name_en,
        )
        # 告警关联工单
        for obj in alert_object_list:
            obj.ticket = ticket
            obj.save()
            if ticket.resolution:  # 已经填写解决方案
                obj.recovery = DateUtils.timestamp()
                obj.status = AlertModel.AlertStatus.RESOLVED.value
                ticket.status = AlertTicket.Status.CLOSED.value
                ticket.save()
                obj.save()
                if obj.type == AlertModel.AlertType.LOG.value:  # 日志类 归入 已恢复队列
                    move_to_resolved(obj)
        return Response(serializer.data, status=status_code.HTTP_201_CREATED)


class AlertTicketDetailGenericAPIView(
    GenericAPIView,
    RetrieveModelMixin,
    UpdateModelMixin,
    DestroyModelMixin
):
    """
    告警工单
    列表查询，创建
    """
    queryset = AlertTicket.objects.all()
    serializer_class = AlertTicketSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AlertTicketFilter
    pagination_class = LimitOffsetPage
    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询指定告警工单'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改指定告警工单'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def put(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除指定告警工单'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def delete(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status_code.HTTP_204_NO_CONTENT)


class WorkOrderListGenericAPIView(GenericAPIView, CreateModelMixin):
    queryset = AlertWorkOrder.objects.all()
    serializer_class = WorkOrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = WorkOrderFilter
    pagination_class = LimitOffsetPage
    permission_classes = [IsAuthenticated, ]

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
                      "creator": "xxx"
                    }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status_code.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        user_monitor_units = UserMonitorUnit(self.request)
        alert_list = self.request.data.get("alert")
        if not alert_list:
            raise errors.InvalidArgument(detail=f'alert argument is required')
        for alert_id in alert_list:
            alert = AlertModel.objects.filter(id=alert_id).first()
            if not alert:
                raise errors.InvalidArgument(detail=f'invalid alert_id :{alert_id}')
            if alert.order:
                raise errors.InvalidArgument(detail=f'alert:{alert_id} existed order')

            if alert.fingerprint not in user_monitor_units.url_hash_list and alert.cluster not in user_monitor_units.clusters and not self.request.user.is_superuser:
                raise PermissionDenied()
        order = serializer.save(
            creator=self.request.user,
            creation=DateUtils.timestamp(),
            modification=DateUtils.timestamp(),
        )
        for alert_id in alert_list:
            alert_object = AlertModel.objects.filter(id=alert_id).first()
            if alert_object:
                alert_object.order = order
                alert_object.recovery = order.creation
                alert_object.status = AlertModel.AlertStatus.RESOLVED.value
                alert_object.save()

            if alert_object.type == AlertModel.AlertType.LOG.value:  # 日志类 归入 已恢复队列
                item = model_to_dict(alert_object)
                item["id"] = alert_object.id
                item["modification"] = order.creation
                item['order'] = order
                try:
                    ResolvedAlertModel.objects.create(**item)
                except IntegrityError as e:
                    pass
                alert_object.delete()


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
        return self.queryset.filter(email=self.request.user.email)


class AlertServiceAPIView(APIView):
    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询告警列表所属的服务'),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['alerts'],
            properties={
                'alerts': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING))
            },
        ),
        responses={
            200: json.dumps({'service': "server_name"}),
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = BelongedServiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = serializer.data.get('alerts')
        service_user = service.users.filter(username=request.user.username)
        if not service_user:
            raise PermissionDenied()
        return Response({"service": service.name_en})


class AlertServiceAdminListGenericAPIView(GenericAPIView, ListModelMixin, CreateModelMixin):
    queryset = ServiceAdminUser.objects.all()
    serializer_class = ServiceAdminUserSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ServiceAdminUserFilter
    pagination_class = LimitOffsetPage
    permission_classes = [IsAuthenticated, ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务的管理员列表'),
        manual_parameters=[
        ],
        responses={
        }
    )
    def get(self, request, *args, **kwargs):
        if not has_service_permission(service_name=request.query_params.get('service'), user=request.user):
            raise PermissionDenied()
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    # def create(self, request, *args, **kwargs):
    #     serializer = self.get_serializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_create(serializer)
    #     headers = self.get_success_headers(serializer.data)
    #     return Response(serializer.data, status=status_code.HTTP_201_CREATED, headers=headers)
    #
    # def perform_create(self, serializer):
    #     serializer.save()
