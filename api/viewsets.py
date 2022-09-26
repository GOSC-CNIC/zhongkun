from django.utils.translation import gettext_lazy, gettext as _
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.conf import settings
from rest_framework import viewsets
from rest_framework.views import set_rollback
from rest_framework.response import Response
from rest_framework.exceptions import (APIException, NotAuthenticated, AuthenticationFailed)
from drf_yasg import openapi

from core.request import request_service, request_vpn_service
from core import errors as exceptions
from service.managers import ServiceManager
from storage.request import request_service as storage_request_service
from storage.models import ObjectsService
from storage.managers import ObjectsServiceManager
from . import request_logger as logger
from .signers import SignatureResponse, SignatureRequest, SignatureParser
from bill.models import PayApp


def str_to_int_or_default(val, default):
    """
    字符串转int，转换失败返回设置的默认值

    :param val: 待转化的字符串
    :param default: 转换失败返回的值
    :return:
        int     # success
        default # failed
    """
    try:
        return int(val)
    except Exception:
        return default


def exception_handler(exc, context):
    """
    Returns the response that should be used for any given exception.

    By default we handle the REST framework `APIException`, and also
    Django's built-in `Http404` and `PermissionDenied` exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    if isinstance(exc, exceptions.Error):
        set_rollback()
        return Response(exc.err_data(), status=exc.status_code)

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.AccessDenied()
    elif isinstance(exc, AuthenticationFailed):
        exc = exceptions.AuthenticationFailed()
    elif isinstance(exc, NotAuthenticated):
        exc = exceptions.NotAuthenticated()
    elif isinstance(exc, APIException):
        if isinstance(exc.detail, (list, dict)):
            data = exc.detail
        else:
            data = {'detail': exc.detail}

        exc = exceptions.Error(message=str(data), status_code=exc.status_code, code=exc.default_code)
    else:
        exc = exceptions.convert_to_error(exc)

    set_rollback()
    logger.error(msg=str(exc))
    return Response(exc.err_data(), status=exc.status_code)


class CustomGenericViewSetMixin:
    PARAMETERS_AS_ADMIN = [
        openapi.Parameter(
            name='as-admin',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_BOOLEAN,
            required=False,
            description=gettext_lazy('以管理员身份请求，如果无管理员权限会返回403错误； 参数不需要值，存在即有效')
        ),
    ]

    @staticmethod
    def is_as_admin_request(request):
        """
        是否是以管理员的身份请求
        """
        as_admin = request.query_params.get('as-admin', None)
        if as_admin is None:
            return False

        return True

    @staticmethod
    def exception_response(exc):
        if not isinstance(exc, exceptions.Error):
            exc = exceptions.Error(message=str(exc))

        return Response(data=exc.err_data(), status=exc.status_code)


class CustomGenericViewSet(CustomGenericViewSetMixin, viewsets.GenericViewSet):
    from django.db.models import QuerySet
    queryset = QuerySet().none()

    @staticmethod
    def request_service(service, method: str, **kwargs):
        """
        向服务发送请求

        :param service: 接入的服务配置对象
        :param method:
        :param kwargs:
        :return:

        :raises: APIException
        """
        return request_service(service=service, method=method, **kwargs)

    @staticmethod
    def request_vpn_service(service, method: str, **kwargs):
        """
        向vpn服务发送请求

        :param service: 接入的服务配置对象
        :param method:
        :param kwargs:
        :return:

        :raises: APIException
        """
        return request_vpn_service(service=service, method=method, **kwargs)

    def get_service(self, request, lookup='service_id', in_='query'):
        """

        :param request:
        :param lookup:
        :param in_: ['query', 'body', 'path']
        :return:

        :raises: APIException
        """
        if in_ == 'query':
            service_id = request.query_params.get(lookup, None)
        elif in_ == 'body':
            service_id = request.data.get(lookup, None)
        else:
            service_id = self.kwargs.get(lookup, None)

        if service_id is None:
            raise exceptions.NoFoundArgument(extend_msg=f'"{lookup}" param were not provided')

        if not service_id:
            raise exceptions.InvalidArgument(_('参数"service_id"值无效.'))

        return self.get_service_by_id(service_id)

    @staticmethod
    def get_service_by_id(service_id):
        return ServiceManager.get_service(service_id=service_id)


class PaySignGenericViewSet(CustomGenericViewSetMixin, viewsets.GenericViewSet):
    """
    仅限JSON格式数据api视图使用
    """
    from django.db.models import QuerySet
    queryset = QuerySet().none()

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        signer = SignatureResponse(private_key=settings.PAYMENT_RSA2048['private_key'])
        response = signer.add_sign(response=response)
        return response

    def initialize_request(self, request, *args, **kwargs):
        request = super().initialize_request(request, *args, **kwargs)
        # 因为json parse时直接转成字典格式了，所以在json parse之前读取body以保存原始body bytes
        # 在视图之前有可能会触发json parse，比如CSRF会读django.POST
        body = request.body
        return request

    @staticmethod
    def check_request_sign(request):
        """
        :raise: Error
        """
        parser = SignatureParser(sign_type=SignatureRequest.SING_TYPE)
        token = parser.get_token_in_header(request)
        auth_type, app_id, timestamp, signature = parser.parse_token(token)
        app = PayApp.objects.filter(id=app_id).first()
        if app is None:
            raise exceptions.NotFound(
                message=_('app_id不存在'), code='NoSuchAPPID'
            )

        if app.status == PayApp.Status.UNAUDITED.value:
            raise exceptions.ConflictError(
                message=_('应用处于未审核状态'), code='AppStatusUnaudited'
            )
        elif app.status == PayApp.Status.BAN.value:
            raise exceptions.ConflictError(
                message=_('应用处于禁止状态'), code='AppStatusBan'
            )

        if not app.rsa_public_key:
            raise exceptions.ConflictError(
                message=_('app未配置RSA公钥'), code='NoSetPublicKey'
            )
        try:
            sr = SignatureRequest(request=request, public_key=app.rsa_public_key)
        except exceptions.Error as e:
            raise e

        method = request.method.upper()
        uri = request.path      # 为编码的
        body = request.body
        ok = sr.verify_signature(
            timestamp=timestamp, method=method, uri=uri,
            querys=request.query_params,
            body=body.decode(encoding='utf-8'), sig=signature
        )
        if not ok:
            raise exceptions.AuthenticationFailed(
                message=_('签名无效'), code='InvalidSignature'
            )

        return app


class StorageGenericViewSet(CustomGenericViewSetMixin, viewsets.GenericViewSet):
    from django.db.models import QuerySet
    queryset = QuerySet().none()

    @staticmethod
    def request_service(service: ObjectsService, method: str, **kwargs):
        """
        向服务发送请求

        :param service: 接入的服务配置对象
        :param method:
        :param kwargs:
        :return:

        :raises: APIException
        """
        return storage_request_service(service=service, method=method, **kwargs)

    def get_service(self, request, lookup='service_id', in_='query') -> ObjectsService:
        """

        :param request:
        :param lookup:
        :param in_: ['query', 'body', 'path']
        :return:

        :raises: APIException
        """
        if in_ == 'query':
            service_id = request.query_params.get(lookup, None)
        elif in_ == 'body':
            service_id = request.data.get(lookup, None)
        else:
            service_id = self.kwargs.get(lookup, None)

        if service_id is None:
            raise exceptions.NoFoundArgument(extend_msg=f'"{lookup}" param were not provided')

        if not service_id:
            raise exceptions.InvalidArgument(_('参数"service_id"值无效.'))

        return self.get_service_by_id(service_id)

    @staticmethod
    def get_service_by_id(service_id: str):
        return ObjectsServiceManager.get_service(service_id=service_id)


class NormalGenericViewSet(viewsets.GenericViewSet):
    from django.db.models import QuerySet
    queryset = QuerySet().none()

    @staticmethod
    def exception_response(exc):
        if not isinstance(exc, exceptions.Error):
            exc = exceptions.Error(message=str(exc))

        return Response(data=exc.err_data(), status=exc.status_code)
