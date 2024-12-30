import ipaddress

from django.db import models
from django.utils.translation import gettext, gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone as dj_timezone

from core import errors
from utils.model import UuidModel
from utils.iprestrict import convert_iprange
from apps.app_users.models import UserProfile
from apps.app_service.models import DataCenter


class ContactPerson(UuidModel):
    """机构二级联系人"""
    name = models.CharField(verbose_name=_('姓名'), max_length=128)
    telephone = models.CharField(verbose_name=_('电话'), max_length=16, default='')
    email = models.EmailField(_('邮箱地址'), blank=True, default='')
    address = models.CharField(verbose_name=_('联系地址'), max_length=255, blank=True, default='',
                               help_text=_('详细的联系地址'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), blank=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), blank=True)
    remarks = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'net_manage_contact_person'
        verbose_name = _('03_机构二级对象联系人')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'[ {self.name} ] Phone: {self.telephone}, Email: {self.email}, Address: {self.address}'

    def clean(self):
        qs = ContactPerson.objects.filter(name=self.name, telephone=self.telephone)
        if self.id:
            qs = qs.exclude(id=self.id)
        if qs.exists():
            msg = gettext('已存在姓名和手机号都相同的联系人')
            exc = ValidationError(message={'name': msg})
            exc.error = errors.TargetAlreadyExists(message=msg)
            raise exc

        if not self.creation_time:
            self.creation_time = dj_timezone.now()

        if not self.update_time:
            self.update_time = self.creation_time


class OrgVirtualObject(UuidModel):
    name = models.CharField(verbose_name=_('名称'), max_length=255)
    organization = models.ForeignKey(
        verbose_name=_('机构'), to=DataCenter, related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True, default=None)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    remark = models.CharField(verbose_name=_('备注信息'), max_length=255, blank=True, default='')
    contacts = models.ManyToManyField(
        verbose_name=_('机构二级对象联系人'), to=ContactPerson, related_name='+', db_table='net_manage_org_obj_contacts',
        db_constraint=False, blank=True
    )

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'net_manage_org_virt_obj'
        verbose_name = _('02_机构二级')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def clean(self):
        qs = OrgVirtualObject.objects.filter(organization_id=self.organization_id, name=self.name)
        if self.id:
            qs = qs.exclude(id=self.id)
        if qs.exists():
            raise ValidationError(message=gettext('同名的机构二级对象已存在'), code=errors.TargetAlreadyExists().code)

        if self.creation_time is None:
            self.creation_time = dj_timezone.now()


class NetManageUserRole(UuidModel):
    """用户角色和权限"""
    class Role(models.TextChoices):
        ORDINARY = 'ordinary', _('普通用户')
        ADMIN = 'admin', _('网管管理员')

    user = models.OneToOneField(
        verbose_name=_('用户'), to=UserProfile, related_name='+', on_delete=models.CASCADE)
    role = models.CharField(verbose_name=_('网管管理角色'), max_length=16, choices=Role.choices)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'net_manage_user_role'
        verbose_name = _('01_综合网管用户角色和权限')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.user.username


class NetIPAccessWhiteList(models.Model):
    id = models.BigAutoField(primary_key=True)
    ip_value = models.CharField(
        verbose_name=_('IP'), max_length=100, help_text='192.168.1.1、 192.168.1.1/24、192.168.1.66 - 192.168.1.100')
    remark = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'net_ipaccesswhitelist'
        ordering = ['-creation_time']
        verbose_name = _('网络管理IP访问白名单')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.id}({self.ip_value})'

    def clean(self):
        try:
            subnet = convert_iprange(self.ip_value)
        except Exception as exc:
            raise ValidationError({'ip_value': str(exc)})

        if isinstance(subnet, ipaddress.IPv4Network):
            self.ip_value = str(subnet)

        obj = NetIPAccessWhiteList.objects.exclude(id=self.id).filter(ip_value=self.ip_value).first()
        if obj:
            raise ValidationError({
                'ip_value': _('已存在相同的IP白名单({value})').format(value=self.ip_value)
            })
