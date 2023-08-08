from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.model import UuidModel, OwnerType
from users.models import UserProfile
from vo.models import VirtualOrganization
from storage.models import ObjectsService


class MonthlyReport(UuidModel):
    creation_time = models.DateTimeField(verbose_name=_('生成时间'))
    report_date = models.DateField(verbose_name=_('报表年月'), help_text=_('报表月度，用日期存储年和月，日统一为1'))
    period_start_time = models.DateTimeField(verbose_name=_('月度报表周期开始时间'), null=True, default=None)
    period_end_time = models.DateTimeField(verbose_name=_('月度报表周期结束时间'), null=True, default=None)
    is_reported = models.BooleanField(verbose_name=_('报表已生成状态'), default=True, help_text=_('true为生成完成'))
    notice_time = models.DateTimeField(verbose_name=_('邮件通知时间'), null=True, blank=True, default=None)
    user = models.ForeignKey(
        verbose_name=_('用户'), to=UserProfile, on_delete=models.SET_NULL, related_name='+',
        null=True, blank=True, default=None, db_constraint=False)
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')
    vo = models.ForeignKey(
        verbose_name=_('VO组'), to=VirtualOrganization, on_delete=models.SET_NULL, related_name='+',
        null=True, blank=True, default=None, db_constraint=False)
    vo_name = models.CharField(verbose_name=_('vo名称'), max_length=255, blank=True, default='')
    owner_type = models.CharField(
        verbose_name=_('所属类型'), max_length=16, choices=OwnerType.choices)
    server_count = models.IntegerField(verbose_name=_('本月度云主机数'), default=0)
    server_original_amount = models.DecimalField(
        verbose_name=_('计费金额'), max_digits=10, decimal_places=2)
    server_payable_amount = models.DecimalField(verbose_name=_('按量应付金额'), max_digits=10, decimal_places=2)
    server_postpaid_amount = models.DecimalField(verbose_name=_('按量后付费金额'), max_digits=10, decimal_places=2)
    server_prepaid_amount = models.DecimalField(verbose_name=_('订购预付费金额'), max_digits=10, decimal_places=2)
    server_cpu_days = models.FloatField(
        verbose_name=_('CPU*Day'), blank=True, default=0, help_text=_('云服务器的CPU Day数'))
    server_ram_days = models.FloatField(
        verbose_name=_('内存GiB*Day'), blank=True, default=0, help_text=_('云服务器的内存Gib Day数'))
    server_disk_days = models.FloatField(
        verbose_name=_('系统盘GiB*Day'), blank=True, default=0, help_text=_('云服务器的系统盘Gib Day数'))
    server_ip_days = models.FloatField(
        verbose_name=_('IP*Day'), blank=True, default=0, help_text=_('云服务器的公网IP Day数'))

    bucket_count = models.IntegerField(verbose_name=_('本月度存储桶数'), default=0)
    storage_days = models.FloatField(
        verbose_name=_('存储容量GiB*Day'), blank=True, default=0, help_text=_('存储桶的存储容量GiB Day数'))
    storage_original_amount = models.DecimalField(
        verbose_name=_('计费金额'), max_digits=10, decimal_places=2)
    storage_payable_amount = models.DecimalField(verbose_name=_('按量应付金额'), max_digits=10, decimal_places=2)
    storage_postpaid_amount = models.DecimalField(verbose_name=_('按量后付费金额'), max_digits=10, decimal_places=2)
    disk_count = models.IntegerField(verbose_name=_('本月度云硬盘数'), default=0)
    disk_size_days = models.FloatField(
        verbose_name=_('云硬盘容量GiB*Day'), blank=True, default=0, help_text=_('云硬盘的容量大小GiB Day数'))
    disk_original_amount = models.DecimalField(
        verbose_name=_('云硬盘计费金额'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    disk_payable_amount = models.DecimalField(
        verbose_name=_('云硬盘按量应付金额'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    disk_postpaid_amount = models.DecimalField(
        verbose_name=_('云硬盘按量后付费金额'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    disk_prepaid_amount = models.DecimalField(
        verbose_name=_('云硬盘订购预付费金额'), max_digits=10, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = _('月度报表')
        verbose_name_plural = verbose_name
        db_table = 'monthly_report'
        ordering = ['-creation_time']

    def __str__(self):
        if self.owner_type == OwnerType.USER.value:
            return f'用户 {self.username} 的月度{self.report_date_dispaly}报表'

        return f'VO组 {self.vo.name} 的月度{self.report_date_dispaly}报表'

    @property
    def report_year(self):
        return self.report_date.year

    @property
    def report_month(self):
        return self.report_date.month

    @property
    def report_date_dispaly(self) -> str:
        date_str: str = self.report_date.isoformat()
        return date_str.rsplit('-', maxsplit=1)[0]

    @property
    def server_payment_amount(self):
        return self.server_postpaid_amount + self.server_prepaid_amount

    @property
    def disk_payment_amount(self):
        return self.disk_postpaid_amount + self.disk_prepaid_amount

    @property
    def server_disk_payment_amount(self):
        return self.server_payment_amount + self.disk_payment_amount

    @property
    def total_payment_amount(self):
        return self.server_disk_payment_amount + self.storage_postpaid_amount


class BucketMonthlyReport(UuidModel):
    creation_time = models.DateTimeField(verbose_name=_('生成时间'))
    report_date = models.DateField(verbose_name=_('报表年月'), help_text=_('报表月度，用日期存储年和月，日统一为1'))
    user = models.ForeignKey(
        verbose_name=_('用户'), to=UserProfile, on_delete=models.DO_NOTHING, related_name='+', db_constraint=False)
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')
    service_id = models.CharField(max_length=36, verbose_name=_('所属服务单元'))
    service_name = models.CharField(max_length=255, verbose_name=_('服务名称'))
    bucket_id = models.CharField(
        verbose_name=_('存储桶实例ID'), max_length=36, default='', help_text=_('对象存储中间件存储桶实例id'))
    bucket_name = models.CharField(verbose_name=_('存储桶名称'), max_length=63)

    storage_days = models.FloatField(
        verbose_name=_('存储容量GiB*Day'), blank=True, default=0, help_text=_('存储桶的存储容量GiB天数'))
    original_amount = models.DecimalField(
        verbose_name=_('计费金额'), max_digits=10, decimal_places=2)
    payable_amount = models.DecimalField(verbose_name=_('按量应付金额'), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _('存储桶月度计量报表')
        verbose_name_plural = verbose_name
        db_table = 'monthly_bucket_metering'
        ordering = ['-creation_time']
        constraints = [
            models.UniqueConstraint(fields=['report_date', 'bucket_id'], name='unique_report_date_bucket')
        ]

    def __str__(self):
        return f'存储桶"{self.bucket_name}"月度计量报表'
