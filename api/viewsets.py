from django.utils.translation import gettext as _
from rest_framework import viewsets

from servers.models import ServiceConfig
from .request import request_service
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
    @staticmethod
    def request_service(service, method: str, **kwargs):
        """
        向服务发送请求

        :param service: 接入的服务配置对象
        :param method:
        :param kwargs:
        :return:

        :raises: APIException, AuthenticationFailed
        """
        return request_service(service=service, method=method, **kwargs)

    @staticmethod
    def get_service(request, lookup='service_id', in_='query'):
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
