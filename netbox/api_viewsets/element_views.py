from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


from api.viewsets import NormalGenericViewSet
from api.paginations import NewPageNumberPagination
from netbox.handlers.link_handlers import (
    ElementHandler, ConnectorBoxHandler, DistriFrameHandler, DistriFramePortHandler,
    FiberCableHandler, OpticalFiberHandler
)
from netbox.serializers import link as link_serializers
from netbox.permissions import LinkIPRestrictPermission


class ElementViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('根据网元id获取网元信息'),
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询一个租用线路
        
            case1:
            http Code 200 Ok:
                {
                    "type": "lease",
                    "lease": {
                        "is_linked": false,
                        "element_id": "ksss6f25mu7vx42yxhyy2gv8r",
                        "link_id": [
                            "t1hgf0ngc901dop1w6f8njo1w"
                        ],
                        "id": "cc31q7a7cz2h7trj6t3986jvd",
                        "private_line_number": "37969041",
                        "lease_line_code": "北京青岛ANE0172NP",
                        "line_username": "国家海洋局北海分局（青岛）",
                        "endpoint_a": "北京市海淀区中关村南四街4号",
                        "endpoint_z": "",
                        "line_type": "接入网",
                        "cable_type": "MSTP电路",
                        "bandwidth": 100,
                        "length": null,
                        "provider": "联通（北京）",
                        "enable_date": "2019-01-31",
                        "is_whithdrawal": false,
                        "money": null,
                        "remarks": "电路代号（长途）：北京青岛ANE0172NP，2019年1月31日开通"
                    },
                    "port": null,
                    "fiber": null,
                    "box": null
                }
                
            case2:
            http Code 200 Ok:
                {
                    "type": "port",
                    "lease": null,
                    "port": {
                        "is_linked": false,
                        "element_id": "mgd1c7adgkikaqudtunkkftkc",
                        "link_id": [],
                        "id": "mgd15851e9m9nix6y1v2cjvb7",
                        "number": "东侧数据处理区中间机柜35至36U_中天科技ODF(1,6)",
                        "row": 1,
                        "col": 6,
                        "distribution_frame": {
                            "id": "mgcgpi7fj115jresrmzazmoy7",
                            "number": "东侧数据处理区中间机柜35至36U_中天科技ODF"
                        }
                    },
                    "fiber": null,
                    "box": null
                }

            case3:
            http Code 200 Ok:
                {
                    "type": "fiber",
                    "lease": null,
                    "port": null,
                    "fiber": {
                        "is_linked": false,
                        "element_id": "mgbar1nvg5b7y601zrhocypzh",
                        "link_id": [],
                        "id": "mgbagzmookwyt4binzao7exzn",
                        "sequence": 3,
                        "fiber_cable": {
                            "id": "mgb1bi5zka5c0dyrgo0m89sq7",
                            "number": "test-fibercable-number-1"
                        }
                    },
                    "box": null
                }

            case4:
            http Code 200 Ok:
                {
                    "type": "box",
                    "lease": null,
                    "port": null,
                    "fiber": null,
                    "box": {
                        "is_linked": true,
                        "element_id": "mgarja3xdy80ubxv2jm6teo62",
                        "link_id": [],
                        "id": "mgarbd5pg0zkmavtitu5gbxzc",
                        "number": "熔纤包测试1",
                        "place": "熔纤包测试-位置",
                        "remarks": "",
                        "location": ""
                    }
                }
        """
        return ElementHandler.retrieve_element(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        return link_serializers.ElementDetailDataSerializer


class ConnectorBoxViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举接头盒'),
        manual_parameters=[
            openapi.Parameter(
                name='is_linked',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='过滤条件，false：未接入；true：已接入；不填查询全部'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举接头盒

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "is_linked": true, # 是否接入链路
                            "link_id": [
                                "t1hgf0ngc901dop1w6f8njo1w" # 链路id
                            ],
                            "element_id": "mgarja3xdy80ubxv2jm6teo62", # 网元id
                            "id": "mgarbd5pg0zkmavtitu5gbxzc",
                            "number": "熔纤包测试1", # 编号
                            "place": "", # 设备位置
                            "remarks": "", # 备注
                            "location": "" # 经纬度
                        }
                    ]
                }

        """
        return ConnectorBoxHandler.list_connectorbox(view=self, request=request)

    def get_serializer_class(self):
        return link_serializers.ConnectorBoxSerializer


class DistriFrameViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举配线架'),
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举配线架信息

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "id": "mgcgpi7fj115jresrmzazmoy7",
                            "number": "东侧数据处理区中间机柜35至36U_中天科技ODF", # 编号
                            "model_type": "LC", # 设备型号
                            "row_count": 1, # 行数
                            "col_count": 12, # 列数
                            "place": "中国资源卫星应用中心一期楼三层机房A301", # 设备位置
                            "remarks": "", # 备注
                            "link_org": {
                                "id": "mfr1i5nitwi6p13hg5extsvvx",
                                "name": "中国遥感卫星地面站"
                            }
                        }
                    ]
                }

        """
        return DistriFrameHandler.list_distriframe(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一个配线架'),
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询一个配线架

            http Code 200 Ok:
                {
                    "id": "mgcgpi7fj115jresrmzazmoy7",
                    "number": "东侧数据处理区中间机柜35至36U_中天科技ODF", # 编号
                    "model_type": "LC", # 设备型号
                    "row_count": 1, # 行数
                    "col_count": 12, # 列数
                    "place": "中国资源卫星应用中心一期楼三层机房A301", # 设备位置
                    "remarks": "", # 备注
                    "link_org": {
                        "id": "mfr1i5nitwi6p13hg5extsvvx",
                        "name": "中国遥感卫星地面站"
                    }
                }
        """
        return DistriFrameHandler.retrieve_distriframe(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        return link_serializers.DistriFrameSerializer


class DistriFramePortViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举配线架端口'),
        manual_parameters=[
            openapi.Parameter(
                name='is_linked',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='过滤条件，false：未接入；true：已接入；不填查询全部'
            ),
            openapi.Parameter(
                name='frame_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='过滤条件，有值则查询配线架id下的端口，不填查询全部'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举配线架端口信息

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "is_linked": true, # 是否接入链路
                            "element_id": "mgcj1voii43a8xd1d0j56hre7",  # 网元id
                            "link_id": [
                                "t1hgf0ngc901dop1w6f8njo1w" # 链路id
                            ],
                            "id": "mgciudagi8j8q9994go07ykyn",
                            "number": "test(1,1)", # 编号
                            "row": 1, # 行号
                            "col": 1, # 列号
                            "distribution_frame": {
                                "id": "mgcgpi7fj115jresrmzazmoy7",
                                "number": "东侧数据处理区中间机柜35至36U_中天科技ODF"
                            }
                        }
                    ]
                }
        """
        return DistriFramePortHandler.list_distriframeport(view=self, request=request)

    def get_serializer_class(self):
        return link_serializers.DistriFramePortSerializer


class FiberCableViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建光缆'),
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建光缆

            http Code 200 Ok:
                {
                    "id": "k9rkav5ffd8jnijbpk8yjiegc",
                    "number": "sm-test",
                    "fiber_count": 10,
                    "length": "10.60",
                    "endpoint_1": "微生物所",
                    "endpoint_2": "软件园",
                    "remarks": ""
                }

        """
        return FiberCableHandler.creat_fibercable(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举光缆'),
        manual_parameters=[
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='过滤条件，关键词模糊查询（光缆编号、端点1、端点2、备注）'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举光缆信息

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "id": "k9rkav5ffd8jnijbpk8yjiegc",
                            "number": "sm-test", # 光缆编号
                            "fiber_count": 10,  纤芯数
                            "length": "10.60", # 长度（km）
                            "endpoint_1": "微生物所",  # 光缆端点1
                            "endpoint_2": "软件园",  # 光缆端点2
                            "remarks": "" # 备注
                        }
                    ]
                }

        """
        return FiberCableHandler.list_fibercable(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一个光缆'),
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询一个光缆

            http Code 200 Ok:
                {
                    "id": "k9rkav5ffd8jnijbpk8yjiegc",
                    "number": "sm-test", # 光缆编号
                    "fiber_count": 10,  纤芯数
                    "length": "10.60", # 长度（km）
                    "endpoint_1": "微生物所",  # 光缆端点1
                    "endpoint_2": "软件园",  # 光缆端点2
                    "remarks": "" # 备注
                }
        """
        return FiberCableHandler.retrieve_fibercable(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action in ['list', 'create']:
            return link_serializers.FiberCableSerializer

        return Serializer


class OpticalFiberViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举光纤'),
        manual_parameters=[
            openapi.Parameter(
                name='is_linked',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='过滤条件，false：未接入；true：已接入；不填查询全部'
            ),
            openapi.Parameter(
                name='cable_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='过滤条件，有值则查询光缆id下的光纤，不填查询全部'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举光纤信息

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "is_linked": true, # 是否接入链路
                            "element_id": "mgb3k0t02f0m954adqenm950n", # 网元id
                            "link_id": [
                                "t1hgf0ngc901dop1w6f8njo1w" # 链路id
                            ],
                            "id": "mgb3ciey2jgjqh0i56ihnpzk2",
                            "sequence": 1, # 纤序
                            "fiber_cable": {
                                "id": "mgb1bi5zka5c0dyrgo0m89sq7",
                                "number": "test-fibercable-number-1"
                            }
                        }
                    ]
                }
        """
        return OpticalFiberHandler.list_opticalfiber(view=self, request=request)

    def get_serializer_class(self):
        return link_serializers.OpticalFiberSerializer
