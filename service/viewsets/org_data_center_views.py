from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core import errors as exceptions
from api.paginations import NewPageNumberPagination100
from api.viewsets import NormalGenericViewSet, serializer_error_msg
from service.models import OrgDataCenter
from service.odc_manager import OrgDataCenterManager
from .. import serializers as dcserializers


class AdminOrgDataCenterViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员列举数据中心'),
        manual_parameters=[
            openapi.Parameter(
                name='org_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('机构ID')
            ),
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('关键字查询，名称和备注信息')
            ),
        ],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        管理员列举数据中心，联邦管理员查询所有，数据中心管理员只查询有权限的数据中心

            {
                "count": 1,
                "page_num": 1,
                "page_size": 20,
                "results": [
                    {
                      "id": "tzo5vc107vksb9nszbufo1dp7",
                      "name": "ttt",
                      "name_en": "string",
                      "organization":  {         # 机构
                          "id": "jzddosfo44z0gc1c4hdk980q9",
                          "name": "obj",
                          "name_en": "xxx"
                        },
                      "longitude": 0,
                      "latitude": 0,
                      "creation_time": "2023-11-06T05:40:20.201159Z",
                      "sort_weight": 0,
                      "remark": "string",
                      "thanos_endpoint_url": "https://xxxxx.com",
                      "thanos_username": "string",
                      "thanos_password": "xxxxxx",
                      "thanos_receive_url": "https://xxxxx.com",
                      "thanos_remark": "string",
                      "loki_endpoint_url": "https://xxxxx.com",
                      "loki_username": "string",
                      "loki_password": "string",
                      "loki_receive_url": "string",
                      "loki_remark": "string"
                    }
                ]
            }
        """
        admin_user = request.user
        org_id = request.query_params.get('org_id', None)
        search = request.query_params.get('search', None)

        try:
            queryset = OrgDataCenterManager.get_odc_queryset(org_id=org_id, search=search)
            if not admin_user.is_federal_admin():
                queryset = queryset.filter(users__id=admin_user.id)

            orgs = self.paginate_queryset(queryset)
            serializer = self.get_serializer(orgs, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员创建数据中心'),
        responses={
            200: ''''''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        管理员创建数据中心，暂时只允许联邦管理员创建

            http code 200
                {
                  "name": "测试1",
                  "name_en": "test1",
                  "organization": {
                    "id": "jzddosfo44z0gc1c4hdk980q9",
                    "name": "测试1"
                  },
                  "longitude": 0,
                  "latitude": 0,
                  "sort_weight": 0,
                  "remark": "",
                  "thanos_endpoint_url": "",
                  "thanos_username": "",
                  "thanos_password": "",
                  "thanos_receive_url": "",
                  "thanos_remark": "",
                  "loki_endpoint_url": "",
                  "loki_username": "",
                  "loki_password": "",
                  "loki_receive_url": "",
                  "loki_remark": "",
                  "id": "5563vam9q6e7tz9fw3kij5p51"
                }

                http code 400, 401, 404：
                {
                    "code": "BadRequest",
                    "message": ""
                }
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return self.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        try:
            if not request.user.is_federal_admin():
                raise exceptions.AccessDenied(message=_('您没有创建数据中心的权限'))

            self.validate_org_id(org_id=data['organization_id'])
            odc = OrgDataCenterManager.create_org_dc(
                name=data['name'], name_en=data['name_en'], organization_id=data['organization_id'],
                longitude=data['longitude'], latitude=data['latitude'],
                sort_weight=data['sort_weight'], remark=data['remark'],
                thanos_endpoint_url=data['thanos_endpoint_url'], thanos_receive_url=data['thanos_receive_url'],
                thanos_username=data['thanos_username'], thanos_password=data['thanos_password'],
                thanos_remark=data['thanos_remark'],
                loki_endpoint_url=data['loki_endpoint_url'], loki_receive_url=data['loki_receive_url'],
                loki_username=data['loki_username'], loki_password=data['loki_password'],
                loki_remark=data['loki_remark']
            )
        except exceptions.Error as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        data = dcserializers.OrgDataCenterSerializer(instance=odc).data
        return Response(data=data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员修改数据中心'),
        responses={
            200: ''''''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        管理员修改数据中心，暂时只允许联邦管理员修改

            http code 200
                {
                  "name": "测试1",
                  "name_en": "test1",
                  "organization":{
                      "id": "skki2uhd4jyg47shvmh0uyo4h",
                      "name": "测试1",
                      "name_en": "xxx"
                    },
                  "longitude": 0,
                  "latitude": 0,
                  "sort_weight": 0,
                  "remark": "",
                  "thanos_endpoint_url": "",
                  "thanos_username": "",
                  "thanos_password": "",
                  "thanos_receive_url": "",
                  "thanos_remark": "",
                  "loki_endpoint_url": "",
                  "loki_username": "",
                  "loki_password": "",
                  "loki_receive_url": "",
                  "loki_remark": "xxxxx",
                  "id": "5563vam9q6e7tz9fw3kij5p51"
                }

                http code 400, 401, 404：
                {
                    "code": "BadRequest",
                    "message": ""
                }
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return self.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        try:
            self.validate_org_id(org_id=data['organization_id'])
            odc = OrgDataCenterManager.get_odc(odc_id=kwargs[self.lookup_field])
            if not request.user.is_federal_admin():
                raise exceptions.AccessDenied(message=_('您没有修改数据中心的权限'))

            odc = OrgDataCenterManager.update_org_dc(
                odc_or_id=odc,
                name=data['name'], name_en=data['name_en'], organization_id=data['organization_id'],
                longitude=data['longitude'], latitude=data['latitude'],
                sort_weight=data['sort_weight'], remark=data['remark'],
                thanos_endpoint_url=data['thanos_endpoint_url'], thanos_receive_url=data['thanos_receive_url'],
                thanos_username=data['thanos_username'], thanos_password=data['thanos_password'],
                thanos_remark=data['thanos_remark'],
                loki_endpoint_url=data['loki_endpoint_url'], loki_receive_url=data['loki_receive_url'],
                loki_username=data['loki_username'], loki_password=data['loki_password'],
                loki_remark=data['loki_remark']
            )
        except exceptions.Error as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        data = dcserializers.OrgDataCenterSerializer(instance=odc).data
        return Response(data=data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员查询数据中心详情'),
        responses={
            200: ''''''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        管理员查询数据中心详情，联邦管理员可查所有，数据中心管理员只能查自己有权限的数据中心

            http code 200
                {
                  "id": "5563vam9q6e7tz9fw3kij5p51",
                  "name": "测试1",
                  "name_en": "test1",
                  "organization":{
                      "id": "skki2uhd4jyg47shvmh0uyo4h",
                      "name": "测试1",
                      "name_en": "xxx"
                    },
                  "longitude": 0,
                  "latitude": 0,
                  "sort_weight": 0,
                  "remark": "",
                  "thanos_endpoint_url": "",
                  "thanos_username": "",
                  "thanos_password": "",
                  "thanos_receive_url": "",
                  "thanos_remark": "",
                  "loki_endpoint_url": "",
                  "loki_username": "",
                  "loki_password": "",
                  "loki_receive_url": "",
                  "loki_remark": "xxxxx",
                  "users": [
                    {
                        "id": "xxx",
                        "username": "xxx"
                    }
                  ]
                }

                http code 400, 401, 404：
                {
                    "code": "BadRequest",
                    "message": ""
                }
        """
        try:
            odc = OrgDataCenterManager.get_odc(odc_id=kwargs[self.lookup_field])
            if not self.has_perm_of_odc(odc=odc, user=request.user):
                raise exceptions.AccessDenied(message=_('您没有此数据中心的访问权限'))
        except exceptions.Error as exc:
            return self.exception_response(exc)

        data = self.get_serializer(instance=odc).data
        return Response(data=data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦管理员为数据中心添加管理员'),
        manual_parameters=[
        ],
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='add/admin', url_name='add-admin')
    def add_admin_for_odc(self, request, *args, **kwargs):
        """
        联邦管理员为数据中心添加管理员

            http code 200
                {
                  "id": "5563vam9q6e7tz9fw3kij5p51",
                  "name": "测试1",
                  "name_en": "test1",
                  "organization":{
                      "id": "skki2uhd4jyg47shvmh0uyo4h",
                      "name": "测试1",
                      "name_en": "xxx"
                    },
                  "longitude": 0,
                  "latitude": 0,
                  "sort_weight": 0,
                  "remark": "",
                  "thanos_endpoint_url": "",
                  "thanos_username": "",
                  "thanos_password": "",
                  "thanos_receive_url": "",
                  "thanos_remark": "",
                  "loki_endpoint_url": "",
                  "loki_username": "",
                  "loki_password": "",
                  "loki_receive_url": "",
                  "loki_remark": "xxxxx",
                  "users": [
                    {
                        "id": "xxx",
                        "username": "xxx"
                    }
                  ]
                }

                http code 400, 401, 404：
                {
                    "code": "BadRequest",
                    "message": ""
                }
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return self.exception_response(exceptions.BadRequest(msg))

        usernames = serializer.validated_data['usernames']

        try:
            if not request.user.is_federal_admin():
                raise exceptions.AccessDenied(message=_('您没有数据中心的管理权限'))

            odc = OrgDataCenterManager.get_odc(odc_id=kwargs[self.lookup_field])
            odc = OrgDataCenterManager.add_admins_for_odc(odc=odc, usernames=usernames)
        except exceptions.Error as exc:
            return self.exception_response(exc)

        return Response(data=dcserializers.OrgDataCenterDetailSerializer(odc).data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦管理员从数据中心移除管理员'),
        manual_parameters=[
        ],
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='remove/admin', url_name='remove-admin')
    def remove_admin_from_odc(self, request, *args, **kwargs):
        """
        联邦管理员从数据中心移除管理员

            http code 200
                {
                  "id": "5563vam9q6e7tz9fw3kij5p51",
                  "name": "测试1",
                  "name_en": "test1",
                  "organization":{
                      "id": "skki2uhd4jyg47shvmh0uyo4h",
                      "name": "测试1",
                      "name_en": "xxx"
                    },
                  "longitude": 0,
                  "latitude": 0,
                  "sort_weight": 0,
                  "remark": "",
                  "thanos_endpoint_url": "",
                  "thanos_username": "",
                  "thanos_password": "",
                  "thanos_receive_url": "",
                  "thanos_remark": "",
                  "loki_endpoint_url": "",
                  "loki_username": "",
                  "loki_password": "",
                  "loki_receive_url": "",
                  "loki_remark": "xxxxx",
                  "users": [
                    {
                        "id": "xxx",
                        "username": "xxx"
                    }
                  ]
                }

                http code 400, 401, 404：
                {
                    "code": "BadRequest",
                    "message": ""
                }
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return self.exception_response(exceptions.BadRequest(msg))

        usernames = serializer.validated_data['usernames']

        try:
            if not request.user.is_federal_admin():
                raise exceptions.AccessDenied(message=_('您没有数据中心的管理权限'))

            odc = OrgDataCenterManager.get_odc(odc_id=kwargs[self.lookup_field])
            odc = OrgDataCenterManager.remove_admins_from_odc(odc=odc, usernames=usernames)
        except exceptions.Error as exc:
            return self.exception_response(exc)

        return Response(data=dcserializers.OrgDataCenterDetailSerializer(odc).data)

    @staticmethod
    def validate_org_id(org_id: str):
        try:
            return OrgDataCenterManager.get_org(org_id=org_id)
        except exceptions.TargetNotExist as exc:
            raise exceptions.InvalidArgument(message=_('指定的机构不存在'))

    def get_serializer_class(self):
        if self.action == 'list':
            return dcserializers.OrgDataCenterSerializer
        elif self.action == 'retrieve':
            return dcserializers.OrgDataCenterDetailSerializer
        elif self.action in ['create', 'update']:
            return dcserializers.OrgDataCenterCreateSerializer
        elif self.action in ['add_admin_for_odc', 'remove_admin_from_odc']:
            return dcserializers.UsernamesBodySerializer

        return Serializer

    @staticmethod
    def has_perm_of_odc(odc: OrgDataCenter, user):
        if user.is_federal_admin():
            return True

        if odc.users.filter(id=user.id).exists():
            return True

        return False


