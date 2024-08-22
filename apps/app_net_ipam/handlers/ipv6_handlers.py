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

    @staticmethod
    def assign_ipv6_range(view: NormalGenericViewSet, request, kwargs):
        org_virt_obj_id = request.query_params.get('org_virt_obj_id')
        if not org_virt_obj_id:
            return view.exception_response(
                errors.InvalidArgument(message=_('必须指定分配给哪个机构二级对象')))

        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有IP管理功能的管理员权限')))

        try:
            org_virt_obj = OrgVirtualObject.objects.filter(id=org_virt_obj_id).first()
            if org_virt_obj is None:
                raise errors.TargetNotExist(message=_('指定的机构二级对象不存在'))

            ipv6_range = IPv6RangeManager.get_ip_range(_id=kwargs[view.lookup_field])
        except errors.Error as exc:
            return view.exception_response(exc)

        if ipv6_range.status not in [IPv6Range.Status.WAIT.value, IPv6Range.Status.RESERVED.value]:
            return view.exception_response(
                errors.ConflictError(message=_('只允许“未分配”和“预留”状态的IP地址段做分配操作')))

        if ipv6_range.status == IPv6Range.Status.RESERVED.value:
            if ipv6_range.org_virt_obj_id != org_virt_obj.id:
                return view.exception_response(
                    errors.ConflictError(message=_('“预留”状态的IP地址段只允许分配给预留的机构二级对象')))

        try:
            IPv6RangeManager.do_assign_ipv6_range(
                ip_range=ipv6_range, user=request.user, org_virt_obj=org_virt_obj)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data=ipam_serializers.IPv6RangeSerializer(instance=ipv6_range).data)

    @staticmethod
    def change_ipv6_range_remark(view: NormalGenericViewSet, request, kwargs):
        try:
            remark = request.query_params.get('remark', None)
            admin_remark = request.query_params.get('admin_remark', None)
            is_as_admin = view.is_as_admin_request(request=request)

            if not remark and not admin_remark:
                raise errors.InvalidArgument(message=_('必须指定要修改的备注信息'))

            if admin_remark and not is_as_admin:
                raise errors.InvalidArgument(message=_('管理员备注参数“admin_remark”只能以管理员身份请求时使用'))

            if remark and len(remark) > 255:
                raise errors.InvalidArgument(message=_('备注信息长度不能超过255字符'))

            if admin_remark and len(admin_remark) > 255:
                raise errors.InvalidArgument(message=_('备注信息长度不能超过255字符'))

            ipv6_range = IPv6RangeManager.get_ip_range(_id=kwargs[view.lookup_field])

            ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
            if is_as_admin:
                if not ur_wrapper.has_ipam_admin_writable():
                    raise errors.AccessDenied(message=_('你没有IP管理功能的管理员权限'))
            else:
                IPv6RangeHandler.check_ip_range_org_admin_perm(ipv6_range=ipv6_range, ur_wrapper=ur_wrapper)
        except errors.Error as exc:
            return view.exception_response(exc)

        update_fields = []
        if remark:
            ipv6_range.remark = remark
            update_fields.append('remark')
        if admin_remark:
            ipv6_range.admin_remark = admin_remark
            update_fields.append('admin_remark')

        if update_fields:
            ipv6_range.save(update_fields=update_fields)

        return Response(data=ipam_serializers.IPv6RangeSerializer(instance=ipv6_range).data)

    @staticmethod
    def check_ip_range_org_admin_perm(ipv6_range: IPv6Range, ur_wrapper: NetIPamUserRoleWrapper):
        """
        检查是否有IP地址段分配机构管理员权限

        :raises: AccessDenied
        """
        if ipv6_range.status != IPv6Range.Status.ASSIGNED.value:
            raise errors.AccessDenied(message=_('IP地址段未分配，你没IP地址段的管理权限'))

        if ipv6_range.org_virt_obj:
            org_id = ipv6_range.org_virt_obj.organization_id
        else:
            org_id = None

        if not org_id or not isinstance(org_id, str):
            raise errors.AccessDenied(message=_('IP地址段无分配机构信息，你没IP地址段的管理权限'))

        if not ur_wrapper.is_ipam_admin_of_org(org_id=org_id):
            raise errors.AccessDenied(message=_('你没IP地址段的管理权限'))

    @staticmethod
    def split_ip_range_to_plan(view: NormalGenericViewSet, request, kwargs):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'sub_ranges' in s_errors:
                errs = s_errors['sub_ranges']
                msg = ''
                if isinstance(errs, list):
                    msg = str(errs[0])
                elif isinstance(errs, dict):
                    for idx, err in errs.items():
                        err_msgs = []
                        for k, v in err.items():
                            if v and isinstance(v, list):
                                err_msgs.append(f'{k}: {v[0]}')
                            else:
                                err_msgs.append(f'{k}: {v}')

                        msg = f'index {idx}, ' + ', '.join(err_msgs)
                        break
                else:
                    msg = str(errs)
                exc = errors.InvalidArgument(message=_('指定的分拆子网无效。') + msg)
            else:
                msg = serializer_error_msg(s_errors)
                exc = errors.BadRequest(message=msg)

            return view.exception_response(exc)

        data = serializer.validated_data.copy()
        sub_ranges = data['sub_ranges']

        if not sub_ranges:
            return view.exception_response(errors.InvalidArgument(message=_('指定的分拆子网数组不能为空')))

        if len(sub_ranges) > 256:
            return view.exception_response(errors.InvalidArgument(message=_('指定的分拆子网数不能超过256')))

        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有网络IP管理功能的管理员权限')))

        try:
            sub_ranges = IPv6RangeManager.split_ipv6_range_to_plan(
                user=request.user, range_id=kwargs[view.lookup_field], sub_ranges=sub_ranges
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data={
            'ip_ranges': ipam_serializers.IPv6RangeSerializer(instance=sub_ranges, many=True).data
        })

    @staticmethod
    def seek_ip_range_split_plan(view: NormalGenericViewSet, request):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            msg = serializer_error_msg(s_errors)
            exc = errors.BadRequest(message=msg)

            return view.exception_response(exc)

        data = serializer.validated_data.copy()
        start_address = data['start']
        end_address = data['end']
        prefix = data['prefix']
        new_prefix = data['new_prefix']

        from apps.app_net_ipam.managers.ipv6_mgrs import IPv6RangeSplitter, IPv6RangeStrItem

        try:
            sub_ranges = IPv6RangeSplitter.mini_split_plan(
                ip_range=IPv6RangeStrItem(start=start_address, end=end_address, prefix=prefix),
                new_prefix=new_prefix, prefixlen_diff=3
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data={
            'ip_ranges': ipam_serializers.SubIPv6RangeSerializer(instance=sub_ranges, many=True).data
        })

    @staticmethod
    def merge_ipv6_ranges(view: NormalGenericViewSet, request, kwargs):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'new_prefix' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('掩码长度可选的有效值为1-127，并且必须大于要拆分的IP地址段的掩码长度。') + s_errors['new_prefix'][0])
            elif 'ip_range_ids' in s_errors:
                exc = errors.InvalidArgument(
                    message=_('IP地址段id列表无效。') + serializer_error_msg(s_errors['ip_range_ids']))
            else:
                msg = serializer_error_msg(s_errors)
                exc = errors.BadRequest(message=msg)

            return view.exception_response(exc)

        data = serializer.validated_data
        new_prefix = data['new_prefix']
        ip_range_ids = data['ip_range_ids']
        fake = data['fake']

        ur_wrapper = NetIPamUserRoleWrapper(user=request.user)
        if not ur_wrapper.has_ipam_admin_writable():
            return view.exception_response(
                errors.AccessDenied(message=_('你没有网络IP管理功能的管理员权限')))

        try:
            supernet = IPv6RangeManager.merge_ipv6_ranges_by_prefix(
                user=request.user, range_ids=ip_range_ids, new_prefix=new_prefix, fake=fake
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data={
            'ip_range': ipam_serializers.IPv6RangeSerializer(instance=supernet).data
        })
