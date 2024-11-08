import ipaddress
from typing import Union, List, Tuple
from datetime import datetime
from collections import namedtuple

from django.db.models import Q, QuerySet
from django.db import transaction, IntegrityError
from django.utils import timezone as dj_timezone
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError

from core import errors
from apps.app_net_manage.models import OrgVirtualObject
from apps.app_net_ipam.models import (
    IPv4Range, ASN, ipv4_str_to_int, IPv4RangeRecord,
    IPRangeItem, IPRangeIntItem, IPv4Address, IPv4Supernet, ExternalIPv4Range
)
from apps.app_net_ipam.managers.common import NetIPamUserRoleWrapper


MAX_IPV4_ADDRESS_INT = 2 ** 32 - 1


def get_or_create_asn(number: int):
    asn = ASN.objects.filter(number=number).first()
    if asn is not None:
        return asn

    try:
        max_id = ASN.get_max_id()
        asn = ASN(id=max_id + 1, name=f'AS{number}', number=number, creation_time=dj_timezone.now())
        asn.save(force_insert=True)
        return asn
    except IntegrityError:
        asn = ASN.objects.filter(number=number).first()
        if asn is not None:
            return asn

        max_id = ASN.get_max_id()
        asn = ASN(id=max_id + 1, name=f'AS{number}', number=number, creation_time=dj_timezone.now())
        asn.save(force_insert=True)
        return asn