class OrgDataCenterViewSet(NormalGenericViewSet):
    permission_classes = []
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举数据中心'),
        manual_parameters=[
            openapi.Parameter(
                name='org_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('机构ID')
            ),
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('关键字查询，名称和备注信息')
            ),
        ],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举数据中心，无需登录

            {
                "count": 1,
                "page_num": 1,
                "page_size": 20,
                "results": [
                    {
                      "id": "tzo5vc107vksb9nszbufo1dp7",
                      "name": "ttt",
                      "name_en": "string",
                      "organization":  {         # 机构
                          "id": "jzddosfo44z0gc1c4hdk980q9",
                          "name": "obj",
                          "name_en": "xxx"
                        },
                      "longitude": 0,
                      "latitude": 0,
                      "creation_time": "2023-11-06T05:40:20.201159Z",
                      "sort_weight": 0,
                      "remark": "string",
                    }
                ]
            }
        """
        org_id = request.query_params.get('org_id', None)
        search = request.query_params.get('search', None)

        try:
            queryset = OrgDataCenterManager.get_odc_queryset(org_id=org_id, search=search)
            orgs = self.paginate_queryset(queryset)
            serializer = self.get_serializer(orgs, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

    def get_serializer_class(self):
        if self.action == 'list':
            return dcserializers.ODCSimpleSerializer

        return Serializer
