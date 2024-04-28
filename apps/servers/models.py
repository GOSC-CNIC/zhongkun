import math
import json

from django.db import models, transaction
from django.db.models import Count, Sum, Q
from django.utils.translation import gettext, gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings

from core import errors
from core import site_configs_manager
from apps.service.models import OrgDataCenter, DataCenter
from utils.model import get_encryptor, PayType, UuidModel, OwnerType
from utils.validators import json_string_validator, http_url_validator
from utils import rand_utils
from apps.vo.models import VirtualOrganization
from apps.users.models import UserProfile as User
from core.adapters.outputs import ImageSysType, ImageSysArch, ImageSysRelease
from core.adapters.params import OpenStackParams


def short_uuid1_l25():
    return rand_utils.short_uuid1_25()


class BaseService(UuidModel):
    class ServiceType(models.TextChoices):
        EVCLOUD = 'evcloud', 'EVCloud'
        OPENSTACK = 'openstack', 'OpenStack'
        VMWARE = 'vmware', 'VMware'
        ALIYUN = 'aliyun', '阿里云'
        UNIS_CLOUD = 'unis-cloud', _('紫光云')

    class CLoudType(models.TextChoices):
        PUBLIC = 'public', _('公有云')
        PRIVATE = 'private', _('私有云')
        HYBRID = 'hybrid', _('混合云')

    service_type = models.CharField(max_length=32, choices=ServiceType.choices, default=ServiceType.EVCLOUD,
                                    verbose_name=_('服务平台类型'))
    cloud_type = models.CharField(max_length=32, choices=CLoudType.choices, default=CLoudType.PRIVATE,
                                  verbose_name=_('云服务类型'))

    class Meta:
        abstract = True


