from typing import Union
from datetime import datetime

from django.db.models import Q, QuerySet
from django.utils.translation import gettext as _
from django.utils import timezone as dj_timezone
from django.core.exceptions import ValidationError

from core import errors
from .models import (
    IPv6Range, ASN, OrgVirtualObject, ipv6_str_to_bytes
)
from .managers import UserIpamRoleWrapper, get_or_create_asn


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
                q = q | Q(admin_remark__icontains=search)

            qs = qs.filter(q)

        return qs

    def get_user_queryset(self, org_id: str, asn: int, ip_bytes: bytes, search: str, user_role: UserIpamRoleWrapper):
        org_ids = user_role.get_user_org_ids()
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
