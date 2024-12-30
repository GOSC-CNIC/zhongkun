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

from apps.app_service.models import DataCenter
from apps.app_servers import format_who_action_str
from core import errors as exceptions
from apps.api.serializers import serializers
from apps.api.viewsets import CustomGenericViewSet
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
