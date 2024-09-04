import ipaddress
from collections import namedtuple

from django.db import models
from django.db.models import Q, Max
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property

from utils.model import UuidModel
from apps.users.models import UserProfile
from apps.service.models import DataCenter as Organization
from apps.app_net_manage.models import OrgVirtualObject
from apps.app_net_ipam.fields import ByteField


_IPRangeItem = namedtuple('IPRangeItem', ['start', 'end', 'mask'])


class IPRangeItem(_IPRangeItem):
    """
    start: '127.0.0.1'
    end: '127.0.0.255'
    mask: 24
    """
    def __str__(self):
        return f'{self.start}-{self.end} /{self.mask}'


_IPRangeItem = namedtuple('IPRangeItem', ['start', 'end', 'mask'])


class IPRangeIntItem(_IPRangeItem):
    """
    start: int
    end: int
    mask: 24
    """
    def __str__(self):
        return f'{self.start}-{self.end} /{self.mask}'


_IPv6RangeItem = namedtuple('IPv6RangeItem', ['start', 'end', 'prefix'])


class IPv6RangeStrItem(_IPv6RangeItem):
    """
    start: str
    end: str
    prefix: int
    """
    def __str__(self):
        return f'{self.start}-{self.end} /{self.prefix}'

    @cached_property
    def start_address_obj(self):
        return ipaddress.IPv6Address(self.start)

    @cached_property
    def end_address_obj(self):
        return ipaddress.IPv6Address(self.end)

    @property
    def start_bytes(self):
        return self.start_address_obj.packed

    @property
    def end_bytes(self):
        return self.end_address_obj.packed

    @property
    def start_int(self):
        return int(self.start_address_obj)

    @property
    def end_int(self):
        return int(self.end_address_obj)


class IPv6RangeBytesItem(_IPv6RangeItem):
    """
    start: bytes
    end: bytes
    prefix: int
    """
    pass


def ipv4_int_to_str(ipv4: int):
    return str(ipaddress.IPv4Address(ipv4))


def ipv4_str_to_int(ipv4: str):
    return int(ipaddress.IPv4Address(ipv4))


def ipv6_str_to_bytes(ipv6: str):
    return ipaddress.IPv6Address(ipv6).packed


def build_ipv4_network(ip_net: str) -> ipaddress.IPv4Network:
    """
    :param ip_net: x.x.x.x/x
    """
    return ipaddress.IPv4Network(ip_net, strict=False)


def build_ipv6_network(ip_net: str) -> ipaddress.IPv6Network:
    """
    :param ip_net: x:x:x:x::x/x
    """
    return ipaddress.IPv6Network(ip_net, strict=False)


class NetIPamUserRole(UuidModel):
    """用户角色和权限"""
    user = models.OneToOneField(
        verbose_name=_('用户'), to=UserProfile, related_name='+', on_delete=models.CASCADE)
    is_ipam_admin = models.BooleanField(
        verbose_name=_('IP管理员'), default=False, help_text=_('选中，用户拥有IP管理功能的管理员权限'))
    is_ipam_readonly = models.BooleanField(
        verbose_name=_('IP管理全局只读权限'), default=False, help_text=_('选中，用户拥有科技网IP管理功能的全局只读权限'))
    organizations = models.ManyToManyField(
        verbose_name=_('拥有IP管理员权限的机构'), to=Organization, related_name='+',
        db_table='net_ipam_user_role_orgs', blank=True)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'net_ipam_user_role'
        verbose_name = _('01_网络管理用户角色和权限')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.user.username


class ASN(models.Model):
    id = models.AutoField(verbose_name=_('ID'), primary_key=True)
    number = models.PositiveIntegerField(verbose_name=_('AS编码'))
    name = models.CharField(verbose_name=_('名称'), max_length=255, blank=True, default='')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))

    class Meta:
        ordering = ('number',)
        db_table = 'net_ipam_asn'
        verbose_name = _('AS编号')
        verbose_name_plural = verbose_name

    def __str__(self):
        return str(self.number)

    @classmethod
    def get_max_id(cls) -> int:
        r = cls.objects.aggregate(max_id=Max('id'))
        return r['max_id'] or 0


