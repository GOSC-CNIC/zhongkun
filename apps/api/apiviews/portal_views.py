from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import BasePermission
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema

from core import errors
from utils.paginators import NoPaginatorInspector
from utils.iprestrict import IPRestrictor
from apps.app_global.configs_manager import IPAccessWhiteListManager
from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import DefaultPageNumberPagination
from apps.app_users.managers import filter_user_queryset
from apps.app_monitor.models import TotalReqNum


class PortalIPRestrictor(IPRestrictor):
    def load_ip_rules(self):
        return IPAccessWhiteListManager.get_module_ip_whitelist(
            module_name=IPAccessWhiteListManager.ModuleName.PORTAL.value)

    @staticmethod
    def clear_cache():
        IPAccessWhiteListManager.clear_cache()

    @staticmethod
    def add_ip_rule(ip_value: str):
        return IPAccessWhiteListManager.add_whitelist_obj(
            module_name=IPAccessWhiteListManager.ModuleName.PORTAL.value, ip_value=ip_value)

    @staticmethod
    def remove_ip_rules(ip_values: list):
        return IPAccessWhiteListManager.delete_whitelist(
            module_name=IPAccessWhiteListManager.ModuleName.PORTAL.value, ip_values=ip_values)


class InAllowedIp(BasePermission):
    def has_permission(self, request, view):
        PortalIPRestrictor().check_restricted(request)
        return True

    @staticmethod
    def check_addr_allowed(request):
        remote_ip, proxys = PortalIPRestrictor.get_remote_ip(request)
        try:
            PortalIPRestrictor().is_restricted(client_ip=remote_ip)
        except errors.AccessDenied as exc:
            return False, remote_ip

        return True, remote_ip


class PortalServiceViewSet(CustomGenericViewSet):
    permission_classes = [InAllowedIp]
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
              "count": 1234
            }
        """
        qs = filter_user_queryset()
        user_num = qs.count()
        return Response(data={
            'code': 200,
            'count': user_num
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
        total_req_num = 0
        until_time = None
        qs = TotalReqNum.objects.filter(
            service_type__in=TotalReqNum.ServiceType.values
        )
        for i in qs:
            i: TotalReqNum
            total_req_num += i.req_num
            if not until_time or i.until_time > until_time:
                until_time = i.until_time

        return Response(data={
            'code': 200,
            'num': total_req_num,
            'until_time': until_time.isoformat() if until_time else None
        })

    def get_serializer_class(self):
        return Serializer

    def allowed_addr_ip(self, request):
        allowd, addr_ip = InAllowedIp.check_addr_allowed(request=request)
        if not allowd:
            return self.exception_response(
                errors.AccessDenied(message=_('您的IP地址%(value)s没有访问权限。') % {'value': addr_ip}))

        return None


class PortalVmsViewSet(CustomGenericViewSet):
    permission_classes = [InAllowedIp]
    pagination_class = DefaultPageNumberPagination

    @swagger_auto_schema(
        operation_summary=gettext_lazy('云主机服务可用性查询'),
        paginator_inspectors=[NoPaginatorInspector],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='status', url_name='status')
    def service_status(self, request, *args, **kwargs):
        """
        云主机服务可用性查询

            Http Code: 状态码200，返回数据：
            {
              "code": 200,
              "status": "success" # success 表示可访问，failure 表示不可访问
            }
        """
        return Response(data={
            'code': 200,
            'status': 'success'
        })

    @swagger_auto_schema(
        operation_summary=gettext_lazy('云主机服务服务用户数查询'),
        paginator_inspectors=[NoPaginatorInspector],
        responses={200: ''}
    )
    @action(methods=['get'], detail=False, url_path='user-num', url_name='user-num')
    def user_number(self, request, *args, **kwargs):
        """
        云主机服务服务用户数查询

            Http Code 200 ok:
            {
              "code": 200,
              "count": 1234
            }
        """
        qs = filter_user_queryset()
        user_num = qs.count()
        return Response(data={
            'code': 200,
            'count': user_num
        })

    @swagger_auto_schema(
        operation_summary=gettext_lazy('云主机服务总请求数查询'),
        paginator_inspectors=[NoPaginatorInspector],
        responses={200: ''}
    )
    @action(methods=['get'], detail=False, url_path='total-req-num', url_name='total-req-num')
    def req_number(self, request, *args, **kwargs):
        """
        云主机服务总请求数查询

            Http Code 200 ok:
            {
              "code": 200,
              "num": 312734,
              "until_time": "2023-07-25T00:00:00+00:00"
            }
        """
        ins = TotalReqNum.get_instance(TotalReqNum.ServiceType.VMS.value)
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
                errors.AccessDenied(message=_('您的IP地址%(value)s没有访问权限。') % {'value': addr_ip}))

        return None


class PortalObsViewSet(CustomGenericViewSet):
    permission_classes = [InAllowedIp]
    pagination_class = DefaultPageNumberPagination

    @swagger_auto_schema(
        operation_summary=gettext_lazy('对象存储服务可用性查询'),
        paginator_inspectors=[NoPaginatorInspector],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='status', url_name='status')
    def service_status(self, request, *args, **kwargs):
        """
        对象存储服务可用性查询

            Http Code: 状态码200，返回数据：
            {
              "code": 200,
              "status": "success" # success 表示可访问，failure 表示不可访问
            }
        """
        return Response(data={
            'code': 200,
            'status': 'success'
        })

    @swagger_auto_schema(
        operation_summary=gettext_lazy('对象存储服务用户数查询'),
        paginator_inspectors=[NoPaginatorInspector],
        responses={200: ''}
    )
    @action(methods=['get'], detail=False, url_path='user-num', url_name='user-num')
    def user_number(self, request, *args, **kwargs):
        """
        对象存储服务用户数查询

            Http Code 200 ok:
            {
              "code": 200,
              "count": 1234
            }
        """
        qs = filter_user_queryset()
        user_num = qs.count()
        return Response(data={
            'code': 200,
            'count': user_num
        })

    @swagger_auto_schema(
        operation_summary=gettext_lazy('对象存储服务总请求数查询'),
        paginator_inspectors=[NoPaginatorInspector],
        responses={200: ''}
    )
    @action(methods=['get'], detail=False, url_path='total-req-num', url_name='total-req-num')
    def req_number(self, request, *args, **kwargs):
        """
        对象存储服务总请求数查询

            Http Code 200 ok:
            {
              "code": 200,
              "num": 312734,
              "until_time": "2023-07-25T00:00:00+00:00"
            }
        """
        ins = TotalReqNum.get_instance(TotalReqNum.ServiceType.OBS.value)
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
                errors.AccessDenied(message=_('您的IP地址%(value)s没有访问权限。') % {'value': addr_ip}))

        return None
