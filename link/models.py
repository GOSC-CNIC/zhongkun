from django.db import models
from utils.model import UuidModel
from django.utils.translation import gettext_lazy as _
from core import errors as exceptions
from users.models import UserProfile
from service.models import DataCenter


class LinkUserRole(UuidModel):
    """链路用户角色和权限"""
    user = models.OneToOneField(verbose_name=_('用户'), to=UserProfile, related_name='userprofile_linkuserrole', on_delete=models.CASCADE)
    is_admin = models.BooleanField(verbose_name=_('链路管理员权限'), default=False, help_text=_('用户拥有科技网链路管理功能的管理员权限'))
    is_readonly = models.BooleanField(verbose_name=_('链路只读权限'), default=False, help_text=_('用户拥有科技网链路管理功能的全局只读权限'))
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-create_time',)
        db_table = 'link_user_role'
        verbose_name = _('链路管理用户角色和权限')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.user.username


class LinkOrg(UuidModel):
    """链路机构对象"""

    data_center = models.ForeignKey(
        verbose_name=_('主机构'), to=DataCenter, related_name='datacenter_linkorg',
        on_delete=models.SET_NULL, null=True, default=None)
    name = models.CharField(verbose_name=_('二级机构名'), max_length=64, default='')
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, default='', blank=True)
    location = models.CharField(verbose_name=_('经纬度'), max_length=64, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-create_time',)
        db_table = 'link_org'
        verbose_name = _('机构二级')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class FiberCable(UuidModel):
    """光缆"""

    number = models.CharField(verbose_name=_('光缆编号'), max_length=64, default='')
    fiber_count = models.IntegerField(verbose_name=_('总纤芯数量'))
    length = models.DecimalField(verbose_name=_('长度'), max_digits=10, decimal_places=2, null=True, blank=True, default=None, help_text='km')
    endpoint_1 = models.CharField(verbose_name=_('端点1'), max_length=255, blank=True, default='')
    endpoint_2 = models.CharField(verbose_name=_('端点2'), max_length=255, blank=True, default='')
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-update_time',)
        db_table = 'link_fiber_cable'
        verbose_name = _('光缆')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.number


class DistributionFrame(UuidModel):
    """配线架"""

    number = models.CharField(verbose_name=_('设备号'), max_length=64, default='')
    model_type = models.CharField(verbose_name=_('设备型号'), max_length=36, blank=True, default='')
    row_count = models.IntegerField(verbose_name=_('行数'), default=None)
    col_count = models.IntegerField(verbose_name=_('列数'), default=None)
    place = models.CharField(verbose_name=_('位置'), max_length=128, blank=True, default='')
    link_org = models.ForeignKey(
        verbose_name=_('机构'), to=LinkOrg, related_name='linkorg_distriframe',
        on_delete=models.SET_NULL, null=True, default=None)
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-update_time',)
        db_table = 'link_distribution_frame'
        verbose_name = _('配线架')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.number


class Element(UuidModel):
    """网元汇总表"""

    class Type(models.TextChoices):
        """网元类型"""
        OPTICAL_FIBER = 'optical-fiber', _('光纤')
        LEASE_LINE = 'lease-line', _('租用线路')
        DISTRIFRAME_PORT = 'distributionframe-port', _('配线架端口')
        CONNECTOR_BOX = 'connector-box', _('光缆接头盒')

    object_type = models.CharField(verbose_name=_('网元对象类型'), max_length=32, choices=Type.choices)
    object_id = models.CharField(verbose_name=_('网元对象id'), max_length=36, db_index=True)
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-create_time',)
        db_table = 'link_element'
        verbose_name = _('网元汇总表')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.object_type + ':' + self.object_id


class ElementBase(UuidModel):
    """网元对象基类"""

    element = models.OneToOneField(
        verbose_name=_('网元记录'), to=Element, related_name='element_%(class)s', 
        db_constraint=False, on_delete=models.SET_NULL, null=True, default=None)

    class Meta:
        abstract = True


class LeaseLine(ElementBase):
    """租用线路"""

    class LeaseStatus(models.TextChoices):
        """租线状态"""
        ENABLE = 'enable', _('在网')
        DISABLE = 'disable', _('撤线')

    private_line_number = models.CharField(verbose_name=_('专线号'), max_length=64, blank=True, default='')
    lease_line_code = models.CharField(verbose_name=_('电路代号'), max_length=64, blank=True, default='')
    line_username = models.CharField(verbose_name=_('专线用户'), max_length=36, blank=True, default='')
    endpoint_a = models.CharField(verbose_name=_('A端'), max_length=255, blank=True, default='')
    endpoint_z = models.CharField(verbose_name=_('Z端'), max_length=255, blank=True, default='')
    line_type = models.CharField(verbose_name=_('线路类型'), max_length=36, blank=True, default='')
    cable_type = models.CharField(verbose_name=_('电路类型'), max_length=36, blank=True, default='')
    bandwidth = models.IntegerField(verbose_name=_('带宽'), null=True, blank=True, default=None, help_text='Mbs')
    length = models.DecimalField(verbose_name=_('长度'), max_digits=10, decimal_places=2, null=True, blank=True, default=None, help_text='km')
    provider = models.CharField(verbose_name=_('运营商'), max_length=36, blank=True, default='')
    enable_date = models.DateField(verbose_name=_('开通日期'), null=True, blank=True, default=None)
    is_whithdrawal = models.BooleanField(verbose_name=_('是否撤线'), default=False, help_text=_('0:在网 1:撤线'))
    money =  models.DecimalField(verbose_name=_('月租费'), max_digits=10, decimal_places=2, null=True, blank=True, default=None, help_text='元')
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-update_time',)
        db_table = 'link_lease_line'
        verbose_name = _('租用线路')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.private_line_number


class OpticalFiber(ElementBase):
    """光纤"""

    fiber_cable = models.ForeignKey(
        verbose_name=_('光缆'), to=FiberCable, related_name='fibercable_opticalfiber', db_constraint=False,
        on_delete=models.SET_NULL, null=True, default=None)
    sequence = models.IntegerField(verbose_name=_('纤序'))
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('sequence',)
        db_table = 'link_optical_fiber'
        verbose_name = _('光纤')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.fiber_cable.number + ':' + str(self.sequence)


class DistriFramePort(ElementBase):
    """配线架端口"""

    number = models.CharField(verbose_name=_('端口编号'), max_length=64, default='', help_text=_('自定义编号'))
    row = models.IntegerField(verbose_name=_('行号'), default=None)
    col = models.IntegerField(verbose_name=_('列号'), default=None)
    distribution_frame = models.ForeignKey(
        verbose_name=_('配线架'), to=DistributionFrame, related_name='distriframe_distriframeport', db_constraint=False,
        on_delete=models.SET_NULL, null=True, default=None)
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('row', 'col',)
        db_table = 'link_distriframe_port'
        verbose_name = _('配线架端口')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.number


class ConnectorBox(ElementBase):
    """光缆接头盒"""

    number = models.CharField(verbose_name=_('接头盒编号'), max_length=64, default='', help_text=_('自定义编号'))
    place = models.CharField(verbose_name=_('位置'), max_length=128, blank=True, default='')
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    location = models.CharField(verbose_name=_('经纬度'), max_length=64, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-update_time',)
        db_table = 'link_connector_box'
        verbose_name = _('光缆接头盒')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.number


class Task(UuidModel):
    """业务"""

    class TaskStatus(models.TextChoices):
        """业务状态"""
        NORMAL = 'normal', _('正常')
        DELETED = 'deleted', _('删除')

    number = models.CharField(verbose_name=_('业务编号'), max_length=64, default='')
    user = models.CharField(verbose_name=_('用户（单位）'), max_length=128, blank=True, default='')
    endpoint_a = models.CharField(verbose_name=_('A端'), max_length=255, blank=True, default='')
    endpoint_z = models.CharField(verbose_name=_('Z端'), max_length=255, blank=True, default='')
    bandwidth = models.IntegerField(verbose_name=_('带宽'), null=True, blank=True, default=None, help_text='Mbs')
    task_description = models.CharField(verbose_name=_('业务描述'), max_length=255, blank=True, default='')
    line_type = models.CharField(verbose_name=_('线路类型'), max_length=36, blank=True, default='')
    task_person = models.CharField(verbose_name=_('商务对接'), max_length=36, blank=True, default='')
    build_person = models.CharField(verbose_name=_('线路搭建'), max_length=36, blank=True, default='')
    task_status = models.CharField(verbose_name=_('业务状态'), max_length=16, choices=TaskStatus.choices, default=TaskStatus.NORMAL)
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-update_time',)
        db_table = 'link_task'
        verbose_name = _('业务')
        verbose_name_plural = verbose_name


class ElementLink(UuidModel):
    """链路"""

    class LinkStatus(models.TextChoices):
        """链路状态"""
        USING = 'using', _('使用')
        IDLE = 'idle', _('闲置')
        BACKUP = 'backup', _('备用')
        DELETED = 'deleted', _('删除')

    number = models.CharField(verbose_name=_('链路编号'), max_length=64, default='')
    element_ids = models.TextField(verbose_name=_('网元序列'), blank=True, default='', help_text=_('逗号分隔'))
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    link_status = models.CharField(verbose_name=_('链路状态'), max_length=16, choices=LinkStatus.choices, default=LinkStatus.IDLE)
    task = models.ForeignKey(
        verbose_name=_('业务'), to=Task, related_name='task_elementLink', db_constraint=False,
        on_delete=models.SET_NULL, null=True, blank=True, default=None)
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        ordering = ('-update_time',)
        db_table = 'link_element_link'
        verbose_name = _('链路')
        verbose_name_plural = verbose_name
    
    def element_id_list(self):
        return self.element_ids.split(',')
