from django.utils.translation import gettext_lazy, gettext as _
from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema

from api.viewsets import CustomGenericViewSet
from api.paginations import DefaultPageNumberPagination
from users.managers import filter_user_queryset
from monitor.models import TotalReqNum
from core import errors
from utils import get_remote_ip
from utils.paginators import NoPaginatorInspector


class InAllowedIp(BasePermission):
    def has_permission(self, request, view):
        allowd, addr_ip = self.check_addr_allowed(request=request)
        return allowd

    @staticmethod
    def check_addr_allowed(request):
        remote_ip, proxys = get_remote_ip(request)
        allowed_ips = getattr(settings, 'API_KJY_PORTAL_ALLOWED_IPS', [])
        if allowed_ips and remote_ip in allowed_ips:
            return True, remote_ip

        return False, remote_ip


class PortalServiceViewSet(CustomGenericViewSet):
    permission_classes = []
    pagination_class = DefaultPageNumberPagination

    @swagger_auto_schema(
        operation_summary=gettext_lazy('服务可用性查询'),
        paginator_inspectors=[NoPaginatorInspector],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='status', url_name='status')
    def service_status(self, request, *args, **kwargs):
        """
        服务可用性查询

            Http Code: 状态码200，返回数据：
            {
              "code": 200,
              "status": "success" # success 表示可访问，failure 表示不可访问
            }
        """
        r = self.allowed_addr_ip(request=request)
        if r:
            return r

        return Response(data={
            'code': 200,
            'status': 'success'
        })

    @swagger_auto_schema(
        operation_summary=gettext_lazy('服务用户数查询'),
        paginator_inspectors=[NoPaginatorInspector],
        responses={200: ''}
    )
    @action(methods=['get'], detail=False, url_path='user-num', url_name='user-num')
    def user_number(self, request, *args, **kwargs):
        """
        服务用户数查询

            Http Code 200 ok:
            {
              "code": 200,
              "num": 1234
            }
        """
        r = self.allowed_addr_ip(request=request)
        if r:
            return r

        qs = filter_user_queryset()
        user_num = qs.count()
        return Response(data={
            'code': 200,
            'num': user_num
        })

    @swagger_auto_schema(
        operation_summary=gettext_lazy('服务总请求数查询'),
        paginator_inspectors=[NoPaginatorInspector],
        responses={200: ''}
    )
    @action(methods=['get'], detail=False, url_path='total-req-num', url_name='total-req-num')
    def req_number(self, request, *args, **kwargs):
        """
        服务总请求数查询

            Http Code 200 ok:
            {
              "code": 200,
              "num": 312734,
              "until_time": "2023-07-25T00:00:00+00:00"
            }
        """
        r = self.allowed_addr_ip(request=request)
        if r:
            return r

        ins = TotalReqNum.get_instance()
        return Response(data={
            'code': 200,
            'num': ins.req_num,
            'until_time': ins.until_time.isoformat()
        })

    def get_serializer_class(self):
        return Serializer

    def allowed_addr_ip(self, request):
        allowd, addr_ip = InAllowedIp.check_addr_allowed(request=request)
        if not allowd:
            return self.exception_response(
                errors.AccessDenied(message=_('您的地址%(value)s没有访问权限。') % {'value': addr_ip}))

        return None