class ServiceConfig(BaseService):
    """
    资源服务接入配置
    """
    class Status(models.TextChoices):
        ENABLE = 'enable', _('服务中')
        DISABLE = 'disable', _('停止服务')
        DELETED = 'deleted', _('删除')

    org_data_center = models.ForeignKey(
        to=OrgDataCenter, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name=_('数据中心'),
        db_constraint=False, blank=True, default=None)
    name = models.CharField(max_length=255, verbose_name=_('服务名称'))
    name_en = models.CharField(verbose_name=_('服务英文名称'), max_length=255, default='')
    region_id = models.CharField(max_length=128, default='', blank=True, verbose_name=_('服务区域/分中心ID'))
    endpoint_url = models.CharField(max_length=255, verbose_name=_('服务地址url'),
                                    help_text='http(s)://{hostname}:{port}/')
    api_version = models.CharField(max_length=64, default='v3', verbose_name=_('API版本'),
                                   help_text=_('预留，主要EVCloud使用'))
    username = models.CharField(max_length=128, verbose_name=_('用户名'), help_text=_('用于此服务认证的用户名'))
    password = models.CharField(max_length=255, verbose_name=_('密码'))
    add_time = models.DateTimeField(auto_now_add=True, verbose_name=_('添加时间'))
    status = models.CharField(verbose_name=_('服务状态'), max_length=32, choices=Status.choices, default=Status.ENABLE)
    remarks = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))
    need_vpn = models.BooleanField(
        verbose_name=_('需要并提供VPN'), default=True,
        help_text=_('访问此服务单元的云主机需要使用vpn，并且支持提供vpn服务，请勾选此项，暂时仅支持EVCloud服务。'))
    vpn_endpoint_url = models.CharField(max_length=255, blank=True, default='', verbose_name=_('VPN服务地址url'),
                                        help_text='http(s)://{hostname}:{port}/')
    vpn_api_version = models.CharField(max_length=64, blank=True, default='v3', verbose_name=_('VPN服务API版本'),
                                       help_text=_('预留，主要EVCloud使用'))
    vpn_username = models.CharField(max_length=128, blank=True, default='', verbose_name=_('VPN服务用户名'),
                                    help_text=_('用于此服务认证的用户名'))
    vpn_password = models.CharField(max_length=255, blank=True, default='', verbose_name=_('VPN服务密码'))
    extra = models.CharField(max_length=1024, blank=True, default='', validators=(json_string_validator,),
                             verbose_name=_('其他配置'), help_text=_('json格式'))
    users = models.ManyToManyField(to=User, verbose_name=_('用户'), blank=True, related_name='service_set')

    contact_person = models.CharField(verbose_name=_('联系人名称'), max_length=128,
                                      blank=True, default='')
    contact_email = models.EmailField(verbose_name=_('联系人邮箱'), blank=True, default='')
    contact_telephone = models.CharField(verbose_name=_('联系人电话'), max_length=16,
                                         blank=True, default='')
    contact_fixed_phone = models.CharField(verbose_name=_('联系人固定电话'), max_length=16,
                                           blank=True, default='')
    contact_address = models.CharField(verbose_name=_('联系人地址'), max_length=256,
                                       blank=True, default='')
    logo_url = models.CharField(verbose_name=_('LOGO url'), max_length=256,
                                blank=True, default='')
    longitude = models.FloatField(verbose_name=_('经度'), blank=True, default=0)
    latitude = models.FloatField(verbose_name=_('纬度'), blank=True, default=0)
    pay_app_service_id = models.CharField(
        verbose_name=_('余额结算APP服务ID'), max_length=36, blank=True, default='',
        help_text=_('此服务对应的APP结算服务单元（注册在余额结算中的APP服务）id，扣费时需要此id，用于指定哪个服务发生的扣费；'
                    '正常情况下此内容会自动填充，不需要手动输入'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))
    disk_available = models.BooleanField(verbose_name=_('提供云硬盘服务'), default=False)
    only_admin_visible = models.BooleanField(verbose_name=_('仅管理员可见'), default=False)
    monitor_task_id = models.CharField(
        verbose_name=_('服务单元对应监控任务ID'), max_length=36, blank=True, default='', editable=False,
        help_text=_('记录为服务单元创建的站点监控任务的ID'))
    version = models.CharField(max_length=32, blank=True, default='', verbose_name=_('版本号'), help_text=_('服务当前的版本'))

    class Meta:
        db_table = 'service_serviceconfig'
        ordering = ['sort_weight']
        verbose_name = _('云主机服务单元接入配置')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)

    def sync_to_pay_app_service(self):
        """
        当name修改时，同步变更到 对应的钱包的pay app service
        """
        from apps.app_wallet.models import PayAppService
        try:
            app_service = PayAppService.objects.filter(id=self.pay_app_service_id).first()
            if app_service:
                update_fields = []
                if app_service.name != self.name:
                    app_service.name = self.name
                    update_fields.append('name')

                if app_service.name_en != self.name_en:
                    app_service.name_en = self.name_en
                    update_fields.append('name_en')

                org_id = self.org_data_center.organization_id if self.org_data_center else None
                if app_service.orgnazition_id != org_id:
                    app_service.orgnazition_id = org_id
                    update_fields.append('orgnazition_id')

                if self.id and app_service.service_id != self.id:
                    app_service.service_id = self.id
                    update_fields.append('service_id')

                if update_fields:
                    app_service.save(update_fields=update_fields)
        except Exception as exc:
            raise ValidationError(str(exc))

    def check_or_register_pay_app_service(self):
        """
        如果指定结算服务单元，确认结算服务单元是否存在有效；未指定结算服务单元时为云主机服务单元注册对应的钱包结算服务单元
        :raises: ValidationError
        """
        from apps.app_wallet.models import PayAppService

        try:
            app_id = site_configs_manager.get_pay_app_id(dj_settings=settings, check_valid=True)
        except Exception as exc:
            raise ValidationError(message=str(exc))

        if self.pay_app_service_id:
            app_service = self.check_pay_app_service_id(self.pay_app_service_id)
            return app_service

        # 新注册
        org_id = self.org_data_center.organization_id if self.org_data_center else None
        with transaction.atomic():
            app_service = PayAppService(
                name=self.name, name_en=self.name_en, app_id=app_id, orgnazition_id=org_id,
                resources='云主机、云硬盘', status=PayAppService.Status.NORMAL.value,
                category=PayAppService.Category.VMS_SERVER.value, service_id=self.id,
                longitude=self.longitude, latitude=self.latitude,
                contact_person=self.contact_person, contact_telephone=self.contact_telephone,
                contact_email=self.contact_email, contact_address=self.contact_address,
                contact_fixed_phone=self.contact_fixed_phone
            )
            app_service.save(force_insert=True)
            self.pay_app_service_id = app_service.id
            self.save(update_fields=['pay_app_service_id'])

        return app_service

    @staticmethod
    def check_pay_app_service_id(pay_app_service_id: str):
        from apps.app_wallet.models import PayAppService

        app_service = PayAppService.objects.filter(id=pay_app_service_id).first()
        if app_service is None:
            raise ValidationError(message={
                'pay_app_service_id': '结算服务单元不存在，请仔细确认。如果是新建服务单元不需要手动填写结算服务单元id，'
                                      '保持为空，保存后会自动注册对应的结算单元，并填充此字段'})

        return app_service

    def clean(self):
        from core.adapters.client import get_adapter_params_for_service, UnsupportedServiceType

        # 网址验证
        try:
            http_url_validator(self.endpoint_url)
        except ValidationError:
            raise ValidationError(message={'endpoint_url': gettext('不是一个有效的网址')})

        if self.pay_app_service_id:
            self.check_pay_app_service_id(self.pay_app_service_id)

        try:
            extra = self.extra_params()
        except Exception as exc:
            raise ValidationError(message={'extra': gettext('配置内容必须是json格式')})

        try:
            ap = get_adapter_params_for_service(service=self)
        except UnsupportedServiceType as exc:
            raise ValidationError(message={
                'service_type': gettext('"%s"类型服务不支持') % self.get_service_type_display()})

        required = {}
        for k, v in ap.items():
            if k not in extra:
                required[k] = v

        if required:
            msgs = [f'{k}: {v}' for k, v in required.items()]
            msgs.insert(0, gettext('"%s"类型服务单元需要配置额外参数:') % self.get_service_type_display())
            raise ValidationError(message={'extra': msgs})

    def raw_password(self):
        """
        :return:
            str     # success
            None    # failed, invalid encrypted password
        """
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self.password)
        except encryptor.InvalidEncrypted as e:
            return None

    def set_password(self, raw_password: str):
        encryptor = get_encryptor()
        self.password = encryptor.encrypt(raw_password)

    def raw_vpn_password(self):
        """
        :return:
            str     # success
            None    # failed, invalid encrypted password
        """
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self.vpn_password)
        except encryptor.InvalidEncrypted as e:
            return None

    def set_vpn_password(self, raw_password: str):
        encryptor = get_encryptor()
        self.vpn_password = encryptor.encrypt(raw_password)

    def is_need_vpn(self):
        return self.need_vpn

    def check_vpn_config(self):
        """
        检查vpn配置
        :return:
        """
        if not self.is_need_vpn():
            return True

        if self.service_type == self.ServiceType.EVCLOUD:
            return True

        if not self.vpn_endpoint_url or not self.vpn_password or not self.vpn_username:
            return False

        return True

    def user_has_perm(self, user):
        """
        用户是否有访问此服务的管理权限

        :param user: 用户
        :return:
            True    # has
            False   # no
        """
        from .managers import ServiceManager

        if not user or not user.id:
            return False

        return ServiceManager.has_perm(user_id=user.id, service_id=self.id)

    def extra_params(self) -> dict:
        if self.extra:
            return json.loads(self.extra)

        return {}

    def create_or_change_monitor_task(self, only_delete: bool = False):
        """
        自动为服务单元创建或更新监控任务
        :return: str
            ''      # 没有做任何操作
            create  # 创建
            change  # 更新
            delete  # 删除
        """
        from apps.monitor.managers import MonitorWebsiteManager

        act = ''
        monitor_url = self.endpoint_url

        # 只删除
        if only_delete:
            if self.monitor_task_id:
                task = MonitorWebsiteManager.get_website_by_id(website_id=self.monitor_task_id)
                if task:
                    self.remove_monitor_task(task)
                    act = 'delete'

            return act

        # 检查是否变化并更新
        if self.monitor_task_id:
            task = MonitorWebsiteManager.get_website_by_id(website_id=self.monitor_task_id)
            if task is None:    # 监控任务不存在，可能被删除了
                if monitor_url:   # 创建监控任务
                    self.create_monitor_task(http_url=monitor_url)
                    act = 'create'
            else:   # 监控网址是否变化
                if not monitor_url:   # 无效,删除监控任务
                    self.remove_monitor_task(task)
                    act = 'delete'
                else:
                    scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(http_url=monitor_url)
                    if not uri:
                        uri = '/'

                    if task.full_url != (scheme + hostname + uri):
                        task.name = self.name
                        task.odc_id = self.org_data_center_id
                        task.remark = _('自动为云主机服务单元“%s”创建的监控任务') % self.name
                        MonitorWebsiteManager.do_change_website_task(
                            user_website=task, new_scheme=scheme, new_hostname=hostname, new_uri=uri,
                            new_tamper_resistant=False)
                        act = 'change'
                    elif task.odc_id != self.org_data_center_id:
                        task.odc_id = self.org_data_center_id
                        update_fields = ['odc_id']
                        if task.name != self.name:
                            task.name = self.name
                            task.remark = _('自动为云主机服务单元“%s”创建的监控任务') % self.name
                            update_fields.append('name')
                            update_fields.append('remark')

                        task.save(update_fields=update_fields)
                        act = 'change'
        else:
            if monitor_url:  # 创建监控任务
                self.create_monitor_task(http_url=monitor_url)
                act = 'create'

        return act

    def create_monitor_task(self, http_url: str):
        """
        请在创建任务前，确认没有对应监控任务存在
        """
        from apps.monitor.managers import MonitorWebsiteManager

        scheme, hostname, uri = MonitorWebsiteManager.parse_http_url(http_url=http_url)
        if not uri:
            uri = '/'
        with transaction.atomic():
            task = MonitorWebsiteManager.add_website_task(
                name=self.name, scheme=scheme, hostname=hostname, uri=uri, is_tamper_resistant=False,
                remark=_('自动为云主机服务单元“%s”创建的监控任务') % self.name,
                user_id=None, odc_id=self.org_data_center_id)
            self.monitor_task_id = task.id
            self.save(update_fields=['monitor_task_id'])

        return task

    def remove_monitor_task(self, task):
        """
        删除对应监控任务
        """
        from apps.monitor.managers import MonitorWebsiteManager

        with transaction.atomic():
            MonitorWebsiteManager.do_delete_website_task(user_website=task)
            self.monitor_task_id = ''
            self.save(update_fields=['monitor_task_id'])


