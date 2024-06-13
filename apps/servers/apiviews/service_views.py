from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import Serializer, DateTimeField as DRFDateTimeField
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import DefaultPageNumberPagination
from apps.service.odc_manager import OrgDataCenterManager
from apps.servers.managers import ServiceManager
from apps.servers.models import ServiceConfig
from apps.servers.handlers import service_handlers as handlers
from apps.servers.handlers.service_handlers import ServiceQuotaHandler
from apps.servers import serializers
from core.adapters import inputs, outputs
from core import errors as exceptions


class ServivePrivateQuotaViewSet(CustomGenericViewSet):
    """
    接入服务私有配额视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举资源提供者接入服务的私有资源配额'),
        manual_parameters=[
            openapi.Parameter(
                name='data_center_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='机构id'
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='服务端点id'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举资源提供者接入服务的私有资源配额

            http code 200：
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "private_ip_total": 0,
                  "public_ip_total": 0,
                  "vcpu_total": 0,
                  "ram_total": 0,       # GiB
                  "disk_size_total": 0,
                  "private_ip_used": 0,
                  "public_ip_used": 0,
                  "vcpu_used": 0,
                  "ram_used": 0,        # GiB
                  "disk_size_used": 0,
                  "creation_time": "2021-03-05T07:20:58.451119Z",
                  "enable": true,
                  "service": {
                    "id": "1",
                    "name": "地球大数据怀柔分中心",
                    "name_en": "xxx"
                  }
                }
              ]
            }
        """
        return ServiceQuotaHandler.list_privete_quotas(view=self, request=request, kwargs=kwargs)


class ServiveShareQuotaViewSet(CustomGenericViewSet):
    """
    接入服务共享配额视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举资源提供者接入服务的共享资源配额'),
        manual_parameters=[
            openapi.Parameter(
                name='data_center_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='机构id'
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='服务端点id'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举资源提供者接入服务的共享资源配额

            http code 200：
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "private_ip_total": 0,
                  "public_ip_total": 0,
                  "vcpu_total": 0,
                  "ram_total": 0,       # GiB
                  "disk_size_total": 0,
                  "private_ip_used": 0,
                  "public_ip_used": 0,
                  "vcpu_used": 0,
                  "ram_used": 0,        # GiB
                  "disk_size_used": 0,
                  "creation_time": "2021-03-05T07:20:58.451119Z",
                  "enable": true,
                  "service": {
                    "id": "1",
                    "name": "地球大数据怀柔分中心",
                    "name_en": "xxx"
                  }
                }
              ]
            }
        """
        return ServiceQuotaHandler.list_share_quotas(view=self, request=request, kwargs=kwargs)


