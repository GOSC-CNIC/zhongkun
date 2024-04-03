from django.db import models
from django.db import transaction
from django.utils.translation import gettext, gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings
from django.contrib.auth import get_user_model

from utils.model import UuidModel
from core import errors
from core import site_configs_manager

User = get_user_model()


class VtScanService(UuidModel):
    """
    安全扫描接入服务配置
    """
    class Status(models.TextChoices):
        ENABLE = 'enable', _('服务中')
        DISABLE = 'disable', _('停止服务')
        DELETED = 'deleted', _('删除')

    name = models.CharField(max_length=255, verbose_name=_('服务名称'))
    name_en = models.CharField(verbose_name=_('服务英文名称'), max_length=255, default='')
    status = models.CharField(verbose_name=_('服务状态'), max_length=32, choices=Status.choices, default=Status.ENABLE)
    remark = models.CharField(max_length=255, default='', blank=True, verbose_name=_('备注'))
    pay_app_service_id = models.CharField(
        verbose_name=_('余额结算APP服务ID'), max_length=36, blank=True, default='',
        help_text=_('此服务对应的APP结算服务单元（注册在余额结算中的APP服务）id，扣费时需要此id，用于指定哪个服务发生的扣费；'
                    '正常情况下此内容会自动填充，不需要手动输入'))
    add_time = models.DateTimeField(auto_now_add=True, verbose_name=_('添加时间'))
    
    class Meta:
        ordering = ['-add_time']
        verbose_name = _('服务配置')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.name} [{self.get_status_display()}]'
    
    @classmethod
    def get_instance(cls):
        inst = cls.objects.order_by('-add_time').first()
        if inst is None:
            raise errors.NotFound(message=gettext('安全扫描服务配置信息不存在。'))

        return inst

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

        app_id = site_configs_manager.get_pay_app_id(dj_settings=settings)

        if self.pay_app_service_id:
            app_service = self.check_pay_app_service_id(self.pay_app_service_id)
            return app_service

        # 新注册
        with transaction.atomic():
            app_service = PayAppService(
                name=self.name, name_en=self.name_en, app_id=app_id, orgnazition_id=None,
                resources=gettext('安全扫描'), status=PayAppService.Status.NORMAL.value,
                category=PayAppService.Category.SCAN.value, service_id=self.id,
                longitude=0, latitude=0,
                contact_person='', contact_telephone='',
                contact_email='', contact_address='',
                contact_fixed_phone=''
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
                'pay_app_service_id': gettext(
                    '结算服务单元不存在，请仔细确认。如果是新建服务单元不需要手动填写结算服务单元id，'
                    '保持为空，保存后会自动注册对应的结算单元，并填充此字段')})

        return app_service

    def clean(self):
        if self.pay_app_service_id:
            self.check_pay_app_service_id(self.pay_app_service_id)

        qs = VtScanService.objects.all()
        if self.id:
            qs = qs.exclude(id=self.id)

        if qs.count() >= 1:
            raise ValidationError(message=gettext('已存在安全扫描服务配置记录，只能创建一个服务配置记录'))
    
    
class VtScanner(UuidModel):

    class ScannerType(models.TextChoices):
        WEB = 'web', _('站点扫描器')
        HOST = 'host', _('主机扫描器')
    
    class Status(models.TextChoices):
        ENABLE = 'enable', _('服务中')
        DISABLE = 'disable', _('停止服务')
        DELETED = 'deleted', _('删除')
    
    class ScannerEngine(models.TextChoices):
        ZAP = 'zaproxy', _('ZAP')
        GVM = 'gvm', _('GVM')
    
    name = models.CharField(verbose_name=_('漏扫节点名称'), max_length=255, unique=True)
    type = models.CharField(verbose_name=_('漏扫节点类型'), max_length=16, choices=ScannerType.choices)
    engine = models.CharField(verbose_name=_('漏扫引擎类型'), max_length=16, choices=ScannerEngine.choices)
    ipaddr = models.CharField(verbose_name=_('漏扫节点地址'), max_length=16)
    port = models.IntegerField(verbose_name=_('漏扫节点端口'))
    status = models.CharField(verbose_name=_('服务状态'), max_length=16, choices=Status.choices,
                              default=Status.ENABLE.value)
    key = models.CharField(verbose_name=_('连接验证Key'), max_length=64)
    max_concurrency = models.IntegerField(verbose_name=_('漏扫最大并发数'))    
    
    class Meta:
        ordering = ['-type']
        verbose_name = _('漏洞扫描器')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'[{self.get_type_display()}]{self.name}'