class ServiceQuotaBase(UuidModel):
    """
    数据中心接入服务的资源配额基类
    """
    private_ip_total = models.IntegerField(verbose_name=_('总私网IP数'), default=0, help_text=_('默认为0，表示不限制'))
    private_ip_used = models.IntegerField(verbose_name=_('已用私网IP数'), default=0)
    public_ip_total = models.IntegerField(verbose_name=_('总公网IP数'), default=0, help_text=_('默认为0，表示不限制'))
    public_ip_used = models.IntegerField(verbose_name=_('已用公网IP数'), default=0)
    vcpu_total = models.IntegerField(verbose_name=_('总CPU核数'), default=0, help_text=_('默认为0，表示不限制'))
    vcpu_used = models.IntegerField(verbose_name=_('已用CPU核数'), default=0)
    ram_total = models.IntegerField(verbose_name=_('总内存大小(GB)'), default=0, help_text=_('默认为0，表示不限制'))
    ram_used = models.IntegerField(verbose_name=_('已用内存大小(GB)'), default=0)
    disk_size_total = models.IntegerField(verbose_name=_('总云硬盘大小(GB)'), default=0, help_text=_('默认为0，表示不限制'))
    disk_size_used = models.IntegerField(verbose_name=_('已用云硬盘大小(GB)'), default=0)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), null=True, blank=True, auto_now_add=True)
    enable = models.BooleanField(verbose_name=_('有效状态'), default=True,
                                 help_text=_('选中，资源配额生效；未选中，无法申请分中心资源'))

    class Meta:
        abstract = True

    @property
    def ram_used_gib(self):
        return self.ram_used

    @ram_used_gib.setter
    def ram_used_gib(self, val):
        self.ram_used = val


class ServicePrivateQuota(ServiceQuotaBase):
    """
    数据中心接入服务的私有资源配额和限制
    """
    service = models.OneToOneField(to=ServiceConfig, null=True, on_delete=models.SET_NULL,
                                   related_name='service_private_quota', verbose_name=_('接入服务'))

    class Meta:
        db_table = 'service_private_quota'
        ordering = ['-creation_time']
        verbose_name = _('云主机服务单元的私有资源配额')
        verbose_name_plural = verbose_name


class ServiceShareQuota(ServiceQuotaBase):
    """
    接入服务的分享资源配额和限制
    """
    service = models.OneToOneField(to=ServiceConfig, null=True, on_delete=models.SET_NULL,
                                   related_name='service_share_quota', verbose_name=_('接入服务'))

    class Meta:
        db_table = 'service_share_quota'
        ordering = ['-creation_time']
        verbose_name = _('云主机服务单元的分享资源配额')
        verbose_name_plural = verbose_name


