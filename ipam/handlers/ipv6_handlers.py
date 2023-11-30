import ipaddress

from django.utils.translation import gettext as _

from core import errors
from api.viewsets import NormalGenericViewSet
from ..managers import UserIpamRoleWrapper
from ..ipv6_managers import IPv6RangeManager
from ..models import IPv6Range


class IPv6RangeHandler:
    def list_ipv6_ranges(self, view: NormalGenericViewSet, request):
        try:
            data = self._list_ipv6_ranges_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        org_id = data['org_id']
        ur_wrapper = UserIpamRoleWrapper(user=request.user)
        if data['is_admin']:
            if not ur_wrapper.has_kjw_admin_readable():
                return view.exception_response(
                    errors.AccessDenied(message=_('你没有科技网IP管理功能的管理员权限')))

            org_ids = [org_id] if org_id else None
            queryset = IPv6RangeManager().get_admin_queryset(
                org_ids=org_ids, status=data['status'], asn=data['asn'],
                ip_bytes=data['ip_bytes'], search=data['search']
            )
        else:
            queryset = IPv6RangeManager().get_user_queryset(
                org_id=org_id, asn=data['asn'], ip_bytes=data['ip_bytes'], search=data['search'], user_role=ur_wrapper
            )
        queryset = queryset.order_by('start_address')
        try:
            objs = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=objs, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_ipv6_ranges_validate_params(view: NormalGenericViewSet, request):
        org_id = request.query_params.get('org_id', None)
        asn = request.query_params.get('asn', None)
        ipv6 = request.query_params.get('ip', None)
        search = request.query_params.get('search', None)
        status = request.query_params.get('status', None)
        is_admin = view.is_as_admin_request(request=request)

        if asn:
            try:
                asn = int(asn)
            except ValueError:
                raise errors.InvalidArgument(message=_('指定的AS编码无效，必须是一个正整数'))

        if ipv6:
            try:
                ipv6 = ipaddress.IPv6Address(ipv6)
            except ipaddress.AddressValueError:
                raise errors.InvalidArgument(message=_('指定的ip地址格式无效'))

        if status:
            if not is_admin:
                raise errors.InvalidArgument(message=_('状态查询是管理员参数，只允许以管理员身份查询时使用'))

            if status not in IPv6Range.Status.values:
                raise errors.InvalidArgument(message=_('指定的状态参数值无效'))

        return {
            'org_id': org_id,
            'asn': asn,
            'ip_bytes': ipv6.packed if ipv6 else None,
            'search': search,
            'is_admin': is_admin,
            'status': status
        }
