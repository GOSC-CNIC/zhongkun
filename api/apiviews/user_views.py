from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.serializers import serializers
from service.managers import ServiceManager
from api.paginations import DefaultPageNumberPagination
from users.managers import filter_user_queryset
from core import errors


class UserViewSet(CustomGenericViewSet):
    """
    用户视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination

    @swagger_auto_schema(
        operation_summary=gettext_lazy('获取用户个人信息'),
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='account', url_name='account')
    def account(self, request, *args, **kwargs):
        """
        获取用户个人信息

            Http Code: 状态码200，返回数据：
            {
              "id": "c172f4b8-984d-11eb-b920-90b11c06b9df",
              "username": "admin",
              "fullname": "",
              "role": {
                "role": [
                  "ordinary", "vms-admin", "storage-admin", "federal-admin"
                ]
              }
            }

        """
        serializer = serializers.UserSerializer(instance=request.user)
        return Response(data=serializer.data)

    swagger_auto_schema(
        operation_summary=gettext_lazy('获取用户角色和权限策略信息'),
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='permission-policy', url_name='permission-policy')
    def permission_policy(self, request, *args, **kwargs):
        """
         获取用户角色和权限策略信息

            200 ok:
            {
              "role": "federal-admin",      # 'ordinary': 普通用户；'federal-admin': 联邦管理员
              "vms": {                      # 有管理员权限的接入服务id
                "role": "admin",
                "service_ids": [
                  "2"
                ]
              }
            }
        """
        user = request.user
        qs = ServiceManager().get_has_perm_service(user)
        service_ids = list(qs.values_list('id', flat=True))
        role = user.Roles.ORDINARY.value
        if user.is_federal_admin():
            role = user.Roles.FEDERAL.value
        data = {
            'role': role,
            'vms': {
                'role': 'admin',
                'service_ids': service_ids
            }
        }
        return Response(data=data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户'),
        manual_parameters=[
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('关键字查询，用户名')
            ),
            openapi.Parameter(
                name='federal_admin',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description=gettext_lazy('联邦管理员用户角色查询')
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        联邦管理元列举用户

            200 ok:
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "1",
                  "username": "shun",
                  "fullname": "",
                  "role": {
                    "role": ["ordinary", "federal-admin"]
                  }
                }
              ]
            }
        """
        search = request.query_params.get('search', None)
        federal_admin = request.query_params.get('federal_admin', None)

        if federal_admin:
            federal_admin = federal_admin.lower()
            if federal_admin == 'true':
                federal_admin = True
            elif federal_admin == 'false':
                return self.exception_response(
                    exc=errors.InvalidArgument(message=_("false不支持")))
            else:
                return self.exception_response(
                    exc=errors.InvalidArgument(message=_('参数“federal_admin”的值无效。')))
        else:
            federal_admin = None

        if not request.user.is_federal_admin():
            return self.exception_response(
                exc=errors.AccessDenied(message=_('你没有访问权限。')))

        queryset = filter_user_queryset(search=search, is_federal_admin=federal_admin)
        paginator = self.paginator
        try:
            page = paginator.paginate_queryset(queryset, request, view=self)
            serializer = self.get_serializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return self.exception_response(errors.convert_to_error(exc))

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.UserSerializer

        return Serializer