class ApplyVmService(BaseService):
    """
    服务接入申请
    """
    class Status(models.TextChoices):
        WAIT = 'wait', _('待审核')
        CANCEL = 'cancel', _('取消申请')
        PENDING = 'pending', _('审核中')
        FIRST_PASS = 'first_pass', _('初审通过')
        FIRST_REJECT = 'first_reject', _('初审拒绝')
        TEST_FAILED = 'test_failed', _('测试未通过')
        TEST_PASS = 'test_pass', _('测试通过')
        REJECT = 'reject', _('拒绝')
        PASS = 'pass', _('通过')

    user = models.ForeignKey(verbose_name=_('申请用户'), to=User, null=True, on_delete=models.SET_NULL)
    creation_time = models.DateTimeField(verbose_name=_('申请时间'), auto_now_add=True)
    approve_time = models.DateTimeField(verbose_name=_('审批时间'), auto_now_add=True)
    status = models.CharField(verbose_name=_('状态'), max_length=16,
                              choices=Status.choices, default=Status.WAIT)

    organization = models.ForeignKey(to=DataCenter, null=True, on_delete=models.SET_NULL, verbose_name=_('数据中心'))
    longitude = models.FloatField(verbose_name=_('经度'), blank=True, default=0)
    latitude = models.FloatField(verbose_name=_('纬度'), blank=True, default=0)
    name = models.CharField(max_length=255, verbose_name=_('服务名称'))
    name_en = models.CharField(verbose_name=_('英文名称'), max_length=255, default='')
    region = models.CharField(max_length=128, default='', blank=True, verbose_name=_('服务区域'),
                              help_text='OpenStack服务区域名称,EVCloud分中心ID')
    # service_type = models.CharField(choices=ServiceType.choices, default=ServiceType.EVCLOUD,
    #                                 max_length=16, verbose_name=_('服务平台类型'))
    endpoint_url = models.CharField(max_length=255, verbose_name=_('服务地址url'), unique=True,
                                    help_text='http(s)://{hostname}:{port}/')
    api_version = models.CharField(max_length=64, default='v3', verbose_name=_('API版本'), help_text=_('预留，主要EVCloud使用'))
    username = models.CharField(max_length=128, verbose_name=_('用户名'), help_text=_('用于此服务认证的用户名'))
    password = models.CharField(max_length=255, verbose_name=_('密码'))
    project_name = models.CharField(
        verbose_name='Project Name', max_length=128, blank=True, default='',
        help_text='only required when OpenStack')
    project_domain_name = models.CharField(
        verbose_name='Project Domain Name', blank=True, max_length=128,
        help_text='only required when OpenStack', default='')
    user_domain_name = models.CharField(
        verbose_name='User Domain Name', max_length=128, blank=True, default='',
        help_text='only required when OpenStack')
    remarks = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))
    need_vpn = models.BooleanField(verbose_name=_('是否需要VPN'), default=True)

    vpn_endpoint_url = models.CharField(max_length=255, verbose_name=_('VPN服务地址url'), blank=True, default='',
                                        help_text='http(s)://{hostname}:{port}/')
    vpn_api_version = models.CharField(max_length=64, blank=True, default='v3', verbose_name=_('VPN API版本'))
    vpn_username = models.CharField(max_length=128, verbose_name=_('用户名'), blank=True, default='',
                                    help_text=_('用于VPN服务认证的用户名'))
    vpn_password = models.CharField(max_length=255, verbose_name=_('密码'), blank=True, default='')
    service = models.OneToOneField(to=ServiceConfig, null=True, on_delete=models.SET_NULL, related_name='apply_service',
                                   blank=True, default=None, verbose_name=_('接入服务'),
                                   help_text=_('服务接入申请审批通过后生成的对应的接入服务'))
    deleted = models.BooleanField(verbose_name=_('删除'), default=False)

    contact_person = models.CharField(verbose_name=_('联系人'), max_length=128,
                                      blank=True, default='')
    contact_email = models.EmailField(verbose_name=_('联系人邮箱'), blank=True, default='')
    contact_telephone = models.CharField(verbose_name=_('联系人电话'), max_length=16,
                                         blank=True, default='')
    contact_fixed_phone = models.CharField(verbose_name=_('联系人固定电话'), max_length=16,
                                           blank=True, default='')
    contact_address = models.CharField(verbose_name=_('联系人地址'), max_length=256,
                                       blank=True, default='')
    logo_url = models.CharField(verbose_name=_('LOGO url'), max_length=256,
                                blank=True, default='')

    class Meta:
        db_table = 'vm_service_apply'
        ordering = ['-creation_time']
        verbose_name = _('VM服务单元接入申请')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'ApplyService(name={self.name})'

    def raw_password(self):
        """
        :return:
            str     # success
            None    # failed, invalid encrypted password
        """
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self.password)
        except encryptor.InvalidEncrypted as e:
            return None

    def set_password(self, raw_password: str):
        encryptor = get_encryptor()
        self.password = encryptor.encrypt(raw_password)

    def raw_vpn_password(self):
        """
        :return:
            str     # success
            None    # failed, invalid encrypted password
        """
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self.vpn_password)
        except encryptor.InvalidEncrypted as e:
            return None

    def set_vpn_password(self, raw_password: str):
        encryptor = get_encryptor()
        self.vpn_password = encryptor.encrypt(raw_password)

    def get_extra_params_string(self):
        params = {
            OpenStackParams.PROJECT_NAME: self.project_name,
            OpenStackParams.PROJECT_DOMAIN_NAME: self.project_domain_name,
            OpenStackParams.USER_DOMAIN_NAME: self.user_domain_name,
        }
        return json.dumps(params)

    def convert_to_service(self) -> ServiceConfig:
        """
        申请转为对应的ServiceConfig对象
        :return:
        """
        if not self.organization_id:
            raise errors.NoCenterBelongToError()

        service = ServiceConfig()
        service.data_center_id = self.organization_id
        service.name = self.name
        service.name_en = self.name_en
        service.region_id = self.region
        service.service_type = self.service_type
        service.cloud_type = self.cloud_type
        service.endpoint_url = self.endpoint_url
        service.api_version = self.api_version
        service.username = self.username
        service.set_password(self.raw_password())
        service.remarks = self.remarks
        service.need_vpn = self.need_vpn
        service.vpn_endpoint_url = self.vpn_endpoint_url
        service.vpn_api_version = self.vpn_api_version
        service.vpn_username = self.vpn_username
        service.set_vpn_password(self.raw_vpn_password())
        service.contact_person = self.contact_person
        service.contact_email = self.contact_email
        service.contact_telephone = self.contact_telephone
        service.contact_fixed_phone = self.contact_fixed_phone
        service.contact_address = self.contact_address
        service.logo_url = self.logo_url
        service.extra = self.get_extra_params_string()
        service.latitude = self.latitude
        service.longitude = self.longitude
        return service

    def do_pass_apply(self) -> ServiceConfig:
        service = self.convert_to_service()
        with transaction.atomic():
            service.save()
            service.users.add(self.user)        # 服务管理员
            self.status = self.Status.PASS
            self.service = service
            self.approve_time = timezone.now()
            self.save(update_fields=['status', 'service', 'approve_time'])

        return service


