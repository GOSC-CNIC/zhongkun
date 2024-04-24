from rest_framework.generics import GenericAPIView
from apps.app_netflow.models import ChartModel
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import RoleModel
from apps.app_netflow.serializers import ChartModelSerializer
from apps.app_netflow.serializers import MenuModelSerializer
from apps.app_netflow.serializers import TrafficSerializer
from django_filters.rest_framework import DjangoFilterBackend
from apps.app_netflow.filters import ChartFilter
from apps.app_netflow.filters import MenuFilter
from apps.app_netflow.pagination import LimitOffsetPage
from apps.app_netflow.permission import CustomPermission
# from apps.app_netflow.permission import MenuPermission
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


# Create your views here.

class MenuAPIView(GenericAPIView):
    queryset = MenuModel.objects.all().filter(id='0')
    serializer_class = MenuModelSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = MenuFilter
    pagination_class = LimitOffsetPage

    permission_classes = [CustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询菜单栏'),
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
            return self.get_paginated_response(self.response(serializer.data))

        serializer = self.get_serializer(queryset, many=True)
        return Response(self.response(serializer.data))

    def response(self, data):
        data = data[0]
        return data.get('sub_categories')

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


class ChartAPIView(GenericAPIView, CreateModelMixin):
    queryset = ChartModel.objects.all()
    serializer_class = ChartModelSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ChartFilter
    pagination_class = LimitOffsetPage
    permission_classes = [CustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询菜单的图表列表'),
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
        operation_summary=gettext_lazy('创建图表'),
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


class TrafficAPIView(APIView, ):
    permission_classes = [CustomPermission]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询流量数据'),
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
        from apps.app_netflow.handlers.easyops import EasyOPS
        from django.forms.models import model_to_dict
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
