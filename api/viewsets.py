from django.utils.translation import gettext_lazy, gettext as _
from django.http import Http404
from django.core.exceptions import PermissionDenied
from rest_framework import viewsets
from rest_framework.views import set_rollback
from rest_framework.response import Response
from rest_framework.exceptions import (APIException, NotAuthenticated, AuthenticationFailed)
from drf_yasg import openapi

from service.models import ServiceConfig
from core.request import request_service, request_vpn_service
from core import errors as exceptions


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
    return Response(exc.err_data(), status=exc.status_code)


class CustomGenericViewSet(viewsets.GenericViewSet):
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
        service = ServiceConfig.objects.select_related('data_center').filter(
            id=service_id, status=ServiceConfig.Status.ENABLE).first()

        if not service:
            raise exceptions.ServiceNotExist(_('服务端点不存在'))

        return service

    @staticmethod
    def exception_response(exc):
        if not isinstance(exc, exceptions.Error):
            exc = exceptions.Error(message=str(exc))

        return Response(data=exc.err_data(), status=exc.status_code)
