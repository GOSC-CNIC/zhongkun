import requests
from io import BytesIO

from django.utils.translation import gettext_lazy, gettext as _
from django.http.response import FileResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.serializers import Serializer
from rest_framework import parsers
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.service.models import DataCenter, ApplyOrganization
from apps.servers.models import ApplyVmService
from apps.servers import format_who_action_str
from core import errors as exceptions
from apps.api.serializers import serializers
from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import DefaultPageNumberPagination
from apps.api.handlers import (
    handlers, VPNHandler,
)


class VPNViewSet(CustomGenericViewSet):
    """
    VPN相关API
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = None
    lookup_field = 'service_id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('获取VPN口令'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        获取VPN口令信息

            Http Code: 状态码200，返回数据：
            {
                "vpn": {
                    "username": "testuser",
                    "password": "password",
                    "active": true,
                    "create_time": "2020-07-29T15:12:08.715731+08:00",
                    "modified_time": "2020-07-29T15:12:08.715998+08:00"
                }
            }
            http code 409, 500:
            {
              "code": "NoResourcesInService",
              "message": "您和您所在的VO组在此服务单元中没有资源可用，不允许创建此服务单元的VPN账户"
            }
            错误码：
                409 NoResourcesInService：您和您所在的VO组在此服务单元中没有资源可用，不允许创建此服务单元的VPN账户
                500 InternalError：xxx
        """
        try:
            service = self.get_service(request, lookup=self.lookup_field, in_='path')
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        if not service.need_vpn:
            exc = exceptions.NoSupportVPN()
            return Response(exc.err_data(), status=exc.status_code)

        if VPNHandler.is_need_vpn(service_id=service.id, user=request.user):
            method = 'get_vpn_or_create'
        else:
            method = 'get_vpn'

        who_action = format_who_action_str(username=request.user.username)
        try:
            r = self.request_vpn_service(service, method=method, username=request.user.username, who_action=who_action)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.NotFound as exc:
            if method == 'get_vpn':
                exc = exceptions.ConflictError(
                    message=_('您和您所在的VO组在此服务单元中没有资源可用，不允许创建此服务单元的VPN账户'),
                    code='NoResourcesInService'
                )
            return Response(data=exc.err_data(), status=exc.status_code)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)
        return Response(data={'vpn': r})

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改vpn口令'),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The new password of vpn'
                )
            }
        ),
        responses={
            status.HTTP_201_CREATED: """
                {
                    "vpn": {
                        "username": "testuser",
                        "password": "password",
                        "active": true,
                        "create_time": "2020-07-29T15:12:08.715731+08:00",
                        "modified_time": "2020-07-29T15:12:08.715998+08:00"
                    }
                }
            """,
            status.HTTP_400_BAD_REQUEST: """
                    {
                        "code": 'xxx',
                        "message": "xxx"
                    }
                """
        }
    )
    def partial_update(self, request, *args, **kwargs):
        """
        修改vpn口令
        """
        password = request.data.get('password')

        try:
            service = self.get_service(request, lookup=self.lookup_field, in_='path')
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        if not service.need_vpn:
            exc = exceptions.NoSupportVPN()
            return Response(exc.err_data(), status=exc.status_code)

        who_action = format_who_action_str(username=request.user.username)
        try:
            r = self.request_vpn_service(service, method='vpn_change_password', username=request.user.username,
                                         password=password, who_action=who_action)
        except exceptions.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except exceptions.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)
        return Response(data={'vpn': r})

    @swagger_auto_schema(
        operation_summary=gettext_lazy('vpn配置文件下载'),
    )
    @action(methods=['get', ], detail=True, url_path='config', url_name='vpn-config')
    def vpn_config(self, request, *args, **kwargs):
        """
        vpn配置文件下载
        """
        try:
            service = self.get_service(request, lookup=self.lookup_field, in_='path')
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        if not service.need_vpn:
            exc = exceptions.NoSupportVPN()
            return Response(exc.err_data(), status=exc.status_code)

        url = self.request_vpn_service(service, 'get_vpn_config_file_url')
        r = requests.get(url)
        if r.status_code == 200:
            response = FileResponse(BytesIO(r.content), as_attachment=True, filename='config')
            response['Content-Type'] = r.headers.get('content-type')
            response['Content-Disposition'] = r.headers.get('content-disposition')
            return response

        return self.exception_response(exceptions.Error(message=str(r.content)))

    @swagger_auto_schema(
        operation_summary=gettext_lazy('vpn ca证书文件下载'),
    )
    @action(methods=['get', ], detail=True, url_path='ca', url_name='vpn-ca')
    def vpn_ca(self, request, *args, **kwargs):
        """
        vpn ca证书文件下载
        """
        try:
            service = self.get_service(request, lookup=self.lookup_field, in_='path')
        except exceptions.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        if not service.need_vpn:
            exc = exceptions.NoSupportVPN()
            return Response(exc.err_data(), status=exc.status_code)

        url = self.request_vpn_service(service, 'get_vpn_ca_file_url')
        r = requests.get(url)
        if r.status_code == 200:
            response = FileResponse(BytesIO(r.content), as_attachment=True, filename='ca')
            response['Content-Type'] = r.headers.get('content-type')
            response['Content-Disposition'] = r.headers.get('content-disposition')
            return response

        return self.exception_response(exceptions.Error(message=str(r.content)))

    @swagger_auto_schema(
        operation_summary=gettext_lazy('激活VPN账户'),
        request_body=no_body,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='active', url_name='active-vpn')
    def active_vpn(self, request, *args, **kwargs):
        """
        激活VPN账户

            Http Code: 200，成功返回数据：
            {}

            Http Code: 400,404,405, 409,500等失败：
            {
                "code": 'xxx',
                "message": "xxx"
            }

            404:
                ServiceNotExist: 服务单元不存在
            405:
                NoSupportVPN: 服务单元未提供VPN服务
            409:
                ServiceStopped: 服务单元停止服务
                NoResourcesInService：您和您所在的VO组在此服务单元中没有资源可用，不允许激活此服务单元的VPN账户
            500:
                InternalError： xxx
        """
        return VPNHandler.active_vpn(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('停用VPN账户'),
        request_body=no_body,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='deactive', url_name='deactive-vpn')
    def deactive_vpn(self, request, *args, **kwargs):
        """
        停用VPN账户

            Http Code: 200，成功返回数据：
            {}

            Http Code: 400,404,405, 409,500等失败：
            {
                "code": 'xxx',
                "message": "xxx"
            }

            404:
                ServiceNotExist: 服务单元不存在
            405:
                NoSupportVPN: 服务单元未提供VPN服务
            409:
                ServiceStopped: 服务单元停止服务
                NoResourcesInService：您和您所在的VO组在此服务单元中没有资源可用，不允许激活此服务单元的VPN账户
            500:
                InternalError： xxx
        """
        return VPNHandler.deactive_vpn(view=self, request=request)

    def get_serializer_class(self):
        return Serializer

    def get_permissions(self):
        if self.action in ['vpn_config', 'vpn_ca']:
            return []

        return super().get_permissions()


