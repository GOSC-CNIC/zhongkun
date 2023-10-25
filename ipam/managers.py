from typing import Union
from datetime import datetime

from django.db.models import Q, QuerySet
from django.utils import timezone as dj_timezone
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError

from core import errors
from .models import IPv4Range, IPAMUserRole, OrgVirtualObject, ASN, ipv4_str_to_int


class UserIpamRoleWrapper:
    def __init__(self, user):
        self.user = user
        self._user_role = None  # ipam user role instance
        self._org_ids = None    # 用户是机构管理员的所有机构id list

    @property
    def user_role(self):
        if not self._user_role:
            self._user_role = self.get_user_ipam_role(user=self.user)

        return self._user_role

    @staticmethod
    def get_user_ipam_role(user):
        urole = IPAMUserRole.objects.select_related('user').filter(user_id=user.id).first()
        if urole:
            return urole

        nt = dj_timezone.now()
        urole = IPAMUserRole(
            user=user, is_admin=False, is_readonly=False,
            creation_time=nt, update_time=nt
        )
        urole.save(force_insert=True)
        return urole

    def has_kjw_admin_readable(self) -> bool:
        """是否有科技网管理员读权限"""
        role = self.user_role
        if role.is_admin:
            return True

        if role.is_readonly:
            return True

        return False

    def has_kjw_admin_writable(self) -> bool:
        """是否有科技网管理员写权限"""
        role = self.user_role
        if role.is_admin:
            return True

        return False

    def is_admin_of_org(self, org_id: str) -> bool:
        """
        是否是指定机构的机构管理员
        """
        return self.user_role.organizations.filter(id=org_id).exists()

    def get_user_org_ids(self, refresh: bool = False):
        """
        用户是机构管理员权限的所有机构id
        """
        if self._org_ids is None or refresh:
            self._org_ids = self.user_role.organizations.values_list('id', flat=True)

        return self._org_ids


class IPv4RangeManager:
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
                q = q | Q(admin_remark__icontains=search)

            qs = qs.filter(q)

        return qs

    def get_user_queryset(self, org_id: str, asn: int, ipv4_int: int, search: str, user_role: UserIpamRoleWrapper):
        org_ids = user_role.get_user_org_ids()
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
            create_time: datetime, update_time: datetime, asn: ASN, status_code: str,
            org_virt_obj: Union[OrgVirtualObject, None], admin_remark: str, remark: str, assigned_time=None
    ):
        """
        :return: IPv4Range
        :raises: ValidationError
        """
        start_int = ipv4_str_to_int(ipv4=start_ip)
        end_int = ipv4_str_to_int(ipv4=end_ip)
        mask_len = int(mask_len)

        if not (0 <= mask_len <= 32):
            raise errors.ValidationError(message=_('子网掩码长度无效，取值范围为0-32'))

        if status_code not in IPv4Range.Status.values:
            raise errors.ValidationError(message=_('IP地址段的状态值无效'))

        ip_range = IPv4Range(
            name=name,
            status=status_code,
            creation_time=create_time,
            update_time=update_time,
            assigned_time=assigned_time,
            asn=asn, org_virt_obj=org_virt_obj,
            start_address=start_int,
            end_address=end_int,
            mask_len=mask_len,
            admin_remark=admin_remark,
            remark=remark
        )
        if not ip_range.name:
            ip_range.name = str(ip_range.start_address_network())

        try:
            ip_range.clean()
        except ValidationError as exc:
            raise errors.ValidationError(message=str(exc))

        ip_range.save(force_insert=True)
        return ip_range
