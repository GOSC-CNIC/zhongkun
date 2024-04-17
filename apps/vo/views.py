from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework import status
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import DefaultPageNumberPagination
from apps.vo.models import VoMember
from apps.vo.vo_handler import VoHandler
from apps.vo import vo_serializers


class VOViewSet(CustomGenericViewSet):
    """
    项目组视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举项目组'),
        manual_parameters=[
                              openapi.Parameter(
                                  name='owner',
                                  type=openapi.TYPE_BOOLEAN,
                                  in_=openapi.IN_QUERY,
                                  required=False,
                                  description=_('列举作为拥有者身份的组，参数不需要值，存在即有效')
                              ),
                              openapi.Parameter(
                                  name='member',
                                  type=openapi.TYPE_BOOLEAN,
                                  in_=openapi.IN_QUERY,
                                  required=False,
                                  description=_('列举作为组员身份的组，参数不需要值，存在即有效')
                              ),
                              openapi.Parameter(
                                  name='name',
                                  type=openapi.TYPE_STRING,
                                  in_=openapi.IN_QUERY,
                                  required=False,
                                  description=_('vo组名关键字查询')
                              )
                          ] + CustomGenericViewSet.PARAMETERS_AS_ADMIN,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户相关的（组员或组拥有者）项目组，联邦管理员列举所有组

            * param "owner", "member"是或的关系，只提交其中一个参数，只列举相关身份的组；
              同时提交时和都不提交效果相同，即列举用户作为组员或组拥有者的项目组；

            http code 200 ok:
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "3bc1b4e8-d232-11eb-8b02-c8009fe2eb10",
                  "name": "test",
                  "company": "string",
                  "description": "test desc",
                  "creation_time": "2021-06-21T01:44:35.774210Z",
                  "owner": {
                    "id": "1",
                    "username": "shun"
                  },
                  "status": "active"
                }
              ]
            }
        """
        return VoHandler.list_vo(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建项目组'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建项目组

            http code 200 ok:
            {
              "id": "3bc1b4e8-d232-11eb-8b02-c8009fe2eb10",
              "name": "test",
              "company": "string",
              "description": "test desc",
              "creation_time": "2021-06-21T01:44:35.774210Z",
              "owner": {
                "id": "1",
                "username": "shun"
              },
              "status": "active"        # active：正常活动的组； disable：被禁用的组
            }
        """
        return VoHandler.create(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除项目组'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除项目组

        * 需要先清理组内的资源，如云主机，云硬盘等
        """
        return VoHandler.delete_vo(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改项目组'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """
        修改项目组

            http code 200:
            {
              "id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",
              "name": "string666",
              "company": "cnic",
              "description": "测试",
              "creation_time": "2021-06-21T02:13:16.663967Z",
              "owner": {
                "id": "1",
                "username": "shun"
              },
              "status": "active"
            }
        """
        return VoHandler.update_vo(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举组员'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=True, url_path='list-members', url_name='vo-list-members')
    def vo_members_list(self, request, *args, **kwargs):
        """
        列举组员

            http code 200:
            {
              "members": [
                {
                  "user": {
                    "id": "15ebb3e4-86cf-11eb-900d-c8009fe2eb10",
                    "username": "wangyushun@cnic.cn"
                  },
                  "role": "member",             # member:普通组员；leader:组管理员
                  "join_time": "2021-06-22T07:40:47.791554Z",
                  "inviter": "shun"
                }
              ],
              "owner": {            # 组拥有者，组长
                "id": "1",
                "username": "shun"
              }
            }
        """
        return VoHandler.vo_list_members(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('添加组员'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='add-members', url_name='vo-add-members')
    def vo_members_add(self, request, *args, **kwargs):
        """
        添加组员

            * http code 200:
            {
              "success": [          # 添加成功的用户
                {
                  "user": {
                    "id": "15ebb3e4-86cf-11eb-900d-c8009fe2eb10",
                    "username": "wangyushun@cnic.cn"
                  },
                  "role": "member",         # member:普通组员；leader:组管理员
                  "join_time": "2021-06-22T07:40:47.791554Z",
                  "inviter": "shun"
                }
              ],
              "failed": [               # 添加失败的用户
                {
                  "username": "test66",
                  "message": "用户名不存在"   # 添加失败的原因
                }
              ]
            }

            * http code 400, 401, 403, 500:
            {
                "code": "xxx",
                "message": "xxx"
            }
        """
        return VoHandler.vo_add_members(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('移出组员'),
        responses={
            status.HTTP_204_NO_CONTENT: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='remove-members', url_name='vo-remove-members')
    def vo_members_remove(self, request, *args, **kwargs):
        """
        移出组员
        """
        return VoHandler.vo_remove_members(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改组成员信息，角色'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='member_id',
                in_=openapi.IN_PATH,
                required=True,
                type=openapi.TYPE_STRING,
                description=gettext_lazy('组员id')
            ),
            openapi.Parameter(
                name='role',
                in_=openapi.IN_PATH,
                required=True,
                type=openapi.TYPE_STRING,
                description=gettext_lazy('组员角色'),
                enum=VoMember.Role.values
            )
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['post'], detail=False, url_path='members/(?P<member_id>.+)/role/(?P<role>.+)',
            url_name='vo-members-role')
    def vo_members_role(self, request, *args, **kwargs):
        """
        修改组成员信息，角色

            http code 200:
            {
              "id": "3b5f3bdc-d3cd-11eb-ab5f-c8009fe2eb10",
              "user": {
                "id": "15ebb3e4-86cf-11eb-900d-c8009fe2eb10",
                "username": "xxx@cnic.cn"
              },
              "role": "leader",
              "join_time": "2021-06-23T02:46:38.283159Z",
              "inviter": "shun"
            }
        """
        return VoHandler.vo_members_role(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询vo组的统计信息'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=True, url_path='statistic', url_name='vo-statistic')
    def vo_statistic(self, request, *args, **kwargs):
        """
        查询vo组的统计信息

            http code 200:
            {
              "vo": {
                "id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",
                "name": "项目组1"
              },
              "my_role": "owner",   # owner： 组长, leader： 组管理员, member：普通组员
              "member_count": 5,
              "server_count": 0,
              "disk_count" 6,
              "order_count": 0,
              "coupon_count": 1,
              "balance": "0.00"
            }
        """
        return VoHandler.vo_statistic(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('把VO组长权限移交给指定的组内成员'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='member_id',
                in_=openapi.IN_QUERY,
                required=False,
                type=openapi.TYPE_STRING,
                description=gettext_lazy('组员id')
            ),
            openapi.Parameter(
                name='username',
                in_=openapi.IN_QUERY,
                required=False,
                type=openapi.TYPE_STRING,
                description=gettext_lazy('组员用户名')
            ),
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='devolve', url_name='devolve')
    def devolve_vo_owner(self, request, *args, **kwargs):
        """
        把VO组长权限移交给指定的组内成员

            * 组长权限的移交目标必须是一个组员，通过组员id(member_id)或者组员用户名（username）指定，推荐组员id

            http code 200:
            {
              "id": "3d7cd5fc-d236-11eb-9da9-c8009fe2eb10",
              "name": "string666",
              "company": "cnic",
              "description": "测试",
              "creation_time": "2021-06-21T02:13:16.663967Z",
              "owner": {
                "id": "1",
                "username": "shun"
              },
              "status": "active"
            }
        """
        return VoHandler.devolve_vo_owner(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        _action = self.action
        if _action in ['list', 'create']:
            return vo_serializers.VoSerializer
        elif _action == 'partial_update':
            return vo_serializers.VoUpdateSerializer
        elif _action in ['vo_members_add', 'vo_members_remove']:
            return vo_serializers.VoMembersAddSerializer
        elif _action == 'vo_members_list':
            return vo_serializers.VoMemberSerializer

        return Serializer
