import json

from django.db import models
from django.db import transaction
from django.conf import settings
from django.utils.translation import gettext, gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError

from utils.model import UuidModel, get_encryptor
from utils.validators import json_string_validator, http_url_validator
from core import errors
from vo.models import VirtualOrganization
from adapters.params import OpenStackParams
from users.models import UserProfile as User


app_name = 'service'


class Contacts(UuidModel):
    """机构联系人"""
    name = models.CharField(verbose_name=_('姓名'), max_length=128)
    telephone = models.CharField(verbose_name=_('电话'), max_length=11, default='')
    email = models.EmailField(_('邮箱地址'), blank=True, default='')
    address = models.CharField(verbose_name=_('联系地址'), max_length=255, help_text=_('详细的联系地址'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))
    remarks = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))

    class Meta:
        ordering = ('-creation_time',)
        db_table = 'contacts'
        verbose_name = _('机构联系人')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'[ {self.name} ] Phone: {self.telephone}, Email: {self.email}, Address: {self.address}'


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
    independent_legal_person = models.BooleanField(verbose_name=_('独立法人单位'), default=True)
    country = models.CharField(verbose_name=_('国家/地区'), max_length=128, default='')
    province = models.CharField(verbose_name=_('省份'), max_length=128, default='')
    city = models.CharField(verbose_name=_('城市'), max_length=128, default='')
    postal_code = models.CharField(verbose_name=_('邮政编码'), max_length=32, default='')
    address = models.CharField(verbose_name=_('单位地址'), max_length=256, default='')
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
    contacts = models.ManyToManyField(
        verbose_name=_('机构联系人'), to=Contacts, related_name='+', db_table='data_center_contacts',
        db_constraint=False, blank=True
    )

    class Meta:
        ordering = ['sort_weight']
        verbose_name = _('机构')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.creation_time:
            self.creation_time = timezone.now()
            if update_fields and 'creation_time' not in update_fields:
                update_fields.append('creation_time')

        super(DataCenter, self).save(
            force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)


