import ipaddress

from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from api.viewsets import NormalGenericViewSet, serializer_error_msg
from ..managers import IPv4RangeManager, UserIpamRoleWrapper
from ..models import IPv4Range
from .. import serializers


class IPv4RangeHandler:
    def list_ipv4_ranges(self, view: NormalGenericViewSet, request):
        try:
            data = self._list_ipv4_ranges_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        org_id = data['org_id']
        ur_wrapper = UserIpamRoleWrapper(user=request.user)
        if data['is_admin']:
            if not ur_wrapper.has_kjw_admin_readable():
                return view.exception_response(
                    errors.AccessDenied(message=_('你没有科技网IP管理功能的管理员权限')))

            org_ids = [org_id] if org_id else None
            queryset = IPv4RangeManager().get_admin_queryset(
                org_ids=org_ids, status=data['status'], asn=data['asn'], ipv4_int=data['ipv4'], search=data['search']
            )
        else:
            queryset = IPv4RangeManager().get_user_queryset(
                org_id=org_id, asn=data['asn'], ipv4_int=data['ipv4'], search=data['search'], user_role=ur_wrapper
            )

        try:
            objs = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=objs, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_ipv4_ranges_validate_params(view: NormalGenericViewSet, request):
        org_id = request.query_params.get('org_id', None)
        asn = request.query_params.get('asn', None)
        ipv4 = request.query_params.get('ip', None)
        search = request.query_params.get('search', None)
        status = request.query_params.get('status', None)
        is_admin = view.is_as_admin_request(request=request)

        if asn:
            try:
                asn = int(asn)
            except ValueError:
                raise errors.InvalidArgument(message=_('指定的AS编码无效，必须是一个正整数'))

        if ipv4:
            try:
                ipv4 = ipaddress.IPv4Address(ipv4)
            except ipaddress.AddressValueError:
                raise errors.InvalidArgument(message=_('指定的ip地址格式无效'))

        if status:
            if not is_admin:
                raise errors.InvalidArgument(message=_('状态查询是管理员参数，只允许以管理员身份查询时使用'))

            if status not in IPv4Range.Status.values:
                raise errors.InvalidArgument(message=_('指定的状态参数值无效'))

        return {
            'org_id': org_id,
            'asn': asn,
            'ipv4': int(ipv4) if ipv4 else None,
            'search': search,
            'is_admin': is_admin,
            'status': status
        }

    def add_ipv4_range(self, view: NormalGenericViewSet, request):
        try:
            data = self._add_ipv4_ranges_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        ur_wrapper = UserIpamRoleWrapper(user=request.user)
        if not ur_wrapper.has_kjw_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有科技网IP管理功能的管理员权限')))

        try:
            ipv4_range = IPv4RangeManager.create_ipv4_range(
                name=data['name'],
                start_ip=data['start_address'], end_ip=data['end_address'], mask_len=data['mask_len'],
                asn=data['asn'], status_code=IPv4Range.Status.WAIT.value, org_virt_obj=None,
                admin_remark=data['admin_remark'], remark='',
                create_time=None, update_time=None, assigned_time=None
            )
        except errors.ValidationError as exc:
            return view.exception_response(errors.InvalidArgument(message=exc.message))

        return Response(data=serializers.IPv4RangeSerializer(instance=ipv4_range).data)

    @staticmethod
    def _add_ipv4_ranges_validate_params(view: NormalGenericViewSet, request):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'start_address' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('起始IP地址无效。') + s_errors['start_address'][0])
            elif 'end_address' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('结束IP地址无效。') + s_errors['end_address'][0])
            elif 'mask_len' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('子网掩码长度无效。') + s_errors['mask_len'][0])
            elif 'asn' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('AS编号无效。') + s_errors['asn'][0])
            else:
                msg = serializer_error_msg(s_errors)
                exc = errors.BadRequest(message=msg)

            raise exc

        data = serializer.validated_data.copy()
        start_address = data['start_address']
        end_address = data['end_address']

        if start_address:
            try:
                start_address = ipaddress.IPv4Address(start_address)
            except ipaddress.AddressValueError:
                raise errors.InvalidArgument(message=_('起始IP地址无效'))

        if end_address:
            try:
                end_address = ipaddress.IPv4Address(end_address)
            except ipaddress.AddressValueError:
                raise errors.InvalidArgument(message=_('结束IP地址无效'))

        data['start_address'] = start_address
        data['end_address'] = end_address
        return data
