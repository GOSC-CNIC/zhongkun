import ipaddress
from typing import Union, List
from datetime import datetime

from django.db.models import Q, QuerySet
from django.db import transaction
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

    @staticmethod
    def split_ipv6_range_to_plan(user, range_id: str, sub_ranges: list) -> List[IPv6Range]:
        """
        按指定拆分计划拆分一个地址段
        """
        return IPv6RangeSplitter(obj_or_id=range_id).split_to_plan(user=user, sub_ranges=sub_ranges)


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

    @staticmethod
    def create_split_record(user, ip_range: IPv6Range, remark: str, ip_ranges: List[IPv6RangeStrItem]):
        return IPv6RangeRecordManager.create_record(
            user=user, record_type=IPv6RangeRecord.RecordType.SPLIT.value,
            start_address=ip_range.start_address, end_address=ip_range.end_address, prefixlen=ip_range.prefixlen,
            ip_ranges=ip_ranges, remark=remark, org_virt_obj=None
        )


class IPv6RangeSplitter:
    def __init__(self, obj_or_id: Union[IPv6Range, str]):
        if isinstance(obj_or_id, str):
            self._ipv6_range_id = obj_or_id
            self._ipv6_range = None
        elif isinstance(obj_or_id, IPv6Range):
            self._ipv6_range = obj_or_id
            self._ipv6_range_id = self._ipv6_range.id
            if not self._ipv6_range_id:
                raise ValueError(_('IPv6地址段对象id无效'))
        else:
            raise ValueError(_('值必须是一个IPv6地址段对象或者是一个id'))

    @staticmethod
    def build_subnets(ipv6_range: IPv6Range, sub_ranges: List[IPv6RangeStrItem]) -> List[IPv6Range]:
        asn = ipv6_range.asn
        assigned_time = ipv6_range.assigned_time
        org_virt_obj = ipv6_range.org_virt_obj
        admin_remark = ipv6_range.admin_remark
        subnets = []
        for sr in sub_ranges:
            nt = dj_timezone.now()
            ip_rg = IPv6Range(
                start_address=sr.start_bytes, end_address=sr.end_bytes, prefixlen=sr.prefix,
                asn=asn, status=ipv6_range.status, creation_time=nt, update_time=nt,
                assigned_time=assigned_time, org_virt_obj=org_virt_obj,
                admin_remark=admin_remark, remark=''
            )
            ip_rg.name = str(ip_rg.start_address_network)
            subnets.append(ip_rg)

        return subnets

    @staticmethod
    def _do_split_ipv6_range(
            ipv6_range: IPv6Range, subnets: List[IPv6Range]) -> List[IPv6Range]:
        """
        * 此函数需要在一个事务中执行
        """
        for sn in subnets:
            sn.enforce_id()  # 生成id

            if not sn.name:
                sn.name = str(sn.start_address_network)

            try:
                sn.clean(exclude_ids=[ipv6_range.id])
            except ValidationError as exc:
                raise errors.ValidationError(
                    message=_('拆分的子网 (%(value)s) 不符合规则。') % {'value': sn} + exc.messages[0])

        IPv6Range.objects.bulk_create(subnets)
        ipv6_range.delete()
        return subnets

    @staticmethod
    def add_split_record(ipv6_range: IPv6Range, range_items: List[IPv6RangeStrItem], user):
        try:
            # range_items = [
            #     IPv6RangeStrItem(
            #         start=str(sn.start_address_obj), end=str(sn.end_address_obj), prefix=sn.prefixlen
            #     ) for sn in subnets
            # ]

            IPv6RangeRecordManager.create_split_record(
                user=user, ip_range=ipv6_range, remark='', ip_ranges=range_items
            )
        except Exception as exc:
            pass

    def split_to_plan(self, sub_ranges: list, user) -> List[IPv6Range]:
        with transaction.atomic():
            ipv6_range = IPv6Range.objects.select_for_update().select_related(
                'asn', 'org_virt_obj__organization').filter(id=self._ipv6_range_id).first()
            if ipv6_range is None:
                raise errors.TargetNotExist(message=_('IP地址段不存在'))

            if ipv6_range.status not in [IPv6Range.Status.WAIT.value, IPv6Range.Status.RESERVED.value]:
                raise errors.ConflictError(message=_('只允许拆分“未分配”和“预留”状态的IP地址段'))

            sub_ranges = self.validate_sub_ranges_plan(ipv6_range=ipv6_range, sub_ranges=sub_ranges)
            ip_ranges = self.build_subnets(ipv6_range=ipv6_range, sub_ranges=sub_ranges)
            # 如果子网和超网一致，返回
            if len(ip_ranges) == 1:
                rg = ip_ranges[0]
                if (
                        ipv6_range.start_address == rg.start_address
                        and ipv6_range.end_address == rg.end_address
                        and ipv6_range.prefixlen == rg.prefixlen
                ):
                    return [ipv6_range]

            ip_ranges = self._do_split_ipv6_range(ipv6_range=ipv6_range, subnets=ip_ranges)

        self.add_split_record(ipv6_range=ipv6_range, range_items=sub_ranges, user=user)
        return ip_ranges

    @staticmethod
    def validate_sub_ranges_plan(ipv6_range: IPv6Range, sub_ranges: list) -> List[IPv6RangeStrItem]:
        """
        验证指定的拆分子网规划

        :sub_ranges item: {'start_address': 'xx', 'end_address': 'xx', 'prefix': 24}
        """
        if len(sub_ranges) > 1024:
            raise errors.InvalidArgument(message=_('每次拆分子网数量不得超过1024个'))

        # 必须是按start address正序排序的
        first_sub_range = IPv6RangeStrItem(
            start=sub_ranges[0]['start_address'], end=sub_ranges[0]['end_address'], prefix=sub_ranges[0]['prefix'])
        if first_sub_range.start_int != int(ipv6_range.start_address_obj):
            raise errors.InvalidArgument(message=_(
                '子网起始地址(%(subaddr)s)与要拆分的超网起始地址(%(superaddr)s)不一致。'
            ) % {'subaddr': sub_ranges[0]['start_address'], 'superaddr': str(ipv6_range.start_address_obj)})

        last_sub_range = IPv6RangeStrItem(
            start=sub_ranges[-1]['start_address'], end=sub_ranges[-1]['end_address'], prefix=sub_ranges[-1]['prefix'])
        if last_sub_range.end_int != int(ipv6_range.end_address_obj):
            raise errors.InvalidArgument(message=_(
                '子网结束地址(%(subaddr)s)与要拆分的超网结束地址(%(superaddr)s)不一致。'
            ) % {'subaddr': sub_ranges[-1]['end_address'], 'superaddr': str(ipv6_range.end_address_obj)})

        subnets = []
        pre_range = None
        for sr in sub_ranges:
            sr = IPv6RangeStrItem(start=sr['start_address'], end=sr['end_address'], prefix=sr['prefix'])

            if ipv6_range.prefixlen > sr.prefix:
                raise errors.InvalidArgument(message=_('子网掩码长度必须不得小于要拆分的超网掩码长度。') + f'{sr}')

            if sr.prefix > 128:
                raise errors.InvalidArgument(message=_('子网掩码长度不得大于128。') + f'{sr}')

            if sr.start_int > sr.end_int:
                raise errors.InvalidArgument(message=_('子网无效，起始地址不能大于结束地址。') + f'{sr}')

            if pre_range and sr.start_int - pre_range.end_int != 1:
                raise errors.InvalidArgument(message=_('相邻子网地址不连续。') + f'{pre_range}；{sr}')

            subnets.append(sr)
            pre_range = sr

        return subnets

    # --- 最小化分拆规划 ---

    @staticmethod
    def split_plan_by_mask(
            start_address: str, end_address: str, prefix: int, new_prefix: int
    ) -> List[IPv6RangeStrItem]:
        """
        按掩码长度划分一个地址段, 按地址正序
        """
        if new_prefix < prefix:
            raise errors.InvalidArgument(message=_('子网掩码长度必须大于拆分IP地址段的掩码长度'))

        if new_prefix > 128:
            raise errors.InvalidArgument(message=_('子网掩码长度不能大于128'))

        super_range = IPv6RangeStrItem(start=start_address, end=end_address, prefix=prefix)
        start_address_int = super_range.start_int
        end_address_int = super_range.end_int
        net_work = ipaddress.IPv6Network((start_address, prefix), strict=False)
        subnets = []
        for sn in net_work.subnets(new_prefix=new_prefix):
            sn_start_addr = int(sn.network_address)
            sn_end_addr = int(sn.broadcast_address)

            # 子网起始地址大于ip地址段截止地址时退出
            if sn_start_addr > end_address_int:
                break

            # 直到起始地址在子网段内的子网
            if sn_end_addr < start_address_int:
                continue

            start = max(sn_start_addr, start_address_int)
            end = min(sn_end_addr, end_address_int)
            subnets.append(IPv6RangeStrItem(
                start=str(ipaddress.IPv6Address(start)),
                end=str(ipaddress.IPv6Address(end)),
                prefix=new_prefix)
            )

        return subnets

    @staticmethod
    def mini_split_plan(
            ip_range: IPv6RangeStrItem, new_prefix: int, prefixlen_diff: int = 3
    ) -> List[IPv6RangeStrItem]:
        """
        最小化分拆规划

        :param ip_range: 被拆分网段
        :param new_prefix: 新的目标拆分前缀/掩码长度
        :param prefixlen_diff: 距离目标拆分前缀/掩码指定长度以内平拆
        """
        if new_prefix <= ip_range.prefix:
            raise errors.Error(message=_('掩码/前缀长度必须大于被拆分网段的掩码/前缀长度'))

        if not (1 <= prefixlen_diff <= 8):
            raise errors.Error(message=_('prefixlen_diff 可选值范围1-8，最多平拆出256个目标前缀长度的子网'))

        # 被拆分网段合法性检查，是否同一网段，网络号是否一致
        try:
            start_network = ipaddress.IPv6Network((ip_range.start, ip_range.prefix), strict=False)
            end_anetwork = ipaddress.IPv6Network((ip_range.end, ip_range.prefix), strict=False)
        except ipaddress.NetmaskValueError as exc:
            raise errors.Error(message=_('子网网段掩码无效') + str(exc))
        except ipaddress.AddressValueError as exc:
            raise errors.Error(message=_('子网网段地址无效') + str(exc))

        if start_network != end_anetwork:
            raise errors.Error(message=_("起始地址网络号({start_net})和结束地址网络号({end_net})不一致").format(
                start_net=start_network, end_net=end_anetwork))

        # 最小化拆分
        subnets = IPv6RangeSplitter.split_step_by_step(
            ip_range=ip_range, new_prefix=new_prefix, prefixlen_diff=prefixlen_diff)

        # 最后一步是按目标前缀长度平拆
        subnets = IPv6RangeSplitter.mini_split_target_subnets(
            subnets=subnets, new_prefix=new_prefix, prefixlen_diff=prefixlen_diff)
        return subnets

    @staticmethod
    def split_step_by_step(
            ip_range: IPv6RangeStrItem, new_prefix: int, prefixlen_diff: int
    ) -> List[IPv6RangeStrItem]:
        """
        按前缀长度逐步 最小化分拆，返回ip正序子网列表

        :param ip_range: 被拆分网段
        :param new_prefix: 新的目标拆分前缀/掩码长度
        :param prefixlen_diff: 距离目标拆分前缀/掩码指定长度以内平拆
        """
        subnets = [ip_range]    # 最终拆分结果子网列表

        step_start = ip_range.prefix + 1
        step_end = new_prefix - prefixlen_diff

        if step_start > step_end:
            return subnets

        # 例如：16 -> [17, 18]; diff = 3 ; split by []
        # 例如：16 -> 19; diff = 3 ; split by [17]
        # 例如：16 -> 24; diff = 3 ; split by [17, 18, 19, 20, 21]
        for next_prefix in range(step_start, step_end + 1):
            # 去除列表 subnets 中的第一个网段，并拆分此网段
            split_range = subnets.pop(0)
            sub_ranges = IPv6RangeSplitter.split_plan_by_mask(
                start_address=split_range.start,
                end_address=split_range.end,
                prefix=split_range.prefix,
                new_prefix=next_prefix
            )

            # 子网正序排序，并合并到 子网列表 前面
            # sub_ranges.sort(key=lambda x: x.start_int, reverse=False)
            subnets = sub_ranges + subnets

        return subnets

    @staticmethod
    def mini_split_target_subnets(
            subnets: list[IPv6RangeStrItem], new_prefix: int, prefixlen_diff: int = 3
    ) -> List[IPv6RangeStrItem]:
        """
        目标前缀长度的子网拆分
        """
        need_count = 2 ** (prefixlen_diff - 1)  # 需要有目标前缀长度的子网数量，至少达到一半

        # 平拆列表 subnets 中的第一个网段
        split_range = subnets.pop(0)
        sub_ranges = IPv6RangeSplitter.split_plan_by_mask(
            start_address=split_range.start,
            end_address=split_range.end,
            prefix=split_range.prefix,
            new_prefix=new_prefix
        )
        if len(sub_ranges) >= need_count or not subnets:
            # 子网正序排序，并合并到 子网列表 前面
            # sub_ranges.sort(key=lambda x: x.start_int, reverse=False)
            return sub_ranges + subnets

        # 第一个子网平拆子网数较少，拆下一个子网
        split_range2 = subnets.pop(0)
        prefix_diff2 = max(prefixlen_diff - 1, 1)   # prefixlen_diff - 1，只需要再平拆出一半的子网
        # 先尝试最小化分拆，再平拆第一个子网
        nets = IPv6RangeSplitter.split_step_by_step(
            ip_range=split_range2, new_prefix=new_prefix, prefixlen_diff=prefix_diff2)
        net1 = nets.pop(0)
        sub2_ranges = IPv6RangeSplitter.split_plan_by_mask(
            start_address=net1.start,
            end_address=net1.end,
            prefix=net1.prefix,
            new_prefix=new_prefix
        )
        sub2_ranges += nets

        subnets = sub_ranges + sub2_ranges + subnets
        # subnets.sort(key=lambda x: x.start_int, reverse=False)
        return subnets

