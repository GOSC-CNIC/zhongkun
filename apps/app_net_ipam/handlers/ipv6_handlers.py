import ipaddress

from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from apps.api.viewsets import NormalGenericViewSet, serializer_error_msg
from apps.app_net_manage.models import OrgVirtualObject
from apps.app_net_ipam.managers.common import NetIPamUserRoleWrapper
from apps.app_net_ipam.managers.ipv6_mgrs import IPv6RangeManager
from apps.app_net_ipam.models import IPv6Range
from apps.app_net_ipam import serializers as ipam_serializers


class IPv6RangeHandler:
    def list_ipv6_ranges(self, view: NormalGenericViewSet, request):
        try:
            data = self._list_ipv6_ranges_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        org_id = data['org_id']
        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if data['is_admin']:
            if not ur_wrapper.has_ipam_admin_readable():
                return view.exception_response(
                    errors.AccessDenied(message=_('你没有IP管理功能的管理员权限')))

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

    def add_ipv6_range(self, view: NormalGenericViewSet, request):
        try:
            data = self._add_ipv6_ranges_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有IP管理功能的管理员权限')))

        try:
            ipv6_range = IPv6RangeManager.do_create_ipv6_range(
                user=request.user, name=data['name'],
                start_ip=data['start_address'], end_ip=data['end_address'], prefixlen=data['prefixlen'],
                asn=data['asn'], org_virt_obj=None,
                admin_remark=data['admin_remark'], remark='',
                create_time=None, update_time=None, assigned_time=None
            )
        except errors.ValidationError as exc:
            return view.exception_response(errors.InvalidArgument(message=exc.message))

        return Response(data=ipam_serializers.IPv6RangeSerializer(instance=ipv6_range).data)

    @staticmethod
    def _add_ipv6_ranges_validate_params(view: NormalGenericViewSet, request):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'start_address' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('起始IP地址无效。') + s_errors['start_address'][0])
            elif 'end_address' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('结束IP地址无效。') + s_errors['end_address'][0])
            elif 'prefixlen' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('子网前缀长度无效。') + s_errors['prefixlen'][0])
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
                start_address = ipaddress.IPv6Address(start_address).packed
            except ipaddress.AddressValueError:
                raise errors.InvalidArgument(message=_('起始IP地址无效'))

        if end_address:
            try:
                end_address = ipaddress.IPv6Address(end_address).packed
            except ipaddress.AddressValueError:
                raise errors.InvalidArgument(message=_('结束IP地址无效'))

        data['start_address'] = start_address
        data['end_address'] = end_address
        return data

    def update_ipv6_range(self, view: NormalGenericViewSet, request, kwargs):
        try:
            data = self._add_ipv6_ranges_validate_params(view=view, request=request)
            ip_range = IPv6RangeManager.get_ip_range(_id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有IP管理功能的管理员权限')))

        if ip_range.status not in [IPv6Range.Status.WAIT.value, IPv6Range.Status.RESERVED.value]:
            return view.exception_response(
                errors.ConflictError(message=_('只允许修改“未分配”和“预留”状态的IP地址段')))

        try:
            ip_range = IPv6RangeManager.do_update_ipv6_range(
                ip_range=ip_range, user=request.user, name=data['name'],
                start_ip=data['start_address'], end_ip=data['end_address'], prefixlen=data['prefixlen'],
                asn=data['asn'],  admin_remark=data['admin_remark']
            )
        except errors.ValidationError as exc:
            return view.exception_response(errors.InvalidArgument(message=exc.message))

        return Response(data=ipam_serializers.IPv6RangeSerializer(instance=ip_range).data)

    @staticmethod
    def delete_ipv6_range(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有IP管理功能的管理员权限')))

        try:
            ip_range = IPv6RangeManager.get_ip_range(_id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        if ip_range.status not in [IPv6Range.Status.WAIT.value, IPv6Range.Status.RESERVED.value]:
            return view.exception_response(
                errors.ConflictError(message=_('只允许删除“未分配”和“预留”状态的IP地址段')))

        try:
            IPv6RangeManager.do_delete_ipv6_range(ip_range=ip_range, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)

    @staticmethod
    def recover_ipv6_range(view: NormalGenericViewSet, request, kwargs):
        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有IP管理功能的管理员权限')))

        try:
            ip_range = IPv6RangeManager.get_ip_range(_id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        if ip_range.status != IPv6Range.Status.WAIT.value:
            try:
                IPv6RangeManager.do_recover_ipv6_range(ip_range=ip_range, user=request.user)
            except Exception as exc:
                return view.exception_response(exc)

        return Response(data=ipam_serializers.IPv6RangeSerializer(instance=ip_range).data)

    @staticmethod
    def reserve_ipv6_range(view: NormalGenericViewSet, request, kwargs):
        org_virt_obj_id = request.query_params.get('org_virt_obj_id')
        if not org_virt_obj_id:
            return view.exception_response(
                errors.InvalidArgument(message=_('必须指定预留给哪个机构二级对象')))

        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有IP管理功能的管理员权限')))

        try:
            org_virt_obj = OrgVirtualObject.objects.filter(id=org_virt_obj_id).first()
            if org_virt_obj is None:
                raise errors.TargetNotExist(message=_('指定的机构二级对象不存在'))

            ip_range = IPv6RangeManager.get_ip_range(_id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        if ip_range.status != IPv6Range.Status.WAIT.value:
            return view.exception_response(
                errors.ConflictError(message=_('只允许“未分配”状态的IP地址段做预留操作')))

        try:
            IPv6RangeManager.do_reserve_ipv6_range(
                ip_range=ip_range, user=request.user, org_virt_obj=org_virt_obj)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data=ipam_serializers.IPv6RangeSerializer(instance=ip_range).data)
