from django.db import models, transaction
from django.conf import settings
from django.utils.translation import gettext, gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from core import site_configs_manager
from utils.model import UuidModel, get_encryptor
from utils.validators import http_url_validator
from apps.app_wallet.models import PayAppService
from apps.service.models import DataCenter, OrgDataCenter


User = get_user_model()


class ObjectsService(UuidModel):
    """
    对象存储接入服务配置
    """
    class ServiceType(models.TextChoices):
        IHARBOR = 'iharbor', 'iHarbor'
        SWIFT = 'swift', 'Swift'
        S3 = 's3', 'S3'

    class Status(models.TextChoices):
        ENABLE = 'enable', _('服务中')
        DISABLE = 'disable', _('停止服务')
        DELETED = 'deleted', _('删除')

    org_data_center = models.ForeignKey(
        to=OrgDataCenter, null=True, on_delete=models.SET_NULL, related_name='+', verbose_name=_('数据中心'),
        db_constraint=False)
    name = models.CharField(max_length=255, verbose_name=_('服务名称'))
    name_en = models.CharField(verbose_name=_('服务英文名称'), max_length=255, default='')
    service_type = models.CharField(max_length=16, choices=ServiceType.choices, default=ServiceType.IHARBOR.value,
                                    verbose_name=_('服务平台类型'))
    endpoint_url = models.CharField(max_length=255, verbose_name=_('服务地址url'),
                                    help_text='http(s)://{hostname}:{port}/')
    api_version = models.CharField(max_length=64, default='v1', verbose_name=_('API版本'),
                                   help_text=_('预留，主要iHarbor使用'))
    username = models.CharField(max_length=128, verbose_name=_('用户名'), help_text=_('用于此服务认证的用户名'))
    password = models.CharField(max_length=128, verbose_name=_('密码'))
    add_time = models.DateTimeField(auto_now_add=True, verbose_name=_('添加时间'))
    status = models.CharField(max_length=16, verbose_name=_('服务状态'), choices=Status.choices,
                              default=Status.ENABLE.value)
    remarks = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))
    extra = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('其他配置'), help_text=_('json格式'))
    users = models.ManyToManyField(to=User, verbose_name=_('用户'), blank=True, related_name='object_service_set')

    provide_ftp = models.BooleanField(verbose_name=_('是否提供FTP服务'), default=True)
    ftp_domains = models.CharField(max_length=1024, blank=True, default='', verbose_name=_('FTP服务域名或IP'),
                                   help_text=_('多个域名时以,分割'))
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
        verbose_name=_('余额结算服务单元ID'), max_length=36, blank=True, default='',
        help_text=_('此服务单元对应的钱包结算服务单元（注册在余额结算中的APP服务）id，扣费时需要此id，用于指定哪个服务发生的扣费；'
                    '正常情况下此内容会自动填充，不需要手动输入'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))
    monitor_task_id = models.CharField(
        verbose_name=_('服务单元对应监控任务ID'), max_length=36, blank=True, default='', editable=False,
        help_text=_('记录为服务单元创建的站点监控任务的ID'))
    version = models.CharField(max_length=32, blank=True, default='', verbose_name=_('版本号'), help_text=_('服务当前的版本'))
    version_update_time = models.DateTimeField(verbose_name=_('版本号更新时间'), null=True, blank=True, default=None)

    class Meta:
        db_table = 'object_service'
        ordering = ['sort_weight']
        verbose_name = _('对象存储服务单元接入配置')
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
        app_service = PayAppService.objects.filter(id=pay_app_service_id).first()
        if app_service is None:
            raise ValidationError(message={
                'pay_app_service_id': gettext('结算服务单元不存在，请仔细确认。如果是新建服务单元不需要手动填写结算服务单元id，'
                                              '保持为空，保存后会自动注册对应的结算单元，并填充此字段')})

        return app_service

    def clean(self):
        # 网址验证
        try:
            http_url_validator(self.endpoint_url)
        except ValidationError:
            raise ValidationError(message={'endpoint_url': gettext('不是一个有效的网址')})

        if self.pay_app_service_id and self.status == self.Status.ENABLE.value:
            self.check_pay_app_service_id(self.pay_app_service_id)

    @property
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

    def ftp_domains_list(self):
        return self.ftp_domains.split(',')

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
                        task.remark = gettext('自动为对象存储服务单元“%s”创建的监控任务') % self.name
                        MonitorWebsiteManager.do_change_website_task(
                            user_website=task, new_scheme=scheme, new_hostname=hostname, new_uri=uri,
                            new_tamper_resistant=False)
                        act = 'change'
                    elif task.odc_id != self.org_data_center_id:
                        task.odc_id = self.org_data_center_id
                        update_fields = ['odc_id']
                        if task.name != self.name:
                            task.name = self.name
                            task.remark = gettext('自动为对象存储服务单元“%s”创建的监控任务') % self.name
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
                remark=gettext('自动为对象存储服务单元“%s”创建的监控任务') % self.name,
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


