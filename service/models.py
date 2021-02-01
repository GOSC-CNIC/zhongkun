from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

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
        ordering = ['id']
        verbose_name = _('机构')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class ServiceConfig(models.Model):
    """
    资源服务接入配置
    """
    SERVICE_EVCLOUD = 0
    SERVICE_OPENSTACK = 1
    SERVICE_VMWARE = 2
    SERVICE_TYPE_CHOICES = (
        (SERVICE_EVCLOUD, 'EVCloud'),
        (SERVICE_OPENSTACK, 'OpenStack'),
        (SERVICE_VMWARE, 'Vmware'),
    )
    SERVICE_TYPE_STRING = {
        SERVICE_EVCLOUD: 'evcloud',
        SERVICE_OPENSTACK: 'openstack',
        SERVICE_VMWARE: 'vmware'
    }

    STATUS_ENABLE = 1
    STATUS_DISABLE = 2
    CHOICE_STATUS = (
        (STATUS_ENABLE, _('开启状态')),
        (STATUS_DISABLE, _('关闭状态'))
    )

    id = models.AutoField(primary_key=True, verbose_name='ID')
    data_center = models.ForeignKey(to=DataCenter, null=True, on_delete=models.SET_NULL,
                                    related_name='service_set', verbose_name=_('数据中心'))
    name = models.CharField(max_length=255, verbose_name=_('服务名称'))
    region_id = models.CharField(max_length=128, default='', blank=True, verbose_name=_('服务区域/分中心ID'))
    service_type = models.SmallIntegerField(choices=SERVICE_TYPE_CHOICES, default=SERVICE_EVCLOUD,
                                            verbose_name=_('服务平台类型'))
    endpoint_url = models.CharField(max_length=255, verbose_name=_('服务地址url'), unique=True,
                                    help_text='http(s)://{hostname}:{port}/')
    api_version = models.CharField(max_length=64, default='v3', verbose_name=_('API版本'),
                                   help_text=_('预留，主要EVCloud使用'))
    username = models.CharField(max_length=128, verbose_name=_('用户名'), help_text=_('用于此服务认证的用户名'))
    password = models.CharField(max_length=128, verbose_name=_('密码'))
    add_time = models.DateTimeField(auto_now_add=True, verbose_name=_('添加时间'))
    status = models.SmallIntegerField(verbose_name=_('服务状态'), choices=CHOICE_STATUS, default=STATUS_ENABLE)
    remarks = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))
    need_vpn = models.BooleanField(verbose_name=_('是否需要VPN'), default=True)
    vpn_endpoint_url = models.CharField(max_length=255, blank=True, default='', verbose_name=_('服务地址url'),
                                        help_text='http(s)://{hostname}:{port}/')
    vpn_api_version = models.CharField(max_length=64, blank=True, default='v3', verbose_name=_('API版本'),
                                       help_text=_('预留，主要EVCloud使用'))
    vpn_username = models.CharField(max_length=128, blank=True, default='', verbose_name=_('用户名'),
                                    help_text=_('用于此服务认证的用户名'))
    vpn_password = models.CharField(max_length=128, blank=True, default='', verbose_name=_('密码'))
    extra = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('其他配置'), help_text=_('json格式'))

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

    def service_type_to_str(self, t):
        """
        :return:
            str or None
        """
        return self.SERVICE_TYPE_STRING.get(t)


class ServiceQuotaBase(models.Model):
    """
    数据中心接入服务的资源配额基类
    """
    id = models.AutoField(verbose_name='ID', primary_key=True)
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
    enable = models.BooleanField(verbose_name=_('有效状态'), default=True, help_text=_('选中，资源配额生效；未选中，无法申请分中心资源'))

    class Meta:
        abstract = True


