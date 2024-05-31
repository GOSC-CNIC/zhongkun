from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from utils.paginators import NoPaginatorInspector
from apps.api.viewsets import NormalGenericViewSet
from apps.app_net_link.managers import NetLinkUserRoleWrapper
from apps.app_net_link.serializers import NetLinkUserRoleSerializer
from apps.app_net_link.permissions import LinkIPRestrictPermission


class NetLinkUserRoleViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询用户在net_link中用户角色和权限'),
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询用户在net_link中用户角色和权限

            http Code 200 Ok:
                {
                  "id": "c89od410t7hwsejr11tyv52w9",
                  "is_link_admin": "false",
                  "is_link_readonly": true,
                  "creation_time": "2023-10-18T06:13:00Z",
                  "update_time": "2023-10-18T06:13:00Z",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  }
                }
        """
        urw = NetLinkUserRoleWrapper(user=request.user)
        user_role = urw.user_role
        return Response(data=NetLinkUserRoleSerializer(user_role).data)

    def get_serializer_class(self):
        return Serializer
