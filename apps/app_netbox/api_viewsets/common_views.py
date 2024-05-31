from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from utils.paginators import NoPaginatorInspector
from apps.api.paginations import NewPageNumberPagination100
from apps.api.viewsets import NormalGenericViewSet
from apps.app_net_ipam.managers import NetIPamUserRoleWrapper
from apps.app_net_link.managers import NetLinkUserRoleWrapper
from apps.app_net_ipam.serializers import NetIPamUserRoleSerializer


class NetBoxUserRoleViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询用户在netbox中用户角色和权限'),
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询用户在netbox中用户角色和权限

            http Code 200 Ok:
                {
                  "id": "c89od410t7hwsejr11tyv52w9",
                  "is_ipam_admin": false,
                  "is_ipam_readonly": true,
                  "is_link_admin": "false",
                  "is_link_readonly": true,
                  "creation_time": "2023-10-18T06:13:00Z",
                  "update_time": "2023-10-18T06:13:00Z",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  },
                  "organizations": [    # 有ipam管理权限的 机构
                    {
                      "id": "b75r1144s5ucku15p6shp9zgf",
                      "name": "中国科学院计算机网络信息中心",
                      "name_en": "中国科学院计算机网络信息中心"
                    }
                  ]
                }
        """
        urw = NetIPamUserRoleWrapper(user=request.user)
        user_role = urw.user_role
        data = NetIPamUserRoleSerializer(instance=user_role).data
        orgs = user_role.organizations.all().values('id', 'name', 'name_en')
        data['organizations'] = orgs
        link_urw = NetLinkUserRoleWrapper(user=request.user)
        data['is_link_admin'] = link_urw.user_role.is_link_admin
        data['is_link_readonly'] = link_urw.user_role.is_link_readonly
        return Response(data=data)

    def get_serializer_class(self):
        return Serializer