class IPRangeBase(UuidModel):
    """IP段基类"""

    class Status(models.TextChoices):
        ASSIGNED = 'assigned', _('已分配')
        RESERVED = 'reserved', _('预留')
        WAIT = 'wait', _('未分配')

    name = models.CharField(verbose_name=_('名称'), max_length=255, blank=True, default='')
    status = models.CharField(verbose_name=_('状态'), max_length=16, choices=Status.choices, default=Status.WAIT.value)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))
    assigned_time = models.DateTimeField(verbose_name=_('分配时间'), null=True, blank=True, default=None)
    asn = models.ForeignKey(to=ASN, verbose_name=_('AS编号'), on_delete=models.CASCADE, related_name='+')
    admin_remark = models.CharField(verbose_name=_('科技网管理员备注信息'), max_length=255, blank=True, default='')
    remark = models.CharField(verbose_name=_('机构管理员备注信息'), max_length=255, blank=True, default='')
    org_virt_obj = models.ForeignKey(
        verbose_name=_('分配给机构二级'), to=OrgVirtualObject, related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True, default=None)

    class Meta:
        abstract = True


class IPv4RangeBase(models.Model):
    """
    ipv4 range抽象基类
    """
    start_address = models.PositiveIntegerField(verbose_name=_('起始地址'))
    end_address = models.PositiveIntegerField(verbose_name=_('截止地址'))
    mask_len = models.PositiveIntegerField(
        verbose_name=_('子网掩码长度'), validators=(MaxValueValidator(32),))

    class Meta:
        abstract = True

    def __str__(self):
        return self.ip_range_display()

    @property
    def num_addresses(self) -> int:
        return self.end_address - self.start_address + 1

    @staticmethod
    def convert_to_ip_obj(val: int):
        return ipaddress.IPv4Address(val)

    def clear_cached_property(self):
        """
        当cached_property有关的字段信息变更后，需要清除属性旧的缓存
        """
        if hasattr(self, 'start_address_obj'):
            delattr(self, 'start_address_obj')
        if hasattr(self, 'end_address_obj'):
            delattr(self, 'end_address_obj')
        if hasattr(self, 'start_address_network'):
            delattr(self, 'start_address_network')
        if hasattr(self, 'end_address_network'):
            delattr(self, 'end_address_network')

    @cached_property
    def start_address_obj(self):
        return self.convert_to_ip_obj(self.start_address)

    @cached_property
    def end_address_obj(self):
        return self.convert_to_ip_obj(self.end_address)

    def ip_range_display(self):
        try:
            return f'{self.start_address_obj} - {self.end_address_obj} /{self.mask_len}'
        except Exception as exc:
            return f'{self.start_address} - {self.end_address} /{self.mask_len}'

    @cached_property
    def start_address_network(self):
        ip_net = f'{self.start_address_obj}/{self.mask_len}'
        return build_ipv4_network(ip_net=ip_net)

    @cached_property
    def end_address_network(self):
        ip_net = f'{self.end_address_obj}/{self.mask_len}'
        return build_ipv4_network(ip_net=ip_net)

    def clean_check(self, range_id: str, exclude_ids: list = None):
        if self.start_address < 0:
            raise ValidationError({
                'start_address': _(
                    "起始地址({start_address})无效"
                ).format(start_address=self.start_address_obj)
            })

        if self.end_address < 0:
            raise ValidationError({
                'end_address': _(
                    "结束地址({start_address})无效"
                ).format(start_address=self.start_address_obj)
            })

        # Check that the ending address is greater than the starting address
        if not self.end_address >= self.start_address:
            raise ValidationError({
                'end_address': _(
                    "结束地址必须大于等于起始地址({start_address})"
                ).format(start_address=self.start_address_obj)
            })

        # 是否同一网段，网络号是否一致
        try:
            start_net_addr = self.start_address_network
            end_net_addr = self.end_address_network
        except ipaddress.NetmaskValueError as exc:
            raise ValidationError({'mask_len': str(exc)})

        if start_net_addr != end_net_addr:
            raise ValidationError(_(
                    "起始地址网络号({start_net_addr})和结束地址网络号({end_net_addr})不一致"
                ).format(start_net_addr=start_net_addr, end_net_addr=end_net_addr)
            )

        # 检查部分重叠的ranges
        ids = [range_id] if range_id else []
        if exclude_ids and range_id not in exclude_ids:
            ids += exclude_ids

        if len(ids) == 0:
            exclude_lookup = {}
        elif len(ids) == 1:
            exclude_lookup = {'id': ids[0]}
        else:
            exclude_lookup = {'id__in': ids}

        overlapping_range = type(self).objects.exclude(**exclude_lookup).filter(
            Q(start_address__gte=self.start_address, start_address__lte=self.end_address) |  # 已存在start在新ip段内部
            Q(end_address__gte=self.start_address, end_address__lte=self.end_address) |  # 已存在end在新ip段内部
            Q(start_address__lte=self.start_address, end_address__gte=self.end_address)  # start和end在新ip段外部
        ).first()
        if overlapping_range:
            raise ValidationError(
                _("定义的IP地址段({value})与已存在地址段({overlapping_range})范围重叠").format(
                    value=self, overlapping_range=overlapping_range
                ))

        # Validate maximum size
        max_size = 2 ** 32 - 1
        if int(self.end_address - self.start_address) + 1 > max_size:
            raise ValidationError(
                _("定义的IP地址段范围超过支持的最大大小({max_size})").format(max_size=max_size)
            )


