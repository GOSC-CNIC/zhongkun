from django.utils.translation import gettext_lazy, gettext as _
from django.http import Http404
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.views import set_rollback
from rest_framework.response import Response
from rest_framework.exceptions import (APIException, NotAuthenticated, AuthenticationFailed)
from drf_yasg import openapi

from core.request import request_service, request_vpn_service
from core import errors as exceptions
from apps.servers.managers import ServiceManager
from apps.storage.request import request_service as storage_request_service
from apps.storage.models import ObjectsService
from apps.storage.managers import ObjectsServiceManager
from apps.monitor.models import ErrorLog
from . import request_logger as logger


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


def serializer_error_msg(errors, default=''):
    """
    获取一个错误信息

    :param errors: serializer.errors
    :param default:
    :return:
        str
    """
    msg = default
    try:
        if isinstance(errors, list):
            for err in errors:
                msg = str(err)
                break
        elif isinstance(errors, dict):
            for key in errors:
                val = errors[key]
                if isinstance(val, list):
                    msg = f'{key}, {str(val[0])}'
                else:
                    msg = f'{key}, {str(val)}'

                break
    except Exception:
        pass

    return msg


def exception_handler(exc, context):
    """
    Returns the response that should be used for any given exception.

    By default we handle the REST framework `APIException`, and also
    Django's built-in `Http404` and `PermissionDenied` exceptions.

    Any unhandled exceptions may return `None`, which will cause a 500 error
    to be raised.
    """
    import traceback
    print(traceback.format_exc())
    if isinstance(exc, exceptions.Error):
        pass
    elif isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, PermissionDenied):
        exc = exceptions.AccessDenied(message=str(exc))
    elif isinstance(exc, AuthenticationFailed):
        exc = exceptions.AuthenticationFailed(message=str(exc))
    elif isinstance(exc, NotAuthenticated):
        exc = exceptions.NotAuthenticated(message=str(exc))
    elif isinstance(exc, APIException):
        if isinstance(exc.detail, (list, dict)):
            data = exc.detail
        else:
            data = {'detail': exc.detail}

        exc = exceptions.Error(message=str(data), status_code=exc.status_code, code=exc.default_code)
    else:
        exc = exceptions.convert_to_error(exc)

    set_rollback()
    status_code = exc.status_code
    method = ''
    full_path = ''
    username = ''
    err_msg = msg = str(exc)
    try:
        request = context.get('request', None)
        if request:
            method = request.method
            full_path = request.get_full_path()
            if bool(request.user and request.user.is_authenticated):
                username = request.user.username

            msg = f'{status_code} {method} {full_path} [{msg}]'
    except Exception:
        pass

    ErrorLog.add_log(status_code=status_code, method=method, full_path=full_path, message=err_msg, username=username)
    logger.error(msg=msg)
    return Response(exc.err_data(), status=status_code)


def log_err_response(_logger, request, response):
    """
    状态码>=400才记录
    """
    status_code = response.status_code
    method = request.method
    full_path = request.get_full_path()
    msg = f'{status_code} {method} {full_path}'
    err_msg = ''
    if 400 <= status_code:
        err_msg = response.data.get('message', '')
        code = response.data.get('code', '')
        if err_msg and code:
            err_msg = f'[{code}:{err_msg}]'
        if not err_msg:
            err_msg = f'{response.data}'

        msg = f'{msg} {err_msg}'

    username = ''
    if bool(request.user and request.user.is_authenticated):
        username = request.user.username

    ErrorLog.add_log(status_code=status_code, method=method, full_path=full_path, message=err_msg, username=username)

    if 400 <= response.status_code < 500:
        _logger.warning(msg)
    elif response.status_code >= 500:
        _logger.error(msg)
    else:
        pass


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


class BaseGenericViewSet(viewsets.GenericViewSet):
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request=request, response=response, *args, **kwargs)
        # 如果是发生了异常，异常处理函数内已经记录了日志
        if getattr(response, 'exception', False):
            return response

        try:
            if response.status_code >= 400:
                log_err_response(_logger=logger, request=request, response=response)
                response._has_been_logged = True    # 告诉django已经记录过日志，不需再此记录了
        except Exception:
            pass

        return response


class NormalGenericViewSet(CustomGenericViewSetMixin, BaseGenericViewSet):
    from django.db.models import QuerySet
    queryset = QuerySet().none()


class CustomGenericViewSet(CustomGenericViewSetMixin, BaseGenericViewSet):
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


class StorageGenericViewSet(CustomGenericViewSetMixin, BaseGenericViewSet):
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


class AsRoleGenericViewSet(BaseGenericViewSet):
    from django.db.models import QuerySet
    queryset = QuerySet().none()

    AS_ROLE_ADMIN = 'admin'

    PARAMETERS_AS_ROLE = [
        openapi.Parameter(
            name='as_role',
            in_=openapi.IN_QUERY,
            type=openapi.TYPE_STRING,
            required=False,
            description=gettext_lazy('以指定的身份请求，如果无对应权限会返回403错误。') + f'[{AS_ROLE_ADMIN}]'
        ),
    ]

    def check_as_role_request(self, request):
        """
        是否是以指定的身份请求

        :return:
            {
                bool,       # True: 指定身份请求；False: 未指定身份请求
                str         # 指定的身份参数值
            }
        :raises: Error
        """
        as_role = request.query_params.get('as_role', None)
        if as_role is None:
            return False, None

        if as_role not in [self.AS_ROLE_ADMIN]:
            raise exceptions.InvalidArgument(message=_('指定的身份无效'), code='InvalidAsRole')

        return True, as_role

    @staticmethod
    def exception_response(exc):
        if not isinstance(exc, exceptions.Error):
            exc = exceptions.Error(message=str(exc))

        return Response(data=exc.err_data(), status=exc.status_code)
