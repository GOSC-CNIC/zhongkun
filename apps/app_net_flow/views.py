import json
import time
from rest_framework.generics import GenericAPIView
from apps.app_net_flow.models import ChartModel
from apps.app_net_flow.models import Menu2Chart
from apps.app_net_flow.models import Menu2Member
from apps.app_net_flow.models import MenuModel
from apps.app_net_flow.models import GlobalAdminModel
from apps.app_net_flow.serializers import ChartSerializer
from apps.app_net_flow.serializers import Menu2ChartSerializer
from apps.app_net_flow.serializers import GlobalAdminSerializer
from apps.app_net_flow.serializers import GlobalAdminWriteSerializer
from apps.app_net_flow.serializers import Menu2MemberSerializer
from apps.app_net_flow.serializers import Menu2MemberWriteSerializer
from apps.app_net_flow.serializers import MenuModelSerializer
from apps.app_net_flow.serializers import MenuWriteSerializer
from apps.app_net_flow.serializers import Menu2ChartWriteSerializer
from apps.app_net_flow.serializers import TrafficSerializer
from django_filters.rest_framework import DjangoFilterBackend
from apps.app_net_flow.filters import MenuFilter
from apps.app_net_flow.filters import ChartFilter
from apps.app_net_flow.filters import Menu2ChartFilter
from apps.app_net_flow.filters import Menu2MemberFilter
from apps.app_net_flow.filters import GlobalAdminFilter
from apps.app_net_flow.pagination import LimitOffsetPage
from apps.app_net_flow.pagination import Menu2ChartListLimitOffsetPage
from apps.app_net_flow.permission import CustomPermission
from apps.app_net_flow.permission import PortListCustomPermission
from apps.app_net_flow.permission import MenuListCustomPermission
from apps.app_net_flow.permission import MenuDetailCustomPermission
from apps.app_net_flow.permission import Menu2ChartListCustomPermission
from apps.app_net_flow.permission import Menu2ChartDetailCustomPermission
from apps.app_net_flow.permission import Menu2MemberListCustomPermission
from apps.app_net_flow.permission import Menu2MemberDetailCustomPermission
from apps.app_net_flow.permission import GlobalAdministratorCustomPermission
from apps.app_net_flow.permission import TrafficCustomPermission
from rest_framework.response import Response
from rest_framework.mixins import CreateModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin
from rest_framework.mixins import DestroyModelMixin
from rest_framework import status as status_code
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.utils.translation import gettext_lazy
from apps.app_net_flow.handlers.easyops import EasyOPS
from django.forms.models import model_to_dict
from django.http import QueryDict
from apps.app_net_flow.permission import PermissionManager