class ServiceViewSet(CustomGenericViewSet):
    """
    接入的服务
    """
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举已接入的服务'),
        manual_parameters=CustomGenericViewSet.PARAMETERS_AS_ADMIN + [
            openapi.Parameter(
                name='org_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='机构id'
            ),
            openapi.Parameter(
                name='center_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='数据中心id'
            ),
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'查询条件，服务单元服务状态, {ServiceConfig.Status.choices}'
            ),
            openapi.Parameter(
                name='with_admin_users',
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description=gettext_lazy('要求返回数据包含管理员信息，此参数不需要值')
            )
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举已接入的服务

            * 参数 with_admin_users 仅在管理员身份请求时有效
            Http Code: 状态码200，返回数据：
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": 9c70cbe2-690c-11eb-a4b7-c8009fe2eb10,
                  "name": "vmware(10.0.200.243)",
                  "name_en": "string",
                  "service_type": "vmware",
                  "cloud_type": "private",
                  "add_time": "2020-10-16T09:01:44.402955Z",
                  "need_vpn": false,
                  "status": "enable",              # enable: 开启状态；disable: 停止服务状态; deleted: 删除
                  "org_data_center": {      # maybe null
                    "id": 3,
                    "name": "VMware测试中心",
                    "name_en": "xxx",
                    "sort_weight": 6,
                    "organization": {       # maybe null
                        "id": 3,
                        "name": "VMware机构",
                        "name_en": "xxx",
                    }
                  },
                  "longitude": 0,
                  "latitude": 0,
                  "pay_app_service_id": "xxx",      # 通过此id可以查询在余额结算系统中此服务可用的券
                  "sort_weight": 8,
                  "disk_available": true    # true: 提供云硬盘服务; false: 云硬盘服务不可用
                  "only_admin_visible": false,   # 是否仅管理员可见
                  "version": "v4.1.0",
                  "version_update_time": "2024-05-14T01:46:17.817050Z",  # 可能为空
                  "admin_users":[   # when query with "with_admin_users"
                    {"id": "xxx", "username": "xxxx", "role": "admin"}  # role: admin(管理员)，ops(运维管理员)
                  ]
                }
              ]
            }
        """
        return handlers.VmServiceHandler.list_services(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举用户有管理权限的服务'),
        manual_parameters=[
            openapi.Parameter(
                name='with_admin_users',
                type=openapi.TYPE_STRING,
                in_=openapi.IN_QUERY,
                required=False,
                description=gettext_lazy('要求返回数据包含管理员信息，此参数不需要值')
            )
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='admin', url_name='admin-list')
    def admin_list(self, request, *args, **kwargs):
        """
        列举用户有管理权限的服务

        Http Code: 状态码200，返回数据：
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": 9c70cbe2-690c-11eb-a4b7-c8009fe2eb10,
                  "name": "vmware(10.0.200.243)",
                  "name_en": "string",
                  "service_type": "vmware",
                  "cloud_type": "private",
                  "add_time": "2020-10-16T09:01:44.402955Z",
                  "need_vpn": false,
                  "status": "enable",              # enable: 开启状态；disable: 停止服务状态; deleted: 删除
                  "org_data_center": {      # maybe null
                    "id": 3,
                    "name": "VMware测试中心",
                    "name_en": "xxx",
                    "sort_weight": 6,
                    "organization": {       # maybe null
                        "id": 3,
                        "name": "VMware机构",
                        "name_en": "xxx",
                    }
                  },
                  "longitude": 0,
                  "latitude": 0,
                  "pay_app_service_id": "xxx",      # 通过此id可以查询在余额结算系统中此服务可用的券
                  "sort_weight": 8,
                  "disk_available": true    # true: 提供云硬盘服务; false: 云硬盘服务不可用
                  "only_admin_visible": false,   # 是否仅管理员可见
                  "version": "v4.1.0",
                  "version_update_time": "2024-05-14T01:46:17.817050Z",  # 可能为空
                  "admin_users":[   #
                    {"id": "xxx", "username": "xxxx", "role": "admin"}  # role: admin(管理员)，ops(运维管理员)
                  ]
                }
              ]
            }
        """
        with_admin_users = request.query_params.get('with_admin_users', None)
        with_admin_users = with_admin_users is not None
        service_qs = ServiceManager().get_has_perm_service(user=request.user)
        return self.paginate_service_response(request=request, qs=service_qs, with_admin_users=with_admin_users)

    @action(methods=[], detail=True, url_path='p-quota', url_name='private-quota')
    def private_quota(self, request, *args, **kwargs):
        pass

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改服务私有配额'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @private_quota.mapping.post
    def change_private_quota(self, request, *args, **kwargs):
        """
        修改服务私有配额，需要有管理员权限
        """
        return handlers.VmServiceHandler.change_private_quota(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务私有配额'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @private_quota.mapping.get
    def get_private_quota(self, request, *args, **kwargs):
        """
        查询服务私有配额，需要有管理员权限

            http code 200 ok:
            {
              "private_ip_total": 10,
              "public_ip_total": 8,
              "vcpu_total": 20,
              "ram_total": 10,       # Gb
              "disk_size_total": 0,     # GB
              "private_ip_used": 5,
              "public_ip_used": 0,
              "vcpu_used": 6,
              "ram_used": 6,         # Gb
              "disk_size_used": 0,      # GB
              "creation_time": null,
              "enable": true
            }
        """
        return handlers.VmServiceHandler.get_private_quota(
            view=self, request=request, kwargs=kwargs)

    @action(methods=[], detail=True, url_path='s-quota', url_name='share-quota')
    def share_quota(self, request, *args, **kwargs):
        pass

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务共享配额'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @share_quota.mapping.get
    def get_share_quota(self, request, *args, **kwargs):
        """
        查询服务共享配额，需要有管理员权限

            http code 200 ok:
            {
              "private_ip_total": 10,
              "public_ip_total": 8,
              "vcpu_total": 20,
              "ram_total": 10,       # Gb
              "disk_size_total": 0,     # GB
              "private_ip_used": 5,
              "public_ip_used": 0,
              "vcpu_used": 6,
              "ram_used": 6,         # Gb
              "disk_size_used": 0,      # GB
              "creation_time": null,
              "enable": true
            }
        """
        return handlers.VmServiceHandler.get_share_quota(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改服务共享配额'),

        responses={
            status.HTTP_200_OK: ''
        }
    )
    @share_quota.mapping.post
    def change_share_quota(self, request, *args, **kwargs):
        """
        修改服务共享配额，需要有管理员权限

            http code 200 ok:
            {
              "private_ip_total": 10,
              "public_ip_total": 8,
              "vcpu_total": 20,
              "ram_total": 10,       # Gb
              "disk_size_total": 0,     # GB
              "private_ip_used": 5,
              "public_ip_used": 0,
              "vcpu_used": 6,
              "ram_used": 6,         # Gb
              "disk_size_used": 0,      # GB
              "creation_time": null,
              "enable": true
            }
        """
        return handlers.VmServiceHandler.change_share_quota(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务单元资源总量'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=True, url_path='provide-quota', url_name='provide-quota')
    def service_provide_quota(self, request, *args, **kwargs):
        """
        查询服务单元（EVCloud、OpenStack、...）的总资源量

            http code 200:
            {
              "vcpu": 5152,         # 虚拟cpu总量
              "ram_gib": 800,       # 内存总量
              "servers": 332,       # 可创建云主机总数量限制
              "public_ips": null,   # 公网IP地址总量，null表示未知
              "private_ips": null,  # 私网IP地址总量
              "disk_gib": 512000,   # 云硬盘总量
              "per_disk_gib": 8192, # 每块硬盘大小上限
              "disks": null         # 可创建云硬盘总量限制
            }
        """
        try:
            service = handlers.VmServiceHandler.get_user_perm_service(
                _id=kwargs.get(self.lookup_field), user=request.user)
        except exceptions.Error as exc:
            return self.exception_response(exc)

        try:
            params = inputs.QuotaInput(region_id=service.region_id)
            r = self.request_service(service, method='get_quota', params=params)
            quota: outputs.Quota = r.quota
            return Response(data={
                'vcpu': quota.vcpu,
                'ram_gib': quota.ram_gib,
                'servers': quota.servers,
                'public_ips': quota.public_ips,
                'private_ips': quota.private_ips,
                'disk_gib': quota.disk_gib,
                'per_disk_gib': quota.per_disk_gib,
                'disks': quota.disks
            })
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询服务单元版本号'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=True, url_path='version', url_name='version')
    def update_get_version(self, request, *args, **kwargs):
        """
        查询服务单元版本号

            http code 200:
            {
              "version": "4.2.1",   # 可能为空字符串，非EVCloud时
              "version_update_time": "2024-05-14T01:46:17.817050Z"  # 可能为空，非EVCloud时
            }
        """
        try:
            service = ServiceManager.get_service_by_id(_id=kwargs.get(self.lookup_field))
            if service is None:
                raise exceptions.ServiceNotExist(message=_('服务单元不存在'))

            if (
                    service.status == ServiceConfig.Status.ENABLE.value
                    and service.service_type == ServiceConfig.ServiceType.EVCLOUD.value
            ):
                ok_or_exc = ServiceManager.update_service_version(service=service)
                if ok_or_exc is not True:
                    raise ok_or_exc
        except exceptions.Error as exc:
            return self.exception_response(exc)

        return Response(data={
            'version': service.version,
            'version_update_time': DRFDateTimeField().to_representation(service.version_update_time)
        }, status=200)

    def paginate_service_response(self, request, qs, with_admin_users: bool = False):
        paginator = self.paginator
        try:
            services = paginator.paginate_queryset(request=request, queryset=qs)
            if with_admin_users:
                self.services_mixin_admins(services=services)
                serializer = serializers.ServiceAdminSerializer(services, many=True)
            else:
                serializer = serializers.ServiceSerializer(services, many=True)

            response = paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

        return response

    @staticmethod
    def services_mixin_admins(services: list):
        """
        给服务单元添加管理员列表属性
        """
        service_ids = []
        odc_ids = []
        for sv in services:
            service_ids.append(sv.id)
            if sv.org_data_center_id not in odc_ids:
                odc_ids.append(sv.org_data_center_id)

        service_admins_map = {}
        if service_ids:
            service_admins_map = ServiceManager.get_service_admins_map(service_ids=service_ids)

        odc_admins_map = {}
        if odc_ids:
            odc_admins_map = OrgDataCenterManager.get_odc_admins_map(odc_ids=odc_ids)

        for sv in services:
            admin_dict = {}
            ops_dict = {}
            # 服务单元管理员和数据中心管理员存在相同用户时，以服务单元管理员优先，角色不去重（同一用户可以同时为管理员和运维）
            if sv.id in service_admins_map:
                sv_admins = service_admins_map[sv.id]
                for u_id, u in sv_admins.items():
                    if u['role'] == 'admin':
                        admin_dict[u_id] = u
                    else:
                        ops_dict[u_id] = u

            if sv.org_data_center_id in odc_admins_map:
                odc_admins = odc_admins_map[sv.org_data_center_id]
                for u_id, u in odc_admins.items():
                    if u['role'] == 'admin':
                        admin_dict[u_id] = u
                    else:
                        ops_dict[u_id] = u

            sv.admin_users = list(admin_dict.values()) + list(ops_dict.values())

    def get_serializer_class(self):
        if self.action == 'change_private_quota':
            return serializers.VmServicePrivateQuotaUpdateSerializer
        elif self.action == 'change_share_quota':
            return serializers.VmServiceShareQuotaUpdateSerializer

        return Serializer

    @property
    def paginator(self):
        if self.action in ['get_share_quota', 'get_private_quota']:
            return None

        return super().paginator