class OrgDataCenter(UuidModel):
    """机构下的数据中心"""
    name = models.CharField(verbose_name=_('名称'), max_length=255)
    name_en = models.CharField(verbose_name=_('英文名称'), max_length=255, default='')
    organization = models.ForeignKey(
        to=DataCenter, verbose_name=_('机构'), on_delete=models.SET_NULL, null=True, blank=False, db_constraint=False)
    users = models.ManyToManyField(
        to=User, verbose_name=_('管理员'), blank=True, related_name='+', db_table='org_data_center_users',
        db_constraint=False)
    longitude = models.FloatField(verbose_name=_('经度'), blank=True, default=0)
    latitude = models.FloatField(verbose_name=_('纬度'), blank=True, default=0)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))
    remark = models.TextField(verbose_name=_('数据中心备注'), max_length=10000, blank=True, default='')

    # 指标数据服务
    thanos_endpoint_url = models.CharField(
        verbose_name=_('指标监控系统查询接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    thanos_username = models.CharField(
        max_length=128, verbose_name=_('指标监控系统认证用户名'), blank=True, default='', help_text=_('用于此服务认证的用户名'))
    thanos_password = models.CharField(max_length=255, verbose_name=_('指标监控系统认证密码'), blank=True, default='')
    thanos_receive_url = models.CharField(
        verbose_name=_('指标监控系统接收接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    thanos_remark = models.CharField(verbose_name=_('指标监控系统备注'), max_length=255, blank=True, default='')
    metric_monitor_url = models.CharField(
        verbose_name=_('指标监控系统监控网址'), max_length=255, blank=True, default='',
        help_text=_('如果填写有效网址会自动创建对应的站点监控任务，格式为 http(s)://example.cn/'))
    metric_task_id = models.CharField(
        verbose_name=_('指标监控系统监控任务ID'), max_length=36, blank=True, default='', editable=False,
        help_text=_('记录为指标监控系统监控地址创建的站点监控任务的ID'))

    # 日志服务
    loki_endpoint_url = models.CharField(
        verbose_name=_('日志聚合系统查询接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    loki_username = models.CharField(
        max_length=128, verbose_name=_('日志聚合系统认证用户名'), blank=True, default='', help_text=_('用于此服务认证的用户名'))
    loki_password = models.CharField(max_length=255, verbose_name=_('日志聚合系统认证密码'), blank=True, default='')
    loki_receive_url = models.CharField(
        verbose_name=_('日志聚合系统接收接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    loki_remark = models.CharField(verbose_name=_('日志聚合系统备注'), max_length=255, blank=True, default='')
    log_monitor_url = models.CharField(
        verbose_name=_('日志聚合系统监控网址'), max_length=255, blank=True, default='',
        help_text=_('如果填写有效网址会自动创建对应的站点监控任务，格式为 http(s)://example.cn/'))
    log_task_id = models.CharField(
        verbose_name=_('日志聚合系统监控任务ID'), max_length=36, blank=True, default='', editable=False,
        help_text=_('记录为日志聚合系统监控网址创建的站点监控任务的ID'))

    class Meta:
        db_table = 'org_data_center'
        ordering = ['sort_weight']
        verbose_name = _('机构数据中心')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def clean(self):
        if self.thanos_endpoint_url:
            try:
                http_url_validator(self.thanos_endpoint_url)
            except ValidationError:
                raise ValidationError(message={'thanos_endpoint_url': gettext('不是一个有效的网址')})

        if self.metric_monitor_url:
            try:
                http_url_validator(self.metric_monitor_url)
            except ValidationError:
                raise ValidationError(message={'metric_monitor_url': gettext('不是一个有效的网址')})

        if self.loki_endpoint_url:
            try:
                http_url_validator(self.loki_endpoint_url)
            except ValidationError:
                raise ValidationError(message={'loki_endpoint_url': gettext('不是一个有效的网址')})

        if self.log_monitor_url:
            try:
                http_url_validator(self.log_monitor_url)
            except ValidationError:
                raise ValidationError(message={'log_monitor_url': gettext('不是一个有效的网址')})

    @property
    def raw_thanos_password(self):
        """
        :return:
            str     # success
            None    # failed, invalid encrypted password
        """
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self.thanos_password)
        except encryptor.InvalidEncrypted as e:
            return None

    @raw_thanos_password.setter
    def raw_thanos_password(self, raw_password: str):
        encryptor = get_encryptor()
        self.thanos_password = encryptor.encrypt(raw_password)

    @property
    def raw_loki_password(self):
        """
        :return:
            str     # success
            None    # failed, invalid encrypted password
        """
        encryptor = get_encryptor()
        try:
            return encryptor.decrypt(self.loki_password)
        except encryptor.InvalidEncrypted as e:
            return None

    @raw_loki_password.setter
    def raw_loki_password(self, raw_password: str):
        encryptor = get_encryptor()
        self.loki_password = encryptor.encrypt(raw_password)


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

    def sync_to_pay_app_service(self):
        """
        当name修改时，同步变更到 对应的钱包的pay app service
        """
        from bill.models import PayAppService
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
        from bill.models import PayAppService

        payment_balance = getattr(settings, 'PAYMENT_BALANCE', {})
        app_id = payment_balance.get('app_id', None)

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
        from bill.models import PayAppService

        app_service = PayAppService.objects.filter(id=pay_app_service_id).first()
        if app_service is None:
            raise ValidationError(message={
                'pay_app_service_id': '结算服务单元不存在，请仔细确认。如果是新建服务单元不需要手动填写结算服务单元id，'
                                      '保持为空，保存后会自动注册对应的结算单元，并填充此字段'})

        return app_service

    def clean(self):
        from adapters.client import get_adapter_params_for_service, UnsupportedServiceType

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
        from monitor.managers import MonitorWebsiteManager

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
        from monitor.managers import MonitorWebsiteManager

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
        from monitor.managers import MonitorWebsiteManager

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