class ServicePrivateQuota(ServiceQuotaBase):
    """
    数据中心接入服务的私有资源配额和限制
    """
    service = models.OneToOneField(to=ServiceConfig, null=True, on_delete=models.SET_NULL,
                                   related_name='service_private_quota', verbose_name=_('接入服务'))

    class Meta:
        db_table = 'service_private_quota'
        ordering = ['-id']
        verbose_name = _('接入服务的私有资源配额')
        verbose_name_plural = verbose_name


class ServiceShareQuota(ServiceQuotaBase):
    """
    接入服务的分享资源配额和限制
    """
    service = models.OneToOneField(to=ServiceConfig, null=True, on_delete=models.SET_NULL,
                                   related_name='service_share_quota', verbose_name=_('接入服务'))

    class Meta:
        db_table = 'service_share_quota'
        ordering = ['-id']
        verbose_name = _('接入服务的分享资源配额')
        verbose_name_plural = verbose_name


class UserQuota(models.Model):
    """
    用户资源配额限制
    """
    TAG_BASE = 1
    TAG_PROBATION = 2
    CHOICES_TAG = (
        (TAG_BASE, _('普通配额')),
        (TAG_PROBATION, _('试用配额'))
    )

    id = models.AutoField(verbose_name='ID', primary_key=True)
    tag = models.SmallIntegerField(verbose_name=_('配额类型'), choices=CHOICES_TAG, default=TAG_BASE)
    user = models.ForeignKey(to=User, null=True, on_delete=models.SET_NULL,
                             related_name='user_quota', verbose_name=_('用户'))
    service = models.ForeignKey(to=ServiceConfig, null=True, on_delete=models.SET_NULL,
                                related_name='service_quota', verbose_name=_('适用服务'))
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
    expiration_time = models.DateTimeField(verbose_name=_('过期时间'), null=True, blank=True, default=None)
    is_email = models.BooleanField(verbose_name=_('是否邮件通知'), default=False, help_text=_('是否邮件通知用户配额即将到期'))
    deleted = models.BooleanField(verbose_name=_('删除'), default=False)

    class Meta:
        db_table = 'user_quota'
        ordering = ['-id']
        verbose_name = _('用户资源配额')
        verbose_name_plural = verbose_name

    def __str__(self):
        values = []
        if self.vcpu_total > 0:
            values.append(f'vCPU: {self.vcpu_total}')
        if self.ram_total > 0:
            values.append(f'RAM: {self.ram_total}Mb')
        if self.disk_size_total > 0:
            values.append(f'Disk: {self.disk_size_total}Gb')
        if self.public_ip_total > 0:
            values.append(f'PublicIP: {self.public_ip_total}')
        if self.private_ip_total > 0:
            values.append(f'PrivateIP: {self.private_ip_total}')

        if values:
            s = ', '.join(values)
        else:
            s = 'vCPU: 0, RAM:0 Mb, 0, 0, 0'

        return f'[{self.get_tag_display()}]({s})'

    @property
    def display(self):
        return self.__str__()

    @property
    def vcpu_free_count(self):
        return self.vcpu_total - self.vcpu_used

    @property
    def ram_free_count(self):
        return self.ram_total - self.ram_used

    @property
    def disk_free_size(self):
        return self.disk_size_total - self.disk_size_used

    @property
    def public_ip_free_count(self):
        return self.public_ip_total - self.public_ip_used

    @property
    def private_ip_free_count(self):
        return self.private_ip_total - self.private_ip_used

    @property
    def all_ip_count(self):
        return self.private_ip_total + self.public_ip_total

    def is_expire_now(self):
        """
        资源配额现在是否过期
        :return:
            True    # 过期
            False   # 未过期
        """
        if self.tag == self.TAG_BASE:       # base配额不检查过期时间
            return False

        if not self.expiration_time:        # 未设置过期时间
            return False

        now = timezone.now()
        ts_now = now.timestamp()
        ts_expire = self.expiration_time.timestamp()
        if (ts_now + 60) > ts_expire:  # 1分钟内算过期
            return True

        return False
