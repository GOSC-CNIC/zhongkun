from django.utils.translation import gettext as _
from rest_framework import viewsets

from oneservice import exceptions as os_exceptions
from servers.models import ServiceConfig
from . import auth
from . import exceptions


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


class CustomGenericViewSet(viewsets.GenericViewSet):
    def get_service_auth_header(self, service, refresh=False):
        """
        :param service:
        :param refresh:
        :return:
            {}
        :raises: AuthenticationFailed
        """
        t = auth.get_auth(service, refresh=refresh)
        h = t.header
        return {h.header_name: h.header_value}

    def request_service(self, service, method: str, **kwargs):
        """
        向服务发送请求

        :param service: 接入的服务配置对象
        :param method:
        :param kwargs:
        :return:

        :raises: APIException, AuthenticationFailed
        """
        headers = self.get_service_auth_header(service)

        client = auth.get_service_client(service)
        handler = getattr(client, method)
        for _ in range(2):
            try:
                return handler(headers=headers, **kwargs)
            except os_exceptions.AuthenticationFailed:
                headers = self.get_service_auth_header(service, refresh=True)
                continue
            except os_exceptions.Error as exc:
                raise exceptions.APIException(message=exc.message)

        raise exceptions.APIException()

    def get_service(self, request, lookup='service_id', in_='query'):
        """

        :param request:
        :param lookup:
        :param in_: ['query', 'body']
        :return:

        :raises: APIException
        """
        if in_ == 'query':
            service_id = request.query_params.get(lookup, None)
        else:
            service_id = request.data.get(lookup, None)

        if service_id is None:
            raise exceptions.NoFoundArgument(extend_msg=f'"{lookup}" param were not provided')

        service_id = str_to_int_or_default(service_id, default=0)
        if service_id <= 0:
            raise exceptions.InvalidArgument(_('参数"service_id"值无效.'))

        service = ServiceConfig.objects.filter(id=service_id, active=True).first()
        if not service:
            raise exceptions.NotFound(_('服务端点不存在'))

        return service