class ServerBase(models.Model):
    """
    云主机实例
    """
    TASK_CREATED_OK = 1
    TASK_IN_CREATING = 2
    TASK_CREATE_FAILED = 3
    CHOICES_TASK = (
        (TASK_CREATED_OK, _('创建成功')),
        (TASK_IN_CREATING, _('正在创建中')),
        (TASK_CREATE_FAILED, _('创建失败')),
    )

    QUOTA_PRIVATE = 1
    QUOTA_SHARED = 2
    CHOICES_QUOTA = (
        (QUOTA_PRIVATE, _('私有资源配额')),
        (QUOTA_SHARED, _('共享资源配额'))
    )

    class Classification(models.TextChoices):
        PERSONAL = 'personal', _('个人的')
        VO = 'vo', _('VO组的')

    class Situation(models.TextChoices):
        NORMAL = 'normal', _('正常')
        EXPIRED = 'expired', _('过期停机')
        ARREARAGE = 'arrearage', _('欠费停机')

    class SysType(models.TextChoices):
        WINDOWS = ImageSysType.WINDOWS, 'Windows'
        LINUX = ImageSysType.LINUX, 'Linux'
        UNIX = ImageSysType.UNIX, 'Unix'
        MACOS = ImageSysType.MACOS, 'MacOS'
        ANDROID = ImageSysType.ANDROID, 'Android'
        UNKNOWN = ImageSysType.UNKNOWN, 'Unknown'

    class SysRelease(models.TextChoices):
        WINDOWS_DESKTOP = ImageSysRelease.WINDOWS_DESKTOP, 'Windows Desktop'
        WINDOWS_SERVER = ImageSysRelease.WINDOWS_SERVER, 'Windows Server'
        UBUNTU = ImageSysRelease.UBUNTU, 'Ubuntu'
        FEDORA = ImageSysRelease.FEDORA, 'Fedora'
        CENTOS = ImageSysRelease.CENTOS, 'CentOS'
        DEEPIN = ImageSysRelease.DEEPIN, 'Deepin'
        DEBIAN = ImageSysRelease.DEBIAN, 'Debian'
        UNKNOWN = '', 'Unknown'

    class SysArch(models.TextChoices):
        X86_64 = ImageSysArch.X86_64, 'x86-64'
        I386 = ImageSysArch.I386, 'i386'
        ARM_64 = ImageSysArch.ARM_64, 'arm-64'
        UNKNOWN = '', 'Unknown'

    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')
    name = models.CharField(max_length=255, verbose_name=_('云主机实例名称'))
    instance_id = models.CharField(max_length=128, verbose_name=_('云主机实例ID'), help_text=_('各接入服务中云主机的ID'))
    instance_name = models.CharField(max_length=255, blank=True, default='', verbose_name=_('云主机实例名称'),
                                     help_text=_('各接入服务中云主机的名称'))
    vcpus = models.IntegerField(verbose_name=_('虚拟CPU数'), default=0)
    ram = models.IntegerField(verbose_name=_('内存GiB'), default=0)
    ipv4 = models.CharField(max_length=128, verbose_name='IPV4', default='')
    public_ip = models.BooleanField(default=True, verbose_name=_('公/私网'), help_text=_('选中为公网'))
    image = models.CharField(max_length=255, verbose_name=_('镜像系统名称'), default='')
    image_id = models.CharField(max_length=64, verbose_name=_('镜像系统ID'), default='')
    img_sys_type = models.CharField(max_length=32, verbose_name=_('镜像系统类型'), default='')
    img_sys_arch = models.CharField(max_length=32, verbose_name=_('镜像系统架构'), default='')
    img_release = models.CharField(max_length=32, verbose_name=_('镜像系统发行版'), default='')
    img_release_version = models.CharField(max_length=32, verbose_name=_('镜像系统发行版版本'), default='')
    image_desc = models.CharField(max_length=255, verbose_name=_('镜像系统描述'), blank=True, default='')
    default_user = models.CharField(max_length=64, verbose_name=_('默认登录用户名'), default='')
    default_password = models.CharField(max_length=255, blank=True, verbose_name=_('默认登录密码'), default='')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    remarks = models.CharField(max_length=255, blank=True, default='', verbose_name=_('备注'))
    task_status = models.SmallIntegerField(verbose_name=_('创建状态'), choices=CHOICES_TASK, default=TASK_CREATED_OK)
    center_quota = models.SmallIntegerField(verbose_name=_('服务配额'), choices=CHOICES_QUOTA, default=QUOTA_PRIVATE)
    expiration_time = models.DateTimeField(verbose_name=_('过期时间'), null=True, blank=True, default=None)
    classification = models.CharField(verbose_name=_('云主机归属类型'), max_length=16,
                                      choices=Classification.choices, default=Classification.PERSONAL,
                                      help_text=_('标识云主机属于申请者个人的，还是vo组的'))
    start_time = models.DateTimeField(verbose_name=_('计量开始时间'), default=timezone.now,
                                      help_text=_('云主机资源使用量计量开始时间'))
    pay_type = models.CharField(verbose_name=_('计费方式'), max_length=16, choices=PayType.choices,
                                default=PayType.POSTPAID)
    azone_id = models.CharField(verbose_name=_('宿主机组id/可用区'), max_length=36, blank=True, default='')
    disk_size = models.IntegerField(verbose_name=_('系统盘GB'), default=0)
    network_id = models.CharField(max_length=64, verbose_name=_('网络ID'), default='')
    situation = models.CharField(
        verbose_name=_('过期欠费管控情况'), max_length=16, choices=Situation.choices, default=Situation.NORMAL.value,
        help_text=_('过期欠费等状态下云主机的停机管控情况')
    )
    situation_time = models.DateTimeField(
        verbose_name=_('管控情况时间'), null=True, blank=True, default=None, help_text=_('过期欠费管控开始时间'))

    class Meta:
        abstract = True

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = short_uuid1_l25() + '-i'

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def do_delete(self):
        """
        :return: True or False
        """
        try:
            self.delete()
        except Exception as e:
            return False

        return True

    @property
    def ram_mib(self):
        return self.ram * 1024

    @ram_mib.setter
    def ram_mib(self, val: int):
        self.ram = math.ceil(val / 1024)

    @property
    def ram_gib(self):
        return self.ram

    @property
    def is_use_shared_quota(self):
        """是否使用的数据中心共享资源配额"""
        return self.center_quota == self.QUOTA_SHARED

    @property
    def is_use_private_quota(self):
        """是否使用的数据中心私有资源配额"""
        return self.center_quota == self.QUOTA_PRIVATE

    @property
    def raw_default_password(self):
        """
        :return:
            str     # success
            None    # failed, invalid encrypted password
        """
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self.default_password)
        except encryptor.InvalidEncrypted as e:
            return None

    @raw_default_password.setter
    def raw_default_password(self, raw_password: str):
        encryptor = get_encryptor()
        self.default_password = encryptor.encrypt(raw_password)

    def belong_to_vo(self):
        return self.classification == self.Classification.VO.value

    def set_situation_normal(self):
        if self.situation == self.Situation.NORMAL.value:
            return True

        self.situation = self.Situation.NORMAL.value
        try:
            self.save(update_fields=['situation'])
        except Exception as e:
            return False

        return True