class DataCenterViewSet(CustomGenericViewSet):
    """
    联邦成员机构
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = None

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦成员机构注册表'),
        responses={
            status.HTTP_200_OK: ''
        },
        deprecated=True
    )
    def list(self, request, *args, **kwargs):
        """
        联邦成员机构注册表

            Http Code: 状态码200，返回数据：
            {
              "registries": [
                {
                  "id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
                  "name": "网络中心",
                  "name_en": "string",
                  "abbreviation": "xxx"
                  "creation_time": 2021-02-07T06:20:00Z,
                  "status": {
                    "code": 1,
                    "message": "开启状态"
                  },
                  "desc": "",
                  "longitude": 0,
                  "latitude": 0,
                  "sort_weight": 6                        # 排序值，由小到大
                }
              ]
            }
        """
        try:
            queryset = DataCenter.objects.all()
            serializer = serializers.DataCenterSerializer(queryset, many=True)
            data = {
                'registries': serializer.data
            }
        except Exception as exc:
            err = exceptions.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

        return Response(data=data)


class ApplyOrganizationViewSet(CustomGenericViewSet):
    """
    机构/数据中心申请视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'

    list_manual_parameters = [
        openapi.Parameter(
            name='deleted',
            in_=openapi.IN_QUERY,
            required=False,
            type=openapi.TYPE_BOOLEAN,
            description=gettext_lazy('筛选参数，true(只返回已删除的申请记录)；false(不包含已删除的申请记录)')
        ),
        openapi.Parameter(
            name='status',
            in_=openapi.IN_QUERY,
            required=False,
            type=openapi.TYPE_STRING,
            enum=ApplyOrganization.Status.values,
            description=gettext_lazy('筛选参数，筛选指定状态的申请记录')
        )
    ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举机构申请'),
        manual_parameters=list_manual_parameters,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举机构申请

            http code 200 ok:
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "69580ac6-c439-11eb-9c87-c8009fe2eb10",
                  "creation_time": null,
                  "status": "wait",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  },
                  "deleted": false,
                  "name": "test",
                  "name_en": "string",
                  "abbreviation": "tt",
                  "independent_legal_person": true,
                  "country": "中国",
                  "city": "北京",
                  "postal_code": "274100",
                  "address": "string",
                  "endpoint_vms": "",
                  "endpoint_object": "",
                  "endpoint_compute": "",
                  "endpoint_monitor": "",
                  "desc": "string",
                  "logo_url": "string",
                  "certification_url": "string",
                  "longitude": 0,
                  "latitude": 0
                }
              ]
            }
        """
        return handlers.ApplyOrganizationHandler.list_apply(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员列举机构申请'),
        manual_parameters=list_manual_parameters,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='admin', url_name='admin-list')
    def admin_list(self, request, *args, **kwargs):
        """
        联邦管理员列举机构申请
        """
        return handlers.ApplyOrganizationHandler.admin_list_apply(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('提交机构/数据中心创建申请'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        提交机构/数据中心创建申请

            Http Code: 状态码200，返回数据：
            {
              "id": "be1f706c-c43e-11eb-867e-c8009fe2eb10",
              "creation_time": null,
              "status": "wait",
              "user": {
                "id": "1",
                "username": "shun"
              },
              "deleted": false,
              "name": "中国科学院计算机信息网络中心",
              "name_en": "string",
              "abbreviation": "中科院网络中心",
              "independent_legal_person": true,
              "country": "中国",
              "city": "北京",
              "postal_code": "100083",
              "address": "北京市海淀区",
              "endpoint_vms": "https://vms.cstcloud.cn/",
              "endpoint_object": "",
              "endpoint_compute": "",
              "endpoint_monitor": "",
              "desc": "test",
              "logo_url": "/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg",
              "certification_url": "/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx",
              "longitude": 0,
              "latitude": 0
            }
            补充说明:
            "status" values:
                wait: 待审批              # 允许申请者修改
                cancel: 取消申请        # 只允许申请者取消
                pending: 审批中            # 挂起，不允许申请者修改，只允许管理者审批
                pass: 审批通过
                reject: 拒绝

            http code 400, 401, 403, 404, 409, 500:
            {
              "code": "xxx",            # "TooManyApply",
              "message": "xxx"             # "您已提交了多个申请，待审批，暂不能提交更多的申请"
            }
        """
        return handlers.ApplyOrganizationHandler.create_apply(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除申请'),
        responses={
            status.HTTP_204_NO_CONTENT: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除
        """
        return handlers.ApplyOrganizationHandler.delete_apply(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('操作审批一个申请'),
        request_body=no_body,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='action/(?P<action>.+)', url_name='action')
    def apply_action(self, request, *args, **kwargs):
        """
        操作审批一个申请

            * action命令选项：
                cancel：取消申请
                pending：挂起申请（审核中）
                reject：拒绝
                pass：通过

            http code 200 ok:
                {
                  "id": "e7dc0622-c43e-11eb-9b23-c8009fe2eb10",
                  "creation_time": null,
                  "status": "pending",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  },
                  "deleted": true,
                  "name": "中国科学院计算机信息网络中心",
                  "name_en": "cnic",
                  "abbreviation": "中科院网络中心",
                  "independent_legal_person": true,
                  "country": "中国",
                  "city": "北京",
                  "postal_code": "100083",
                  "address": "北京市海淀区",
                  "endpoint_vms": "https://vms.cstcloud.cn/",
                  "endpoint_object": "",
                  "endpoint_compute": "",
                  "endpoint_monitor": "",
                  "desc": "test",
                  "logo_url": "/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg",
                  "certification_url": "/certification/c5ff90480c7fc7c9125ca4dd86553e23.docx"
                }
            http code 400, 401, 403, 404, 409, 500:
                {
                  "code": "xxx",                # 错误码
                  "message": "xxx"              # 错误信息
                }
        """
        return handlers.ApplyOrganizationHandler.apply_action(
            view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.ApplyOrganizationSerializer

        return Serializer


class ApplyVmServiceViewSet(CustomGenericViewSet):
    """
    云主机服务接入申请视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'id'

    list_manual_parameters = [
        openapi.Parameter(
            name='deleted',
            in_=openapi.IN_QUERY,
            required=False,
            type=openapi.TYPE_BOOLEAN,
            description=gettext_lazy('筛选参数，true(只返回已删除的申请记录)；false(不包含已删除的申请记录)')
        ),
        openapi.Parameter(
            name='organization',
            in_=openapi.IN_QUERY,
            required=False,
            type=openapi.TYPE_STRING,
            description=gettext_lazy('筛选参数，机构id')
        ),
        openapi.Parameter(
            name='status',
            in_=openapi.IN_QUERY,
            required=False,
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(
                type=openapi.TYPE_STRING,
                enum=ApplyVmService.Status.values
            ),
            description=gettext_lazy('筛选参数，筛选指定状态的申请记录')
        )
    ]

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举云主机服务接入申请'),
        manual_parameters=list_manual_parameters,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举云主机服务接入申请

            http code 200 ok:
            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "deec2f54-bf86-11eb-bf23-c8009fe2eb10",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  },
                  "creation_time": "2021-05-28T07:32:35.153984Z",
                  "approve_time": "2021-05-28T07:32:35.154143Z",
                  "status": "wait",
                  "organization_id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
                  "longitude": 0,
                  "latitude": 0,
                  "name": "string",
                  "name_en": "string",
                  "region": "1",
                  "service_type": "evcloud",
                  "cloud_type": "private",
                  "endpoint_url": "http://159.226.235.3",
                  "api_version": "v3",
                  "username": "string",
                  "password": "string",
                  "project_name": "string",
                  "project_domain_name": "string",
                  "user_domain_name": "string",
                  "need_vpn": true,
                  "vpn_endpoint_url": "string",
                  "vpn_api_version": "string",
                  "vpn_username": "string",
                  "vpn_password": null,
                  "deleted": false,
                  "contact_person": "string",
                  "contact_email": "user@example.com",
                  "contact_telephone": "string",
                  "contact_fixed_phone": "string",
                  "contact_address": "string",
                  "remarks": "string",
                  "logo_url": ""
                }
              ]
            }
        """
        return handlers.ApplyVmServiceHandler.list_apply(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('联邦管理员列举云主机服务接入申请'),
        manual_parameters=list_manual_parameters,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='admin', url_name='admin-list')
    def admin_list(self, request, *args, **kwargs):
        """
        联邦管理员列举云主机服务接入申请

            http code 200 ok:

        """
        return handlers.ApplyVmServiceHandler.admin_list_apply(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('提交云主机服务接入申请'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        提交云主机服务接入申请

            Http Code: 状态码200，返回数据：
            {
              "id": "deec2f54-bf86-11eb-bf23-c8009fe2eb10",
              "user": {
                "id": "1",
                "username": "shun"
              },
              "creation_time": "2021-05-28T07:32:35.153984Z",
              "approve_time": "2021-05-28T07:32:35.154143Z",
              "status": "wait",
              "organization_id": "9c70cbe2-690c-11eb-a4b7-c8009fe2eb10",
              "center_apply_id": null,
              "longitude": 0,
              "latitude": 0,
              "name": "string",
              "name_en": "string",
              "region": "1",
              "service_type": "evcloud",
              "cloud_type": "private",
              "endpoint_url": "http://159.226.235.3",
              "api_version": "v3",
              "username": "string",
              "password": "#e9xd3xa2x8exd8xd3",
              "project_name": "string",
              "project_domain_name": "string",
              "user_domain_name": "string",
              "need_vpn": true,
              "vpn_endpoint_url": "string",
              "vpn_api_version": "string",
              "vpn_username": "string",
              "vpn_password": "string",
              "deleted": false,
              "contact_person": "string",
              "contact_email": "user@example.com",
              "contact_telephone": "string",
              "contact_fixed_phone": "string",
              "contact_address": "string",
              "remarks": "string"
            }
            补充说明:
            "status" values:
                wait: 待审批              # 允许申请者修改
                cancel: 取消申请        # 只允许申请者取消
                pending: 审批中            # 挂起，不允许申请者修改，只允许管理者审批
                first_pass: 初审通过
                first_reject: 初审拒绝
                test_failed: 测试未通过
                test_pass: 测试通过
                pass: 审批通过
                reject: 拒绝
        """
        return handlers.ApplyVmServiceHandler.create_apply(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('操作审批一个申请'),
        request_body=no_body,
        responses={
            status.HTTP_200_OK: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='action/(?P<action>.+)', url_name='action')
    def apply_action(self, request, *args, **kwargs):
        """
        操作审批一个申请

            * action命令选项：
                cancel：取消申请
                pending：挂起申请（审核中）
                first_pass：初审通过
                first_reject：初审拒绝
                test：测试
                reject：拒绝
                pass：通过

            http code 200 ok (test命令除外) response A:
            {
                'id': '9417080a-c7fb-11eb-8525-c8009fe2eb10',
                'user': {'id': '94104e5c-c7fb-11eb-8525-c8009fe2eb10', 'username': 'test'},
                'creation_time': '2021-06-08T01:48:10.020838Z',
                'approve_time': '2021-06-08T01:48:10.070267Z',
                'status': 'test_pass',
                'organization_id': '94142dec-c7fb-11eb-8525-c8009fe2eb10',
                'longitude': 0.0,
                'latitude': 0.0,
                'name': '地球大数据',
                "name_en": "string",
                'region': '1',
                'service_type': 'evcloud',
                'endpoint_url': 'http://159.226.235.3/',
                'api_version': 'v3',
                'username': '869588058@qq.com',
                'password': 'wangyushun',
                'project_name': '',
                'project_domain_name': '',
                'user_domain_name': '',
                'need_vpn': True,
                'vpn_endpoint_url': '',
                'vpn_api_version': '',
                'vpn_username': '',
                'vpn_password': '',
                'deleted': False,
                'contact_person': 'shun',
                'contact_email': 'user@example.com',
                'contact_telephone': 'string',
                'contact_fixed_phone': 'string',
                'contact_address': '北京信息化大厦',
                'remarks': 'string',
                'logo_url': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg'
            }

            * "test" action response B:
            {
                'ok': bool,         # true: 测试通过；false: 测试失败
                'message': '',      # 测试失败描述
                'apply': {
                    参考 response A
                }
            }
        """
        return handlers.ApplyVmServiceHandler.apply_action(
            view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除申请'),
        responses={
            status.HTTP_204_NO_CONTENT: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除
        """
        return handlers.ApplyVmServiceHandler.delete_apply(
            view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.ApplyVmServiceCreateSerializer

        return Serializer


class MediaViewSet(CustomGenericViewSet):
    """
    静态文件视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = None
    # parser_classes = [parsers.FileUploadParser]
    lookup_field = 'url_path'
    lookup_value_regex = '.+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('上传文件'),
        request_body=openapi.Schema(
            title='二进制数据',
            type=openapi.TYPE_STRING,
            format=openapi.FORMAT_BINARY,
        ),
        manual_parameters=[
            openapi.Parameter(
                name='Content-MD5', in_=openapi.IN_HEADER,
                type=openapi.TYPE_STRING,
                description=gettext_lazy("文件对象hex md5"),
                required=True
            ),
        ],
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        上传文件

        * 必须提交标头Content-MD5、Content-Length，将根据提供的MD5值检查对象，如果不匹配，则返回错误。
        * 数据以二进制格式直接填充请求体

        * 上传logo图片，请务必使用logo前缀区分，即url_path = logo/test.png;
        * 机构/组织独立法人单位认证码文件，请务必使用certification前缀区分，即url_path = certification/test.docx;

            http code 200:
            {
                'url_path': '/api/media/logo/c5ff90480c7fc7c9125ca4dd86553e23.jpg'     # 上传文件对应的下载路径
            }
        """
        return handlers.MediaHandler.media_upload(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('下载文件'),
        responses={
            status.HTTP_200_OK: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        下载文件
        """
        return handlers.MediaHandler.media_download(view=self, request=request, kwargs=kwargs)

    def get_parsers(self):
        """
        动态分配请求体解析器
        """
        method = self.request.method.lower()
        act = self.action_map.get(method)
        if act == 'update':
            return [parsers.FileUploadParser()]

        return super().get_parsers()

    def get_permissions(self):
        if self.action in ['retrieve']:
            return []

        return super().get_permissions()
