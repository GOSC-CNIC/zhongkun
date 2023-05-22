import json

from django.db import models
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from utils.model import UuidModel, get_encryptor
from utils.validators import json_string_validator
from core import errors
from vo.models import VirtualOrganization
from adapters.params import OpenStackParams
from users.models import UserProfile as User
from bill.models import PayAppService


app_name = 'service'


class DataCenter(UuidModel):
    STATUS_ENABLE = 1
    STATUS_DISABLE = 2
    CHOICE_STATUS = (
        (STATUS_ENABLE, _('开启状态')),
        (STATUS_DISABLE, _('关闭状态'))
    )

    name = models.CharField(verbose_name=_('名称'), max_length=255)
    name_en = models.CharField(verbose_name=_('英文名称'), max_length=255, default='')
    abbreviation = models.CharField(verbose_name=_('简称'), max_length=64, default='')
    independent_legal_person = models.BooleanField(verbose_name=_('是否独立法人单位'), default=True)
    country = models.CharField(verbose_name=_('国家/地区'), max_length=128, default='')
    city = models.CharField(verbose_name=_('城市'), max_length=128, default='')
    postal_code = models.CharField(verbose_name=_('邮政编码'), max_length=32, default='')
    address = models.CharField(verbose_name=_('单位地址'), max_length=256, default='')

    endpoint_vms = models.CharField(max_length=255, verbose_name=_('云主机服务地址url'),
                                    null=True, blank=True, default=None, help_text='http(s)://{hostname}:{port}/')
    endpoint_object = models.CharField(max_length=255, verbose_name=_('存储服务地址url'),
                                       null=True, blank=True, default=None, help_text='http(s)://{hostname}:{port}/')
    endpoint_compute = models.CharField(max_length=255, verbose_name=_('计算服务地址url'),
                                        null=True, blank=True, default=None, help_text='http(s)://{hostname}:{port}/')
    endpoint_monitor = models.CharField(max_length=255, verbose_name=_('检测报警服务地址url'),
                                        null=True, blank=True, default=None, help_text='http(s)://{hostname}:{port}/')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), null=True, blank=True, default=None)
    status = models.SmallIntegerField(verbose_name=_('服务状态'), choices=CHOICE_STATUS, default=STATUS_ENABLE)
    desc = models.CharField(verbose_name=_('描述'), blank=True, max_length=255)

    logo_url = models.CharField(verbose_name=_('LOGO url'), max_length=256,
                                blank=True, default='')
    certification_url = models.CharField(verbose_name=_('机构认证代码url'), max_length=256,
                                         blank=True, default='')
    longitude = models.FloatField(verbose_name=_('经度'), blank=True, default=0)
    latitude = models.FloatField(verbose_name=_('纬度'), blank=True, default=0)
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))

    class Meta:
        ordering = ['sort_weight']
        verbose_name = _('机构')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


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

    data_center = models.ForeignKey(to=DataCenter, null=True, on_delete=models.SET_NULL,
                                    related_name='service_set', verbose_name=_('数据中心'))
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
    need_vpn = models.BooleanField(verbose_name=_('是否需要VPN'), default=True)
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
        verbose_name=_('余额结算APP服务ID'), max_length=36, default='',
        help_text=_('此服务对应的APP服务（注册在余额结算中的APP服务）id，扣费时需要此id，用于指定哪个服务发生的扣费'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))

    class Meta:
        ordering = ['sort_weight']
        verbose_name = _('云主机服务单元接入配置')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super().save(force_insert=force_insert, force_update=force_update,
                     using=using, update_fields=update_fields)
        self._sync_name_to_pay_app_service()

    def _sync_name_to_pay_app_service(self):
        """
        当name修改时，同步变更到 对应的钱包的pay app service
        """
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

                if update_fields:
                    app_service.save(update_fields=update_fields)
        except Exception as exc:
            pass

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
        if not user or not user.id:
            return False

        return self.users.filter(id=user.id).exists()

    def extra_params(self) -> dict:
        if self.extra:
            return json.loads(self.extra)

        return {}


class ServiceQuotaBase(UuidModel):
    """
    数据中心接入服务的资源配额基类
    """
    private_ip_total = models.IntegerField(verbose_name=_('总私网IP数'), default=0)
    private_ip_used = models.IntegerField(verbose_name=_('已用私网IP数'), default=0)
    public_ip_total = models.IntegerField(verbose_name=_('总公网IP数'), default=0)
    public_ip_used = models.IntegerField(verbose_name=_('已用公网IP数'), default=0)
    vcpu_total = models.IntegerField(verbose_name=_('总CPU核数'), default=0)
    vcpu_used = models.IntegerField(verbose_name=_('已用CPU核数'), default=0)
    ram_total = models.IntegerField(verbose_name=_('总内存大小(GB)'), default=0)
    ram_used = models.IntegerField(verbose_name=_('已用内存大小(GB)'), default=0)
    disk_size_total = models.IntegerField(verbose_name=_('总硬盘大小(GB)'), default=0)
    disk_size_used = models.IntegerField(verbose_name=_('已用硬盘大小(GB)'), default=0)
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


