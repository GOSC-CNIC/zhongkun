from django.db import models
from utils.model import UuidModel
from django.utils.translation import gettext_lazy as _
from apps.app_alert.utils.utils import DateUtils
import shortuuid
import uuid


# Create your models here.

class AlertUuidModel(UuidModel):
    class Meta:
        abstract = True

    def generate_id(self):
        short_uuid = shortuuid.ShortUUID(alphabet='23456789abcdefghjkmnpqrstuvwxyz').encode(uuid.uuid1())
        return f"{str(DateUtils.now().date()).replace('-', '')}-{short_uuid[-5:]}"


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
