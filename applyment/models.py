from datetime import timedelta
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from service.models import ServiceConfig, DataCenter, UserQuota

from utils.model import UuidModel

User = get_user_model()


class ApplyService(UuidModel):
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
        ordering = ['-creation_time']
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


class ApplyQuota(UuidModel):
    """
    用户资源申请
    """
    STATUS_WAIT = 'wait'
    STATUS_PENDING = 'pending'
    STATUS_PASS = 'pass'
    STATUS_REJECT = 'reject'
    STATUS_CANCEL = 'cancel'
    CHOICE_STATUS = (
        (STATUS_WAIT, _('待审批')),
        (STATUS_PENDING, _('审批中')),
        (STATUS_PASS, _('审批通过')),
        (STATUS_REJECT, _('拒绝')),
        (STATUS_CANCEL, _('取消申请')),
    )
    LIST_STATUS = [STATUS_WAIT, STATUS_PENDING, STATUS_PASS, STATUS_REJECT, STATUS_CANCEL]

    service = models.ForeignKey(verbose_name=_('服务'), to=ServiceConfig, default='',
                                on_delete=models.DO_NOTHING, related_name='service_apply_quota_set')
    user = models.ForeignKey(verbose_name=_('申请用户'), to=User, null=True,
                             on_delete=models.SET_NULL, related_name='user_apply_quota_set')
    approve_user = models.ForeignKey(verbose_name=_('审批人'), to=User, null=True, on_delete=models.SET_NULL,
                                     related_name='approve_apply_quota', default=None)
    creation_time = models.DateTimeField(verbose_name=_('申请时间'), auto_now_add=True)
    approve_time = models.DateTimeField(verbose_name=_('审批时间'), null=True, blank=True, default=None)
    status = models.CharField(verbose_name=_('状态'), max_length=16, choices=CHOICE_STATUS, default=STATUS_WAIT)

    private_ip = models.IntegerField(verbose_name=_('总私网IP数'), default=0)
    public_ip = models.IntegerField(verbose_name=_('总公网IP数'), default=0)
    vcpu = models.IntegerField(verbose_name=_('总CPU核数'), default=0)
    ram = models.IntegerField(verbose_name=_('总内存大小(MB)'), default=0)
    disk_size = models.IntegerField(verbose_name=_('总硬盘大小(GB)'), default=0)

    duration_days = models.IntegerField(verbose_name=_('申请使用时长(天)'), blank=True, default=0,
                                        help_text=_('审批通过后到配额到期期间的时长，单位天'))
    company = models.CharField(verbose_name=_('申请人单位'), max_length=64, blank=True, default='')
    contact = models.CharField(verbose_name=_('联系方式'), max_length=64, blank=True, default='')
    purpose = models.CharField(verbose_name=_('用途'), max_length=255, blank=True, default='')
    user_quota = models.OneToOneField(to=UserQuota, null=True, on_delete=models.SET_NULL, related_name='apply_quota',
                                      default=None, verbose_name=_('用户资源配额'),
                                      help_text=_('资源配额申请审批通过后生成的对应的用户资源配额'))
    deleted = models.BooleanField(verbose_name=_('删除'), default=False, help_text=_('选中为删除'))

    class Meta:
        ordering = ['-creation_time']
        verbose_name = _('用户资源申请')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'ApplyQuota(vcpu={self.vcpu}, ram={self.ram}Mb, disk_size={self.disk_size}Gb, ' \
               f'status={self.get_status_display()})'

    def is_wait_status(self):
        """
        是否是待审批状态
        :return:
            True
            False
        """
        return self.status == self.STATUS_WAIT

    def is_pending_status(self):
        """
        是否是审批中状态
        :return:
            True
            False
        """
        return self.status == self.STATUS_PENDING

    def is_cancel_status(self):
        """
        是否是已取消状态
        :return:
            True
            False
        """
        return self.status == self.STATUS_CANCEL

    def set_pending(self, user):
        """
        挂起申请
        :return:
            True    # success
            False   # failed
        """
        if not self.is_wait_status():
            return False

        self.status = self.STATUS_PENDING
        self.approve_user = user
        self.approve_time = timezone.now()
        self.save(update_fields=['status', 'approve_time', 'approve_user'])
        return True

    def set_reject(self, user):
        """
        拒绝申请
        :return:
            True    # success
            False   # failed
        """
        if not self.is_pending_status():
            return False

        self.status = self.STATUS_REJECT
        self.approve_user = user
        self.approve_time = timezone.now()
        self.save(update_fields=['status', 'approve_time', 'approve_user'])
        return True

    def set_pass(self, user, quota):
        """
        通过申请
        :return:
            True    # success
            False   # failed
        """
        if not self.is_pending_status():
            return False

        self.status = self.STATUS_PASS
        self.approve_user = user
        self.approve_time = timezone.now()
        self.user_quota = quota
        self.save(update_fields=['status', 'approve_time', 'approve_user', 'user_quota'])
        return True

    def set_cancel(self):
        """
        取消申请
        :return:
            True    # success
            False   # failed
        """
        if not self.is_wait_status():
            return False

        self.status = self.STATUS_CANCEL
        self.save(update_fields=['status'])
        return True

    def do_pass(self, user):
        """
        通过申请处理
        """
        quota = UserQuota()
        quota.user = self.user
        quota.service = self.service
        quota.private_ip_total = self.private_ip
        quota.public_ip_total = self.public_ip
        quota.vcpu_total = self.vcpu
        quota.ram_total = self.ram
        quota.disk_size_total = self.disk_size
        quota.expiration_time = timezone.now() + timedelta(days=15)
        quota.duration_days = self.duration_days
        with transaction.atomic():
            quota.save()
            self.set_pass(user=user, quota=quota)

        return quota

    def do_soft_delete(self):
        """
        软删除申请记录
        :return:
            True    # success
        """
        self.deleted = True
        self.save(update_fields=['deleted'])
        return True