class IPv4Range(IPRangeBase, IPv4RangeBase):
    class Meta:
        ordering = ('start_address',)
        db_table = 'net_ipam_ipv4_range'
        verbose_name = _('IPv4地址段')
        verbose_name_plural = verbose_name

    def clean(self, exclude_ids: list = None):
        super(IPv4Range, self).clean()
        self.clean_check(range_id=self.id, exclude_ids=exclude_ids)


class IPAddressBase(UuidModel):
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))
    admin_remark = models.CharField(verbose_name=_('网络管理员备注信息'), max_length=255, blank=True, default='')
    remark = models.CharField(verbose_name=_('机构管理员备注信息'), max_length=255, blank=True, default='')

    class Meta:
        abstract = True


class IPv4Address(IPAddressBase):
    ip_address = models.PositiveIntegerField(verbose_name=_('IP地址'))

    class Meta:
        ordering = ('ip_address',)
        db_table = 'net_ipam_ipv4_addr'
        verbose_name = _('IPv4地址')
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=('ip_address',), name='net_ipam_uniq_ipv4_addr')
        ]

    def __str__(self):
        return self.ip_address_str()

    @property
    def ip_address_obj(self):
        return ipaddress.IPv4Address(self.ip_address)

    def ip_address_str(self):
        try:
            return self.ip_address_obj.__str__()
        except Exception as exc:
            return f'{self.ip_address}'


class IPRangeRecordBase(UuidModel):
    class RecordType(models.TextChoices):
        ASSIGN = 'assign', _('分配')
        RECOVER = 'recover', _('收回')
        SPLIT = 'split', _('拆分')
        MERGE = 'merge', _('合并')
        ADD = 'add', _('添加')
        CHANGE = 'change', _('修改')
        DELETE = 'delete', _('删除')
        RESERVE = 'reserve', _('预留')

    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    record_type = models.CharField(verbose_name=_('记录类型'), max_length=16, choices=RecordType.choices)
    ip_ranges = models.JSONField(verbose_name=_('拆分或合并的IP段'), blank=True, default=dict)
    remark = models.CharField(verbose_name=_('备注信息'), max_length=255, blank=True, default='')
    user = models.ForeignKey(
        verbose_name=_('操作用户'), to=UserProfile, related_name='+', null=True, on_delete=models.SET_NULL)
    org_virt_obj = models.ForeignKey(
        verbose_name=_('分配给机构二级对象'), to=OrgVirtualObject, related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True, default=None)

    class Meta:
        abstract = True


class IPv4RangeRecord(IPRangeRecordBase):
    start_address = models.PositiveIntegerField(verbose_name=_('起始地址'))
    end_address = models.PositiveIntegerField(verbose_name=_('截止地址'))
    mask_len = models.PositiveIntegerField(
        verbose_name=_('子网掩码长度'), validators=(MaxValueValidator(32),))

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'net_ipam_ipv4_range_record'
        verbose_name = _('IPv4段操作记录')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.build_record_display()

    @staticmethod
    def convert_to_ip_obj(val: int):
        return ipaddress.IPv4Address(val)

    @property
    def start_address_obj(self):
        return self.convert_to_ip_obj(self.start_address)

    @property
    def end_address_obj(self):
        return self.convert_to_ip_obj(self.end_address)

    def ip_range_display(self):
        try:
            return f'{self.start_address_obj} - {self.end_address_obj} /{self.mask_len}'
        except Exception as exc:
            return f'{self.start_address} - {self.end_address} /{self.mask_len}'

    def build_record_display(self):
        ip_range_str = self.ip_range_display()
        # r_type = self.RecordType[self.record_type]
        return f"{self.record_type} {ip_range_str}"

    def set_ip_ranges(self, ip_ranges: list[IPRangeItem]):
        """
        :ip_ranges: [{
            'start': '127.0.0.1',
            'end': '127.0.0.255',
            'mask': 24
        }]
        """
        self.ip_ranges = [i._asdict() for i in ip_ranges]


