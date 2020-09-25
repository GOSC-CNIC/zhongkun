from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()
app_name = 'service'


class DataCenter(models.Model):
    STATUS_ENABLE = 1
    STATUS_DISABLE = 2
    CHOICE_STATUS = (
        (STATUS_ENABLE, _('开启状态')),
        (STATUS_DISABLE, _('关闭状态'))
    )

    id = models.AutoField(verbose_name='ID', primary_key=True)
    name = models.CharField(verbose_name=_('名称'), max_length=255)
    users = models.ManyToManyField(to=User, verbose_name=_('用户'), blank=True, related_name='data_center_set')
    status = models.SmallIntegerField(verbose_name=_('服务状态'), choices=CHOICE_STATUS, default=STATUS_ENABLE)
    desc = models.CharField(verbose_name=_('描述'), blank=True, max_length=255)

    class Meta:
        ordering = ['-id']
        verbose_name = _('数据中心')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ServiceConfig(models.Model):
    """
    资源服务接入配置
    """
    SERVICE_EVCLOUD = 0
    SERVICE_OPENSTACK = 1
    SERVICE_TYPE_CHOICES = (
        (SERVICE_EVCLOUD, 'EVCloud'),
        (SERVICE_OPENSTACK, 'OpenStack'),
    )

    STATUS_ENABLE = 1
    STATUS_DISABLE = 2
    CHOICE_STATUS = (
        (STATUS_ENABLE, _('开启状态')),
        (STATUS_DISABLE, _('关闭状态'))
    )

    id = models.AutoField(primary_key=True, verbose_name='ID')
    data_center = models.ForeignKey(to=DataCenter, null=True, on_delete=models.SET_NULL, verbose_name=_('数据中心'))
    name = models.CharField(max_length=255, verbose_name=_('服务名称'))
    region_id = models.CharField(max_length=128, default='', blank=True, verbose_name=_('服务区域/分中心ID'))
    service_type = models.SmallIntegerField(choices=SERVICE_TYPE_CHOICES, default=SERVICE_EVCLOUD, verbose_name=_('服务平台类型'))
    endpoint_url = models.CharField(max_length=255, verbose_name=_('服务地址url'), unique=True, help_text='http(s)://{hostname}:{port}/')
    api_version = models.CharField(max_length=64, default='v3', verbose_name=_('API版本'), help_text=_('预留，主要EVCloud使用'))
    username = models.CharField(max_length=128, verbose_name=_('用户名'), help_text=_('用于此服务认证的用户名'))
    password = models.CharField(max_length=128, verbose_name=_('密码'))
    add_time = models.DateTimeField(auto_now_add=True, verbose_name=_('添加时间'))
    status = models.SmallIntegerField(verbose_name=_('服务状态'), choices=CHOICE_STATUS, default=STATUS_ENABLE)
    remarks = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))
    need_vpn = models.BooleanField(verbose_name=_('是否需要VPN'), default=True)
    vpn_endpoint_url = models.CharField(max_length=255, blank=True, default='', verbose_name=_('服务地址url'), help_text='http(s)://{hostname}:{port}/')
    vpn_api_version = models.CharField(max_length=64, blank=True, default='v3', verbose_name=_('API版本'), help_text=_('预留，主要EVCloud使用'))
    vpn_username = models.CharField(max_length=128, blank=True, default='', verbose_name=_('用户名'), help_text=_('用于此服务认证的用户名'))
    vpn_password = models.CharField(max_length=128, blank=True, default='', verbose_name=_('密码'))

    class Meta:
        ordering = ['-id']
        verbose_name = _('服务接入配置')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def is_need_vpn(self):
        return self.need_vpn

    def check_vpn_config(self):
        """
        检查vpn配置
        :return:
        """
        if not self.is_need_vpn():
            return True

        if self.service_type == self.SERVICE_EVCLOUD:
            return True

        if not self.vpn_endpoint_url or not self.vpn_password or not self.vpn_username:
            return False

        return True


class ServiceQuota(models.Model):
    """
    服务中心资源配额和限制
    """
    id = models.IntegerField(verbose_name='ID', primary_key=True)
    data_center = models.OneToOneField(to=DataCenter, null=True, on_delete=models.SET_NULL,
                                       related_name='data_center_quota', verbose_name=_('数据中心'))
    private_ip_total = models.IntegerField(verbose_name=_('总私网IP数'), default=0)
    private_ip_used = models.IntegerField(verbose_name=_('已用私网IP数'), default=0)
    public_ip_total = models.IntegerField(verbose_name=_('总公网IP数'), default=0)
    public_ip_used = models.IntegerField(verbose_name=_('已用公网IP数'), default=0)
    vcpu_total = models.IntegerField(verbose_name=_('总CPU核数'), default=0)
    vcpu_used = models.IntegerField(verbose_name=_('已用CPU核数'), default=0)
    ram_total = models.IntegerField(verbose_name=_('总内存大小(MB)'), default=0)
    ram_used = models.IntegerField(verbose_name=_('已用内存大小(MB)'), default=0)
    disk_size_total = models.IntegerField(verbose_name=_('总硬盘大小(GB)'), default=0)
    disk_size_used = models.IntegerField(verbose_name=_('已用硬盘大小(GB)'), default=0)
    enable = models.BooleanField(verbose_name=_('有效状态'), help_text=_('选中，资源配额生效；未选中，无法申请分中心资源'))

    class Meta:
        db_table = 'service_quota'
        ordering = ['-id']
        verbose_name = _('服务中心资源配额')
        verbose_name_plural = verbose_name


class UserQuota(models.Model):
    """
    用户资源配额限制
    """
    id = models.IntegerField(verbose_name='ID', primary_key=True)
    user = models.OneToOneField(to=User, null=True, on_delete=models.SET_NULL,
                                related_name='user_quota', verbose_name=_('用户'))
    private_ip_total = models.IntegerField(verbose_name=_('总私网IP数'), default=0)
    private_ip_used = models.IntegerField(verbose_name=_('已用私网IP数'), default=0)
    public_ip_total = models.IntegerField(verbose_name=_('总公网IP数'), default=0)
    public_ip_used = models.IntegerField(verbose_name=_('已用公网IP数'), default=0)
    vcpu_total = models.IntegerField(verbose_name=_('总CPU核数'), default=0)
    vcpu_used = models.IntegerField(verbose_name=_('已用CPU核数'), default=0)
    ram_total = models.IntegerField(verbose_name=_('总内存大小(MB)'), default=0)
    ram_used = models.IntegerField(verbose_name=_('已用内存大小(MB)'), default=0)
    disk_size_total = models.IntegerField(verbose_name=_('总硬盘大小(GB)'), default=0)
    disk_size_used = models.IntegerField(verbose_name=_('已用硬盘大小(GB)'), default=0)

    class Meta:
        db_table = 'user_quota'
        ordering = ['-id']
        verbose_name = _('用户资源配额')
        verbose_name_plural = verbose_name