class VtReport(UuidModel):
    
    # 站点扫描和主机扫描生成的文件分别为html格式与pdf格式
    class FileType(models.TextChoices):
        HTML = 'html', _('HTML格式')
        PDF = 'pdf', _('PDF格式')
        
    filename = models.CharField(verbose_name=_('文件名'), max_length=255)
    type = models.CharField(verbose_name=_('漏扫报告类型'), max_length=8, choices=FileType.choices, default=FileType.HTML.value)
    content = models.BinaryField(verbose_name=_('漏扫报告内容'), null=True)
    size = models.IntegerField(verbose_name=_('文件大小'), default=0)
    create_time = models.DateTimeField(verbose_name=_('修改时间'), auto_now_add=True)

    class Meta:
        ordering = ['-create_time']
        verbose_name = _('任务扫描报告')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.filename}.{self.type}'

    
class VtTask(UuidModel):

    class TaskType(models.TextChoices):
        WEB = 'web', _('站点扫描')
        HOST = 'host', _('主机扫描')
    
    class Status(models.TextChoices):
        QUEUED = 'queued', _('排队等待')
        RUNNING = 'running', _('正在运行')
        DONE = 'done', _('运行完成')
        FAILED = 'failed', _('运行失败')
    
    class RunningStatus(models.TextChoices):
        SPIDER = 'spider', _('爬虫')
        AJAXSPIDER = 'ajaxspider', _('Ajax爬虫')
        ACTIVE = 'active', _('主动扫描')
        PASSIVE = 'passive', _('被动扫描')
        DONE = 'done', _('运行结束')
        FAILED = 'failed', _('运行失败')

    name = models.CharField(verbose_name=_('任务名称'), max_length=255)
    priority = models.IntegerField(verbose_name=_('任务优先级'), default=2)
    target = models.CharField(verbose_name=_('扫描目标'), max_length=255)
    type = models.CharField(verbose_name=_('任务类型'), max_length=8, choices=TaskType.choices)
    task_status = models.CharField(verbose_name=_('任务状态'), max_length=16, choices=Status.choices, default=Status.QUEUED.value)
    scanner = models.ForeignKey(verbose_name=_('扫描器'), to=VtScanner, on_delete=models.SET_NULL, related_name='tasks', blank=True, null=True)
    user = models.ForeignKey(verbose_name=_('所属用户'), to=User, on_delete=models.SET_NULL, blank=True, null=True)
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    finish_time = models.DateTimeField(verbose_name=_('结束时间'), null=True, blank=True, default=None)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)
    errmsg = models.CharField(verbose_name=_('任务失败原因'), max_length=255, default='', blank=True)
    report = models.ForeignKey(verbose_name=_('扫描报告'), to=VtReport, on_delete=models.SET_NULL, blank=True, null=True)
    remark = models.CharField(verbose_name=_('备注'), max_length=255, default='', blank=True)
    # 站点扫描使用的ZAP所需要的字段
    running_status = models.CharField(verbose_name=_('内部扫描状态'), max_length=16, choices=RunningStatus.choices, null=True)
    # 主机扫描使用的GVM所需要的字段
    running_id = models.CharField(verbose_name=_('内部扫描id'), max_length=36, null=True, blank=True, default='')

    class Meta:
        ordering = ['-update_time']
        verbose_name = _('漏洞扫描任务')
        verbose_name_plural = verbose_name