class Server(ServerBase):
    """
    云主机实例
    """

    class Lock(models.TextChoices):
        FREE = 'free', _('无锁')
        DELETE = 'lock-delete', _('锁定删除')
        OPERATION = 'lock-operation', _('锁定所有操作，只允许读')

    service = models.ForeignKey(to=ServiceConfig, null=True, on_delete=models.SET_NULL, related_name='server_set',
                                verbose_name=_('接入的服务配置'))
    user = models.ForeignKey(to=User, verbose_name=_('创建者'), on_delete=models.SET_NULL, related_name='user_servers',
                             null=True)
    vo = models.ForeignKey(to=VirtualOrganization, null=True, on_delete=models.SET_NULL, default=None, blank=True,
                           related_name='vo_server_set', verbose_name=_('项目组'))
    lock = models.CharField(verbose_name=_('锁'), max_length=16, choices=Lock.choices, default=Lock.FREE,
                            help_text=_('加锁锁定云主机，防止误操作'))
    email_lasttime = models.DateTimeField(verbose_name=_('上次发送邮件时间'), null=True, blank=True, default=None,
                                          help_text=_('记录上次发邮件的时间，邮件通知用户配额即将到期'))

    class Meta:
        ordering = ['-creation_time']
        verbose_name = _('云主机')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'Server({self.id}, {self.ipv4})'

    def user_has_perms(self, user):
        """
        用户是否有访问此宿主机的权限

        :param user: 用户
        :return:
            True    # has
            False   # no
        """
        if not user.id:  # 未认证用户
            return False

        if user.is_superuser:
            return True

        if self.user_id == user.id:
            return True

        return False

    def do_archive(self, archive_user):
        """
        创建归档记录
        :return: True or False
        """
        if not self.id:
            return False

        try:
            with transaction.atomic():
                a = ServerArchive.init_archive_from_server(
                    server=self, archive_user=archive_user,
                    archive_type=ServerArchive.ArchiveType.ARCHIVE, commit=True
                )
                self.delete()
        except Exception as e:
            return False

        return True

    @staticmethod
    def count_private_quota_used(service):
        """
        接入服务的私有资源配额已用统计

        :param service: 接入服务配置对象
        :return:
            {
                'vcpu_used_count': 1,
                'ram_used_count': 80,
                'public_ip_count': 0,
                'private_ip_count': 1
            }
        """
        if not isinstance(service, models.Model):
            service_id = service
        else:
            service_id = service.id

        stat = Server.objects.filter(service=service_id, center_quota=Server.QUOTA_PRIVATE).aggregate(
            vcpu_used_count=Sum('vcpus'), ram_used_count=Sum('ram'),
            public_ip_count=Count('id', filter=Q(public_ip=True)),
            private_ip_count=Count('id', filter=Q(public_ip=False))
        )
        if stat.get('vcpu_used_count', 0) is None:
            stat['vcpu_used_count'] = 0

        if stat.get('ram_used_count', 0) is None:
            stat['ram_used_count'] = 0

        return stat

    @staticmethod
    def count_share_quota_used(service):
        """
        接入服务的分享资源配额已用统计

        :param service: 接入服务配置对象
        :return:
            {
                'vcpu_used_count': 1,
                'ram_used_count': 80,
                'public_ip_count': 0,
                'private_ip_count': 1
            }
        """
        if not isinstance(service, models.Model):
            service_id = service
        else:
            service_id = service.id

        stat = Server.objects.filter(service=service_id, center_quota=Server.QUOTA_SHARED).aggregate(
            vcpu_used_count=Sum('vcpus'), ram_used_count=Sum('ram'),
            public_ip_count=Count('id', filter=Q(public_ip=True)),
            private_ip_count=Count('id', filter=Q(public_ip=False))
        )
        if stat.get('vcpu_used_count', 0) is None:
            stat['vcpu_used_count'] = 0

        if stat.get('ram_used_count', 0) is None:
            stat['ram_used_count'] = 0

        return stat

    def is_locked_operation(self):
        """
        是否加锁, 锁定了一切操作
        :return:
            True        # locked
            False       # not locked
        """
        return self.lock == self.Lock.OPERATION

    def is_locked_delete(self):
        """
        检查是否加锁，是否锁定删除
        :return:
            True        # lock delete
            False       # not lock delete
        """
        return self.lock in [self.Lock.DELETE, self.Lock.OPERATION]


class ServerArchive(ServerBase):
    """
    云主机实例归档
    """

    class ArchiveType(models.TextChoices):
        ARCHIVE = 'archive', _('删除归档记录')
        REBUILD = 'rebuild', _('重建修改记录')
        POST2PRE = 'post2pre', _('按量付费转包年包月')
        # PRE2POST = 'pre2post', _('包年包月转按量付费')

    server_id = models.CharField(verbose_name=_('云主机ID'), max_length=36, blank=True, default='',
                                 help_text=_('归档云主机的ID'))
    service = models.ForeignKey(to=ServiceConfig, null=True, on_delete=models.SET_NULL,
                                related_name='server_archive_set', verbose_name=_('接入的服务配置'))
    user = models.ForeignKey(to=User, verbose_name=_('创建者'), on_delete=models.SET_NULL,
                             related_name='user_server_archives', null=True)
    vo = models.ForeignKey(to=VirtualOrganization, null=True, on_delete=models.SET_NULL, default=None, blank=True,
                           related_name='vo_server_archive_set', verbose_name=_('项目组'))
    deleted_time = models.DateTimeField(verbose_name=_('删除归档时间'))
    archive_user = models.ForeignKey(to=User, verbose_name=_('归档人'), on_delete=models.SET_NULL,
                                     related_name='+', blank=True, null=True, default=None)
    archive_type = models.CharField(
        verbose_name=_('归档记录类型'), max_length=16, choices=ArchiveType.choices, default=ArchiveType.ARCHIVE)

    class Meta:
        ordering = ['-deleted_time']
        verbose_name = _('云主机归档和变更日志')
        verbose_name_plural = verbose_name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = short_uuid1_l25()

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    @classmethod
    def init_archive_from_server(cls, server, archive_user, archive_type, archive_time=None, commit: bool = True):
        """
        创建归档记录
        :return:
            ServerArchive()

        :raises: Exception
        """
        if archive_type not in cls.ArchiveType.values:
            raise Exception(f'Invalid input archive_type')

        a = cls()
        a.server_id = server.id
        a.service = server.service
        a.name = server.name
        a.instance_id = server.instance_id
        a.instance_name = server.instance_name
        a.vcpus = server.vcpus
        a.ram = server.ram
        a.ipv4 = server.ipv4
        a.public_ip = server.public_ip
        a.image = server.image
        a.creation_time = server.creation_time
        a.remarks = server.remarks
        a.user_id = server.user_id
        a.vo_id = server.vo_id
        a.deleted_time = archive_time if archive_time else timezone.now()
        a.task_status = server.task_status
        a.center_quota = server.center_quota
        a.expiration_time = server.expiration_time
        a.classification = server.classification
        a.image_id = server.image_id
        a.image_desc = server.image_desc
        a.img_sys_type = server.img_sys_type
        a.img_sys_arch = server.img_sys_arch
        a.img_release = server.img_release
        a.img_release_version = server.img_release_version
        a.default_user = server.default_user
        a.default_password = server.default_password
        a.archive_user = archive_user
        a.start_time = server.start_time
        a.archive_type = archive_type
        a.pay_type = server.pay_type
        a.azone_id = server.azone_id
        a.disk_size = server.disk_size
        a.network_id = server.network_id
        a.situation = server.situation
        a.situation_time = server.situation_time

        if commit:
            a.save(force_insert=True)

        return a


