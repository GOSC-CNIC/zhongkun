from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.paginations import NewPageNumberPagination
from api.viewsets import NormalGenericViewSet
from apps.app_netbox.serializers.link import LeaseLineSerializer
from apps.app_netbox.handlers.link_handlers import LeaseLineHandler
from apps.app_netbox.permissions import LinkIPRestrictPermission


class LeaseLineViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, LinkIPRestrictPermission]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建租用线路'),
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建租用线路信息

            http Code 200 Ok:
                {
                    "id": "tggprpr26coj92g1t08gjoim5",
                    "private_line_number": "28622091", # 专线号
                    "lease_line_code": "北京乌鲁木齐ANE0033NP", # 电路代号
                    "line_username": "北京-乌鲁木齐", # 用户名
                    "endpoint_a": "北京市海淀区中关村南四街4号",
                    "endpoint_z": "新疆省乌鲁木齐市北京南路40号",
                    "line_type": "骨干网", # 线路类型
                    "cable_type": "MSTP电路", # 电路类型
                    "bandwidth": 1000, # 宽带（Mbs）
                    "length": 20.00, # 长度 （km）
                    "provider": "联通（北京）", # 运营商
                    "enable_date": "2014-07-01", # 启用日期
                    "is_whithdrawal": true, # 是否撤线
                    "money": 8500.00, # 月租费（元）
                    "remarks": "电路代号：北京乌鲁木齐ANE0033NP,2015-1-18日由300M扩容至600M，升级1G时撤租"
                }

        """
        return LeaseLineHandler.creat_leaseline(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举租用线路'),
        manual_parameters=[
            openapi.Parameter(
                name='is_linked',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='过滤条件，false：未接入；true：已接入；不填查询全部'
            ),
            openapi.Parameter(
                name='is_whithdrawal',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_BOOLEAN,
                required=False,
                description='过滤条件，false：在网租用线路；true：撤线租用线路；不填查询全部'
            ),
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='过滤条件，关键词模糊查询（专线号、电路代号、专线用户、A端、Z端、备注）'
            ),
            openapi.Parameter(
                name='enable_date_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'开通日期查询，时间段起，ISO8601格式：YYYY-MM-dd'
            ),
            openapi.Parameter(
                name='enable_date_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'开通日期查询，时间段止，ISO8601格式：YYYY-MM-dd'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举租用线路信息

            http Code 200 Ok:
                {
                    "count": 141,
                    "page_num": 8,
                    "page_size": 20,
                    "results": [
                        {
                            "is_linked": false,
                            "element_id": "spr88xs2bre1y56nk0d0ykf72",
                            "link_id": [],
                            "id": "tggprpr26coj92g1t08gjoim5",
                            "private_line_number": "28622091", # 专线号
                            "lease_line_code": "北京乌鲁木齐ANE0033NP", # 电路代号
                            "line_username": "北京-乌鲁木齐", # 用户名
                            "endpoint_a": "北京市海淀区中关村南四街4号",
                            "endpoint_z": "新疆省乌鲁木齐市北京南路40号",
                            "line_type": "骨干网", # 线路类型
                            "cable_type": "MSTP电路", # 电路类型
                            "bandwidth": 1000, # 宽带（Mbs）
                            "length": 20.00, # 长度 （km）
                            "provider": "联通（北京）", # 运营商
                            "enable_date": "2014-07-01", # 启用日期
                            "is_whithdrawal": true, # 是否撤线 true(撤线) false(在网)
                            "money": 8500.00, # 月租费（元）
                            "remarks": "电路代号：北京乌鲁木齐ANE0033NP,2015-1-18日由300M扩容至600M，升级1G时撤租"
                        }
                    ]
                }

        """
        return LeaseLineHandler.list_leaseline(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('更改一个租用线路'),
        responses={
            200: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='update', url_name='update-leaseline')
    def update_leaseline(self, request, *args, **kwargs):
        """
        更改一个租用线路

            http Code 200 Ok:
                {
                    "id": "tggprpr26coj92g1t08gjoim5",
                    "private_line_number": "28622091", # 专线号
                    "lease_line_code": "北京乌鲁木齐ANE0033NP", # 电路代号
                    "line_username": "北京-乌鲁木齐", # 用户名
                    "endpoint_a": "北京市海淀区中关村南四街4号",
                    "endpoint_z": "新疆省乌鲁木齐市北京南路40号",
                    "line_type": "骨干网", # 线路类型
                    "cable_type": "MSTP电路", # 电路类型
                    "bandwidth": 1000, # 宽带（Mbs）
                    "length": 20.00, # 长度 （km）
                    "provider": "联通（北京）", # 运营商
                    "enable_date": "2014-07-01", # 启用日期
                    "is_whithdrawal": true, # 是否撤线
                    "money": 8500.00, # 月租费（元）
                    "remarks": "电路代号：北京乌鲁木齐ANE0033NP,2015-1-18日由300M扩容至600M，升级1G时撤租"
                }
        """
        return LeaseLineHandler.update_leaseline(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一个租用线路'),
        responses={
            200: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询一个租用线路

            http Code 200 Ok:
                {
                    "is_linked": false,
                    "element_id": "spr88xs2bre1y56nk0d0ykf72",
                    "link_id": [],
                    "id": "tggprpr26coj92g1t08gjoim5",
                    "private_line_number": "28622091", # 专线号
                    "lease_line_code": "北京乌鲁木齐ANE0033NP", # 电路代号
                    "line_username": "北京-乌鲁木齐", # 用户名
                    "endpoint_a": "北京市海淀区中关村南四街4号",
                    "endpoint_z": "新疆省乌鲁木齐市北京南路40号",
                    "line_type": "骨干网", # 线路类型
                    "cable_type": "MSTP电路", # 电路类型
                    "bandwidth": 1000, # 宽带（Mbps）
                    "length": 20.00, # 长度 （km）
                    "provider": "联通（北京）", # 运营商
                    "enable_date": "2014-07-01", # 启用日期
                    "is_whithdrawal": true, # 是否撤线
                    "money": 8500.00, # 月租费（元）
                    "remarks": "电路代号：北京乌鲁木齐ANE0033NP,2015-1-18日由300M扩容至600M，升级1G时撤租" # 备注
                }
        """
        return LeaseLineHandler.retrieve_leaseline(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        return LeaseLineSerializer