# Create your views here.
class GlobalUserRoleAPIView(APIView):
    permission_classes = [CustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询当前用户的角色'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request):
        """
        查询当前用户的角色
            super-admin    流量模块超级管理员
            admin          流量模块运维管理员
            group-admin   流量模块组管理员
            ordinary      流量模块组员
        """
        result = PermissionManager(request).get_user_role()
        return Response({"role": result})


class MenuListGenericAPIView(GenericAPIView):
    queryset = MenuModel.objects.all()
    serializer_class = MenuModelSerializer
    permission_classes = [MenuListCustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询当前用户权限内的分组列表'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request):
        queryset = self.get_queryset().values('id', 'name', 'father_id', 'level', 'sort_weight', 'remark')
        result = self.filter_queryset(queryset)
        return Response({
            'count': len(result),
            "results": result}
        )

    def filter_queryset(self, queryset):
        perm = PermissionManager(request=self.request)
        """
        超级管理员和运维管理员 返回所有分组集合
        组管理员和组员返回 所在的分组集合
        """
        if perm.is_global_super_admin_or_ops_admin():
            nodes = queryset
        else:
            nodes = [_.__dict__ for _ in perm.get_relation_group_set()]
        result = perm.generate_group_tree('root', nodes)
        return result

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建分组'),
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
        serializer.save()

    def get_success_headers(self, data):
        try:
            return {'Location': str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            return {}


class MenuDetailGenericAPIView(GenericAPIView, RetrieveModelMixin, DestroyModelMixin, UpdateModelMixin):
    queryset = MenuModel.objects.all().exclude(id='root')
    serializer_class = MenuWriteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MenuFilter
    pagination_class = LimitOffsetPage
    permission_classes = [MenuDetailCustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询指定分组'),
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
        operation_summary=gettext_lazy('修改指定分组'),
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

    def perform_update(self, serializer):
        serializer.save()

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除指定分组'),
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

    def perform_destroy(self, instance):
        instance.delete()


class PortListGenericAPIView(GenericAPIView, ):
    queryset = ChartModel.objects.all()
    serializer_class = ChartSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ChartFilter
    pagination_class = LimitOffsetPage
    permission_classes = [PortListCustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询端口列表'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('新增端口'),
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
        serializer.save()

    def get_success_headers(self, data):
        try:
            return {'Location': str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            return {}


class Menu2ChartListGenericAPIView(GenericAPIView, CreateModelMixin):
    queryset = Menu2Chart.objects.all()
    serializer_class = Menu2ChartSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = Menu2ChartFilter
    pagination_class = Menu2ChartListLimitOffsetPage
    permission_classes = [Menu2ChartListCustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询组内元素列表'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page and isinstance(page[0], str):
            page = self.get_queryset().filter(id__in=page)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('添加组内元素'),
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


class Menu2ChartDetailGenericAPIView(GenericAPIView, RetrieveModelMixin, DestroyModelMixin, UpdateModelMixin):
    queryset = Menu2Chart.objects.all()
    serializer_class = Menu2ChartWriteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = Menu2ChartFilter
    pagination_class = LimitOffsetPage
    permission_classes = [Menu2ChartDetailCustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询组内指定元素信息'),
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
        operation_summary=gettext_lazy('修改组内指定元素信息'),
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

    def perform_update(self, serializer):
        serializer.save()

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除组内指定元素'),
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

    def perform_destroy(self, instance):
        instance.delete()


class Menu2MemberListGenericAPIView(GenericAPIView, CreateModelMixin):
    queryset = Menu2Member.objects.all()
    serializer_class = Menu2MemberSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = Menu2MemberFilter
    pagination_class = LimitOffsetPage
    permission_classes = [Menu2MemberListCustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询组内成员列表'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('添加组内成员'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def post(self, request, *args, **kwargs):
        """
        可批量添加成员
        """
        raw, params = self.pretreatment(request)
        serializers = list()
        for param in params:
            serializer = self.get_serializer(data=param)
            serializer.is_valid(raise_exception=True)
            serializers.append(serializer)
        for serializer in serializers:
            self.perform_create(serializer)
        return Response(raw, status=status_code.HTTP_201_CREATED, )

    def perform_create(self, serializer):
        context = serializer.context
        request = context.get('request')  # 邀请人
        serializer.save(inviter=request.user.username)

    def pretreatment(self, request):
        """
        参数与处理
        """
        import copy
        request_data = dict(request.data)
        raw = copy.deepcopy(request_data)
        members = request_data.pop("member") or []
        if isinstance(members, str):
            members = [members]
        params = []
        for member in members:
            data = QueryDict(mutable=True)
            for k, v in request_data.items():
                v = v[0] if isinstance(v, list) else v
                data[k] = v
            data["member"] = member
            params.append(data)
        return raw, params


class Menu2MemberDetailGenericAPIView(GenericAPIView, RetrieveModelMixin, DestroyModelMixin, UpdateModelMixin):
    queryset = Menu2Member.objects.all()
    serializer_class = Menu2MemberWriteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = Menu2MemberFilter
    pagination_class = LimitOffsetPage
    permission_classes = [Menu2MemberDetailCustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询组内指定成员信息'),
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
        operation_summary=gettext_lazy('修改组内指定成员角色'),
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

    def perform_update(self, serializer):
        serializer.save()

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除组内指定成员'),
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

    def perform_destroy(self, instance):
        instance.delete()


class GlobalAdministratorListGenericAPIView(GenericAPIView, CreateModelMixin):
    queryset = GlobalAdminModel.objects.all()
    serializer_class = GlobalAdminSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = GlobalAdminFilter
    pagination_class = LimitOffsetPage
    permission_classes = [GlobalAdministratorCustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询全局管理员列表'),
        manual_parameters=[
        ],
        responses={
            200: ""
        }
    )
    def get(self, request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('添加全局管理员'),
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
        return Response(serializer.data, status=status_code.HTTP_201_CREATED, )

    def perform_create(self, serializer):
        context = serializer.context
        request = context.get('request')  # 邀请人
        serializer.save(inviter=request.user.username)


class GlobalAdministratorDetailGenericAPIView(GenericAPIView, RetrieveModelMixin, DestroyModelMixin, UpdateModelMixin):
    queryset = GlobalAdminModel.objects.all()
    serializer_class = GlobalAdminWriteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = GlobalAdminFilter
    pagination_class = LimitOffsetPage
    permission_classes = [GlobalAdministratorCustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询指定管理员信息'),
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
        operation_summary=gettext_lazy('修改指定管理员角色'),
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

    def perform_update(self, serializer):
        serializer.save()

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除指定管理员'),
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

    def perform_destroy(self, instance):
        instance.delete()


class TrafficAPIView(APIView, ):
    permission_classes = [TrafficCustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询指定端口流量数据'),
        manual_parameters=[
            openapi.Parameter(name='start',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_INTEGER,
                              required=True,
                              description='起始时间戳'),
            openapi.Parameter(name='end',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_INTEGER,
                              required=True,
                              description='结束时间戳'),
            openapi.Parameter(name='chart',
                              in_=openapi.IN_QUERY,
                              type=openapi.TYPE_INTEGER,
                              required=True,
                              description='图表ID')
        ],
        responses={
            200: ""
        }
    )
    def post(self, request):
        serializer = TrafficSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response = self.download(**serializer.data)
        return Response(response)

    def download(self, *args, **kwargs):
        start = kwargs.get('start')
        end = kwargs.get('end')
        metrics_ids = kwargs.get('metrics_ids')
        chart = ChartModel.objects.filter(id=kwargs.get('chart')).first()
        return EasyOPS().traffic(
            chart=model_to_dict(chart),
            metrics_ids=metrics_ids,
            start=start,
            end=end,
        )
