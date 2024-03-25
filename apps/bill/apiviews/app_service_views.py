from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.paginations import NewPageNumberPagination
from bill import trade_serializers
from bill.models import PayAppService
from utils.crypto.rsa import generate_rsa_key


class AppRSAKeyViewSet(CustomGenericViewSet):
    """
    app
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('生成一个RSA密钥对'),
        request_body=no_body,
        responses={
            200: ''
        }
    )
    @action(methods=['post'], detail=False, url_path='generate', url_name='generate')
    def generate_rsakey(self, request, *args, **kwargs):
        """
        生成一个RSA密钥对

            http code 200:
            {
              "key_size": 2048,
              "private_key": "-----BEGIN PRIVATE KEY-----xxx-----END PRIVATE KEY-----",
              "public_key": "-----BEGIN PUBLIC KEY-----xxx-----END PUBLIC KEY-----"
            }
        """
        key_size = 2048
        try:
            private_key, public_key = generate_rsa_key(key_size=key_size)
        except Exception as exc:
            return self.exception_response(exc)

        return Response(data={
            'key_size': key_size,
            'private_key': private_key,
            'public_key': public_key
        })

    def get_serializer_class(self):
        return Serializer


class AppServiceViewSet(CustomGenericViewSet):
    """
    app子服务
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举app子服务'),
        manual_parameters=[
            openapi.Parameter(
                name='app_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='查询指定app的子服务'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举所有app子服务

            * 通过科技云通行证jwt和session认证

            http code 200：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 20,
              "results": [
                {
                  "id": "s20220623023119",
                  "name": "怀柔204机房研发测试",
                  "name_en": "怀柔204机房研发测试",
                  "resources": "云主机，云硬盘",
                  "desc": "",
                  "creation_time": "2022-06-23T07:35:44.784474Z",
                  "status": "normal",   # unaudited(未审核); normal(正常); ban(禁止)
                  "longitude": 0,
                  "latitude": 0,
                  "category": "vms-server",
                  "orgnazition": {
                    "id": "o20220623073034",
                    "name": "网络中心",
                    "name_en": "cnic"
                  },
                  "app_id": "20220622082141"
                }
              ]
            }
        """
        app_id = request.query_params.get('app_id', None)

        lookups = {}
        if app_id:
            lookups['app_id'] = app_id

        queryset = PayAppService.objects.select_related(
            'orgnazition'
        ).filter(**lookups)

        try:
            tickets = self.paginate_queryset(queryset=queryset)
            serializer = self.get_serializer(tickets, many=True)
            return self.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return self.exception_response(exc)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举有管理权限的app子服务'),
        manual_parameters=[
            openapi.Parameter(
                name='app_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='查询指定app的子服务'
            ),
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='admin', url_name='admin-list')
    def admin_list(self, request, *args, **kwargs):
        """
        列举有管理权限的 app子服务

            * 通过科技云通行证jwt和session认证
            * 联邦管理员列举所有app子服务

            http code 200：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 20,
              "results": [
                {
                  "id": "s20220623023119",
                  "name": "怀柔204机房研发测试",
                  "name_en": "怀柔204机房研发测试",
                  "resources": "云主机，云硬盘",
                  "desc": "",
                  "creation_time": "2022-06-23T07:35:44.784474Z",
                  "status": "normal",
                  "contact_person": "",
                  "contact_email": "",
                  "contact_telephone": "",
                  "contact_fixed_phone": "",
                  "contact_address": "",
                  "longitude": 0,
                  "latitude": 0,
                  "category": "vms-server",
                  "orgnazition": {
                    "id": "o20220623073034",
                    "name": "网络中心",
                    "name_en": "cnic"
                  },
                  "app_id": "20220622082141"
                }
              ]
            }
        """
        app_id = request.query_params.get('app_id', None)
        user = request.user

        lookups = {}
        if app_id:
            lookups['app_id'] = app_id

        queryset = PayAppService.objects.select_related(
            'orgnazition'
        ).filter(**lookups)

        if not user.is_federal_admin():     # 非联邦管理员只返回有管理权限的
            queryset = queryset.filter(users__id=user.id)

        try:
            tickets = self.paginate_queryset(queryset=queryset)
            serializer = self.get_serializer(tickets, many=True)
            return self.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return self.exception_response(exc)

    def get_serializer_class(self):
        if self.action == 'admin_list':
            return trade_serializers.AppServiceSerializer
        elif self.action == 'list':
            return trade_serializers.AppServiceSimpleSerializer

        return Serializer
