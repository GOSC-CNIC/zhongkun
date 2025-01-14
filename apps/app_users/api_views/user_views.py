from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from core import errors
from utils.paginators import NoPaginatorInspector
from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import NewPageNumberPagination100
from apps.app_users import serializers
from apps.app_users.managers import filter_user_queryset
from apps.app_service.models import DataCenter as Organization


class UserViewSet(CustomGenericViewSet):
    """
    用户视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination100

    @swagger_auto_schema(
        operation_summary=gettext_lazy('获取用户个人信息'),
        paginator_inspectors=[NoPaginatorInspector],
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
              "fullname": "张三",
              "is_fed_admin": true, # true(联邦管理员)
              "organization": {
                "id": "xx",
                "name": "xx",
                "name_en": "xx"
              }
            }
        """
        serializer = serializers.UserSerializer(instance=request.user)
        return Response(data=serializer.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('更改用户的机构'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='organization_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('机构ID，空值表示清除机构')
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['post'], detail=False, url_path='change-org', url_name='change-org')
    def change_org(self, request, *args, **kwargs):
        """
        更改用户的机构

            Http Code: 状态码200，返回数据：
            {
              "id": "c172f4b8-984d-11eb-b920-90b11c06b9df",
              "username": "admin",
              "fullname": "张三",
              "is_fed_admin": true, # true(联邦管理员)
              "organization": {
                "id": "xx",
                "name": "xx",
                "name_en": "xx"
              }
            }
        """
        organization_id = request.query_params.get('organization_id')
        if organization_id is None:
            return self.exception_response(
                exc=errors.BadRequest(message=_('必须提交机构ID参数')))

        if organization_id:
            org = Organization.objects.filter(id=organization_id).first()
            if org is None:
                return self.exception_response(
                    exc=errors.InvalidArgument(message=_('机构不存在')))
        else:
            org = None

        user = request.user
        user.organization = org
        user.save(update_fields=['organization'])
        serializer = serializers.UserSerializer(instance=request.user)
        return Response(data=serializer.data)

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
        联邦管理员列举用户

            200 ok:
            {
              "count": 1,
              "page_num": 1,
              "page_size": 100,
              "results": [
                {
                  "id": "1",
                  "username": "shun",
                  "fullname": "",
                  "is_fed_admin": true, # true(联邦管理员)
                  "organization": {
                    "id": "xx",
                    "name": "xx",
                    "name_en": "xx"
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
        queryset = queryset.select_related('organization')
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
