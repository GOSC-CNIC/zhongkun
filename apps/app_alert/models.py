from django.db import models
from utils.model import UuidModel
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext
from apps.app_alert.utils.utils import DateUtils
from apps.users.models import UserProfile
import shortuuid
import uuid
from django.utils import timezone as dj_timezone
from utils.validators import http_url_validator
from django.core.exceptions import ValidationError
from utils.model import get_encryptor


# Create your models here.

class AlertUuidModel(UuidModel):
    class Meta:
        abstract = True

    def generate_id(self):
        short_uuid = shortuuid.ShortUUID(alphabet='23456789abcdefghjkmnpqrstuvwxyz').encode(uuid.uuid1())
        return f"{str(DateUtils.now().date()).replace('-', '')}-{short_uuid[-5:]}"


class AlertMonitorJobServer(UuidModel):
    """
    主机集群监控单元
    """
    name = models.CharField(verbose_name=_('监控的主机集群名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('监控的主机集群英文名称'), max_length=255, default='')
    job_tag = models.CharField(
        verbose_name=_('主机集群标签名称'), max_length=255, default='', help_text=_('模板：xxx_node_metric'))
    prometheus = models.CharField(
        verbose_name=_('Prometheus接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    remark = models.TextField(verbose_name=_('备注'), blank=True, default='')
    users = models.ManyToManyField(
        to="users.UserProfile",
        db_table='alert_server_users',
        related_name='+',
        db_constraint=False,
        verbose_name=_('管理用户'),
        blank=True)
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))
    grafana_url = models.CharField(verbose_name=_('Grafana连接'), max_length=255, blank=True, default='')
    dashboard_url = models.CharField(verbose_name=_('Dashboard连接'), max_length=255, blank=True, default='')

    def __str__(self):
        return self.name

    class Meta:
        db_table = "alert_monitorjobserver"
        ordering = ['-creation']
        verbose_name = _("告警集群")
        verbose_name_plural = verbose_name


# 监控的服务列表
class AlertService(UuidModel):
    """监控服务"""
    name = models.CharField(verbose_name=_('名称'), max_length=255)
    name_en = models.CharField(verbose_name=_('英文名称'), max_length=255, default='')
    users = models.ManyToManyField(
        to=UserProfile, verbose_name=_('管理员'), blank=True, related_name='+',
        through='ServiceAdminUser', through_fields=('service', 'userprofile'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))
    remark = models.TextField(verbose_name=_('监控服务备注'), max_length=10000, blank=True, default='')

    # 指标数据服务
    thanos_endpoint_url = models.CharField(
        verbose_name=_('指标监控系统查询接口'), max_length=255, blank=True, default='',
        help_text=_('http(s)://example.cn/'))
    thanos_username = models.CharField(
        max_length=128, verbose_name=_('指标监控系统认证用户名'), blank=True, default='',
        help_text=_('用于此服务认证的用户名'))
    thanos_password = models.CharField(max_length=255, verbose_name=_('指标监控系统认证密码'), blank=True, default='')
    thanos_receive_url = models.CharField(
        verbose_name=_('指标监控系统接收接口'), max_length=255, blank=True, default='',
        help_text=_('http(s)://example.cn/'))
    thanos_remark = models.CharField(verbose_name=_('指标监控系统备注'), max_length=255, blank=True, default='')
    metric_monitor_url = models.CharField(
        verbose_name=_('指标监控系统监控网址'), max_length=255, blank=True, default='',
        help_text=_('如果填写有效网址会自动创建对应的站点监控任务，格式为 http(s)://example.cn/'))
    metric_task_id = models.CharField(
        verbose_name=_('指标监控系统监控任务ID'), max_length=36, blank=True, default='', editable=False,
        help_text=_('记录为指标监控系统监控地址创建的站点监控任务的ID'))

    # 日志服务
    loki_endpoint_url = models.CharField(
        verbose_name=_('日志聚合系统查询接口'), max_length=255, blank=True, default='',
        help_text=_('http(s)://example.cn/'))
    loki_username = models.CharField(
        max_length=128, verbose_name=_('日志聚合系统认证用户名'), blank=True, default='',
        help_text=_('用于此服务认证的用户名'))
    loki_password = models.CharField(max_length=255, verbose_name=_('日志聚合系统认证密码'), blank=True, default='')
    loki_receive_url = models.CharField(
        verbose_name=_('日志聚合系统接收接口'), max_length=255, blank=True, default='',
        help_text=_('http(s)://example.cn/'))
    loki_remark = models.CharField(verbose_name=_('日志聚合系统备注'), max_length=255, blank=True, default='')
    log_monitor_url = models.CharField(
        verbose_name=_('日志聚合系统监控网址'), max_length=255, blank=True, default='',
        help_text=_('如果填写有效网址会自动创建对应的站点监控任务，格式为 http(s)://example.cn/'))
    log_task_id = models.CharField(
        verbose_name=_('日志聚合系统监控任务ID'), max_length=36, blank=True, default='', editable=False,
        help_text=_('记录为日志聚合系统监控网址创建的站点监控任务的ID'))

    class Meta:
        db_table = 'alert_service'
        ordering = ['sort_weight']
        verbose_name = _('监控服务')
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

    def add_admin_user(self, user, is_ops_user: bool = False):
        """
        :is_admin: False(管理员)，True(运维人员)
        """
        if isinstance(user, str):
            user_id = user
        else:
            user_id = user.id

        if is_ops_user:
            user_role = ServiceAdminUser.Role.OPS.value
        else:
            user_role = ServiceAdminUser.Role.ADMIN.value

        odc_admin = ServiceAdminUser.objects.filter(service_id=self.id, userprofile_id=user_id).first()
        if odc_admin:
            if odc_admin.role == user_role:
                return False, odc_admin

            odc_admin.role = user_role
            odc_admin.save(update_fields=['role'])
            return True, odc_admin

        admin_user = ServiceAdminUser(
            service_id=self.id, userprofile_id=user_id, role=user_role, join_time=dj_timezone.now())
        admin_user.save(force_insert=True)
        return True, admin_user

    def remove_admin_user(self, user):
        if isinstance(user, str):
            user_id = user
        else:
            user_id = user.id

        num, d = ServiceAdminUser.objects.filter(service_id=self.id, userprofile_id=user_id).delete()
        return num


# 服务的管理员列表
class ServiceAdminUser(UuidModel):
    """
    监控服务管理员
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', _('管理员')
        OPS = 'ops', _('运维')

    userprofile = models.ForeignKey(verbose_name=_('用户'), to=UserProfile, on_delete=models.CASCADE,
                                    db_constraint=False)
    service = models.ForeignKey(
        verbose_name=_('监控服务'), to=AlertService, on_delete=models.CASCADE, db_constraint=False)
    role = models.CharField(verbose_name=_('角色'), max_length=16, choices=Role.choices, default=Role.ADMIN.value)
    join_time = models.DateTimeField(verbose_name=_('加入时间'), default=dj_timezone.now)

    class Meta:
        db_table = 'alert_service_users'
        ordering = ['-join_time']
        verbose_name = _('监控服务管理员')
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=('service', 'userprofile'), name='unique_together_service_user')
        ]

    def __str__(self):
        return f'{self.userprofile.username}[{self.get_role_display()}]'


# 指标类
class ServiceMetric(UuidModel):
    """
    主机集群监控单元
    """
    name = models.CharField(verbose_name=_('监控的主机集群名称'), max_length=255, default='')
    name_en = models.CharField(verbose_name=_('监控的主机集群英文名称'), max_length=255, default='')
    job_tag = models.CharField(
        verbose_name=_('主机集群标签名称'), max_length=255, default='', help_text=_('模板：xxx_node_metric'))
    prometheus = models.CharField(
        verbose_name=_('Prometheus接口'), max_length=255, blank=True, default='', help_text=_('http(s)://example.cn/'))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    remark = models.TextField(verbose_name=_('备注'), blank=True, default='')
    users = models.ManyToManyField(
        to=UserProfile, db_table='alert_metric_users', related_name='+',
        db_constraint=False, verbose_name=_('管理用户'), blank=True)
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=0, help_text=_('值越小排序越靠前'))
    grafana_url = models.CharField(verbose_name=_('Grafana连接'), max_length=255, blank=True, default='')
    dashboard_url = models.CharField(verbose_name=_('Dashboard连接'), max_length=255, blank=True, default='')
    service = models.ForeignKey(
        to=AlertService, null=True, on_delete=models.SET_NULL, related_name='service_metric_set',
        verbose_name=_('监控服务'),
        db_constraint=False)

    class Meta:
        db_table = 'alert_service_metric'
        ordering = ['sort_weight']
        verbose_name = _('监控指标单元')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


# 日志类
class ServiceLog(UuidModel):
    class LogType(models.TextChoices):
        HTTP = 'http', 'HTTP'
        NAT = 'nat', 'NAT'

    name = models.CharField(max_length=50, null=False, blank=False, verbose_name=_("日志单元站点名称"))
    name_en = models.CharField(verbose_name=_('日志单元英文名称'), max_length=128, default='')
    log_type = models.CharField(
        verbose_name=_("日志类型"), max_length=16, choices=LogType.choices, default=LogType.HTTP.value)
    job_tag = models.CharField(verbose_name=_('网站日志单元标识'), max_length=64, default='',
                               help_text=_('Loki日志中对应的job标识，模板xxx_log'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), help_text=_('值越小排序越靠前'))
    desc = models.CharField(max_length=255, blank=True, default="", verbose_name=_("备注"))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    modification = models.DateTimeField(verbose_name=_('修改时间'), auto_now=True)
    users = models.ManyToManyField(
        to=UserProfile, db_table='alert_log_users', related_name='+',
        db_constraint=False, verbose_name=_('管理用户'), blank=True)
    service = models.ForeignKey(
        to=AlertService, null=True, on_delete=models.SET_NULL, related_name='service_log_set',
        verbose_name=_('监控服务'),
        db_constraint=False)

    class Meta:
        db_table = "alert_service_log"
        ordering = ['sort_weight']
        verbose_name = _("监控日志单元")
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


# 工单
class TicketResolutionCategory(UuidModel):
    """
    告警工单 解决方案 类型
    """
    name = models.CharField(verbose_name=_('类型名称'), max_length=250, help_text=_('类型名称'))
    service = models.CharField(verbose_name=_('服务名称'), max_length=250, help_text=_('服务名称'))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    modification = models.DateTimeField(verbose_name=_('修改时间'), auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "alert_ticket_resolution_category"
        verbose_name = _("告警工单解决方案类别")
        ordering = ['-creation']
        verbose_name_plural = verbose_name


class TicketResolution(UuidModel):
    """
    告警工单 原因及解决方案
    """
    category = models.ForeignKey(
        to=TicketResolutionCategory,
        verbose_name=_('类型'),
        on_delete=models.DO_NOTHING,
        related_name='resolutions',
    )
    resolution = models.TextField(
        verbose_name=_('原因及解决方案'), blank=True, default='',
        help_text=_('原因及解决方案'),
    )
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    modification = models.DateTimeField(verbose_name=_('修改时间'), auto_now=True)

    def __str__(self):
        return '{} | {}'.format(self.category, self.resolution)

    class Meta:
        db_table = "alert_ticket_resolution"
        verbose_name = _("告警工单解决方案")
        ordering = ['-creation']
        verbose_name_plural = verbose_name


class AlertTicket(AlertUuidModel):
    """
    告警工单
    """

    title = models.CharField(verbose_name=_('工单标题'), max_length=250, blank=True, default='',
                             help_text=_('工单标题'))
    description = models.TextField(
        verbose_name=_('工单描述'),
        null=True,
        blank=True,
        default='',
        help_text=_('工单描述'),
    )
    service = models.CharField(verbose_name=_('服务名称'), max_length=250, help_text=_('服务名称'))

    class Severity(models.TextChoices):
        CRITICAL = 'critical', _('严重')
        HIGH = 'high', _('高')
        NORMAL = 'normal', _('一般')
        LOW = 'low', _('低')
        VERY_LOW = 'verylow', _('很低')

    severity = models.CharField(
        verbose_name=_('严重程度'), max_length=16, blank=True,
        choices=Severity.choices, default=Severity.NORMAL.value
    )

    class Status(models.TextChoices):
        ACCEPTED = 'accepted', _('已受理')
        CHANGED = 'changed', _('已转移')
        CLOSED = 'closed', _('已完成')

    status = models.CharField(
        verbose_name=_('状态'), max_length=16,
        choices=Status.choices, default=Status.ACCEPTED.value
    )

    creation = models.DateTimeField(
        verbose_name=_('提交时间'), blank=True, auto_now_add=True, help_text=_('工单提交的时间')
    )
    modification = models.DateTimeField(
        verbose_name=_('修改时间'), blank=True, auto_now=True, help_text=_('工单最近修改的时间')
    )
    submitter = models.ForeignKey(
        to=UserProfile, verbose_name=_('工单提交人'),
        related_name='submitted_tickets', on_delete=models.SET_NULL, null=True
    )
    handlers = models.ManyToManyField(
        to=UserProfile,
        verbose_name=_('管理员'),
        related_name='+',
        through='TicketHandler',
        through_fields=('ticket', 'user'))
    # 在工单处理完成后，关闭工单时填充此工单的解决方案
    resolution = models.ForeignKey(
        to=TicketResolution, verbose_name=_('原因及解决方案'),
        on_delete=models.SET_NULL, related_name='tickets',
        blank=True, null=True, default=None
    )

    class Meta:
        db_table = 'alert_ticket'
        ordering = ['-creation']
        verbose_name = _('告警工单')
        verbose_name_plural = verbose_name

    def __str__(self):
        return '%s %s' % (self.id, self.title)


class TicketHandler(UuidModel):
    ticket = models.ForeignKey(
        to=AlertTicket,
        verbose_name=_('所属的工单'),
        on_delete=models.CASCADE,
        related_name='handler_set',
        related_query_name="handler",
        db_constraint=False
    )
    user = models.ForeignKey(
        to=UserProfile,
        verbose_name=_('处理人'),
        related_name="%(app_label)s_%(class)s_related",
        related_query_name="%(app_label)s_%(class)ss",
        db_constraint=False,
        on_delete=models.SET_NULL,
        null=True
    )
    creation = models.DateTimeField(
        verbose_name=_('提交时间'), blank=True, auto_now_add=True, help_text=_('提交时间')
    )
    modification = models.DateTimeField(
        verbose_name=_('修改时间'), blank=True, auto_now=True, help_text=_('修改时间')
    )

    # def __str__(self):
    #     return '{} | {}'.format(self.ticket, self.handler)

    class Meta:
        db_table = "alert_ticket_handler"
        verbose_name = _("告警工单处理人")
        ordering = ['-creation']
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=('ticket', 'user'), name='unique_together_ticket_user')
        ]


class AlertWorkOrder(AlertUuidModel):
    """
    告警工单
    """

    class OrderStatus(models.TextChoices):
        MISREPORT = '误报', _('误报')
        FINISHED = '已完成', _('已完成')
        IGNORE = '无需处理', _('无需处理')

    status = models.CharField(max_length=10,
                              default=OrderStatus.IGNORE.value,
                              choices=OrderStatus.choices,
                              verbose_name=_("状态"))
    remark = models.TextField(blank=True, default="", verbose_name=_('备注'))
    creator = models.ForeignKey(null=False,
                                to="users.UserProfile",
                                on_delete=models.DO_NOTHING,
                                related_name="work_order",
                                verbose_name=_('创建者'))
    creation = models.PositiveBigIntegerField(null=True, verbose_name=_('创建时间'))
    modification = models.PositiveBigIntegerField(null=True, verbose_name=_('更新时间'))

    class Meta:
        db_table = "alert_work_order"
        ordering = ['-creation']
        verbose_name = _("告警工单")
        verbose_name_plural = verbose_name


# 告警

class AlertAbstractModel(AlertUuidModel):
    fingerprint = models.CharField(blank=False, unique=True, db_index=True, max_length=40, verbose_name=_('指纹'))
    name = models.CharField(max_length=100, verbose_name=_('名称'))

    class AlertType(models.TextChoices):
        METRIC = 'metric', _('指标类')
        LOG = 'log', _('日志类')
        WEBMONITOR = 'webmonitor', _('网站监控')

    type = models.CharField(max_length=64, choices=AlertType.choices, db_index=True, verbose_name=_('类型'))
    instance = models.CharField(null=False, default="", db_index=True, max_length=100, verbose_name=_('告警实例'))
    port = models.CharField(null=False, default="", db_index=True, max_length=100, verbose_name=_('告警端口'))
    cluster = models.CharField(db_index=True, max_length=50, verbose_name=_('集群名称'))

    class AlertSeverity(models.TextChoices):
        WARNING = 'warning', _('警告')
        ERROR = 'error', _('错误')
        CRITICAL = 'critical', _('严重错误')

    severity = models.CharField(max_length=50, choices=AlertSeverity.choices, db_index=True, verbose_name=_('级别'))
    summary = models.TextField(null=False, blank=False, verbose_name=_('摘要'))
    description = models.TextField(null=False, blank=False, verbose_name=_('详情'))
    start = models.PositiveBigIntegerField(db_index=True, verbose_name=_('告警开始时间'))
    end = models.PositiveBigIntegerField(null=True, db_index=True, verbose_name=_('告警预结束时间'))
    recovery = models.PositiveBigIntegerField(null=True, verbose_name=_('恢复时间'))

    class AlertStatus(models.TextChoices):
        FIRING = 'firing', _('进行中')
        RESOLVED = 'resolved', _('已恢复')

    status = models.CharField(max_length=20,
                              null=False,
                              default=AlertStatus.FIRING.value,
                              choices=AlertStatus.choices,
                              verbose_name=_("告警状态"))
    ticket = models.ForeignKey(
        null=True,
        to='AlertTicket',
        on_delete=models.SET_NULL,
        verbose_name=_('工单'),
        related_name="%(app_label)s_%(class)s_related",
        related_query_name="%(app_label)s_%(class)ss",
        db_constraint=False
    )

    count = models.PositiveBigIntegerField(null=False, default=1, verbose_name=_('累加条数'))
    creation = models.FloatField(null=False, db_index=True, verbose_name=_('创建时间'))
    modification = models.PositiveBigIntegerField(null=True, verbose_name=_('更新时间'))
    first_notification = models.PositiveBigIntegerField(null=True, verbose_name=_('首次通知时间'))
    last_notification = models.PositiveBigIntegerField(null=True, verbose_name=_('上次通知时间'))

    class Meta:
        abstract = True


class PreAlertModel(AlertAbstractModel):
    """
    预处理告警
    如网站类 多个探针同时告警则判定为告警
    """

    class Meta:
        db_table = "alert_prepare"
        ordering = ['-creation']
        verbose_name = _("预处理告警")
        verbose_name_plural = verbose_name


class AlertModel(AlertAbstractModel):
    """
    进行中告警
    """

    class Meta:
        db_table = "alert_firing"
        ordering = ['-creation']
        verbose_name = _("进行中告警")
        verbose_name_plural = verbose_name


class ResolvedAlertModel(AlertAbstractModel):
    """
    已恢复告警
    """
    fingerprint = models.CharField(blank=False, db_index=True, max_length=40, verbose_name=_('指纹'))
    status = models.CharField(
        max_length=20, null=False, default=AlertAbstractModel.AlertStatus.RESOLVED.value,
        choices=AlertAbstractModel.AlertStatus.choices, verbose_name=_("告警状态"))

    class Meta:
        db_table = "alert_resolved"
        ordering = ['-creation']
        verbose_name = _("已恢复告警")
        verbose_name_plural = verbose_name
        unique_together = (
            ('fingerprint', 'start'),
        )


class EmailNotification(AlertUuidModel):
    """
    邮件通知记录
    """
    alert = models.CharField(null=False, db_index=True, max_length=40, verbose_name='告警ID')
    email = models.CharField(null=False, db_index=True, max_length=100, verbose_name='邮箱')
    timestamp = models.PositiveBigIntegerField(db_index=True, verbose_name='通知时间')

    class Meta:
        db_table = "alert_email_notification"
        ordering = ["-timestamp", "email"]
        unique_together = (('alert', 'email', 'timestamp'),)
        verbose_name = _("邮件通知记录")
        verbose_name_plural = verbose_name