class IPv4RangeManager:
    @staticmethod
    def get_ip_range(_id: str) -> IPv4Range:
        iprange = IPv4Range.objects.select_related('asn', 'org_virt_obj').filter(id=_id).first()
        if iprange is None:
            raise errors.TargetNotExist(message=_('IP地址段不存在'))

        return iprange

    @staticmethod
    def get_ip_range_by_ip(ip_int: int) -> IPv4Range:
        iprange = IPv4Range.objects.select_related('asn', 'org_virt_obj').filter(
            start_address__lte=ip_int, end_address__gte=ip_int).first()
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

        return IPv4Range.objects.select_related(*fileds).all()

    def filter_queryset(self, org_ids: Union[list, None], status: Union[str, None], asn: int, ipv4_int: int,
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

        if ipv4_int:
            lookups['start_address__lte'] = ipv4_int
            lookups['end_address__gte'] = ipv4_int

        if lookups:
            qs = qs.filter(**lookups)

        if search:
            q = Q(name__icontains=search) | Q(remark__icontains=search)
            if is_admin:
                q |= Q(admin_remark__icontains=search)

            qs = qs.filter(q)

        return qs

    def get_user_queryset(self, org_id: str, asn: int, ipv4_int: int, search: str, user_role: NetIPamUserRoleWrapper):
        org_ids = user_role.get_user_ipam_org_ids()
        if not org_ids:
            return self.get_queryset().none()

        if org_id:
            if org_id not in org_ids:
                return self.get_queryset().none()
            else:
                org_ids = [org_id]

        return self.filter_queryset(
            org_ids=org_ids, status=IPv4Range.Status.ASSIGNED.value, asn=asn,
            ipv4_int=ipv4_int, search=search, is_admin=False)

    def get_admin_queryset(self, org_ids: Union[list, None], status: str, asn: int, ipv4_int: int, search: str):
        return self.filter_queryset(
            org_ids=org_ids, status=status, asn=asn, ipv4_int=ipv4_int, search=search, is_admin=True)

    @staticmethod
    def create_ipv4_range(
            name: str, start_ip: Union[str, int], end_ip: Union[str, int], mask_len: int,
            asn: Union[ASN, int], status_code: str, org_virt_obj: Union[OrgVirtualObject, None],
            admin_remark: str, remark: str,
            create_time: Union[datetime, None], update_time: Union[datetime, None], assigned_time=None
    ):
        """
        :return: IPv4Range
        :raises: ValidationError
        """
        ip_range = IPv4RangeManager.build_ipv4_range(
            name=name, start_ip=start_ip, end_ip=end_ip, mask_len=mask_len,
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
    def build_ipv4_range(
            name: str, start_ip: Union[str, int], end_ip: Union[str, int], mask_len: int,
            asn: Union[ASN, int], status_code: str, org_virt_obj: Union[OrgVirtualObject, str, None],
            admin_remark: str, remark: str,
            create_time: Union[datetime, None], update_time: Union[datetime, None], assigned_time=None
    ):
        """
        构建一个IPv4Range对象，不保存到数据库

        :return: IPv4Range
        :raises: ValidationError
        """
        if isinstance(start_ip, int):
            start_int = start_ip
        else:
            start_int = ipv4_str_to_int(ipv4=start_ip)

        if isinstance(end_ip, int):
            end_int = end_ip
        else:
            end_int = ipv4_str_to_int(ipv4=end_ip)

        mask_len = int(mask_len)
        if not (0 <= mask_len <= 32):
            raise errors.ValidationError(message=_('子网掩码长度无效，取值范围为0-32'))

        if status_code not in IPv4Range.Status.values:
            raise errors.ValidationError(message=_('IP地址段的状态值无效'))

        if isinstance(asn, int):
            asn = get_or_create_asn(number=asn)

        if create_time is None:
            create_time = dj_timezone.now()
        if update_time is None:
            update_time = create_time

        ip_range = IPv4Range(
            name=name,
            status=status_code,
            creation_time=create_time,
            update_time=update_time,
            assigned_time=assigned_time,
            asn=asn,
            start_address=start_int,
            end_address=end_int,
            mask_len=mask_len,
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
    def do_create_ipv4_range(
            user, name: str, start_ip: Union[str, int], end_ip: Union[str, int], mask_len: int,
            asn: Union[ASN, int], org_virt_obj: Union[OrgVirtualObject, None],
            admin_remark: str, remark: str,
            create_time: Union[datetime, None], update_time: Union[datetime, None], assigned_time=None
    ):
        """
        :return: IPv4Range
        :raises: ValidationError
        """
        ip_range = IPv4RangeManager.create_ipv4_range(
            name=name, start_ip=start_ip, end_ip=end_ip, mask_len=mask_len,
            asn=asn, status_code=IPv4Range.Status.WAIT.value, org_virt_obj=org_virt_obj,
            admin_remark=admin_remark, remark=remark,
            create_time=create_time, update_time=update_time, assigned_time=assigned_time
        )
        try:
            IPv4RangeRecordManager.create_add_record(
                user=user, ipv4_range=ip_range, remark=''
            )
        except Exception as exc:
            pass

        return ip_range

    @staticmethod
    def update_ipv4_range(
            ip_range: IPv4Range, name: str, start_ip: Union[str, int], end_ip: Union[str, int], mask_len: int,
            asn: Union[ASN, int], admin_remark: str
    ):
        """
        :return: IPv4Range, update_fields: list
        :raises: ValidationError
        """
        if isinstance(start_ip, int):
            start_int = start_ip
        else:
            start_int = ipv4_str_to_int(ipv4=start_ip)

        if isinstance(end_ip, int):
            end_int = end_ip
        else:
            end_int = ipv4_str_to_int(ipv4=end_ip)

        mask_len = int(mask_len)
        if not (0 <= mask_len <= 32):
            raise errors.ValidationError(message=_('子网掩码长度无效，取值范围为0-32'))

        if isinstance(asn, int):
            asn = get_or_create_asn(number=asn)

        update_fields = []
        if name and ip_range.name != name:
            ip_range.name = name
            update_fields.append('name')

        if start_int != ip_range.start_address:
            ip_range.start_address = start_int
            update_fields.append('start_address')

        if end_int != ip_range.end_address:
            ip_range.end_address = end_int
            update_fields.append('end_address')

        if mask_len != ip_range.mask_len:
            ip_range.mask_len = mask_len
            update_fields.append('mask_len')

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
                ip_range.clear_cached_property()    # 字段值变更了，需要清除缓存属性
                ip_range.clean()
            except ValidationError as exc:
                raise errors.ValidationError(message=exc.messages[0])

            ip_range.save(update_fields=update_fields)

        return ip_range, update_fields

    @staticmethod
    def do_update_ipv4_range(
            ip_range: IPv4Range, user, name: str, start_ip: Union[str, int], end_ip: Union[str, int], mask_len: int,
            asn: Union[ASN, int], admin_remark: str
    ) -> IPv4Range:
        """
        :raises: ValidationError
        """
        old_ip_range = IPRangeIntItem(
            start=ip_range.start_address, end=ip_range.end_address, mask=ip_range.mask_len
        )
        ip_range, update_fields = IPv4RangeManager.update_ipv4_range(
            ip_range=ip_range, name=name, start_ip=start_ip, end_ip=end_ip, mask_len=mask_len,
            asn=asn, admin_remark=admin_remark
        )

        # need_record = any(True if f in update_fields else False for f in ['start_address', 'end_address', 'mask_len'])
        need_record = False
        if update_fields:
            for f in ['start_address', 'end_address', 'mask_len']:
                if f in update_fields:
                    need_record = True
                    break

        if need_record:
            try:
                new_ip_range = IPRangeItem(
                    start=str(ip_range.start_address_obj), end=str(ip_range.end_address_obj), mask=ip_range.mask_len
                )
                IPv4RangeRecordManager.create_change_record(
                    user=user, new_ipv4_range=new_ip_range, remark='', old_ip_range=old_ip_range
                )
            except Exception as exc:
                pass

        return ip_range

    @staticmethod
    def do_delete_ipv4_range(ip_range: IPv4Range, user):
        ip_range.delete()
        try:
            IPv4RangeRecordManager.create_delete_record(
                user=user, ipv4_range=ip_range, remark='', org_virt_obj=ip_range.org_virt_obj)
        except Exception as exc:
            pass

        return ip_range

    @staticmethod
    def split_ipv4_range_by_mask(user, range_id: str, new_prefix: int, fake: bool = False) -> List[IPv4Range]:
        """
        按掩码长度划分一个地址段
        """
        return IPv4RangeSplitter(obj_or_id=range_id).split_by_mask(user=user, new_prefix=new_prefix, fake=fake)

    @staticmethod
    def split_ipv4_range_to_plan(user, range_id: str, sub_ranges: list) -> List[IPv4Range]:
        """
        按指定拆分计划拆分一个地址段
        """
        return IPv4RangeSplitter(obj_or_id=range_id).split_to_plan(user=user, sub_ranges=sub_ranges)

    @staticmethod
    def merge_ipv4_ranges_by_mask(user, range_ids: List[str], new_prefix: int, fake: bool = False) -> IPv4Range:
        """
        按掩码长度把子网地址段合并为一个超网
        """
        try:
            supernet, ip_ranges = IPv4RangeMerger(
                ipv4_range_ids=range_ids, new_prefix=new_prefix).do_merge(user=user, fake=fake)
        except errors.ValidationError as exc:
            raise errors.ConflictError(message=exc.message)

        return supernet

    @staticmethod
    def do_recover_ipv4_range(ip_range: IPv4Range, user):
        """
        从 已分配和预留 状态 收回
        """
        org_virt_obj = ip_range.org_virt_obj

        status = ip_range.status
        ip_range.status = IPv4Range.Status.WAIT.value
        ip_range.org_virt_obj = None
        ip_range.assigned_time = None
        ip_range.update_time = dj_timezone.now()
        ip_range.remark = ''
        ip_range.save(update_fields=['status', 'org_virt_obj', 'assigned_time', 'update_time', 'remark'])
        try:
            remark = f'{IPv4Range.Status.WAIT.value} from {status}'
            IPv4RangeRecordManager.create_recover_record(
                user=user, ipv4_range=ip_range, remark=remark, org_virt_obj=org_virt_obj
            )
        except Exception as exc:
            pass

        return ip_range

    @staticmethod
    def do_reserve_ipv4_range(ip_range: IPv4Range, org_virt_obj, user):
        """
        预留
        """
        status = ip_range.status
        ip_range.status = IPv4Range.Status.RESERVED.value
        ip_range.org_virt_obj = org_virt_obj
        ip_range.assigned_time = None
        ip_range.update_time = dj_timezone.now()
        ip_range.remark = ''
        ip_range.save(update_fields=['status', 'org_virt_obj', 'assigned_time', 'update_time', 'remark'])
        try:
            remark = f'{IPv4Range.Status.RESERVED.value} from {status}'
            IPv4RangeRecordManager.create_reserve_record(
                user=user, ipv4_range=ip_range, remark=remark, org_virt_obj=org_virt_obj
            )
        except Exception as exc:
            pass

        return ip_range

    @staticmethod
    def do_assign_ipv4_range(ip_range: IPv4Range, org_virt_obj, user):
        """
        分配
        """
        old_status = ip_range.status
        nt = dj_timezone.now()
        ip_range.status = IPv4Range.Status.ASSIGNED.value
        ip_range.org_virt_obj = org_virt_obj
        ip_range.assigned_time = nt
        ip_range.update_time = nt
        ip_range.remark = ''
        ip_range.save(update_fields=['status', 'org_virt_obj', 'assigned_time', 'update_time', 'remark'])
        try:
            remark = f'{IPv4Range.Status.ASSIGNED.value} from {old_status}'
            IPv4RangeRecordManager.create_assign_record(
                user=user, ipv4_range=ip_range, remark=remark, org_virt_obj=org_virt_obj
            )
        except Exception as exc:
            pass


class IPv4RangeRecordManager:
    @staticmethod
    def create_record(
            user, record_type: str,
            start_address: int, end_address: int, mask_len: int, ip_ranges: List[IPRangeItem],
            remark: str = '', org_virt_obj: OrgVirtualObject = None
    ):
        record = IPv4RangeRecord(
            creation_time=dj_timezone.now(),
            record_type=record_type,
            start_address=start_address,
            end_address=end_address,
            mask_len=mask_len,
            user=user,
            org_virt_obj=org_virt_obj,
            remark=remark
        )
        record.set_ip_ranges(ip_ranges=ip_ranges)
        record.save(force_insert=True)
        return record

    @staticmethod
    def create_add_record(user, ipv4_range: IPv4Range, remark: str):
        return IPv4RangeRecordManager.create_record(
            user=user, record_type=IPv4RangeRecord.RecordType.ADD.value,
            start_address=ipv4_range.start_address, end_address=ipv4_range.end_address, mask_len=ipv4_range.mask_len,
            ip_ranges=[], remark=remark, org_virt_obj=None
        )

    @staticmethod
    def create_delete_record(user, ipv4_range: IPv4Range, remark: str, org_virt_obj):
        return IPv4RangeRecordManager.create_record(
            user=user, record_type=IPv4RangeRecord.RecordType.DELETE.value,
            start_address=ipv4_range.start_address, end_address=ipv4_range.end_address, mask_len=ipv4_range.mask_len,
            ip_ranges=[], remark=remark, org_virt_obj=org_virt_obj
        )

    @staticmethod
    def create_change_record(user, new_ipv4_range: IPRangeItem, remark: str, old_ip_range: IPRangeIntItem):
        return IPv4RangeRecordManager.create_record(
            user=user, record_type=IPv4RangeRecord.RecordType.CHANGE.value,
            start_address=old_ip_range.start, end_address=old_ip_range.end, mask_len=old_ip_range.mask,
            ip_ranges=[new_ipv4_range], remark=remark, org_virt_obj=None
        )

    @staticmethod
    def create_split_record(user, ipv4_range: IPv4Range, remark: str, ip_ranges: List[IPRangeItem]):
        return IPv4RangeRecordManager.create_record(
            user=user, record_type=IPv4RangeRecord.RecordType.SPLIT.value,
            start_address=ipv4_range.start_address, end_address=ipv4_range.end_address, mask_len=ipv4_range.mask_len,
            ip_ranges=ip_ranges, remark=remark, org_virt_obj=None
        )

    @staticmethod
    def create_merge_record(user, ipv4_range: IPv4Range, remark: str, ip_ranges: List[IPRangeItem]):
        return IPv4RangeRecordManager.create_record(
            user=user, record_type=IPv4RangeRecord.RecordType.MERGE.value,
            start_address=ipv4_range.start_address, end_address=ipv4_range.end_address, mask_len=ipv4_range.mask_len,
            ip_ranges=ip_ranges, remark=remark, org_virt_obj=None
        )

    @staticmethod
    def create_recover_record(user, ipv4_range: IPv4Range, remark: str, org_virt_obj):
        return IPv4RangeRecordManager.create_record(
            user=user, record_type=IPv4RangeRecord.RecordType.RECOVER.value,
            start_address=ipv4_range.start_address, end_address=ipv4_range.end_address, mask_len=ipv4_range.mask_len,
            ip_ranges=[], remark=remark, org_virt_obj=org_virt_obj
        )

    @staticmethod
    def create_reserve_record(user, ipv4_range: IPv4Range, remark: str, org_virt_obj):
        return IPv4RangeRecordManager.create_record(
            user=user, record_type=IPv4RangeRecord.RecordType.RESERVE.value,
            start_address=ipv4_range.start_address, end_address=ipv4_range.end_address, mask_len=ipv4_range.mask_len,
            ip_ranges=[], remark=remark, org_virt_obj=org_virt_obj
        )

    @staticmethod
    def create_assign_record(user, ipv4_range: IPv4Range, remark: str, org_virt_obj):
        return IPv4RangeRecordManager.create_record(
            user=user, record_type=IPv4RangeRecord.RecordType.ASSIGN.value,
            start_address=ipv4_range.start_address, end_address=ipv4_range.end_address, mask_len=ipv4_range.mask_len,
            ip_ranges=[], remark=remark, org_virt_obj=org_virt_obj
        )


class IPv4RangeSplitter:
    def __init__(self, obj_or_id: Union[IPv4Range, str]):
        if isinstance(obj_or_id, str):
            self._ipv4_range_id = obj_or_id
            self._ipv4_range = None
        elif isinstance(obj_or_id, IPv4Range):
            self._ipv4_range = obj_or_id
            self._ipv4_range_id = self._ipv4_range.id
            if not self._ipv4_range_id:
                raise ValueError(_('IPv4地址段对象id无效'))
        else:
            raise ValueError(_('值必须是一个IPv4地址段对象或者是一个id'))

    def split_by_mask(self, user, new_prefix: int, fake: bool = False):
        """
        :raises: Error
        """
        self._ipv4_range, sub_ip_ranges = self.split_ipv4_range_by_mask(
            range_id=self._ipv4_range_id, new_prefix=new_prefix, fake=fake
        )

        if not fake:
            self.add_split_record(ipv4_range=self._ipv4_range, subnets=sub_ip_ranges, user=user)

        return sub_ip_ranges

    @staticmethod
    def split_subnets(ipv4_range: IPv4Range, new_prefix: int) -> List[IPv4Range]:
        """
        :raises: Error
        """
        sub_ranges = IPv4RangeSplitter.split_plan_by_mask(
            start_address=ipv4_range.start_address, end_address=ipv4_range.end_address,
            mask_len=ipv4_range.mask_len, split_mask=new_prefix
        )
        return IPv4RangeSplitter.build_subnets(ipv4_range=ipv4_range, sub_ranges=sub_ranges)

    @staticmethod
    def build_subnets(ipv4_range: IPv4Range, sub_ranges: List[IPRangeIntItem]):
        asn = ipv4_range.asn
        assigned_time = ipv4_range.assigned_time
        org_virt_obj = ipv4_range.org_virt_obj
        admin_remark = ipv4_range.admin_remark
        subnets = []
        for sr in sub_ranges:
            nt = dj_timezone.now()
            ip_rg = IPv4Range(
                start_address=sr.start, end_address=sr.end, mask_len=sr.mask,
                asn=asn, status=ipv4_range.status, creation_time=nt, update_time=nt,
                assigned_time=assigned_time, org_virt_obj=org_virt_obj,
                admin_remark=admin_remark, remark=''
            )
            ip_rg.name = str(ip_rg.start_address_network)
            subnets.append(ip_rg)

        return subnets

    @staticmethod
    def split_plan_by_mask(
            start_address: int, end_address: int, mask_len: int, split_mask: int
    ) -> List[IPRangeIntItem]:
        """
        按掩码长度划分一个地址段
        """
        if split_mask < mask_len:
            raise errors.InvalidArgument(message=_('子网掩码长度必须大于拆分IP地址段的掩码长度'))

        if split_mask > 32:
            raise errors.InvalidArgument(message=_('子网掩码长度不能大于32'))

        net_work = ipaddress.IPv4Network((start_address, mask_len), strict=False)
        subnets = []
        for sn in net_work.subnets(new_prefix=split_mask):
            sn_start_addr = int(sn.network_address)
            sn_end_addr = int(sn.broadcast_address)

            # 子网起始地址大于ip地址段截止地址时退出
            if sn_start_addr > end_address:
                break

            # 直到起始地址在子网段内的子网
            if sn_end_addr < start_address:
                continue

            start = max(sn_start_addr, start_address)
            end = min(sn_end_addr, end_address)
            subnets.append(IPRangeIntItem(start=start, end=end, mask=split_mask))

        return subnets

    @staticmethod
    def do_split_ipv4_range_by_mask(
            ipv4_range: IPv4Range, new_prefix: int, fake: bool = False) -> List[IPv4Range]:
        """
        按掩码长度拆分一个地址段

        * 此函数需要在一个事务中执行

        :param ipv4_range: 要拆分的地址段
        :param new_prefix: 要拆分的掩码长度
        :param fake: True(假拆分，只返回拆分结果，不保存到数据库)；False(拆分并保存结果到数据库)
        """
        if new_prefix < ipv4_range.mask_len:
            raise errors.ConflictError(message=_('子网掩码长度必须大于拆分IP地址段的掩码长度'))

        if (new_prefix - ipv4_range.mask_len) > 8:
            raise errors.ConflictError(
                message=_('子网掩码长度与被拆分IP地址段的掩码长度相差不允许超过8，即每次拆分子网数量不得超过256个'))

        if ipv4_range.status not in [IPv4Range.Status.WAIT.value, IPv4Range.Status.RESERVED.value]:
            raise errors.ConflictError(message=_('只允许拆分“未分配”和“预留”状态的IP地址段'))

        subnets = IPv4RangeSplitter.split_subnets(ipv4_range=ipv4_range, new_prefix=new_prefix)
        if fake:
            return subnets

        return IPv4RangeSplitter._do_split_ipv4_range(ipv4_range=ipv4_range, subnets=subnets)

    @staticmethod
    def _do_split_ipv4_range(
            ipv4_range: IPv4Range, subnets: List[IPv4Range]) -> List[IPv4Range]:
        """
        * 此函数需要在一个事务中执行
        """
        for sn in subnets:
            sn.enforce_id()  # 生成id

            if not sn.name:
                sn.name = str(sn.start_address_network)

            try:
                sn.clean(exclude_ids=[ipv4_range.id])
            except ValidationError as exc:
                raise errors.ValidationError(
                    message=_('拆分的子网 (%(value)s) 不符合规则。') % {'value': sn} + exc.messages[0])

        IPv4Range.objects.bulk_create(subnets)
        ipv4_range.delete()
        return subnets

    @staticmethod
    def split_ipv4_range_by_mask(
            range_id: str, new_prefix: int, fake: bool = False
    ) -> (IPv4Range, List[IPv4Range]):
        """
        按掩码长度划分一个地址段
        """
        if new_prefix > 32:
            raise errors.InvalidArgument(message=_('子网掩码长度不能大于32'))

        if fake:
            ipv4_range = IPv4RangeManager.get_ip_range(_id=range_id)
            return ipv4_range, IPv4RangeSplitter.do_split_ipv4_range_by_mask(
                ipv4_range=ipv4_range, new_prefix=new_prefix, fake=True)

        with transaction.atomic():
            ipv4_range = IPv4Range.objects.select_for_update().select_related(
                'asn', 'org_virt_obj').filter(id=range_id).first()
            if ipv4_range is None:
                raise errors.TargetNotExist(message=_('IP地址段不存在'))

            subnets = IPv4RangeSplitter.do_split_ipv4_range_by_mask(
                ipv4_range=ipv4_range, new_prefix=new_prefix, fake=False)

        return ipv4_range, subnets

    @staticmethod
    def add_split_record(ipv4_range: IPv4Range, subnets: List[IPv4Range], user):
        try:
            range_items = [
                IPRangeItem(
                    start=str(sn.start_address_obj), end=str(sn.end_address_obj), mask=sn.mask_len
                ) for sn in subnets
            ]

            IPv4RangeRecordManager.create_split_record(
                user=user, ipv4_range=ipv4_range, remark='', ip_ranges=range_items
            )
        except Exception as exc:
            pass

    def split_to_plan(self, sub_ranges: list, user) -> List[IPv4Range]:
        with transaction.atomic():
            ipv4_range = IPv4Range.objects.select_for_update().select_related(
                'asn', 'org_virt_obj__organization').filter(id=self._ipv4_range_id).first()
            if ipv4_range is None:
                raise errors.TargetNotExist(message=_('IP地址段不存在'))

            if ipv4_range.status not in [IPv4Range.Status.WAIT.value, IPv4Range.Status.RESERVED.value]:
                raise errors.ConflictError(message=_('只允许拆分“未分配”和“预留”状态的IP地址段'))

            sub_ranges = self.validate_sub_ranges_plan(ipv4_range=ipv4_range, sub_ranges=sub_ranges)
            ip_ranges = self.build_subnets(ipv4_range=ipv4_range, sub_ranges=sub_ranges)
            # 如果子网和超网一致，返回
            if len(ip_ranges) == 1:
                rg = ip_ranges[0]
                if (
                        ipv4_range.start_address == rg.start_address
                        and ipv4_range.end_address == rg.end_address
                        and ipv4_range.mask_len == rg.mask_len
                ):
                    return [ipv4_range]

            ip_ranges = self._do_split_ipv4_range(ipv4_range=ipv4_range, subnets=ip_ranges)

        self.add_split_record(ipv4_range=ipv4_range, subnets=ip_ranges, user=user)
        return ip_ranges

    @staticmethod
    def validate_sub_ranges_plan(ipv4_range: IPv4Range, sub_ranges: list) -> List[IPRangeIntItem]:
        """
        验证指定的拆分子网规划

        :sub_ranges item: {'start_address': 0, 'end_address': 255, 'prefix': 24}
        """
        if len(sub_ranges) > 1024:
            raise errors.InvalidArgument(message=_('每次拆分子网数量不得超过1024个'))

        # 必须是按start address正序排序的
        if sub_ranges[0]['start_address'] != ipv4_range.start_address:
            raise errors.InvalidArgument(message=_(
                '子网起始地址(%(subaddr)d)与要拆分的超网起始地址(%(superaddr)d)不一致。'
            ) % {'subaddr': sub_ranges[0]['start_address'], 'superaddr': ipv4_range.start_address})

        if sub_ranges[-1]['end_address'] != ipv4_range.end_address:
            raise errors.InvalidArgument(message=_(
                '子网结束地址(%(subaddr)d)与要拆分的超网结束地址(%(superaddr)d)不一致。'
            ) % {'subaddr': sub_ranges[-1]['end_address'], 'superaddr': ipv4_range.end_address})

        subnets = []
        pre_range = None
        for sr in sub_ranges:
            start = sr['start_address']
            end = sr['end_address']
            prefix = sr['prefix']
            sr = IPRangeIntItem(start=start, end=end, mask=prefix)

            if ipv4_range.mask_len > prefix:
                raise errors.InvalidArgument(message=_('子网掩码长度必须不得小于要拆分的超网掩码长度。') + f'{sr}')

            if prefix > 32:
                raise errors.InvalidArgument(message=_('子网掩码长度不得大于32。') + f'{sr}')

            if start > end:
                raise errors.InvalidArgument(message=_('子网无效，起始地址不能大于结束地址。') + f'{sr}')

            if pre_range and start - pre_range.end != 1:
                raise errors.InvalidArgument(message=_('相邻子网地址不连续。') + f'{pre_range}；{sr}')

            subnets.append(sr)
            pre_range = sr

        return subnets

    # --- 最小化分拆规划 ---
    @staticmethod
    def mini_split_plan(
            ip_range: IPRangeIntItem, new_prefix: int, prefixlen_diff: int = 3
    ) -> List[IPRangeIntItem]:
        """
        最小化分拆规划

        :param ip_range: 被拆分网段
        :param new_prefix: 新的目标拆分前缀/掩码长度
        :param prefixlen_diff: 距离目标拆分前缀/掩码指定长度以内平拆
        """
        if new_prefix <= ip_range.mask:
            raise errors.Error(message=_('掩码/前缀长度必须大于被拆分网段的掩码/前缀长度'))

        if not (1 <= prefixlen_diff <= 10):
            raise errors.Error(message=_('prefixlen_diff 可选值范围1-10，最多平拆出1024个目标前缀长度的子网'))

        # 被拆分网段合法性检查，是否同一网段，网络号是否一致
        try:
            start_network = ipaddress.IPv4Network((ip_range.start, ip_range.mask), strict=False)
            end_anetwork = ipaddress.IPv4Network((ip_range.end, ip_range.mask), strict=False)
        except ipaddress.NetmaskValueError as exc:
            raise errors.Error(message=_('子网网段掩码无效') + str(exc))
        except ipaddress.AddressValueError as exc:
            raise errors.Error(message=_('子网网段地址无效') + str(exc))

        if start_network != end_anetwork:
            raise errors.Error(message=_("起始地址网络号({start_net})和结束地址网络号({end_net})不一致").format(
                start_net=start_network, end_net=end_anetwork))

        # 最小化拆分
        subnets = IPv4RangeSplitter.split_step_by_step(
            ip_range=ip_range, new_prefix=new_prefix, prefixlen_diff=prefixlen_diff)

        # 最后一步是按目标前缀长度平拆
        subnets = IPv4RangeSplitter.mini_split_target_subnets(
            subnets=subnets, new_prefix=new_prefix, prefixlen_diff=prefixlen_diff)
        return subnets

    @staticmethod
    def split_step_by_step(
            ip_range: IPRangeIntItem, new_prefix: int, prefixlen_diff: int
    ) -> List[IPRangeIntItem]:
        """
        按前缀长度逐步 最小化分拆，返回ip正序子网列表

        :param ip_range: 被拆分网段
        :param new_prefix: 新的目标拆分前缀/掩码长度
        :param prefixlen_diff: 距离目标拆分前缀/掩码指定长度以内平拆
        """
        subnets = [ip_range]    # 最终拆分结果子网列表

        step_start = ip_range.mask + 1
        step_end = new_prefix - prefixlen_diff

        if step_start > step_end:
            return subnets

        # 例如：16 -> [17, 18]; diff = 3 ; split by []
        # 例如：16 -> 19; diff = 3 ; split by [17]
        # 例如：16 -> 24; diff = 3 ; split by [17, 18, 19, 20, 21]
        for next_prefix in range(step_start, step_end + 1):
            # 去除列表 subnets 中的第一个网段，并拆分此网段
            split_range = subnets.pop(0)
            sub_ranges = IPv4RangeSplitter.split_plan_by_mask(
                start_address=split_range.start,
                end_address=split_range.end,
                mask_len=split_range.mask,
                split_mask=next_prefix
            )

            # 子网正序排序，并合并到 子网列表 前面
            sub_ranges.sort(key=lambda x: x.start, reverse=False)
            subnets = sub_ranges + subnets

        return subnets

    @staticmethod
    def mini_split_target_subnets(
            subnets: list[IPRangeIntItem], new_prefix: int, prefixlen_diff: int = 3
    ) -> List[IPRangeIntItem]:
        """
        目标前缀长度的子网拆分
        """
        need_count = 2 ** (prefixlen_diff - 1)  # 需要有目标前缀长度的子网数量，至少达到一半

        # 平拆列表 subnets 中的第一个网段
        split_range = subnets.pop(0)
        sub_ranges = IPv4RangeSplitter.split_plan_by_mask(
            start_address=split_range.start,
            end_address=split_range.end,
            mask_len=split_range.mask,
            split_mask=new_prefix
        )
        if len(sub_ranges) >= need_count or not subnets:
            # 子网正序排序，并合并到 子网列表 前面
            sub_ranges.sort(key=lambda x: x.start, reverse=False)
            return sub_ranges + subnets

        # 第一个子网平拆子网数较少，拆下一个子网
        split_range2 = subnets.pop(0)
        prefix_diff2 = max(prefixlen_diff - 1, 1)   # prefixlen_diff - 1，只需要再平拆出一半的子网
        # 先尝试最小化分拆，再平拆第一个子网
        nets = IPv4RangeSplitter.split_step_by_step(
            ip_range=split_range2, new_prefix=new_prefix, prefixlen_diff=prefix_diff2)
        net1 = nets.pop(0)
        sub2_ranges = IPv4RangeSplitter.split_plan_by_mask(
            start_address=net1.start,
            end_address=net1.end,
            mask_len=net1.mask,
            split_mask=new_prefix
        )
        sub2_ranges += nets

        subnets = sub_ranges + sub2_ranges + subnets
        subnets.sort(key=lambda x: x.start, reverse=False)
        return subnets


class IPv4RangeMerger:
    def __init__(self, ipv4_range_ids: List[str], new_prefix: int):
        self.ipv4_range_ids = ipv4_range_ids
        self.new_prefix = new_prefix
        if not ipv4_range_ids:
            raise errors.ValidationError(message=_('要合并的子网IP地址段id列表不能为空'))

        if not (0 < new_prefix <= 32):
            raise errors.ValidationError(message=_('要合并成的超网IP地址段的掩码长度必须为1-32'))

    def get_ip_ranges(self, select_for_update: bool = False) -> List[IPv4Range]:
        qs = IPv4Range.objects.filter(id__in=self.ipv4_range_ids).order_by('start_address')
        if select_for_update:
            qs = qs.select_for_update()

        return list(qs)

    def do_validate(self, ip_ranges):
        """
        :raises: Error
        """
        exists_id_set = {ir.id for ir in ip_ranges}
        merge_id_set = set(self.ipv4_range_ids)
        notfound_ids = merge_id_set.difference(exists_id_set)
        if len(notfound_ids) > 0:
            raise errors.ValidationError(message=_('以下IP地址段id不存在：') + ','.join(notfound_ids))

        if not ip_ranges:
            raise errors.ValidationError(message=_('至少要指定一个要合并的IP地址段'))

        ip_ranges.sort(key=lambda x: x.start_address, reverse=False)
        ip_ranges = self.merge_validate(ip_ranges=ip_ranges, new_prefix=self.new_prefix)
        return ip_ranges

    @staticmethod
    def merge_validate(ip_ranges: List[IPv4Range], new_prefix: int):
        pre_range = None
        for ir in ip_ranges:
            if ir.status not in [IPv4Range.Status.WAIT.value, IPv4Range.Status.RESERVED.value]:
                raise errors.ValidationError(
                    message=_('合并的地址段的状态必须为"未分配"和“预留”，以下IP地址段不能参与合并：') + str(ir))

            if new_prefix > ir.mask_len:
                raise errors.ValidationError(
                    message=_('地址段的掩码长度小于新的合并掩码长度。') + str(ir))

            if pre_range is not None:
                # asn一致检查
                if ir.asn_id != pre_range.asn_id:
                    raise errors.ValidationError(
                        message=_('以下2个地址段AS编码不一致：') + f'{str(pre_range)}、{str(ir)}')

                # 分配状态 一致检查
                if ir.status != pre_range.status:
                    raise errors.ValidationError(
                        message=_(
                            '所有要合并的子网的分配状态必须一致，以下2个地址段的分配状态不一致：'
                        ) + f'{str(pre_range)}、{str(ir)}')

                # 预留状态时关联机构二级对象一致检查
                if ir.status == IPv4Range.Status.RESERVED.value:
                    if ir.org_virt_obj_id != pre_range.org_virt_obj_id:
                        raise errors.ValidationError(
                            message=_(
                                '所有要合并的子网IP地址段是“预留”状态时，关联的机构二级对象必须一致，以下2个地址段不一致：'
                            ) + f'{str(pre_range)}、{str(ir)}')

                # 相邻的地址段首尾IP地址必须是连续的
                if (ir.start_address - pre_range.end_address) != 1:
                    raise errors.ValidationError(
                        message=_('相邻的地址段首尾IP地址必须是连续的，以下2个地址段不是连续的：'
                                  ) + f'{str(pre_range)}、{str(ir)}')

                # 2个地址段 合并掩码长度的超网 是否一致
                pre_supersut = pre_range.start_address_network.supernet(new_prefix=new_prefix)
                ir_supersut = ir.start_address_network.supernet(new_prefix=new_prefix)
                if pre_supersut != ir_supersut:
                    raise errors.ValidationError(
                        message=_('以下2个地址段不属于同一个超网，无法合并为指定掩码长度的超网：'
                                  ) + f'{pre_supersut}({str(pre_range)})、{ir_supersut}({str(ir)})')

            pre_range = ir

        return ip_ranges

    def do_merge(self, user, fake: bool = False):
        """
        :raises: Error
        """
        if fake:
            ip_ranges = self.get_ip_ranges(select_for_update=False)
            return self._merge(ip_ranges=ip_ranges, fake=True)

        with transaction.atomic():
            ip_ranges = self.get_ip_ranges(select_for_update=True)
            supernet, ip_ranges = self._merge(ip_ranges=ip_ranges, fake=False)

        self.add_merge_record(ipv4_range=supernet, subnets=ip_ranges, user=user)
        return supernet, ip_ranges

    def _merge(self, ip_ranges: List[IPv4Range], fake: bool = False) -> Tuple[IPv4Range, List[IPv4Range]]:
        """
        * 需要在一个事务中执行
        """
        ip_ranges = self.do_validate(ip_ranges=ip_ranges)
        # 就一个合并IP地址段，并且掩码长度没变化，不需要合并
        if len(ip_ranges) == 1:
            subnet1 = ip_ranges[0]
            if subnet1.mask_len == self.new_prefix:
                return subnet1, [subnet1]

        subnet1 = ip_ranges[0]
        start_addr = subnet1.start_address
        end_addr = ip_ranges[-1].end_address
        if subnet1.status == IPv4Range.Status.WAIT.value:
            org_virt_obj_id = None
        else:
            org_virt_obj_id = subnet1.org_virt_obj_id

        nt = dj_timezone.now()
        supernet = IPv4RangeManager.build_ipv4_range(
            name='', start_ip=start_addr, end_ip=end_addr, mask_len=self.new_prefix,
            asn=subnet1.asn, status_code=subnet1.status, org_virt_obj=org_virt_obj_id,
            admin_remark='', remark='', create_time=nt, update_time=nt, assigned_time=None
        )
        supernet.clean(exclude_ids=self.ipv4_range_ids)

        if fake:
            return supernet, ip_ranges

        IPv4Range.objects.filter(id__in=self.ipv4_range_ids).delete()
        supernet.clean()
        supernet.save(force_insert=True)
        return supernet, ip_ranges

    @staticmethod
    def add_merge_record(ipv4_range: IPv4Range, subnets: List[IPv4Range], user):
        try:
            range_items = [
                IPRangeItem(
                    start=str(sn.start_address_obj), end=str(sn.end_address_obj), mask=sn.mask_len
                ) for sn in subnets
            ]

            IPv4RangeRecordManager.create_merge_record(
                user=user, ipv4_range=ipv4_range, remark='', ip_ranges=range_items
            )
        except Exception as exc:
            pass


class IPv4AddressManager:
    MAX_IPV4_ADDRESS_INT = MAX_IPV4_ADDRESS_INT

    @staticmethod
    def validete_ip_int(ip_int: int):
        if not (0 <= ip_int <= MAX_IPV4_ADDRESS_INT):
            raise errors.InvalidArgument(message=_('不是有效的整型数值形式的IP地址'))

    @staticmethod
    def change_ip_remark(ip_int: int, remark: str, admin_remark: str) -> IPv4Address:
        IPv4AddressManager.validete_ip_int(ip_int)
        nt = dj_timezone.now()
        updates = {'update_time': nt, 'creation_time': nt}
        if remark:
            updates['remark'] = remark
        if admin_remark:
            updates['admin_remark'] = admin_remark

        ip_addr, created = IPv4Address.objects.get_or_create(defaults=updates, ip_address=ip_int)
        if created:
            return ip_addr

        update_fields = []
        if remark:
            ip_addr.remark = remark
            update_fields.append('remark')
        if admin_remark:
            ip_addr.admin_remark = admin_remark
            update_fields.append('admin_remark')

        if updates:
            ip_addr.update_time = nt
            update_fields.append('update_time')
            ip_addr.save(update_fields=update_fields)

        return ip_addr

    @staticmethod
    def filter_ip_address_qs(start_ip: int = None, end_ip: int = None, remark: str = None, is_admin: bool = False):
        """
        :param start_ip: 起始地址大小
        :param end_ip: 截止地址大小
        :param remark: 备注关键字查询，为空字符串时查询备注有效的ip
        :param is_admin: 是否是管理员
        """
        lookups = {}
        if start_ip:
            lookups['ip_address__gte'] = start_ip

        if end_ip:
            lookups['ip_address__lte'] = end_ip

        qs = IPv4Address.objects.filter(**lookups).order_by('ip_address')
        if is_admin:
            if remark:
                qs = qs.filter(Q(remark__icontains=remark) | Q(admin_remark__icontains=remark))
            elif remark == '':
                qs = qs.filter(~Q(remark='') | ~Q(admin_remark=''))
        else:
            if remark:
                qs = qs.filter(remark__icontains=remark)
            elif remark == '':
                qs = qs.filter(~Q(remark=''))

        return qs


class IPv4SubnetCollector:
    def __init__(
            self, supernet: IPv4Supernet,
            assigned_ranges: list, assigned_ip_count: int,
            reserved_ranges: list, reserved_ip_count: int,
            wait_ranges: list, wait_ip_count: int,
            subnet_count: int
    ):
        self.supernet = supernet
        self.assigned_ranges = assigned_ranges
        self.assigned_ip_count = assigned_ip_count
        self.reserved_ranges = reserved_ranges
        self.reserved_ip_count = reserved_ip_count
        self.wait_ranges = wait_ranges
        self.wait_ip_count = wait_ip_count
        self.subnet_count = subnet_count

    @classmethod
    def parse(cls, supernet: IPv4Supernet):
        ipv4_ranges = IPv4Range.objects.filter(
            start_address__gte=supernet.start_address, end_address__lte=supernet.end_address
        )
        assigned_ip_count = 0
        assigned_ip_ranges = []
        reserved_ip_count = 0
        reserved_ip_ranges = []
        wait_ip_count = 0
        wait_ip_ranges = []
        for iprange in ipv4_ranges:
            ip_count = iprange.end_address - iprange.start_address + 1
            if iprange.status == IPv4Range.Status.ASSIGNED.value:
                assigned_ip_count += ip_count
                assigned_ip_ranges.append(iprange)
            elif iprange.status == IPv4Range.Status.RESERVED.value:
                reserved_ip_count += ip_count
                reserved_ip_ranges.append(iprange)
            else:
                wait_ip_count += ip_count
                wait_ip_ranges.append(iprange)

        return cls(
            supernet=supernet,
            assigned_ranges=assigned_ip_ranges, assigned_ip_count=assigned_ip_count,
            reserved_ranges=reserved_ip_ranges, reserved_ip_count=reserved_ip_count,
            wait_ranges=wait_ip_ranges, wait_ip_count=wait_ip_count, subnet_count=len(ipv4_ranges)
        )

    @property
    def subnet_ips_num(self) -> int:
        return self.assigned_ip_count + self.reserved_ip_count + self.wait_ip_count

    @property
    def supernet_ips_num(self) -> int:
        return self.supernet.ips_num

    def supernet_status(self):
        subnet_count = self.subnet_count
        if subnet_count <= 0:  # 未入库
            status = IPv4Supernet.Status.OUT_WAREHOUSE.value
        elif subnet_count > 1:  # 已拆分
            status = IPv4Supernet.Status.SPLIT.value
        else:
            if self.subnet_ips_num < self.supernet_ips_num:
                status = IPv4Supernet.Status.SPLIT.value  # 已拆分
            else:
                status = IPv4Supernet.Status.IN_WAREHOUSE.value  # 已入库

        return status


class IPv4SupernetManager:
    @staticmethod
    def get_ip_supernet(_id: str, select_for_update: bool = False) -> IPv4Supernet:
        if select_for_update:
            ipsupernet = IPv4Supernet.objects.select_for_update().filter(id=_id).first()
        else:
            ipsupernet = IPv4Supernet.objects.filter(id=_id).first()

        if ipsupernet is None:
            raise errors.TargetNotExist(message=_('IP地址超网段不存在'))

        return ipsupernet

    @staticmethod
    def get_ip_supernet_by_ip(ip_int: int) -> IPv4Supernet:
        ipsupernet = IPv4Supernet.objects.filter(
            start_address__lte=ip_int, end_address__gte=ip_int).first()
        if ipsupernet is None:
            raise errors.TargetNotExist(message=_('IP地址超网段不存在'))

        return ipsupernet

    @staticmethod
    def get_queryset() -> QuerySet:
        return IPv4Supernet.objects.all()

    def filter_queryset(self, status: Union[str, None], asn: int, ipv4_int: int, search: str):
        """
        各参数为真时过滤
        """
        qs = self.get_queryset()
        lookups = {}

        if status:
            lookups['status'] = status

        if asn:
            lookups['asn'] = asn

        if ipv4_int:
            lookups['start_address__lte'] = ipv4_int
            lookups['end_address__gte'] = ipv4_int

        if lookups:
            qs = qs.filter(**lookups)

        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(remark__icontains=search))

        return qs

    def create_ipv4_supernet(
            self, start_address: int, end_address: int, mask_len: int, asn: int, remark: str,
            operator: str
    ):
        supernet = self.build_ipv4_supernet(
            start_address=start_address, end_address=end_address, mask_len=mask_len, asn=asn,
            remark=remark, operator=operator, status=IPv4Supernet.Status.OUT_WAREHOUSE.value,
            used_ip_count=0
        )
        subnet_collector = IPv4SubnetCollector.parse(supernet=supernet)
        supernet.used_ip_count = subnet_collector.assigned_ip_count
        supernet.status = subnet_collector.supernet_status()
        try:
            supernet.clean()
        except ValidationError as exc:
            raise errors.ValidationError(message=str(exc))

        supernet.save(force_insert=True)
        return supernet

    @staticmethod
    def build_ipv4_supernet(
            start_address: int, end_address: int, mask_len: int, asn: int, remark: str,
            operator: str, used_ip_count: int, status: str, creation_time=None, update_time=None
    ):
        """
        构建超网对象，不保存到数据库
        """
        nt = dj_timezone.now()
        if not creation_time:
            creation_time = nt

        if not update_time:
            update_time = nt

        supernet_ip_num = end_address - start_address + 1
        supernet = IPv4Supernet(
            start_address=start_address, end_address=end_address, mask_len=mask_len, asn=asn,
            remark=remark, operator=operator, creation_time=creation_time, update_time=update_time,
            total_ip_count=supernet_ip_num, used_ip_count=used_ip_count, status=status
        )

        supernet.name = str(supernet.start_address_network)
        return supernet

    def update_ipv4_supernet(
            self, ip_supernet: IPv4Supernet, start_address: Union[str, int], end_address: Union[str, int],
            mask_len: int, asn: int, remark: str, operator: str
    ) -> (IPv4Supernet, List):
        """
        :return: IPv4Supernet, update_fields: list
        :raises: ValidationError
        """
        if isinstance(start_address, int):
            start_int = start_address
        else:
            start_int = ipv4_str_to_int(ipv4=start_address)

        if isinstance(end_address, int):
            end_int = end_address
        else:
            end_int = ipv4_str_to_int(ipv4=end_address)

        mask_len = int(mask_len)
        if not (0 <= mask_len <= 32):
            raise errors.ValidationError(message=_('子网掩码长度无效，取值范围为0-32'))

        update_fields = []
        if start_int != ip_supernet.start_address:
            ip_supernet.start_address = start_int
            update_fields.append('start_address')

        if end_int != ip_supernet.end_address:
            ip_supernet.end_address = end_int
            update_fields.append('end_address')

        if mask_len != ip_supernet.mask_len:
            ip_supernet.mask_len = mask_len
            update_fields.append('mask_len')

        if asn != ip_supernet.asn:
            ip_supernet.asn = asn
            update_fields.append('asn')

        if remark and ip_supernet.remark != remark:
            ip_supernet.remark = remark
            update_fields.append('remark')

        if update_fields:
            ip_supernet.clear_cached_property()  # 字段值变更了，需要清除缓存属性
            new_name = str(ip_supernet.start_address_network)
            if ip_supernet.name != new_name:
                ip_supernet.name = new_name
                update_fields.append('name')

            if ip_supernet.operator != operator:
                ip_supernet.operator = operator
                update_fields.append('operator')

            ip_supernet.update_time = dj_timezone.now()
            update_fields.append('update_time')

            try:
                ip_supernet.clean()
            except ValidationError as exc:
                raise errors.ValidationError(message=exc.messages[0])

            ip_supernet.save(update_fields=update_fields)

        sp, sub_fields = self.update_supernet_status_rate(supernet=ip_supernet)
        update_fields += sub_fields

        return ip_supernet, update_fields

    @staticmethod
    def update_supernet_status_rate(supernet: IPv4Supernet):
        """
        更新超网状态和ip分配率
        """
        update_fields = []
        subnet_collector = IPv4SubnetCollector.parse(supernet=supernet)
        if supernet.used_ip_count != subnet_collector.assigned_ip_count:
            supernet.used_ip_count = subnet_collector.assigned_ip_count
            update_fields.append('used_ip_count')

        new_status = subnet_collector.supernet_status()
        if supernet.status != new_status:
            supernet.status = new_status
            update_fields.append('status')

        if update_fields:
            supernet.save(update_fields=update_fields)

        return supernet, update_fields


class ExternalIPv4RangeManager:
    @staticmethod
    def get_ipv4_range(_id: str) -> ExternalIPv4Range:
        ip_range = ExternalIPv4Range.objects.filter(id=_id).first()
        if ip_range is None:
            raise errors.TargetNotExist(message=_('外部IP地址段不存在'))

        return ip_range

    @staticmethod
    def get_ipv4_range_by_ip(ip_int: int) -> ExternalIPv4Range:
        ip_range = ExternalIPv4Range.objects.filter(
            start_address__lte=ip_int, end_address__gte=ip_int).first()
        if ip_range is None:
            raise errors.TargetNotExist(message=_('外部IP地址段不存在'))

        return ip_range

    @staticmethod
    def get_queryset() -> QuerySet:
        return ExternalIPv4Range.objects.all()

    def filter_queryset(self, asn: int, ipv4_int: int, search: str):
        """
        各参数为真时过滤
        """
        qs = self.get_queryset()
        lookups = {}

        if asn:
            lookups['asn'] = asn

        if ipv4_int:
            lookups['start_address__lte'] = ipv4_int
            lookups['end_address__gte'] = ipv4_int

        if lookups:
            qs = qs.filter(**lookups)

        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(remark__icontains=search) | Q(org_name__icontains=search)
                | Q(country__icontains=search) | Q(city__icontains=search)
            )

        return qs

    def create_external_ipv4_range(
            self, start_address: int, end_address: int, mask_len: int, asn: int, remark: str,
            operator: str, org_name: str, country: str, city: str
    ):
        ip_range = self.build_external_ipv4_range(
            start_address=start_address, end_address=end_address, mask_len=mask_len, asn=asn,
            remark=remark, operator=operator, org_name=org_name, country=country, city=city
        )
        try:
            ip_range.clean()
        except ValidationError as exc:
            raise errors.ValidationError(message=str(exc))

        ip_range.save(force_insert=True)
        return ip_range

    @staticmethod
    def build_external_ipv4_range(
            start_address: int, end_address: int, mask_len: int, asn: int, remark: str,
            operator: str, org_name: str, country: str, city: str, creation_time=None, update_time=None
    ):
        """
        构建超网对象，不保存到数据库
        """
        nt = dj_timezone.now()
        if not creation_time:
            creation_time = nt

        if not update_time:
            update_time = nt

        ip_range = ExternalIPv4Range(
            start_address=start_address, end_address=end_address, mask_len=mask_len, asn=asn,
            remark=remark, operator=operator, creation_time=creation_time, update_time=update_time,
            org_name=org_name, country=country, city=city
        )

        ip_range.name = str(ip_range.start_address_network)
        return ip_range

    @staticmethod
    def update_external_ipv4_range(
            ip_range: ExternalIPv4Range,
            start_address: Union[str, int], end_address: Union[str, int], mask_len: int, asn: int,
            remark: str, operator: str, org_name: str, country: str, city: str
    ) -> Tuple[ExternalIPv4Range, List[str]]:
        """
        :return: IPv4Range, update_fields: list
        :raises: ValidationError
        """
        if isinstance(start_address, int):
            start_int = start_address
        else:
            start_int = ipv4_str_to_int(ipv4=start_address)

        if isinstance(end_address, int):
            end_int = end_address
        else:
            end_int = ipv4_str_to_int(ipv4=end_address)

        mask_len = int(mask_len)
        if not (0 <= mask_len <= 32):
            raise errors.ValidationError(message=_('子网掩码长度无效，取值范围为0-32'))

        update_fields = []
        if start_int != ip_range.start_address:
            ip_range.start_address = start_int
            update_fields.append('start_address')

        if end_int != ip_range.end_address:
            ip_range.end_address = end_int
            update_fields.append('end_address')

        if mask_len != ip_range.mask_len:
            ip_range.mask_len = mask_len
            update_fields.append('mask_len')

        if asn != ip_range.asn:
            ip_range.asn = asn
            update_fields.append('asn')

        if remark and ip_range.remark != remark:
            ip_range.remark = remark
            update_fields.append('remark')

        if operator and ip_range.operator != operator:
            ip_range.operator = operator
            update_fields.append('operator')

        if org_name and ip_range.org_name != org_name:
            ip_range.org_name = org_name
            update_fields.append('org_name')

        if country and ip_range.country != country:
            ip_range.country = country
            update_fields.append('country')

        if city and ip_range.city != city:
            ip_range.city = city
            update_fields.append('city')

        if update_fields:
            ip_range.clear_cached_property()  # 字段值变更了，需要清除缓存属性
            ip_range.name = str(ip_range.start_address_network)
            update_fields.append('name')

            ip_range.update_time = dj_timezone.now()
            update_fields.append('update_time')

            try:
                ip_range.clean()
            except ValidationError as exc:
                raise errors.ValidationError(message=exc.messages[0])

            ip_range.save(update_fields=update_fields)

        return ip_range, update_fields