class BucketBase(UuidModel):

    class TaskStatus(models.TextChoices):
        SUCCESS = 'created', _('创建成功')
        CREATING = 'creating', _('正在创建中')
        FAILED = 'failed', _('创建失败')

    class Situation(models.TextChoices):
        NORMAL = 'normal', _('正常')
        ARREARAGE = 'arrearage', _('欠费')
        ARREARS_LOCK = 'arrears-lock', _('欠费锁定读写')
        LOCK = 'lock', _('锁定读写')
        LOCK_WRITE = 'lock-write', _('锁定写(只读)')

    class Tags(models.TextChoices):
        NONE = '', _('无')
        SPECIAL = 'special', _('专项')

    bucket_id = models.CharField(max_length=36, verbose_name=_('存储桶ID'), help_text=_('存储桶在对象存储服务单元中的id'))
    name = models.CharField(max_length=63, verbose_name=_('存储桶名称'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    task_status = models.CharField(
        verbose_name=_('创建状态'), max_length=16, choices=TaskStatus.choices, default=TaskStatus.SUCCESS.value)
    situation = models.CharField(
        verbose_name=_('过期欠费管控情况'), max_length=16, choices=Situation.choices, default=Situation.NORMAL.value,
        help_text=_('欠费状态下存储桶读写锁定管控情况')
    )
    situation_time = models.DateTimeField(
        verbose_name=_('管控情况时间'), null=True, blank=True, default=None, help_text=_('欠费管控开始时间'))
    storage_size = models.BigIntegerField(verbose_name=_('桶存储容量'), blank=True, default=0)
    object_count = models.IntegerField(verbose_name=_('桶对象数量'), blank=True, default=0)
    stats_time = models.DateTimeField(verbose_name=_('桶资源统计时间'), null=True, blank=True, default=None)
    tag = models.CharField(
        verbose_name=_('标签'), max_length=32, choices=Tags.choices, blank=True, default=Tags.NONE.value)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def set_situation(self, status: str):
        self.situation = status
        self.situation_time = timezone.now()
        self.save(update_fields=['situation', 'situation_time'])


class Bucket(BucketBase):
    user = models.ForeignKey(to=User, null=True, related_name='+', on_delete=models.SET_NULL,
                             verbose_name=_('所属用户'))
    service = models.ForeignKey(to=ObjectsService, related_name='+', null=True,
                                on_delete=models.SET_NULL, verbose_name=_('服务单元'))

    class Meta:
        db_table = 'bucket'
        ordering = ['-creation_time']
        verbose_name = _('存储桶')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def do_archive(self, archiver: str, raise_exception: bool = False):
        """
        删除归档存储桶
        """
        arc = BucketArchive()
        arc.original_id = self.id
        arc.bucket_id = self.bucket_id
        arc.name = self.name
        arc.creation_time = self.creation_time
        arc.user_id = self.user_id
        arc.service_id = self.service_id
        arc.archiver = archiver
        arc.task_status = self.task_status
        arc.situation = self.situation
        arc.situation_time = self.situation_time
        arc.storage_size = self.storage_size
        arc.object_count = self.object_count
        arc.stats_time = self.stats_time
        arc.tag = self.tag

        try:
            with transaction.atomic():
                arc.save(force_insert=True)
                self.delete()
        except Exception as e:
            if raise_exception:
                raise e

            return False

        return True


class BucketArchive(BucketBase):
    original_id = models.CharField(max_length=36, verbose_name=_('存储桶删除前原始id'), default='',
                                   help_text=_('存储桶删除前在存储桶表中原始id'))
    user = models.ForeignKey(to=User, null=True, related_name='+', on_delete=models.SET_NULL,
                             verbose_name=_('所属用户'))
    service = models.ForeignKey(to=ObjectsService, null=True, related_name='+',
                                on_delete=models.SET_NULL, verbose_name=_('服务单元'))
    delete_time = models.DateTimeField(auto_now_add=True, verbose_name=_('删除时间'))
    archiver = models.CharField(verbose_name=_('删除归档人'), max_length=128, blank=True, default='')

    class Meta:
        db_table = 'bucket_archive'
        ordering = ['-delete_time']
        verbose_name = _('存储桶归档记录')
        verbose_name_plural = verbose_name
