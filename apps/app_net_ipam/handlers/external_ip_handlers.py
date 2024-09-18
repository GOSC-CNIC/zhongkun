import ipaddress

from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from apps.api.viewsets import NormalGenericViewSet, serializer_error_msg
from apps.app_net_ipam.managers.common import NetIPamUserRoleWrapper
from apps.app_net_ipam.managers.ipv4_mgrs import ExternalIPv4RangeManager
from apps.app_net_ipam import serializers as ipam_serializers


class ExternalIPv4RangeHandler:
    def add_external_ipv4_range(self, view: NormalGenericViewSet, request):
        try:
            data = self._add_external_ipv4_validate(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有网络IP管理功能的管理员权限')))

        try:
            ipv4_range = ExternalIPv4RangeManager().create_external_ipv4_range(
                start_address=int(data['start_address']), end_address=int(data['end_address']),
                mask_len=data['mask_len'], asn=data['asn'],
                remark=data['remark'], operator=request.user.username,
                org_name=data['org_name'], country=data['country'], city=data['city']
            )
        except errors.ValidationError as exc:
            return view.exception_response(errors.InvalidArgument(message=exc.message))

        return Response(data=ipam_serializers.ExternalIPv4RangeSerializer(instance=ipv4_range).data)

    @staticmethod
    def _add_external_ipv4_validate(view: NormalGenericViewSet, request):
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

    def update_external_ipv4_range(self, view: NormalGenericViewSet, request, kwargs):
        try:
            data = self._add_external_ipv4_validate(view=view, request=request)
            ipv4_range = ExternalIPv4RangeManager.get_ipv4_range(_id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有网络IP管理功能的管理员权限')))

        try:
            ipv4_range, ud_fileds = ExternalIPv4RangeManager.update_external_ipv4_range(
                ip_range=ipv4_range, operator=request.user.username,
                start_address=data['start_address'], end_address=data['end_address'],
                mask_len=data['mask_len'], asn=data['asn'],
                remark=data['remark'], org_name=data['org_name'], country=data['country'], city=data['city']
            )
        except errors.ValidationError as exc:
            return view.exception_response(errors.InvalidArgument(message=exc.message))

        return Response(data=ipam_serializers.ExternalIPv4RangeSerializer(instance=ipv4_range).data)

    def list_external_ipv4_ranges(self, view: NormalGenericViewSet, request):
        try:
            data = self._list_ipv4_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_readable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有网络IP管理功能的管理员权限')))

        queryset = ExternalIPv4RangeManager().filter_queryset(
            asn=data['asn'], ipv4_int=data['ipv4'], search=data['search']
        )

        queryset = queryset.order_by('start_address')
        try:
            objs = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=objs, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_ipv4_validate_params(request):
        asn = request.query_params.get('asn', None)
        ipv4 = request.query_params.get('ip', None)
        search = request.query_params.get('search', None)

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

        return {
            'asn': asn,
            'ipv4': int(ipv4) if ipv4 else None,
            'search': search
        }
