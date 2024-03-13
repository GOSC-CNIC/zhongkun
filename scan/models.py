from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from utils.model import UuidModel
from django.contrib.auth import get_user_model

from core import errors

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
    host_scan_price = models.DecimalField(
        verbose_name=_('主机扫描单价'), max_digits=10, decimal_places=2, default=Decimal(0))
    web_scan_price = models.DecimalField(
        verbose_name=_('站点扫描单价'), max_digits=10, decimal_places=2, default=Decimal(0))
    pay_app_service_id = models.CharField(
        verbose_name=_('余额结算APP服务ID'), max_length=36, blank=True, default='',
        help_text=_('此服务对应的APP结算服务单元（注册在余额结算中的APP服务）id，扣费时需要此id，用于指定哪个服务发生的扣费；'
                    '正常情况下此内容会自动填充，不需要手动输入'))
    add_time = models.DateTimeField(auto_now_add=True, verbose_name=_('添加时间'))
    
    class Meta:
        ordering = ['-add_time']
        verbose_name = _('安全扫描服务')
        verbose_name_plural = verbose_name
    
    @classmethod
    def get_instance(cls):
        inst = cls.objects.order_by('-add_time').first()
        if inst is None:
            raise errors.NotFound(message=_(f'安全扫描服务配置信息不存在。'))
        return inst
    
    
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
    key = models.CharField(verbose_name=_('连接验证Key'), max_length=64, choices=Status.choices,
                              default=Status.ENABLE.value)
    max_concurrency = models.IntegerField(verbose_name=_('漏扫最大并发数'))    
    
    class Meta:
        ordering = ['-type']
        verbose_name = _('漏洞扫描节点')
        verbose_name_plural = verbose_name


class VtReport(UuidModel):
    
    # 站点扫描和主机扫描生成的文件分别为html格式与pdf格式
    class FileType(models.TextChoices):
        HTML = 'html', _('HTML格式')
        PDF = 'pdf', _('PDF格式')
        
    filename = models.CharField(verbose_name=_('文件名'), max_length=255)
    type = models.CharField(verbose_name=_('漏扫报告类型'), max_length=8, choices=FileType.choices, default=FileType.HTML.value)
    content = models.BinaryField(verbose_name=_('漏扫报告内容'), null=True)
    create_time = models.DateTimeField(verbose_name=_('修改时间'), auto_now_add=True)

    class Meta:
        ordering = ['-create_time']
        verbose_name = _('站点扫描报告')
        verbose_name_plural = verbose_name

    
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
        
    name = models.CharField(verbose_name=_('任务名称'), max_length=255)
    priority = models.IntegerField(verbose_name=_('任务优先级'),default=2)
    target = models.CharField(verbose_name=_('扫描目标'), max_length=255)
    type = models.CharField(verbose_name=_('任务类型'), max_length = 8, choices=TaskType.choices)
    task_status = models.CharField(verbose_name=_('任务状态'), max_length = 16, choices=Status.choices, default=Status.QUEUED.value)
    scanner = models.ForeignKey(verbose_name=_('扫描器'), to=VtScanner, on_delete=models.SET_NULL, related_name='tasks', blank=True, null=True)
    user = models.ForeignKey(verbose_name=_('所属用户'), to=User, on_delete=models.SET_NULL, blank=True, null =True)
    create_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    finish_time = models.DateTimeField(verbose_name=_('结束时间'), null=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)
    report = models.ForeignKey(verbose_name=_('扫描报告'), to=VtReport, on_delete=models.SET_NULL, blank=True, null=True)
    remark = models.CharField(verbose_name=_('备注'), max_length=255, default='', blank=True)
    payment_history_id = models.CharField(verbose_name=_('支付记录id'), max_length=36, blank=True, default='')
    # 站点扫描使用的ZAP所需要的字段
    running_status = models.CharField(verbose_name=_('内部扫描状态'), max_length=16, choices=RunningStatus.choices, null=True)
    # 主机扫描使用的GVM所需要的字段
    running_id = models.CharField(verbose_name=_('内部扫描id'), max_length=36, null=True)
    # 支付信息字段
    pay_amount = models.DecimalField(
        verbose_name=_('实付金额'), max_digits=10, decimal_places=2, default=Decimal('0'),
        help_text=_('实际交易金额')
    )
    balance_amount = models.DecimalField(
        verbose_name=_('余额支付金额'), max_digits=10, decimal_places=2, default=Decimal('0'))
    coupon_amount = models.DecimalField(
        verbose_name=_('券支付金额'), max_digits=10, decimal_places=2, default=Decimal('0'))

    
    class Meta:
        ordering = ['-update_time']
        verbose_name = _('漏洞扫描任务')
        verbose_name_plural = verbose_name
