import ipaddress
from collections import namedtuple

from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property

from utils.model import UuidModel
from users.models import UserProfile
from service.models import DataCenter


_IPRangeItem = namedtuple('IPRangeItem', ['start', 'end', 'mask'])


class IPRangeItem(_IPRangeItem):
    """
    start: '127.0.0.1'
    end: '127.0.0.255'
    mask: 24
    """
    pass


_IPRangeItem = namedtuple('IPRangeItem', ['start', 'end', 'mask'])


class IPRangeIntItem(_IPRangeItem):
    """
    start: int
    end: int
    mask: 24
    """
    pass


def ipv4_int_to_str(ipv4: int):
    return str(ipaddress.IPv4Address(ipv4))


def ipv4_str_to_int(ipv4: str):
    return int(ipaddress.IPv4Address(ipv4))


def build_ipv4_network(ip_net: str) -> ipaddress.IPv4Network:
    """
    :param ip_net: x.x.x.x/x
    """
    return ipaddress.IPv4Network(ip_net, strict=False)


class IPAMUserRole(UuidModel):
    """ipam用户角色和权限"""
    user = models.OneToOneField(
        verbose_name=_('用户'), to=UserProfile, related_name='+', on_delete=models.CASCADE)
    is_admin = models.BooleanField(
        verbose_name=_('科技网IP管理员'), default=False, help_text=_('选中，用户拥有科技网IP管理功能的管理员权限'))
    is_readonly = models.BooleanField(
        verbose_name=_('IP管理全局只读权限'), default=False, help_text=_('选中，用户拥有科技网IP管理功能的全局只读权限'))
    organizations = models.ManyToManyField(
        verbose_name=_('拥有管理员权限的机构'), to=DataCenter, related_name='+', db_table='ipam_user_role_orgs', blank=True)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'ipam_user_role'
        verbose_name = _('IP管理用户角色和权限')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.user.username


class OrgVirtualObject(UuidModel):
    name = models.CharField(verbose_name=_('名称'), max_length=255)
    organization = models.ForeignKey(
        verbose_name=_('机构'), to=DataCenter, related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True, default=None)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    remark = models.CharField(verbose_name=_('备注信息'), max_length=255, blank=True, default='')

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'ipam_org_virt_obj'
        verbose_name = _('机构二级')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ASN(models.Model):
    id = models.AutoField(verbose_name=_('ID'), primary_key=True)
    number = models.PositiveIntegerField(verbose_name=_('AS编码'))
    name = models.CharField(verbose_name=_('名称'), max_length=255, blank=True, default='')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))

    class Meta:
        ordering = ('number',)
        db_table = 'ipam_asn'
        verbose_name = _('AS编号')
        verbose_name_plural = verbose_name

    def __str__(self):
        return str(self.number)


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


class IPv4Range(IPRangeBase):
    """
    注意：删除时会一起删除关联的 ip address，删除前需要先更新 ip address 关联的ip range
    """
    start_address = models.PositiveIntegerField(verbose_name=_('起始地址'))
    end_address = models.PositiveIntegerField(verbose_name=_('截止地址'))
    mask_len = models.PositiveIntegerField(
        verbose_name=_('子网掩码长度'), validators=(MaxValueValidator(32),))

    class Meta:
        ordering = ('start_address',)
        db_table = 'ipam_ipv4_range'
        verbose_name = _('IPv4地址段')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.ip_range_display()

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

            overlapping_range = IPv4Range.objects.exclude(**exclude_lookup).filter(
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


class IPAddressBase(UuidModel):
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))
    admin_remark = models.CharField(verbose_name=_('科技网管理员备注信息'), max_length=255, blank=True, default='')
    remark = models.CharField(verbose_name=_('机构管理员备注信息'), max_length=255, blank=True, default='')

    class Meta:
        abstract = True


class IPv4Address(IPAddressBase):
    ip_address = models.PositiveIntegerField(verbose_name=_('IP地址'))
    ip_range = models.ForeignKey(verbose_name=_('IP段'), to=IPv4Range, on_delete=models.CASCADE, related_name='+')

    class Meta:
        ordering = ('ip_address',)
        db_table = 'ipam_ipv4_addr'
        verbose_name = _('IPv4地址')
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=('ip_address',), name='unique_ip_address')
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

    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    record_type = models.CharField(verbose_name=_('记录类型'), max_length=16, choices=RecordType.choices)
    ip_ranges = models.JSONField(verbose_name=_('拆分或合并的IP段'), blank=True, default=dict)
    remark = models.CharField(verbose_name=_('备注信息'), max_length=255, blank=True, default='')
    user = models.ForeignKey(
        verbose_name=_('操作用户'), to=UserProfile, related_name='+', null=True, on_delete=models.SET_NULL)
    org_virt_obj = models.ForeignKey(
        verbose_name=_('分配给机构虚拟对象'), to=OrgVirtualObject, related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True, default=None)

    class Meta:
        abstract = True

    def set_ip_ranges(self, ip_ranges: list[IPRangeItem]):
        """
        :ip_ranges: [{
            'start': '127.0.0.1',
            'end': '127.0.0.255',
            'mask': 24
        }]
        """
        self.ip_ranges = [i._asdict() for i in ip_ranges]


class IPv4RangeRecord(IPRangeRecordBase):
    start_address = models.PositiveIntegerField(verbose_name=_('起始地址'))
    end_address = models.PositiveIntegerField(verbose_name=_('截止地址'))
    mask_len = models.PositiveIntegerField(
        verbose_name=_('子网掩码长度'), validators=(MaxValueValidator(32),))

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'ipam_ipv4_range_record'
        verbose_name = 'IPv4段操作记录'
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
