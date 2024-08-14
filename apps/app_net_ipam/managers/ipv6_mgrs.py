from typing import Union, List
from datetime import datetime

from django.db.models import Q, QuerySet
from django.utils.translation import gettext as _
from django.utils import timezone as dj_timezone
from django.core.exceptions import ValidationError

from core import errors
from apps.app_net_manage.models import OrgVirtualObject
from apps.app_net_ipam.models import (
    IPv6Range, ASN, ipv6_str_to_bytes,
    IPv6RangeRecord, IPv6RangeStrItem, IPv6RangeBytesItem
)
from apps.app_net_ipam.managers.ipv4_mgrs import get_or_create_asn
from apps.app_net_ipam.managers.common import NetIPamUserRoleWrapper


class IPv6RangeManager:
    @staticmethod
    def get_ip_range(_id: str) -> IPv6Range:
        iprange = IPv6Range.objects.select_related('asn', 'org_virt_obj').filter(id=_id).first()
        if iprange is None:
            raise errors.TargetNotExist(message=_('IP地址段不存在'))

        return iprange

    @staticmethod
    def get_queryset(related_fields: list = None) -> QuerySet:
        fileds = ['asn', 'org_virt_obj']
        if related_fields:
            for f in related_fields:
                if f not in fileds:
                    fileds.append(f)

        return IPv6Range.objects.select_related(*fileds).all()

    def filter_queryset(self, org_ids: Union[list, None], status: Union[str, None], asn: int, ip_bytes: bytes,
                        search: str, is_admin: bool):
        """
        各参数为真时过滤
        """
        qs = self.get_queryset(related_fields=['org_virt_obj__organization'])
        lookups = {}
        if org_ids:
            if len(org_ids) == 1:
                lookups['org_virt_obj__organization_id'] = org_ids[0]
            else:
                lookups['org_virt_obj__organization_id__in'] = org_ids

        if status:
            lookups['status'] = status

        if asn:
            lookups['asn__number'] = asn

        if ip_bytes:
            lookups['start_address__lte'] = ip_bytes
            lookups['end_address__gte'] = ip_bytes

        if lookups:
            qs = qs.filter(**lookups)

        if search:
            q = Q(name__icontains=search) | Q(remark__icontains=search)
            if is_admin:
                q |= Q(admin_remark__icontains=search)

            qs = qs.filter(q)

        return qs

    def get_user_queryset(self, org_id: str, asn: int, ip_bytes: bytes, search: str, user_role: NetIPamUserRoleWrapper):
        org_ids = user_role.get_user_ipam_org_ids()
        if not org_ids:
            return self.get_queryset().none()

        if org_id:
            if org_id not in org_ids:
                return self.get_queryset().none()
            else:
                org_ids = [org_id]

        return self.filter_queryset(
            org_ids=org_ids, status=IPv6Range.Status.ASSIGNED.value, asn=asn,
            ip_bytes=ip_bytes, search=search, is_admin=False)

    def get_admin_queryset(self, org_ids: Union[list, None], status: str, asn: int, ip_bytes: bytes, search: str):
        return self.filter_queryset(
            org_ids=org_ids, status=status, asn=asn, ip_bytes=ip_bytes, search=search, is_admin=True)

    @staticmethod
    def create_ipv6_range(
            name: str, start_ip: Union[str, bytes], end_ip: Union[str, bytes], prefixlen: int,
            asn: Union[ASN, int], status_code: str, org_virt_obj: Union[OrgVirtualObject, None],
            admin_remark: str, remark: str,
            create_time: Union[datetime, None], update_time: Union[datetime, None], assigned_time=None
    ):
        """
        :return: IPv6Range
        :raises: ValidationError
        """
        ip_range = IPv6RangeManager.build_ipv6_range(
            name=name, start_ip=start_ip, end_ip=end_ip, prefixlen=prefixlen,
            asn=asn, status_code=status_code, org_virt_obj=org_virt_obj,
            admin_remark=admin_remark, remark=remark,
            create_time=create_time, update_time=update_time, assigned_time=assigned_time
        )

        try:
            ip_range.clean()
        except ValidationError as exc:
            raise errors.ValidationError(message=exc.messages[0])

        ip_range.save(force_insert=True)
        return ip_range

    @staticmethod
    def build_ipv6_range(
            name: str, start_ip: Union[str, bytes], end_ip: Union[str, bytes], prefixlen: int,
            asn: Union[ASN, int], status_code: str, org_virt_obj: Union[OrgVirtualObject, str, None],
            admin_remark: str, remark: str,
            create_time: Union[datetime, None], update_time: Union[datetime, None], assigned_time=None
    ):
        """
        构建一个IPv6Range对象，不保存到数据库

        :return: IPv6Range
        :raises: ValidationError
        """
        if isinstance(start_ip, bytes):
            if len(start_ip) != 16:
                raise ValidationError(_('字节格式的ip地址长度必须是16字节'))
            start_bytes = start_ip
        else:
            start_bytes = ipv6_str_to_bytes(start_ip)

        if isinstance(end_ip, bytes):
            if len(end_ip) != 16:
                raise ValidationError(_('字节格式的ip地址长度必须是16字节'))
            end_bytes = end_ip
        else:
            end_bytes = ipv6_str_to_bytes(end_ip)

        prefixlen = int(prefixlen)
        if not (0 <= prefixlen <= 128):
            raise errors.ValidationError(message=_('前缀长度无效，取值范围为0-128'))

        if status_code not in IPv6Range.Status.values:
            raise errors.ValidationError(message=_('IP地址段的状态值无效'))

        if isinstance(asn, int):
            asn = get_or_create_asn(number=asn)

        if create_time is None:
            create_time = dj_timezone.now()
        if update_time is None:
            update_time = create_time

        ip_range = IPv6Range(
            name=name,
            status=status_code,
            creation_time=create_time,
            update_time=update_time,
            assigned_time=assigned_time,
            asn=asn,
            start_address=start_bytes,
            end_address=end_bytes,
            prefixlen=prefixlen,
            admin_remark=admin_remark,
            remark=remark
        )
        if isinstance(org_virt_obj, str):
            ip_range.org_virt_obj_id = org_virt_obj
        else:
            ip_range.org_virt_obj = org_virt_obj

        if not ip_range.name:
            ip_range.name = str(ip_range.start_address_network)

        return ip_range

    @staticmethod
    def do_create_ipv6_range(
            user, name: str, start_ip: Union[str, bytes], end_ip: Union[str, bytes], prefixlen: int,
            asn: Union[ASN, int], org_virt_obj: Union[OrgVirtualObject, None],
            admin_remark: str, remark: str,
            create_time: Union[datetime, None], update_time: Union[datetime, None], assigned_time=None
    ) -> IPv6Range:
        """
        :raises: ValidationError
        """
        ip_range = IPv6RangeManager.create_ipv6_range(
            name=name, start_ip=start_ip, end_ip=end_ip, prefixlen=prefixlen,
            asn=asn, status_code=IPv6Range.Status.WAIT.value, org_virt_obj=org_virt_obj,
            admin_remark=admin_remark, remark=remark,
            create_time=create_time, update_time=update_time, assigned_time=assigned_time
        )
        try:
            IPv6RangeRecordManager.create_add_record(
                user=user, ip_range=ip_range, remark=''
            )
        except Exception as exc:
            pass

        return ip_range

    @staticmethod
    def update_ipv6_range(
            ip_range: IPv6Range, name: str, start_ip: Union[str, bytes], end_ip: Union[str, bytes], prefixlen: int,
            asn: Union[ASN, int], admin_remark: str
    ):
        """
        :return: IPv6Range, update_fields: list
        :raises: ValidationError
        """
        if isinstance(start_ip, bytes):
            if len(start_ip) != 16:
                raise ValidationError(_('字节格式的ip地址长度必须是16字节'))
            start_bytes = start_ip
        else:
            start_bytes = ipv6_str_to_bytes(start_ip)

        if isinstance(end_ip, bytes):
            if len(end_ip) != 16:
                raise ValidationError(_('字节格式的ip地址长度必须是16字节'))
            end_bytes = end_ip
        else:
            end_bytes = ipv6_str_to_bytes(end_ip)

        prefixlen = int(prefixlen)
        if not (0 <= prefixlen <= 128):
            raise errors.ValidationError(message=_('前缀长度无效，取值范围为0-128'))

        if isinstance(asn, int):
            asn = get_or_create_asn(number=asn)

        update_fields = []
        if name and ip_range.name != name:
            ip_range.name = name
            update_fields.append('name')

        if start_bytes != ip_range.start_address:
            ip_range.start_address = start_bytes
            update_fields.append('start_address')

        if end_bytes != ip_range.end_address:
            ip_range.end_address = end_bytes
            update_fields.append('end_address')

        if prefixlen != ip_range.prefixlen:
            ip_range.prefixlen = prefixlen
            update_fields.append('prefixlen')

        if asn.id != ip_range.asn_id:
            ip_range.asn = asn
            ip_range.asn_id = asn.id
            update_fields.append('asn_id')

        if admin_remark and ip_range.admin_remark != admin_remark:
            ip_range.admin_remark = admin_remark
            update_fields.append('admin_remark')

        if update_fields:
            ip_range.update_time = dj_timezone.now()
            update_fields.append('update_time')

            try:
                ip_range.clear_cached_property()  # 字段值变更了，需要清除缓存属性
                ip_range.clean()
            except ValidationError as exc:
                raise errors.ValidationError(message=exc.messages[0])

            ip_range.save(update_fields=update_fields)

        return ip_range, update_fields

    @staticmethod
    def do_update_ipv6_range(
            ip_range: IPv6Range, user, name: str, start_ip: Union[str, bytes], end_ip: Union[str, bytes],
            prefixlen: int, asn: Union[ASN, int], admin_remark: str
    ) -> IPv6Range:
        """
        :raises: ValidationError
        """
        old_ip_range = IPv6RangeBytesItem(
            start=ip_range.start_address, end=ip_range.end_address, prefix=ip_range.prefixlen
        )
        ip_range, update_fields = IPv6RangeManager.update_ipv6_range(
            ip_range=ip_range, name=name, start_ip=start_ip, end_ip=end_ip, prefixlen=prefixlen,
            asn=asn, admin_remark=admin_remark
        )

        # need_record = any(True if f in update_fields else False for f in ['start_address', 'end_address', 'mask_len'])
        need_record = False
        if update_fields:
            for f in ['start_address', 'end_address', 'prefixlen']:
                if f in update_fields:
                    need_record = True
                    break

        if need_record:
            try:
                new_ip_range = IPv6RangeStrItem(
                    start=str(ip_range.start_address_obj), end=str(ip_range.end_address_obj), prefix=ip_range.prefixlen
                )
                IPv6RangeRecordManager.create_change_record(
                    user=user, new_ip_range=new_ip_range, remark='', old_ip_range=old_ip_range
                )
            except Exception as exc:
                pass

        return ip_range

    @staticmethod
    def do_delete_ipv6_range(ip_range: IPv6Range, user):
        ip_range.delete()
        try:
            IPv6RangeRecordManager.create_delete_record(
                user=user, ip_range=ip_range, remark='', org_virt_obj=ip_range.org_virt_obj)
        except Exception as exc:
            pass

        return ip_range

    @staticmethod
    def do_recover_ipv6_range(ip_range: IPv6Range, user):
        """
        从 已分配和预留 状态 收回
        """
        org_virt_obj = ip_range.org_virt_obj

        status = ip_range.status
        ip_range.status = IPv6Range.Status.WAIT.value
        ip_range.org_virt_obj = None
        ip_range.assigned_time = None
        ip_range.update_time = dj_timezone.now()
        ip_range.remark = ''
        ip_range.save(update_fields=['status', 'org_virt_obj', 'assigned_time', 'update_time', 'remark'])
        try:
            remark = f'{IPv6Range.Status.WAIT.value} from {status}'
            IPv6RangeRecordManager.create_recover_record(
                user=user, ip_range=ip_range, remark=remark, org_virt_obj=org_virt_obj
            )
        except Exception as exc:
            pass

        return ip_range

    @staticmethod
    def do_reserve_ipv6_range(ip_range: IPv6Range, org_virt_obj, user):
        """
        预留
        """
        status = ip_range.status
        ip_range.status = IPv6Range.Status.RESERVED.value
        ip_range.org_virt_obj = org_virt_obj
        ip_range.assigned_time = None
        ip_range.update_time = dj_timezone.now()
        ip_range.remark = ''
        ip_range.save(update_fields=['status', 'org_virt_obj', 'assigned_time', 'update_time', 'remark'])
        try:
            remark = f'{IPv6Range.Status.RESERVED.value} from {status}'
            IPv6RangeRecordManager.create_reserve_record(
                user=user, ip_range=ip_range, remark=remark, org_virt_obj=org_virt_obj
            )
        except Exception as exc:
            pass

        return ip_range

    @staticmethod
    def do_assign_ipv6_range(ip_range: IPv6Range, org_virt_obj, user):
        """
        分配
        """
        old_status = ip_range.status
        nt = dj_timezone.now()
        ip_range.status = IPv6Range.Status.ASSIGNED.value
        ip_range.org_virt_obj = org_virt_obj
        ip_range.assigned_time = nt
        ip_range.update_time = nt
        ip_range.remark = ''
        ip_range.save(update_fields=['status', 'org_virt_obj', 'assigned_time', 'update_time', 'remark'])
        try:
            remark = f'{IPv6Range.Status.ASSIGNED.value} from {old_status}'
            IPv6RangeRecordManager.create_assign_record(
                user=user, ip_range=ip_range, remark=remark, org_virt_obj=org_virt_obj
            )
        except Exception as exc:
            pass


