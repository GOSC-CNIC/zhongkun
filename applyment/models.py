from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from service.models import ServiceConfig, DataCenter


User = get_user_model()


class ApplyService(models.Model):
    """
    服务接入申请
    """
    STATUS_WAIT = 1
    STATUS_PASS = 2
    STATUS_REJECT = 3
    CHOICE_STATUS = (
        (STATUS_WAIT, _('待审批')),
        (STATUS_PASS, _('审批通过')),
        (STATUS_REJECT, _('拒绝'))
    )

    SERVICE_EVCLOUD = 0
    SERVICE_OPENSTACK = 1
    SERVICE_TYPE_CHOICES = (
        (SERVICE_EVCLOUD, 'EVCloud'),
        (SERVICE_OPENSTACK, 'OpenStack'),
    )

    id = models.AutoField(verbose_name='ID', primary_key=True)
    user = models.ForeignKey(verbose_name=_('申请用户'), to=User, null=True, on_delete=models.SET_NULL)
    creation_time = models.DateTimeField(verbose_name=_('申请时间'), auto_now_add=True)
    approve_time = models.DateTimeField(verbose_name=_('审批时间'), auto_now_add=True)
    status = models.SmallIntegerField(verbose_name=_('状态'), choices=CHOICE_STATUS, default=STATUS_WAIT)

    data_center = models.ForeignKey(to=DataCenter, null=True, on_delete=models.SET_NULL, verbose_name=_('数据中心'))
    name = models.CharField(max_length=255, verbose_name=_('服务名称'))
    region_id = models.CharField(max_length=128, default='', blank=True, verbose_name=_('服务区域/分中心ID'))
    service_type = models.SmallIntegerField(choices=SERVICE_TYPE_CHOICES, default=SERVICE_EVCLOUD,
                                            verbose_name=_('服务平台类型'))
    endpoint_url = models.CharField(max_length=255, verbose_name=_('服务地址url'), unique=True,
                                    help_text='http(s)://{hostname}:{port}/')
    api_version = models.CharField(max_length=64, default='v3', verbose_name=_('API版本'), help_text=_('预留，主要EVCloud使用'))
    username = models.CharField(max_length=128, verbose_name=_('用户名'), help_text=_('用于此服务认证的用户名'))
    password = models.CharField(max_length=128, verbose_name=_('密码'))
    remarks = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))
    need_vpn = models.BooleanField(verbose_name=_('是否需要VPN'), default=True)

    vpn_endpoint_url = models.CharField(max_length=255, verbose_name=_('VPN服务地址url'),
                                        help_text='http(s)://{hostname}:{port}/')
    vpn_api_version = models.CharField(max_length=64, default='v3', verbose_name=_('VPN API版本'))
    vpn_username = models.CharField(max_length=128, verbose_name=_('用户名'), help_text=_('用于VPN服务认证的用户名'))
    vpn_password = models.CharField(max_length=128, verbose_name=_('密码'))

    class Meta:
        ordering = ['-id']
        verbose_name = _('服务接入申请')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'ApplyService(data_center={self.data_center}, name={self.name})'

    def convert_to_service(self):
        """
        申请转为对应的ServiceConfig对象
        :return:
        """
        service = ServiceConfig()
        service.data_center = self.data_center
        service.name = self.name
        service.region_id = self.region_id
        service.service_type = self.service_type
        service.endpoint_url = self.endpoint_url
        service.api_version = self.api_version
        service.username = self.username
        service.password = self.password
        service.remarks = self.remarks
        service.need_vpn = self.need_vpn
        service.vpn_endpoint_url = self.vpn_endpoint_url
        service.vpn_api_version = self.vpn_api_version
        service.vpn_username = self.vpn_username
        service.vpn_password = self.vpn_password
        return service


class ApplyQuota(models.Model):
    """
    用户资源申请
    """
    STATUS_WAIT = 1
    STATUS_PASS = 2
    STATUS_REJECT = 3
    CHOICE_STATUS = (
        (STATUS_WAIT, _('待审批')),
        (STATUS_PASS, _('审批通过')),
        (STATUS_REJECT, _('拒绝'))
    )

    id = models.AutoField(verbose_name='ID', primary_key=True)
    user = models.ForeignKey(verbose_name=_('申请用户'), to=User, null=True, on_delete=models.SET_NULL)
    creation_time = models.DateTimeField(verbose_name=_('申请时间'), auto_now_add=True)
    approve_time = models.DateTimeField(verbose_name=_('审批时间'), auto_now_add=True)
    status = models.SmallIntegerField(verbose_name=_('状态'), choices=CHOICE_STATUS, default=STATUS_WAIT)

    private_ip = models.IntegerField(verbose_name=_('总私网IP数'), default=0)
    public_ip = models.IntegerField(verbose_name=_('总公网IP数'), default=0)
    vcpu = models.IntegerField(verbose_name=_('总CPU核数'), default=0)
    ram = models.IntegerField(verbose_name=_('总内存大小(MB)'), default=0)
    disk_size = models.IntegerField(verbose_name=_('总硬盘大小(GB)'), default=0)

    class Meta:
        ordering = ['-id']
        verbose_name = _('用户资源申请')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'ApplyQuota(vcpu={self.vcpu}, ram={self.ram}Mb, disk_size={self.disk_size}Gb, status={self.get_status_display()})'
