from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core import errors as exceptions
from apps.api.paginations import NewPageNumberPagination100
from apps.api.viewsets import NormalGenericViewSet, serializer_error_msg
from apps.service.models import OrgDataCenter
from apps.service.odc_manager import OrgDataCenterManager
from apps.servers.models import ServiceConfig
from apps.servers.serializers import AdminServiceSerializer
from apps.storage.models import ObjectsService
from apps.storage.serializers import AdminObjectsServiceSerializer
from apps.monitor.models import MonitorJobServer, MonitorJobCeph, MonitorJobTiDB, LogSite
from apps.monitor.serializers import (
    MonitorUnitServerSerializer, MonitorUnitCephSerializer, MonitorUnitTiDBSerializer, LogSiteSerializer
)
from .. import serializers as dcserializers


class AdminOrgDataCenterViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员列举数据中心'),
        manual_parameters=[
            openapi.Parameter(
                name='org_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('机构ID')
            ),
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('关键字查询，名称和备注信息')
            ),
        ],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        管理员列举数据中心，联邦管理员查询所有，数据中心管理员只查询有权限的数据中心

            {
                "count": 1,
                "page_num": 1,
                "page_size": 20,
                "results": [
                    {
                      "id": "tzo5vc107vksb9nszbufo1dp7",
                      "name": "ttt",
                      "name_en": "string",
                      "organization":  {         # 机构
                          "id": "jzddosfo44z0gc1c4hdk980q9",
                          "name": "obj",
                          "name_en": "xxx"
                        },
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
                ]
            }
        """
        admin_user = request.user
        org_id = request.query_params.get('org_id', None)
        search = request.query_params.get('search', None)

        try:
            queryset = OrgDataCenterManager.get_odc_queryset(org_id=org_id, search=search)
            if not admin_user.is_federal_admin():
                queryset = queryset.filter(users__id=admin_user.id)

            orgs = self.paginate_queryset(queryset)
            serializer = self.get_serializer(orgs, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员创建数据中心'),
        responses={
            200: ''''''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        管理员创建数据中心，暂时只允许联邦管理员创建

            http code 200
                {
                  "name": "测试1",
                  "name_en": "test1",
                  "organization": {
                    "id": "jzddosfo44z0gc1c4hdk980q9",
                    "name": "测试1"
                  },
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
            return self.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        try:
            if not request.user.is_federal_admin():
                raise exceptions.AccessDenied(message=_('您没有创建数据中心的权限'))

            self.validate_org_id(org_id=data['organization_id'])
            odc = OrgDataCenterManager.create_org_dc(
                name=data['name'], name_en=data['name_en'], organization_id=data['organization_id'],
                longitude=data['longitude'], latitude=data['latitude'],
                sort_weight=data['sort_weight'], remark=data['remark'],
                thanos_endpoint_url=data['thanos_endpoint_url'], thanos_receive_url=data['thanos_receive_url'],
                thanos_username=data['thanos_username'], thanos_password=data['thanos_password'],
                thanos_remark=data['thanos_remark'],
                loki_endpoint_url=data['loki_endpoint_url'], loki_receive_url=data['loki_receive_url'],
                loki_username=data['loki_username'], loki_password=data['loki_password'],
                loki_remark=data['loki_remark']
            )
        except exceptions.Error as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        data = dcserializers.OrgDataCenterSerializer(instance=odc).data
        return Response(data=data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员修改数据中心'),
        responses={
            200: ''''''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        管理员修改数据中心，暂时只允许联邦管理员修改

            http code 200
                {
                  "name": "测试1",
                  "name_en": "test1",
                  "organization":{
                      "id": "skki2uhd4jyg47shvmh0uyo4h",
                      "name": "测试1",
                      "name_en": "xxx"
                    },
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
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return self.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        try:
            self.validate_org_id(org_id=data['organization_id'])
            odc = OrgDataCenterManager.get_odc(odc_id=kwargs[self.lookup_field])
            if not request.user.is_federal_admin():
                raise exceptions.AccessDenied(message=_('您没有修改数据中心的权限'))

            odc = OrgDataCenterManager.update_org_dc(
                odc_or_id=odc,
                name=data['name'], name_en=data['name_en'], organization_id=data['organization_id'],
                longitude=data['longitude'], latitude=data['latitude'],
                sort_weight=data['sort_weight'], remark=data['remark'],
                thanos_endpoint_url=data['thanos_endpoint_url'], thanos_receive_url=data['thanos_receive_url'],
                thanos_username=data['thanos_username'], thanos_password=data['thanos_password'],
                thanos_remark=data['thanos_remark'],
                loki_endpoint_url=data['loki_endpoint_url'], loki_receive_url=data['loki_receive_url'],
                loki_username=data['loki_username'], loki_password=data['loki_password'],
                loki_remark=data['loki_remark']
            )
        except exceptions.Error as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        data = dcserializers.OrgDataCenterSerializer(instance=odc).data
        return Response(data=data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员查询数据中心详情'),
        responses={
            200: ''''''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        管理员查询数据中心详情，联邦管理员可查所有，数据中心管理员只能查自己有权限的数据中心

            http code 200
                {
                  "id": "5563vam9q6e7tz9fw3kij5p51",
                  "name": "测试1",
                  "name_en": "test1",
                  "organization":{
                      "id": "skki2uhd4jyg47shvmh0uyo4h",
                      "name": "测试1",
                      "name_en": "xxx"
                    },
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
                  "users": [
                    {
                        "id": "xxx",
                        "username": "xxx"
                    }
                  ]
                }

                http code 400, 401, 404：
                {
                    "code": "BadRequest",
                    "message": ""
                }
        """
        try:
            odc = OrgDataCenterManager.get_odc(odc_id=kwargs[self.lookup_field])
            if not self.has_perm_of_odc(odc=odc, user=request.user):
                raise exceptions.AccessDenied(message=_('您没有此数据中心的访问权限'))
        except exceptions.Error as exc:
            return self.exception_response(exc)

        data = self.get_serializer(instance=odc).data
        return Response(data=data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦管理员为数据中心添加管理员'),
        manual_parameters=[
        ],
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='add/admin', url_name='add-admin')
    def add_admin_for_odc(self, request, *args, **kwargs):
        """
        联邦管理员为数据中心添加管理员

            http code 200
                {
                  "id": "5563vam9q6e7tz9fw3kij5p51",
                  "name": "测试1",
                  "name_en": "test1",
                  "organization":{
                      "id": "skki2uhd4jyg47shvmh0uyo4h",
                      "name": "测试1",
                      "name_en": "xxx"
                    },
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
                  "users": [
                    {
                        "id": "xxx",
                        "username": "xxx"
                    }
                  ]
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
            return self.exception_response(exceptions.BadRequest(msg))

        usernames = serializer.validated_data['usernames']

        try:
            if not request.user.is_federal_admin():
                raise exceptions.AccessDenied(message=_('您没有数据中心的管理权限'))

            odc = OrgDataCenterManager.get_odc(odc_id=kwargs[self.lookup_field])
            odc = OrgDataCenterManager.add_admins_for_odc(odc=odc, usernames=usernames)
        except exceptions.Error as exc:
            return self.exception_response(exc)

        return Response(data=dcserializers.OrgDataCenterDetailSerializer(odc).data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦管理员从数据中心移除管理员'),
        manual_parameters=[
        ],
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='remove/admin', url_name='remove-admin')
    def remove_admin_from_odc(self, request, *args, **kwargs):
        """
        联邦管理员从数据中心移除管理员

            http code 200
                {
                  "id": "5563vam9q6e7tz9fw3kij5p51",
                  "name": "测试1",
                  "name_en": "test1",
                  "organization":{
                      "id": "skki2uhd4jyg47shvmh0uyo4h",
                      "name": "测试1",
                      "name_en": "xxx"
                    },
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
                  "users": [
                    {
                        "id": "xxx",
                        "username": "xxx"
                    }
                  ]
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
            return self.exception_response(exceptions.BadRequest(msg))

        usernames = serializer.validated_data['usernames']

        try:
            if not request.user.is_federal_admin():
                raise exceptions.AccessDenied(message=_('您没有数据中心的管理权限'))

            odc = OrgDataCenterManager.get_odc(odc_id=kwargs[self.lookup_field])
            odc = OrgDataCenterManager.remove_admins_from_odc(odc=odc, usernames=usernames)
        except exceptions.Error as exc:
            return self.exception_response(exc)

        return Response(data=dcserializers.OrgDataCenterDetailSerializer(odc).data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦管理员查询一个数据中心下关联的各服务单元信息'),
        responses={
            200: ''''''
        }
    )
    @action(methods=['GET'], detail=True, url_path='units', url_name='units')
    def odc_units(self, request, *args, **kwargs):
        """
        联邦管理员查询一个数据中心下关联的各服务单元信息

            http code 200:
            {
                "org_data_center": {        # 数据中心
                    "id": "kc8sco1iegj7rfyz52v6epdig",
                    "name": "数据中心-中国科学院计算机网络信息中心",
                    "name_en": "",
                    "organization": {
                        "id": "1",
                        "name": "中国科学院计算机网络信息中心",
                        "name_en": "Computer Network Information Center,  Chinese Academy of Sciences"
                    },
                    "longitude": 0.0,
                    "latitude": 0.0,
                    "creation_time": "2023-11-06T07:39:57.106579Z",
                    "sort_weight": 0,
                    "remark": "",
                    "thanos_endpoint_url": "http://x.x.x.x:19194",
                    "thanos_username": "",
                    "thanos_password": null,
                    "thanos_receive_url": "",
                    "thanos_remark": "",
                    "loki_endpoint_url": "http://x.x.x.x:44135",
                    "loki_username": "",
                    "loki_password": null,
                    "loki_receive_url": "",
                    "loki_remark": ""
                },
                "server_units": [       # 云主机服务单元，可能为空数组
                    {
                        "id": "1",
                        "name": "GOSC中国科学院节点",
                        "name_en": "CSTCloud Federation Env",
                        "service_type": "evcloud",
                        "cloud_type": "private",
                        "add_time": "2020-06-17T08:42:56.213607Z",
                        "need_vpn": true,
                        "status": "enable",
                        "org_data_center": {
                            "id": "kc8sco1iegj7rfyz52v6epdig",
                            "name": "数据中心-中国科学院计算机网络信息中心",
                            "name_en": "",
                            "sort_weight": 0,
                            "organization": {
                                "id": "1",
                                "name": "中国科学院计算机网络信息中心",
                                "name_en": "Computer Network Information Center,  Chinese Academy of Sciences"
                            }
                        },
                        "longitude": 116.336601,
                        "latitude": 39.98772,
                        "pay_app_service_id": "s20627372168",
                        "sort_weight": -10,
                        "disk_available": true,
                        "region_id": "1",
                        "endpoint_url": "https://fedevcloud.cstcloud.cn/",
                        "api_version": "v3",
                        "username": "cstclou",
                        "extra": "",                # json格式字符串
                        "remarks": "虚拟机位于 10.0.200.83"
                    }
                ],
                "object_units": [   # 对象存储服务单元，可能为空数组
                    {
                        "id": "0fb92e48-3565-11ed-9877-c8009fe2eb03",
                        "name": "中国科技云对象存储服务",
                        "name_en": "CSTCloud Object Storage",
                        "service_type": "iharbor",
                        "endpoint_url": "https://obs.cstcloud.cn",
                        "add_time": "2022-09-16T02:12:49.015287Z",
                        "status": "enable",
                        "remarks": "地球大数据对象存储服务",
                        "provide_ftp": true,
                        "ftp_domains": [
                            "ftp.cstcloud.cn"
                        ],
                        "longitude": 0.0,
                        "latitude": 0.0,
                        "pay_app_service_id": "s20221109940444",
                        "org_data_center": {...}    # 内容参考 上面的云主机服务单元
                        "sort_weight": -99,
                        "loki_tag": "",
                        "username": "gosc"
                    }
                ],
                "monitor_server_units": [   # 主机监控单元，可能为空数组
                    {
                        "id": "36571950-60a5-11ed-a7f0-c8009fe2eb03",
                        "name": "中国科技云-运维大数据-云主机",
                        "name_en": "CSTcloud AIOPS VMs",
                        "job_tag": "aiops-node-vms",
                        "creation": "2022-11-10T03:10:21.592558Z",
                        "remark": "",
                        "sort_weight": -99,
                        "grafana_url": "http://x.x.x.x:3000/d/AIOPSVMs/cstcloud-aiops-vms?orgId=1",
                        "dashboard_url": "",
                        "org_data_center": {...}   # 内容参考 上面的云主机服务单元
                    }
                ],
                "monitor_ceph_units": [     # CEPH监控单元，可能为空数组
                    {
                        "id": "2afff430-1f67-11ec-b90d-c8009fe2eb03",
                        "name": "中国科技云-运维大数据",
                        "name_en": "CSTcloud AIOPS",
                        "job_tag": "aiops-ceph",
                        "creation": "2021-09-27T07:47:30.516477Z",
                        "remark": "",
                        "sort_weight": -99,
                        "grafana_url": "http://xx.xx.xx.xx:3000/d/aiops-ceph/aiops-ceph?orgId=1&refresh=30s",
                        "dashboard_url": "",
                        "org_data_center": {...}    # 内容参考 上面的云主机服务单元
                    }
                ],
                "monitor_tidb_units": [     # TiDB监控单元，可能为空数组
                    {
                        "id": "3e64ff6a-d9ca-11ed-a6f9-c800dfc12405",
                        "name": "运维大数据平台 TiDB 集群",
                        "name_en": "aiops TiDB Cluster",
                        "job_tag": "aiops-tidb",
                        "creation": "2023-04-13T07:10:17.183160Z",
                        "remark": "",
                        "sort_weight": -99,
                        "grafana_url": "http://10.16.1.28:3000/login",
                        "dashboard_url": "http://10.16.1.26:2379/dashboard/#/overview",
                        "version": "",
                        "org_data_center": {...}    # 内容参考 上面的云主机服务单元
                    }
                ],
                "site_log_units": [     # 站点日志单元，可能为空数组
                    {
                        "id": "qffxh8i0845s0cghs083pe8w9",
                        "name": "科技云对象存储",
                        "name_en": "CSTC OBS",
                        "log_type": "http",
                        "job_tag": "obs",
                        "sort_weight": 1,
                        "desc": "",
                        "creation": "2023-07-24T02:50:31.208282Z",
                        "site_type": {
                            "id": "bfoebqo5nwputx5p4s5hsox1d",
                            "name": "对象存储OBS",
                            "name_en": "IHarbor",
                            "sort_weight": 1,
                            "desc": ""
                        },
                        "org_data_center": {...}    # 内容参考 上面的云主机服务单元
                    }
                ]
            }
        """
        try:
            if not request.user.is_federal_admin():
                raise exceptions.AccessDenied(message=_('您不是联邦管理员，没有访问权限'))

            odc = OrgDataCenterManager.get_odc(odc_id=kwargs[self.lookup_field])
        except exceptions.Error as exc:
            return self.exception_response(exc)

        # 云主机服务单元
        server_units = []
        for u in ServiceConfig.objects.filter(org_data_center_id=odc.id):
            u.org_data_center = odc
            server_units.append(u)

        # 对象存储服务单元
        object_units = []
        for u in ObjectsService.objects.filter(org_data_center_id=odc.id):
            u.org_data_center = odc
            object_units.append(u)

        # monitor server单元
        monitor_server_units = []
        for u in MonitorJobServer.objects.filter(org_data_center_id=odc.id):
            u.org_data_center = odc
            monitor_server_units.append(u)

        # monitor ceph单元
        monitor_ceph_units = []
        for u in MonitorJobCeph.objects.filter(org_data_center_id=odc.id):
            u.org_data_center = odc
            monitor_ceph_units.append(u)

        # monitor tidb单元
        monitor_tidb_units = []
        for u in MonitorJobTiDB.objects.filter(org_data_center_id=odc.id):
            u.org_data_center = odc
            monitor_tidb_units.append(u)

        # 日志单元
        site_log_units = []
        for u in LogSite.objects.select_related('site_type').filter(org_data_center_id=odc.id):
            u.org_data_center = odc
            site_log_units.append(u)

        odc_data = dcserializers.OrgDataCenterSerializer(instance=odc).data
        server_units_data = AdminServiceSerializer(server_units, many=True).data
        object_units_data = AdminObjectsServiceSerializer(object_units, many=True).data
        monitor_server_units_data = MonitorUnitServerSerializer(monitor_server_units, many=True).data
        monitor_ceph_units_data = MonitorUnitCephSerializer(monitor_ceph_units, many=True).data
        monitor_tidb_units_data = MonitorUnitTiDBSerializer(monitor_tidb_units, many=True).data
        site_log_units_data = LogSiteSerializer(site_log_units, many=True).data
        return Response(data={
            'org_data_center': odc_data,
            'server_units': server_units_data,
            'object_units': object_units_data,
            'monitor_server_units': monitor_server_units_data,
            'monitor_ceph_units': monitor_ceph_units_data,
            'monitor_tidb_units': monitor_tidb_units_data,
            'site_log_units': site_log_units_data
        })

    @staticmethod
    def validate_org_id(org_id: str):
        try:
            return OrgDataCenterManager.get_org(org_id=org_id)
        except exceptions.TargetNotExist as exc:
            raise exceptions.InvalidArgument(message=_('指定的机构不存在'))

    def get_serializer_class(self):
        if self.action == 'list':
            return dcserializers.OrgDataCenterSerializer
        elif self.action == 'retrieve':
            return dcserializers.OrgDataCenterDetailSerializer
        elif self.action in ['create', 'update']:
            return dcserializers.OrgDataCenterCreateSerializer
        elif self.action in ['add_admin_for_odc', 'remove_admin_from_odc']:
            return dcserializers.UsernamesBodySerializer

        return Serializer

    @staticmethod
    def has_perm_of_odc(odc: OrgDataCenter, user):
        if user.is_federal_admin():
            return True

        if odc.users.filter(id=user.id).exists():
            return True

        return False


class OrgDataCenterViewSet(NormalGenericViewSet):
    permission_classes = []
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举数据中心'),
        manual_parameters=[
            openapi.Parameter(
                name='org_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('机构ID')
            ),
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('关键字查询，名称和备注信息')
            ),
        ],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举数据中心，无需登录

            {
                "count": 1,
                "page_num": 1,
                "page_size": 20,
                "results": [
                    {
                      "id": "tzo5vc107vksb9nszbufo1dp7",
                      "name": "ttt",
                      "name_en": "string",
                      "organization":  {         # 机构
                          "id": "jzddosfo44z0gc1c4hdk980q9",
                          "name": "obj",
                          "name_en": "xxx"
                        },
                      "longitude": 0,
                      "latitude": 0,
                      "creation_time": "2023-11-06T05:40:20.201159Z",
                      "sort_weight": 0,
                      "remark": "string",
                    }
                ]
            }
        """
        org_id = request.query_params.get('org_id', None)
        search = request.query_params.get('search', None)

        try:
            queryset = OrgDataCenterManager.get_odc_queryset(org_id=org_id, search=search)
            orgs = self.paginate_queryset(queryset)
            serializer = self.get_serializer(orgs, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

    def get_serializer_class(self):
        if self.action == 'list':
            return dcserializers.ODCSimpleSerializer

        return Serializer
