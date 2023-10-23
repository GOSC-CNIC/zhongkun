from django.db import models
from utils.model import UuidModel
from django.utils.translation import gettext_lazy as _
from core import errors as exceptions
from users.models import UserProfile
from service.models import DataCenter

class LinkUserRole(UuidModel):
    """链路用户角色和权限"""
    user = models.OneToOneField(
        verbose_name=_('用户'), to=UserProfile, related_name='userprofile_linkuserrole', on_delete=models.CASCADE)
    is_admin = models.BooleanField(
        verbose_name=_('科技网IP管理员'), default=False, help_text=_('用户拥有科技网链路管理功能的管理员权限'))
    is_readonly = models.BooleanField(
        verbose_name=_('IP管理全局只读权限'), default=False, help_text=_('用户拥有科技网链路管理功能的全局只读权限'))
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)


    class Meta:
        ordering = ('-create_time',)
        db_table = 'link_user_role'
        verbose_name = _('链路管理用户角色和权限')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.user.username

class Element(UuidModel):
    """网元"""

    def __init__(self, *args, **kwargs):
        super(Element, self).__init__(*args, **kwargs)
        self.elemtny_type = None

    class Type(models.TextChoices):
        """网元类型"""
        OPTICAL_FIBER = 'optical-fiber', _('光纤')
        LEASE_LINE = 'lease-line', _('租用线路')
        PORT = 'port', _('配线架端口')
        CONNECTOR_BOX = 'connector-box', _('光缆接头盒')

    # class Status(models.TextChoices):
    #     '网元状态'
    #     IDLE = 'idle', _('空闲')
    #     USING = 'using', _('使用中')

    # element_status = models.CharField(verbose_name=_('网元状态'), max_length=16, choices=Status.choices, default=Status.IDLE)
    element_link_id = models.TextField(verbose_name=_('链路id'), blank=True, default='')

    class Meta:
        abstract = True

    def get_serial(self) -> str:
        """获得网元序列"""
        if self.elemtny_type is None or self.id is None:
            raise exceptions.Error(message=_('网元对象未初始化'))
        return f'{self.elemtny_type}:{self.id}'

class LeaseLine(Element):
    """租用线路"""

    def __init__(self, *args, **kwargs):
        super(LeaseLine, self).__init__(*args, **kwargs)
        self.elemtny_type = Element.Type.LEASE_LINE

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


class OpticalFiber(Element):
    """光纤"""
    def __init__(self, *args, **kwargs):
        super(OpticalFiber, self).__init__(*args, **kwargs)
        self.elemtny_type = Element.Type.OPTICAL_FIBER

    fiber_cable_id = models.CharField(verbose_name=_('光缆ID'), max_length=36, default='', db_index=True)
    sequence = models.IntegerField(verbose_name=_('纤序'), default=0)
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'link_optical_fiber'
        verbose_name = _('光纤')
        verbose_name_plural = verbose_name

class Port(Element):
    """端口"""
    def __init__(self, *args, **kwargs):
        super(Port, self).__init__(*args, **kwargs)
        self.elemtny_type = Element.Type.PORT

    number = models.CharField(verbose_name=_('端口编号'), max_length=24, default='', help_text=_('自定义编号'))
    model_type = models.CharField(verbose_name=_('型号'), max_length=36, blank=True, default='')
    detail = models.CharField(verbose_name=_('详情'), max_length=255, blank=True, default='')
    distribution_frame_id = models.CharField(verbose_name=_('配线架id'), max_length=36, default='', db_index=True)
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'link_port'
        verbose_name = _('端口')
        verbose_name_plural = verbose_name

class ConnectorBox(Element):
    """光缆接头盒"""
    def __init__(self, *args, **kwargs):
        super(ConnectorBox, self).__init__(*args, **kwargs)
        self.elemtny_type = Element.Type.CONNECTOR_BOX

    number = models.CharField(verbose_name=_('接头盒编号'), max_length=24, default='', help_text=_('自定义编号'))
    place = models.CharField(verbose_name=_('位置'), max_length=128, blank=True, default='')
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    location = models.CharField(verbose_name=_('经纬度'), max_length=64, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'link_connector_box'
        verbose_name = _('光缆接头盒')
        verbose_name_plural = verbose_name


class FiberCable(UuidModel):
    """光缆"""

    number = models.CharField(verbose_name=_('光缆编号'), max_length=24, default='')
    fiber_count = models.IntegerField(verbose_name=_('总纤芯数量'), default=0)
    length = models.DecimalField(verbose_name=_('长度'), max_digits=10, decimal_places=2, null=True, blank=True, default=None, help_text='km')
    endpoint_1 = models.CharField(verbose_name=_('端点1'), max_length=255, blank=True, default='')
    endpoint_2 = models.CharField(verbose_name=_('端点2'), max_length=255, blank=True, default='')
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    fiber_ids = models.TextField(verbose_name=_('光纤ID列表'), blank=True, default='', help_text=_('逗号分隔'))
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'link_fiber_cable'
        verbose_name = _('光缆')
        verbose_name_plural = verbose_name

class DistributionFrame(UuidModel):
    """配线架"""

    device_id = models.CharField(verbose_name=_('设备号'), max_length=24, default='')
    model_type = models.CharField(verbose_name=_('设备型号'), max_length=36, blank=True, default='')
    size = models.CharField(verbose_name=_('行列数'), max_length=36, blank=True, default='')
    place = models.CharField(verbose_name=_('位置'), max_length=128, blank=True, default='')
    institution_id = models.CharField(verbose_name=_('机构ID'), max_length=36, blank=True, default='', db_index=True)
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'link_distribution_frame'
        verbose_name = _('配线架')
        verbose_name_plural = verbose_name

class LinkOrg(UuidModel):
    """链路机构对象"""

    organization = models.ForeignKey(
        verbose_name=_('分配机构'), to=DataCenter, related_name='datacenter_linkorg',
        on_delete=models.SET_NULL, null=True, blank=True, default=None)
    name = models.CharField(verbose_name=_('机构名'), max_length=64, default='')
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
    
class ElementLink(UuidModel):
    """链路"""

    class LinkStatus(models.TextChoices):
        """链路状态"""
        USING = 'using', _('使用')
        IDLE = 'idle', _('闲置')
        BACKUP = 'backup', _('备用')
        DELETED = 'deleted', _('删除')

    number = models.CharField(verbose_name=_('链路编号'), max_length=24, default='')
    serials = models.TextField(verbose_name=_('网元序列'), default='', help_text=_('逗号分隔'))
    remarks = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    link_status = models.CharField(verbose_name=_('链路状态'), max_length=16, choices=LinkStatus.choices, default=LinkStatus.IDLE)
    task_id = models.CharField(verbose_name=_('机构ID'), max_length=36, blank=True, default='', db_index=True)
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'link_element_link'
        verbose_name = _('链路')
        verbose_name_plural = verbose_name


class Task(UuidModel):
    """业务"""

    class TaskStatus(models.TextChoices):
        """业务状态"""
        NORMAL = 'normal', _('正常')
        DELETED = 'deleted', _('删除')
    number = models.CharField(verbose_name=_('业务编号'), max_length=24, default='')
    user = models.CharField(verbose_name=_('用户（单位）'), max_length=36, blank=True, default='')
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
        db_table = 'link_task'
        verbose_name = _('业务')
        verbose_name_plural = verbose_name