class IPv6RangeRecordManager:
    @staticmethod
    def create_record(
            user, record_type: str,
            start_address: bytes, end_address: bytes, prefixlen: int, ip_ranges: List[IPv6RangeStrItem],
            remark: str = '', org_virt_obj: OrgVirtualObject = None
    ):
        record = IPv6RangeRecord(
            creation_time=dj_timezone.now(),
            record_type=record_type,
            start_address=start_address,
            end_address=end_address,
            prefixlen=prefixlen,
            user=user,
            org_virt_obj=org_virt_obj,
            remark=remark
        )
        record.set_ip_ranges(ip_ranges=ip_ranges)
        record.save(force_insert=True)
        return record

    @staticmethod
    def create_add_record(user, ip_range: IPv6Range, remark: str):
        return IPv6RangeRecordManager.create_record(
            user=user, record_type=IPv6RangeRecord.RecordType.ADD.value,
            start_address=ip_range.start_address, end_address=ip_range.end_address, prefixlen=ip_range.prefixlen,
            ip_ranges=[], remark=remark, org_virt_obj=None
        )

    @staticmethod
    def create_change_record(user, new_ip_range: IPv6RangeStrItem, remark: str, old_ip_range: IPv6RangeBytesItem):
        return IPv6RangeRecordManager.create_record(
            user=user, record_type=IPv6RangeRecord.RecordType.CHANGE.value,
            start_address=old_ip_range.start, end_address=old_ip_range.end, prefixlen=old_ip_range.prefix,
            ip_ranges=[new_ip_range], remark=remark, org_virt_obj=None
        )

    @staticmethod
    def create_delete_record(user, ip_range: IPv6Range, remark: str, org_virt_obj):
        return IPv6RangeRecordManager.create_record(
            user=user, record_type=IPv6RangeRecord.RecordType.DELETE.value,
            start_address=ip_range.start_address, end_address=ip_range.end_address, prefixlen=ip_range.prefixlen,
            ip_ranges=[], remark=remark, org_virt_obj=org_virt_obj
        )

    @staticmethod
    def create_recover_record(user, ip_range: IPv6Range, remark: str, org_virt_obj):
        return IPv6RangeRecordManager.create_record(
            user=user, record_type=IPv6RangeRecord.RecordType.RECOVER.value,
            start_address=ip_range.start_address, end_address=ip_range.end_address, prefixlen=ip_range.prefixlen,
            ip_ranges=[], remark=remark, org_virt_obj=org_virt_obj
        )

    @staticmethod
    def create_reserve_record(user, ip_range: IPv6Range, remark: str, org_virt_obj):
        return IPv6RangeRecordManager.create_record(
            user=user, record_type=IPv6RangeRecord.RecordType.RESERVE.value,
            start_address=ip_range.start_address, end_address=ip_range.end_address, prefixlen=ip_range.prefixlen,
            ip_ranges=[], remark=remark, org_virt_obj=org_virt_obj
        )

    @staticmethod
    def create_assign_record(user, ip_range: IPv6Range, remark: str, org_virt_obj):
        return IPv6RangeRecordManager.create_record(
            user=user, record_type=IPv6RangeRecord.RecordType.ASSIGN.value,
            start_address=ip_range.start_address, end_address=ip_range.end_address, prefixlen=ip_range.prefixlen,
            ip_ranges=[], remark=remark, org_virt_obj=org_virt_obj
        )
