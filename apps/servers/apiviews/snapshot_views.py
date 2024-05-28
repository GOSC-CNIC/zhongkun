from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.servers.handlers.snapshot_handler import SnapshotHandler
from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import NewPageNumberPagination100
from apps.servers import serializers


class ServerSnapshotViewSet(CustomGenericViewSet):
    """
    虚拟服务器快照视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户个人或vo组云主机快照，或者以管理员身份列举云主机快照'),
        manual_parameters=CustomGenericViewSet.PARAMETERS_AS_ADMIN + [
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('服务单元id')
            ),
            openapi.Parameter(
                name='server_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('云主机id')
            ),
            openapi.Parameter(
                name='remark',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('过滤条件，备注模糊查询')
            ),
            openapi.Parameter(
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('vo组id，查询vo组的快照，需要vo组访问权限，不能与参数“vo_name”一起提交')
            ),
            openapi.Parameter(
                name='vo_name',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('过滤条件，vo组名称，此参数只有以管理员身份请求时有效，否则400，不能与参数“vo_id”一起提交')
            ),
            openapi.Parameter(
                name='user_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('过滤条件，用户id，此参数只有以管理员身份请求时有效，否则400，不能与参数“username”一起提交')
            ),
            openapi.Parameter(
                name='username',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('过滤条件，用户名，此参数只有以管理员身份请求时有效，否则400，不能与参数“user_id”一起提交')
            ),
            openapi.Parameter(
                name='exclude_vo',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('过滤条件，排除vo组只查询个人，此参数不需要值，此参数只有以管理员身份请求时有效，否则400，'
                                         '不能与参数“vo_id”、“vo_name”一起提交')
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举用户个人或vo组云主机快照，或者以管理员身份列举云主机快照

            200: {
                "count": 2,
                "page_num": 1,
                "page_size": 100,
                "results": [
                    {
                        "id": "r7o6ab5guv3uc6qs9uckfu89w-s",
                        "name": "name1",
                        "size": 66,     # GiB
                        "remarks": "snapshot1 test",
                        "creation_time": "2024-05-11T06:15:35.707263Z",
                        "expiration_time": "2024-05-10T06:15:35.707268Z",
                        "pay_type": "prepaid",
                        "classification": "vo",
                        "user": {
                            "id": "r7kfbn3aick5z4o3re2y08mo1",
                            "username": "test"
                        },
                        "vo": {
                            "id": "dkfbn3a3ergz4o3r42y08mrt",
                            "name": "test"
                        },
                        "server": {
                            "id": "r7n8h7zsjppav5m757sxzndeb-i",
                            "vcpus": 6,
                            "ram_gib": 8,
                            "ipv4": "127.12.33.111",
                            "image": "test-image",
                            "creation_time": "2024-05-11T06:15:35.696297Z",
                            "expiration_time": null,
                            "remarks": "test server"
                        },
                        "service": {
                            "id": "r7msvmmvr2i6zi59s45y3gvjb",
                            "name": "test",
                            "name_en": "test_en"
                        }
                    }
                ]
            }
        """
        return SnapshotHandler.list_server_snapshot(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建云主机快照'),
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建云主机快照

            请求成功会创建一个云主机快照订购订单，订单支付后创建交付云主机快照

            http code 200 ok:
            {
                "order_id": "xxx"
            }
        """
        return SnapshotHandler.create_server_snapshot(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一个用户个人或vo组云主机快照信息，或者以管理员身份查询云主机快照信息'),
        manual_parameters=CustomGenericViewSet.PARAMETERS_AS_ADMIN,
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询一个用户个人或vo组云主机快照信息，或者以管理员身份查询云主机快照信息

            200: {
                "id": "r7o6ab5guv3uc6qs9uckfu89w-s",
                "name": "name1",
                "size": 66,     # GiB
                "remarks": "snapshot1 test",
                "creation_time": "2024-05-11T06:15:35.707263Z",
                "expiration_time": "2024-05-10T06:15:35.707268Z",
                "pay_type": "prepaid",
                "classification": "vo",
                "user": {
                    "id": "r7kfbn3aick5z4o3re2y08mo1",
                    "username": "test"
                },
                "vo": {
                    "id": "dkfbn3a3ergz4o3r42y08mrt",
                    "name": "test"
                },
                "server": {
                    "id": "r7n8h7zsjppav5m757sxzndeb-i",
                    "vcpus": 6,
                    "ram_gib": 8,
                    "ipv4": "127.12.33.111",
                    "image": "test-image",
                    "creation_time": "2024-05-11T06:15:35.696297Z",
                    "expiration_time": null,
                    "remarks": "test server"
                },
                "service": {
                    "id": "r7msvmmvr2i6zi59s45y3gvjb",
                    "name": "test",
                    "name_en": "test_en"
                }
            }
        """
        return SnapshotHandler.detail_server_snapshot(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除一个用户个人或vo组的云主机快照，或者以管理员身份删除云主机快照'),
        manual_parameters=CustomGenericViewSet.PARAMETERS_AS_ADMIN
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除一个用户个人或vo组的云主机快照，或者以管理员身份删除云主机快照

            204 ok
        """
        return SnapshotHandler.delete_server_snapshot(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('用户个人或vo组的云主机回滚到快照')
    )
    @action(methods=['POST'], detail=True, url_path=r'rollback/server/(?P<server_id>[^/]+)', url_name='rollback')
    def rollback_server(self, request, *args, **kwargs):
        """
        用户个人或vo组的云主机回滚到快照

            200 ok
        """
        return SnapshotHandler.rollback_server_to_snapshot(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('续费云主机快照'),
        responses={
            200: ''
        }
    )
    @action(methods=['POST'], detail=False, url_path=r'renew', url_name='renew')
    def renew_snapshot(self, request, *args, **kwargs):
        """
        续费云主机快照

            请求成功会创建一个云主机快照订购订单，订单支付后延后云主机快照过期时间

            http code 200 ok:
            {
                "order_id": "xxx"
            }
        """
        return SnapshotHandler.renew_server_snapshot(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.SnapshotCreateSerializer
        elif self.action == 'renew_snapshot':
            return serializers.SnapshotRenewSerializer

        return Serializer