class ApplyOrganization(UuidModel):
    """
    数据中心/机构申请
    """
    class Status(models.TextChoices):
        WAIT = 'wait', '待审批'
        CANCEL = 'cancel', _('取消申请')
        PENDING = 'pending', '审批中'
        REJECT = 'reject', '拒绝'
        PASS = 'pass', '通过'

    name = models.CharField(verbose_name=_('名称'), max_length=255)
    name_en = models.CharField(verbose_name=_('英文名称'), max_length=255, default='')
    abbreviation = models.CharField(verbose_name=_('简称'), max_length=64, default='')
    independent_legal_person = models.BooleanField(verbose_name=_('是否独立法人单位'), default=True)
    country = models.CharField(verbose_name=_('国家/地区'), max_length=128, default='')
    city = models.CharField(verbose_name=_('城市'), max_length=128, default='')
    postal_code = models.CharField(verbose_name=_('邮政编码'), max_length=32, default='')
    address = models.CharField(verbose_name=_('单位地址'), max_length=256, default='')

    endpoint_vms = models.CharField(max_length=255, verbose_name=_('云主机服务地址url'),
                                    null=True, blank=True, default=None, help_text='http(s)://{hostname}:{port}/')
    endpoint_object = models.CharField(max_length=255, verbose_name=_('存储服务地址url'),
                                       null=True, blank=True, default=None, help_text='http(s)://{hostname}:{port}/')
    endpoint_compute = models.CharField(max_length=255, verbose_name=_('计算服务地址url'),
                                        null=True, blank=True, default=None, help_text='http(s)://{hostname}:{port}/')
    endpoint_monitor = models.CharField(max_length=255, verbose_name=_('检测报警服务地址url'),
                                        null=True, blank=True, default=None, help_text='http(s)://{hostname}:{port}/')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), null=True, blank=True, auto_now_add=True)
    status = models.CharField(verbose_name=_('状态'), max_length=16,
                              choices=Status.choices, default=Status.WAIT)
    desc = models.CharField(verbose_name=_('描述'), blank=True, max_length=255)
    data_center = models.OneToOneField(to=DataCenter, null=True, on_delete=models.SET_NULL,
                                       related_name='apply_data_center', blank=True,
                                       default=None, verbose_name=_('机构'),
                                       help_text=_('机构加入申请审批通过后对应的机构'))

    logo_url = models.CharField(verbose_name=_('LOGO url'), max_length=256,
                                blank=True, default='')
    certification_url = models.CharField(verbose_name=_('机构认证代码url'), max_length=256,
                                         blank=True, default='')

    user = models.ForeignKey(verbose_name=_('申请用户'), to=User, null=True, on_delete=models.SET_NULL)
    deleted = models.BooleanField(verbose_name=_('删除'), default=False)
    longitude = models.FloatField(verbose_name=_('经度'), blank=True, default=0)
    latitude = models.FloatField(verbose_name=_('纬度'), blank=True, default=0)

    class Meta:
        db_table = 'organization_apply'
        ordering = ['creation_time']
        verbose_name = _('机构加入申请')
        verbose_name_plural = verbose_name

    def is_pass(self):
        return self.status == self.Status.PASS

    def __str__(self):
        return self.name

    def do_pass_apply(self) -> DataCenter:
        organization = DataCenter()
        organization.name = self.name
        organization.name_en = self.name_en
        organization.abbreviation = self.abbreviation
        organization.independent_legal_person = self.independent_legal_person
        organization.country = self.country
        organization.city = self.city
        organization.postal_code = self.postal_code
        organization.address = self.address
        organization.endpoint_vms = self.endpoint_vms
        organization.endpoint_object = self.endpoint_object
        organization.endpoint_compute = self.endpoint_compute
        organization.endpoint_monitor = self.endpoint_monitor
        organization.desc = self.desc
        organization.logo_url = self.logo_url
        organization.certification_url = self.certification_url
        organization.longitude = self.longitude
        organization.latitude = self.latitude

        with transaction.atomic():
            organization.save()
            self.status = self.Status.PASS
            self.data_center = organization
            self.save(update_fields=['status', 'data_center'])

        return organization


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