class IPSupernetBase(UuidModel):
    """IP地址超网段基类"""

    class Status(models.TextChoices):
        OUT_WAREHOUSE = 'out-warehouse', _('未入库')
        IN_WAREHOUSE = 'in-warehouse', _('已入库')
        SPLIT = 'split', _('已拆分')

    name = models.CharField(verbose_name=_('名称'), max_length=255, blank=True, default='')
    status = models.CharField(
        verbose_name=_('状态'), max_length=16, choices=Status.choices, default=Status.OUT_WAREHOUSE.value)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))
    asn = models.PositiveIntegerField(verbose_name=_('AS编码'), default=0)
    remark = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    operator = models.CharField(verbose_name=_('操作人'), max_length=128, blank=True, default='')

    class Meta:
        abstract = True


class IPv4Supernet(IPSupernetBase, IPv4RangeBase):
    """
    ipv4地址超网
    """
    used_ip_count = models.PositiveIntegerField(verbose_name=_('已分配IP数'), blank=True, default=0)
    total_ip_count = models.PositiveIntegerField(verbose_name=_('IP总数'), blank=True)

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'net_ipam_ipv4_supernet'
        verbose_name = _('IPv4地址超网段')
        verbose_name_plural = verbose_name

    def clean(self):
        super(IPv4Supernet, self).clean()
        self.clean_check(range_id=self.id)


class IPv6Range(IPRangeBase):
    """
    注意：删除时会一起删除关联的 ip address，删除前需要先更新 ip address 关联的ip range
    """
    start_address = ByteField(verbose_name=_('起始地址'), max_length=16)
    end_address = ByteField(verbose_name=_('截止地址'), max_length=16)
    prefixlen = models.PositiveIntegerField(
        verbose_name=_('前缀长度'), validators=(MaxValueValidator(128),))

    class Meta:
        ordering = ('start_address',)
        db_table = 'net_ipam_ipv6_range'
        verbose_name = _('IPv6地址段')
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['start_address'], name='net_ipam_idx_ipv6rg_start_addr'),
            models.Index(fields=['end_address'], name='net_ipam_idx_ipv6rg_end_addr')
        ]

    def __str__(self):
        return self.ip_range_display()

    @staticmethod
    def convert_to_ip_obj(val: bytes):
        return ipaddress.IPv6Address(val)

    def clear_cached_property(self):
        """
        当cached_property有关的字段信息变更后，需要清除属性旧的缓存
        """
        if hasattr(self, 'start_address_obj'):
            delattr(self, 'start_address_obj')
        if hasattr(self, 'end_address_obj'):
            delattr(self, 'end_address_obj')
        if hasattr(self, 'start_address_network'):
            delattr(self, 'start_address_network')
        if hasattr(self, 'end_address_network'):
            delattr(self, 'end_address_network')

    @cached_property
    def start_address_obj(self):
        return self.convert_to_ip_obj(self.start_address)

    @cached_property
    def end_address_obj(self):
        return self.convert_to_ip_obj(self.end_address)

    def ip_range_display(self):
        try:
            return f'{self.start_address_obj} - {self.end_address_obj} /{self.prefixlen}'
        except Exception as exc:
            return f'{self.start_address.hex(":", 2)} - {self.end_address.hex(":", 2)} /{self.prefixlen}'

    @cached_property
    def start_address_network(self):
        ip_net = f'{self.start_address_obj}/{self.prefixlen}'
        return build_ipv6_network(ip_net=ip_net)

    @cached_property
    def end_address_network(self):
        ip_net = f'{self.end_address_obj}/{self.prefixlen}'
        return build_ipv6_network(ip_net=ip_net)

    def clean(self, exclude_ids: list = None):
        super().clean()

        if self.start_address and self.end_address:
            # Check that the ending address is greater than the starting address
            if not self.end_address >= self.start_address:
                raise ValidationError({
                    'end_address': _(
                        "结束地址必须大于等于起始地址({start_address})"
                    ).format(start_address=self.start_address_obj)
                })

            # 是否同一网段，网络号是否一致
            try:
                start_net_addr = self.start_address_network
                end_net_addr = self.end_address_network
            except ipaddress.NetmaskValueError as exc:
                raise ValidationError({'mask_len': str(exc)})

            if start_net_addr != end_net_addr:
                raise ValidationError(_(
                    "起始地址网络号({start_net_addr})和结束地址网络号({end_net_addr})不一致"
                ).format(start_net_addr=start_net_addr, end_net_addr=end_net_addr)
                                      )

            # 检查部分重叠的ranges
            ids = [self.id] if self.id else []
            if exclude_ids and self.id not in exclude_ids:
                ids = ids + exclude_ids

            if len(ids) == 0:
                exclude_lookup = {}
            elif len(ids) == 1:
                exclude_lookup = {'id': ids[0]}
            else:
                exclude_lookup = {'id__in': ids}

            overlapping_range = IPv6Range.objects.exclude(**exclude_lookup).filter(
                Q(start_address__gte=self.start_address, start_address__lte=self.end_address) |  # 已存在start在新ip段内部
                Q(end_address__gte=self.start_address, end_address__lte=self.end_address) |  # 已存在end在新ip段内部
                Q(start_address__lte=self.start_address, end_address__gte=self.end_address)  # start和end在新ip段外部
            ).first()
            if overlapping_range:
                raise ValidationError(
                    _("定义的IP地址段({value})与已存在地址段({overlapping_range})范围重叠").format(
                        value=self, overlapping_range=overlapping_range
                    ))

    @property
    def start_address_int(self):
        return int(self.start_address_obj)

    @property
    def end_address_int(self):
        return int(self.end_address_obj)


