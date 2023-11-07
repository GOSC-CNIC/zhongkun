from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from core import errors as exceptions
from api.paginations import NewPageNumberPagination
from api.viewsets import NormalGenericViewSet, serializer_error_msg
from service.models import OrgDataCenter
from .. import serializers as dcserializers
from ..handlers.org_data_center_handlers import OrgDataCenterHandler


class OrgDataCenterViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举数据中心'),
        manual_parameters=NormalGenericViewSet.PARAMETERS_AS_ADMIN,
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """"
        列举数据中心

        {
          "id": "tzo5vc107vksb9nszbufo1dp7",
          "name": "ttt",
          "name_en": "string",
          "organization": [
            {
              "id": "jzddosfo44z0gc1c4hdk980q9",
              "name": "obj"
            }
          ],
          "users": [
            {
              "id": "ivugx4m7q410qwh6zznsnanjy",
              "username": "wanghuang"
            }
          ],
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

        """

        try:
            queryset = OrgDataCenter.objects.order_by('-creation_time')
            orgs = self.paginate_queryset(queryset)
            serializer = dcserializers.OrgDataCenterSerializer(orgs, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建数据中心'),
        manual_parameters=NormalGenericViewSet.PARAMETERS_AS_ADMIN,
        responses={
            200: ''''''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建数据中心
        http code 200
            {
              "name": "测试1",
              "name_en": "test1",
              "organization": "obj",
              "users": [
                "wanghuang"
              ],
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
            raise exceptions.BadRequest(msg)

        valid_data = serializer.validated_data
        u = valid_data.get('users', 'None')
        if not u:
            return self.exception_response(exceptions.ValidationError(message='users不能为空'))

        user_list = u.split(',')
        try:
            org_data_center_obj = OrgDataCenterHandler().create_org_dc(user_list=user_list,
                                                                       valid_data=valid_data)

        except exceptions.Error as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        data = dcserializers.OrgDataCenterCreateSerializer(instance=org_data_center_obj).data
        data['users'] = user_list
        data['id'] = org_data_center_obj.id

        return Response(data=data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改数据中心'),
        manual_parameters=NormalGenericViewSet.PARAMETERS_AS_ADMIN + [

        ],
        responses={
            200: ''''''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        修改数据中心

        {
          "name": "测试1",
          "name_en": "test1",
          "organization": "obj",
          "users": [
            "wanghuang"
          ],
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
        id = kwargs[self.lookup_field]

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise exceptions.BadRequest(msg)

        valid_data = serializer.validated_data
        users = valid_data.get('users', 'None')
        if not users:
            return self.exception_response(exceptions.ValidationError(message='users不能为空'))
        user_list = users.split(',')

        try:
            org_data_center_obj = OrgDataCenterHandler().update_org_dc(user_list=user_list,
                                                                       valid_data=valid_data, update_id=id)

        except exceptions.Error as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        data = dcserializers.OrgDataCenterCreateSerializer(instance=org_data_center_obj).data
        data['users'] = user_list
        data['id'] = org_data_center_obj.id

        return Response(data=data)

    def get_serializer_class(self):
        if self.action == 'list':
            return dcserializers.OrgDataCenterSerializer
        elif self.action in ['create', 'update']:
            return dcserializers.OrgDataCenterCreateSerializer

        return Serializer