class Flavor(models.Model):
    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')
    flavor_id = models.CharField(blank=True, max_length=256, verbose_name='服务端规格ID')
    vcpus = models.IntegerField(verbose_name=_('虚拟CPU数'), default=0)
    ram = models.IntegerField(verbose_name=_('内存GiB'), default=0)
    disk = models.IntegerField(verbose_name=_('硬盘GB'), default=0)
    desc = models.CharField(max_length=255, verbose_name=_('Tag描述'), blank=True, default='')
    enable = models.BooleanField(verbose_name=_('可用状态'), default=True)
    creation_time = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    service = models.ForeignKey(to=ServiceConfig, on_delete=models.SET_NULL, db_constraint=False,
                                related_name='+', null=True, blank=True, default=None, verbose_name=_('服务单元'))

    class Meta:
        db_table = 'flavor'
        ordering = ['vcpus']
        verbose_name = _('云主机配置样式')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'Flavor(vcpus={self.vcpus}, ram={self.ram_mib}Mb)'

    @property
    def ram_mib(self):
        return self.ram * 1024

    @property
    def ram_gib(self):
        return self.ram

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = short_uuid1_l25()

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class DiskBase(models.Model):
    """
    云硬盘实例
    """
    class TaskStatus(models.TextChoices):
        OK = 'ok', _('创建成功')
        CREATING = 'creating', _('正在创建中')
        FAILED = 'failed', _('创建失败')

    class QuotaType(models.TextChoices):
        PRIVATE = 'private', _('私有资源配额')
        SHARED = 'shared', _('共享资源配额')

    class Classification(models.TextChoices):
        PERSONAL = 'personal', _('个人的')
        VO = 'vo', _('VO组的')

    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')
    name = models.CharField(max_length=255, verbose_name=_('云硬盘名称'))
    instance_id = models.CharField(max_length=128, verbose_name=_('云硬盘实例ID'), help_text=_('各接入服务单元中云硬盘的ID'))
    instance_name = models.CharField(
        max_length=255, blank=True, default='', verbose_name=_('云硬盘实例名称'), help_text=_('各接入服务单元中云硬盘的名称'))
    size = models.IntegerField(verbose_name=_('容量大小GiB'), default=0)
    service = models.ForeignKey(
        verbose_name=_('服务单元'), to=ServiceConfig, null=True, on_delete=models.SET_NULL, related_name='+',
        db_constraint=False, db_index=False
    )
    azone_id = models.CharField(verbose_name=_('可用区Id'), max_length=36, blank=True, default='')
    azone_name = models.CharField(verbose_name=_('可用区名称'), max_length=36, blank=True, default='')
    quota_type = models.CharField(
        verbose_name=_('服务单元配额'), max_length=16, choices=QuotaType.choices, default=QuotaType.PRIVATE.value)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    remarks = models.CharField(max_length=255, blank=True, default='', verbose_name=_('备注'))
    task_status = models.CharField(
        verbose_name=_('创建状态'), max_length=16, choices=TaskStatus.choices, default=TaskStatus.OK.value)
    expiration_time = models.DateTimeField(verbose_name=_('过期时间'), null=True, blank=True, default=None)
    start_time = models.DateTimeField(
        verbose_name=_('计量开始时间'), default=timezone.now, help_text=_('云硬盘资源使用量计量开始时间'))
    pay_type = models.CharField(
        verbose_name=_('计费方式'), max_length=16, choices=PayType.choices, default=PayType.POSTPAID.value)
    classification = models.CharField(
        verbose_name=_('云硬盘归属类型'), max_length=16, choices=Classification.choices, default=Classification.PERSONAL,
        help_text=_('标识云硬盘属于申请者个人的，还是vo组的'))
    user = models.ForeignKey(
        to=User, verbose_name=_('创建者'), related_name='+', null=True, on_delete=models.SET_NULL,
        db_constraint=False, blank=True, default=None)
    vo = models.ForeignKey(
        verbose_name=_('项目组'), to=VirtualOrganization, related_name='+', null=True, on_delete=models.SET_NULL,
        db_constraint=False, blank=True, default=None)

    class Meta:
        abstract = True


