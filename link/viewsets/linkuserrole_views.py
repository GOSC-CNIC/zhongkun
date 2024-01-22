from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from api.paginations import NewPageNumberPagination
from api.viewsets import NormalGenericViewSet
from utils.paginators import NoPaginatorInspector
from link.managers.userrole_manager import UserRoleWrapper
from link.serializers.linkuserrole_serializer import LinkUserRoleSerializer, FromNetBoxUserRoleSerializer
from link.permissions import LinkIPRestrictPermission
from netbox.managers.common import NetBoxUserRoleWrapper


class LinkUserRoleViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询用户链路管理中用户角色和权限'),
        deprecated=True,
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询用户链路管理中用户角色和权限

            http Code 200 Ok:
                {
                      "id": "5cvp5ok3xu6ybo7nijrosshw9",
                      "is_admin": true,
                      "is_readonly": false,
                      "create_time": "2023-10-27T02:18:55.893804Z",
                      "update_time": "2023-10-27T02:18:55.893868Z",
                      "user": {
                          "id": "o6o3kj8x2eyfqpnunucfmicye",
                          "username": "xk"
                      }
                }
        """
        user_role = UserRoleWrapper(user=request.user).user_role
        return Response(data=LinkUserRoleSerializer(instance=user_role).data)

    def get_serializer_class(self):
        return LinkUserRoleSerializer


class FromNetBoxUserRoleViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询用户链路管理中用户角色和权限'),
        deprecated=True,
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询用户链路管理中用户角色和权限

            http Code 200 Ok:
                {
                      "id": "5cvp5ok3xu6ybo7nijrosshw9",
                      "is_admin": true,
                      "is_readonly": false,
                      "create_time": "2023-10-27T02:18:55.893804Z",
                      "update_time": "2023-10-27T02:18:55.893868Z",
                      "user": {
                          "id": "o6o3kj8x2eyfqpnunucfmicye",
                          "username": "xk"
                      }
                }
        """
        user_role = NetBoxUserRoleWrapper(user=request.user).user_role
        return Response(data=FromNetBoxUserRoleSerializer(instance=user_role).data)

    def get_serializer_class(self):
        return FromNetBoxUserRoleSerializer