class IPv6Address(IPAddressBase):
    ip_address = ByteField(verbose_name=_('IP地址'), max_length=16)

    class Meta:
        ordering = ('ip_address',)
        db_table = 'net_ipam_ipv6_addr'
        verbose_name = _('IPv6地址')
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=('ip_address',), name='net_ipam_uniq_ipv6_addr')
        ]

    def __str__(self):
        return self.ip_address_str()

    @property
    def ip_address_obj(self):
        return ipaddress.IPv6Address(self.ip_address)

    def ip_address_str(self):
        try:
            return self.ip_address_obj.__str__()
        except Exception as exc:
            return f'{self.ip_address}'


class IPv6RangeRecord(IPRangeRecordBase):
    start_address = ByteField(verbose_name=_('起始地址'), max_length=16)
    end_address = ByteField(verbose_name=_('截止地址'), max_length=16)
    prefixlen = models.PositiveIntegerField(
        verbose_name=_('前缀长度'), validators=(MaxValueValidator(128),))

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'net_ipam_ipv6_range_record'
        verbose_name = _('IPv6段操作记录')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.build_record_display()

    @staticmethod
    def convert_to_ip_obj(val: int):
        return ipaddress.IPv6Address(val)

    @property
    def start_address_obj(self):
        return self.convert_to_ip_obj(self.start_address)

    @property
    def end_address_obj(self):
        return self.convert_to_ip_obj(self.end_address)

    def ip_range_display(self):
        try:
            return f'{self.start_address_obj} - {self.end_address_obj} /{self.prefixlen}'
        except Exception as exc:
            return f'{self.start_address.hex(":", 2)} - {self.end_address.hex(":", 2)} /{self.prefixlen}'

    def build_record_display(self):
        ip_range_str = self.ip_range_display()
        # r_type = self.RecordType[self.record_type]
        return f"{self.record_type} {ip_range_str}"

    def set_ip_ranges(self, ip_ranges: list[IPv6RangeStrItem]):
        """
        :ip_ranges: [{
            'start': '2400:dd01:1010:30::',
            'end': '2400:dd01:1010:30:ffff:ffff:ffff:ffff',
            'prefix': 64
        }]
        """
        self.ip_ranges = [i._asdict() for i in ip_ranges]
