from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone as dj_timezone

from utils.model import UuidModel, OwnerType, PayType
from apps.users.models import UserProfile
from apps.app_vo.models import VirtualOrganization
from apps.app_storage.models import ObjectsService, BucketBase
from apps.servers.models import Server, ServiceConfig


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
        verbose_name=_('云主机计费金额'), max_digits=10, decimal_places=2)
    server_payable_amount = models.DecimalField(verbose_name=_('云主机按量应付金额'), max_digits=10, decimal_places=2)
    server_postpaid_amount = models.DecimalField(verbose_name=_('云主机按量后付费金额'), max_digits=10, decimal_places=2)
    server_prepaid_amount = models.DecimalField(verbose_name=_('云主机订购预付费金额'), max_digits=10, decimal_places=2)
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
        verbose_name=_('存储桶计费金额'), max_digits=10, decimal_places=2)
    storage_payable_amount = models.DecimalField(verbose_name=_('存储桶按量应付金额'), max_digits=10, decimal_places=2)
    storage_postpaid_amount = models.DecimalField(verbose_name=_('存储桶按量后付费金额'), max_digits=10, decimal_places=2)
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
    site_count = models.IntegerField(verbose_name=_('本月站点监控任务数'), default=0)
    site_days = models.FloatField(
        verbose_name=_('监控总天数'), blank=True, default=0, help_text=_('所有站点监控任务总监控天数'))
    site_tamper_days = models.FloatField(
        verbose_name=_('防篡改监控总天数'), blank=True, default=0, help_text=_('所有站点监控任务总防篡改监控天数'))
    site_original_amount = models.DecimalField(
        verbose_name=_('站点监控计费金额'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    site_payable_amount = models.DecimalField(
        verbose_name=_('站点监控应付金额'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    site_paid_amount = models.DecimalField(
        verbose_name=_('站点监控付费金额'), max_digits=10, decimal_places=2, default=Decimal('0.00'))

    s_snapshot_count = models.IntegerField(verbose_name=_('云主机快照数'), default=0)
    s_snapshot_prepaid_amount = models.DecimalField(
        verbose_name=_('云主机快照预付费金额'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    scan_web_count = models.IntegerField(verbose_name=_('Web安全扫描数'), default=0)
    scan_host_count = models.IntegerField(verbose_name=_('Host安全扫描数'), default=0)
    scan_prepaid_amount = models.DecimalField(
        verbose_name=_('安全扫描预付费金额'), max_digits=10, decimal_places=2, default=Decimal('0.00'))

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
        return self.server_postpaid_amount + self.server_prepaid_amount + self.s_snapshot_prepaid_amount

    @property
    def disk_payment_amount(self):
        return self.disk_postpaid_amount + self.disk_prepaid_amount

    @property
    def server_disk_payment_amount(self):
        return self.server_payment_amount + self.disk_payment_amount

    @property
    def total_payment_amount(self):
        return (
                self.server_disk_payment_amount + self.storage_postpaid_amount + self.scan_prepaid_amount
                + self.site_paid_amount
        )

    @property
    def has_resources(self):
        return (
                self.server_count or self.disk_count or self.bucket_count or self.site_count or self.scan_web_count
                or self.scan_host_count
        )


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


class BucketStatsMonthly(UuidModel):
    service = models.ForeignKey(
        verbose_name=_('存储服务单元'), to=ObjectsService, db_constraint=False, related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True, default=None)
    bucket_id = models.CharField(verbose_name=_('存储桶ID'), max_length=36)
    bucket_name = models.CharField(verbose_name=_('存储桶名称'), max_length=73)
    size_byte = models.BigIntegerField(verbose_name=_('存储容量(Byte)'), default=0, help_text='byte')
    increment_byte = models.BigIntegerField(verbose_name=_('存储容量增量(Byte)'), default=0, help_text='byte')
    object_count = models.BigIntegerField(verbose_name=_('桶对象数量'), blank=True, default=0)
    original_amount = models.DecimalField(
        verbose_name=_('计费金额'), max_digits=10, decimal_places=2)
    increment_amount = models.DecimalField(
        verbose_name=_('计费金额增量'), max_digits=10, decimal_places=2)
    user = models.ForeignKey(
        verbose_name=_('用户'), to=UserProfile, on_delete=models.DO_NOTHING, related_name='+', db_constraint=False,
        blank=True)
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')
    date = models.DateField(verbose_name=_('数据日期(月份)'), help_text=_('根据数据采样周期，数据是哪个月的'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))

    class Meta:
        db_table = 'bucket_stats_monthly'
        ordering = ['-creation_time']
        verbose_name = _('存储桶月度容量增量统计数据')
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(
                fields=('bucket_id', 'date'), name='unique_bucket_date'
            )
        ]
        indexes = [
            models.Index(fields=('date',), name='idx_date')
        ]


class ArrearServer(UuidModel):
    server_id = models.CharField(
        verbose_name=_('云主机ID'), max_length=36, blank=True, default='')
    service = models.ForeignKey(
        verbose_name=_('云主机服务单元'), to=ServiceConfig, db_constraint=False, related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True, default=None)
    service_name = models.CharField(max_length=255, verbose_name=_('云主机服务单元'))
    ipv4 = models.CharField(max_length=128, verbose_name='IPV4', default='')
    vcpus = models.IntegerField(verbose_name=_('虚拟CPU数'), default=0)
    ram = models.IntegerField(verbose_name=_('内存GiB'), default=0)
    image = models.CharField(max_length=255, verbose_name=_('镜像系统名称'), default='')
    pay_type = models.CharField(
        verbose_name=_('计费方式'), max_length=16, choices=PayType.choices, default=PayType.POSTPAID.value)
    server_creation = models.DateTimeField(verbose_name=_('云主机创建时间'))
    server_expire = models.DateTimeField(verbose_name=_('云主机过期时间'), null=True, blank=True, default=None)
    remarks = models.CharField(max_length=255, blank=True, default='', verbose_name=_('云主机备注'))
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='',
                                help_text=_('个人云主机的拥有者，或者vo组云主机的创建者'))
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    vo_name = models.CharField(verbose_name=_('VO组名'), max_length=256, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)
    balance_amount = models.DecimalField(
        verbose_name=_('所有者的余额'), max_digits=10, decimal_places=2, help_text=_('用户个人余额，或者VO组余额'))
    date = models.DateField(verbose_name=_('数据日期'), help_text=_('查询欠费云主机数据采样日期'))
    creation_time = models.DateTimeField(verbose_name=_('判定为欠费的时间'))

    class Meta:
        db_table = 'report_arrear_server'
        ordering = ['-creation_time']
        verbose_name = _('欠费的云主机')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'ArrearServer({self.server_id}, {self.ipv4}, {self.image})'

    def clean(self):
        if not self.creation_time:
            self.creation_time = dj_timezone.now()


class ArrearBucket(UuidModel):
    bucket_id = models.CharField(verbose_name=_('存储桶ID'), max_length=36)
    bucket_name = models.CharField(verbose_name=_('存储桶名称'), max_length=73)
    service = models.ForeignKey(
        verbose_name=_('存储服务单元'), to=ObjectsService, db_constraint=False, related_name='+',
        on_delete=models.SET_NULL, null=True, blank=True, default=None)
    service_name = models.CharField(max_length=255, verbose_name=_('存储服务单元'))
    size_byte = models.BigIntegerField(verbose_name=_('存储容量(Byte)'), default=0, help_text='byte')
    object_count = models.BigIntegerField(verbose_name=_('桶对象数量'), blank=True, default=0)
    bucket_creation = models.DateTimeField(verbose_name=_('存储桶创建时间'))
    situation = models.CharField(
        verbose_name=_('过期欠费管控情况'), max_length=16,
        choices=BucketBase.Situation.choices, default=BucketBase.Situation.NORMAL.value,
        help_text=_('欠费状态下存储桶读写锁定管控情况')
    )
    situation_time = models.DateTimeField(
        verbose_name=_('管控情况时间'), null=True, blank=True, default=None, help_text=_('欠费管控开始时间'))
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')
    balance_amount = models.DecimalField(verbose_name=_('余额'), max_digits=10, decimal_places=2)
    date = models.DateField(verbose_name=_('数据日期'), help_text=_('查询欠费存储桶数据采样日期'))
    creation_time = models.DateTimeField(verbose_name=_('判定为欠费的时间'))
    remarks = models.CharField(max_length=255, blank=True, default='', verbose_name=_('存储桶备注'))

    class Meta:
        db_table = 'report_arrear_bucket'
        ordering = ['-creation_time']
        verbose_name = _('欠费的存储桶')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'ArrearBucket({self.bucket_id}, {self.bucket_name})'

    def clean(self):
        if not self.creation_time:
            self.creation_time = dj_timezone.now()