class Disk(DiskBase):
    """
    云硬盘实例
    """
    class Lock(models.TextChoices):
        FREE = 'free', _('无锁')
        DELETE = 'lock-delete', _('锁定删除')
        OPERATION = 'lock-operation', _('锁定所有操作，只允许读')

    lock = models.CharField(verbose_name=_('锁'), max_length=16, choices=Lock.choices, default=Lock.FREE,
                            help_text=_('加锁锁定云硬盘，防止误操作'))
    email_lasttime = models.DateTimeField(verbose_name=_('上次发送邮件时间'), null=True, blank=True, default=None,
                                          help_text=_('记录上次发邮件的时间，邮件通知用户云硬盘即将到期'))
    server = models.ForeignKey(
        verbose_name=_('挂载于云主机'), to=Server, related_name='mounted_disk_set', on_delete=models.SET_NULL,
        db_constraint=False, db_index=False, null=True, blank=True, default=None)
    mountpoint = models.CharField(
        verbose_name=_('挂载点/设备名'), max_length=64, blank=True, default='', help_text='例如 "/dev/vdc"')
    attached_time = models.DateTimeField(verbose_name=_('最后一次挂载时间'), null=True, blank=True, default=None)
    detached_time = models.DateTimeField(verbose_name=_('最后一次卸载时间'), null=True, blank=True, default=None)
    deleted = models.BooleanField(verbose_name=_('删除状态'), default=False, help_text=_('选中表示已删除'))
    deleted_time = models.DateTimeField(verbose_name=_('删除时间'), null=True, blank=True, default=None)
    deleted_user = models.CharField(verbose_name=_('删除人'), max_length=128, default='')

    class Meta:
        db_table = 'servers_disk'
        ordering = ['-creation_time']
        verbose_name = _('云硬盘')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'Disk({self.id}, {self.size}GiB)'

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = short_uuid1_l25() + '-d'

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def do_soft_delete(self, deleted_user: str, raise_exception=True):
        """
        :return: True or False
        """
        try:
            self.deleted = True
            self.deleted_time = timezone.now()
            self.deleted_user = deleted_user
            self.save(update_fields=['deleted', 'deleted_time', 'deleted_user'])
        except Exception as e:
            if raise_exception:
                raise e

            return False

        return True

    def is_locked_operation(self):
        """
        是否加锁, 锁定了一切操作
        :return:
            True        # locked
            False       # not locked
        """
        return self.lock == self.Lock.OPERATION.value

    def is_locked_delete(self):
        """
        检查是否加锁，是否锁定删除
        :return:
            True        # lock delete
            False       # not lock delete
        """
        return self.lock in [self.Lock.DELETE.value, self.Lock.OPERATION.value]

    def set_attach(self, server_id: str):
        self.server_id = server_id
        self.attached_time = timezone.now()
        self.save(update_fields=['server_id', 'attached_time'])

    def set_detach(self):
        self.server_id = None
        self.detached_time = timezone.now()
        self.save(update_fields=['server_id', 'detached_time'])

    def is_attached(self):
        if self.server_id:
            return True

        return False

    @staticmethod
    def count_private_quota_used(service):
        """
        接入服务的私有资源配额已用统计

        :param service: 接入服务配置对象
        :return:
            {
                'disk_used_count': 1
            }
        """
        if not isinstance(service, models.Model):
            service_id = service
        else:
            service_id = service.id

        stat = Disk.objects.filter(
            service_id=service_id, deleted=False, quota_type=Disk.QuotaType.PRIVATE.value
        ).aggregate(disk_used_count=Sum('size'))

        if stat.get('disk_used_count', 0) is None:
            stat['disk_used_count'] = 0

        return stat

    def belong_to_vo(self):
        return self.classification == self.Classification.VO.value


class DiskChangeLog(DiskBase):
    """
    云硬盘变更日志
    """
    class LogType(models.TextChoices):
        EXPANSION = 'expansion', _('扩容')
        POST2PRE = 'post2pre', _('按量转包年包月')

    disk_id = models.CharField(verbose_name=_('云硬盘ID'), editable=False, max_length=36)
    log_type = models.CharField(verbose_name=_('变更类型'), max_length=16, choices=LogType.choices)
    change_time = models.DateTimeField(verbose_name=_('变更时间'))
    change_user = models.CharField(verbose_name=_('变更人'), max_length=128, default='')

    class Meta:
        db_table = 'disk_change_log'
        ordering = ['-change_time']
        verbose_name = _('云硬盘变更日志')
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=('disk_id',), name='idx_disk_id')
        ]

    def __str__(self):
        return f'DiskChangeLog({self.get_log_type_display()})'

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.id:
            self.id = short_uuid1_l25()

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    @classmethod
    def add_change_log_for_disk(cls, disk: Disk, log_type: str, change_time, change_user: str, save_db: bool):
        if log_type not in cls.LogType.values:
            raise Exception(f'Invalid input disk change log type')

        ins = cls()
        ins.log_type = log_type
        ins.change_time = change_time
        ins.change_user = change_user
        ins.disk_id = disk.id
        ins.name = disk.name
        ins.instance_id = disk.instance_id
        ins.instance_name = disk.instance_name
        ins.size = disk.size
        ins.service_id = disk.service_id
        ins.azone_id = disk.azone_id
        ins.azone_name = disk.azone_name
        ins.quota_type = disk.quota_type
        ins.creation_time = disk.creation_time
        ins.remarks = disk.remarks
        ins.task_status = disk.task_status
        ins.expiration_time = disk.expiration_time
        ins.start_time = disk.start_time
        ins.pay_type = disk.pay_type
        ins.classification = disk.classification
        ins.user_id = disk.user_id
        ins.vo_id = disk.vo_id

        if save_db:
            ins.save(force_insert=True)

        return ins


class ResourceActionLog(UuidModel):
    class ResourceType(models.TextChoices):
        SERVER = 'server', _('云主机')
        DISK = 'disk', _('云硬盘')
        BUCHET = 'bucket', _('存储桶')

    class ActionFlag(models.TextChoices):
        ADDITION = 'add', _('添加')
        CHANGE = 'change', _('修改')
        DELETION = 'delete', _('删除')

    action_time = models.DateTimeField(verbose_name=_('操作时间'), editable=False)
    user_id = models.CharField(verbose_name=_('操作者id'), max_length=36)
    username = models.CharField(verbose_name=_('操作者'), max_length=150)
    action_flag = models.CharField(verbose_name=_('操作类型'), max_length=16, choices=ActionFlag.choices)
    resource_type = models.CharField(verbose_name=_('资源类型'), max_length=16, choices=ResourceType.choices)
    resource_id = models.TextField(_('资源id'), blank=True, null=True)
    resource_repr = models.CharField(_('资源描述'), max_length=200)
    resource_message = models.JSONField(_('资源信息'), blank=True)
    owner_id = models.CharField(verbose_name=_('资源拥有者id'), max_length=32)
    owner_name = models.CharField(verbose_name=_('资源拥有者'), max_length=128)
    owner_type = models.CharField(verbose_name=_('资源拥有者类型'), max_length=16, choices=OwnerType.choices)

    class Meta:
        verbose_name = _('资源操作日志')
        verbose_name_plural = verbose_name
        db_table = 'resource_action_log'
        ordering = ['-action_time']

    def __repr__(self):
        return str(self.action_time)

    def __str__(self):
        if self.is_addition():
            return _('创建 “%(object)s”') % {'object': self.resource_repr}
        elif self.is_change():
            return _('修改 “%(object)s”') % {'object': self.resource_repr}
        elif self.is_deletion():
            return _('删除 “%(object)s”') % {'object': self.resource_repr}

        return _('资源操作日志')

    def is_addition(self):
        return self.action_flag == self.ActionFlag.ADDITION.value

    def is_change(self):
        return self.action_flag == self.ActionFlag.CHANGE.value

    def is_deletion(self):
        return self.action_flag == self.ActionFlag.DELETION.value
