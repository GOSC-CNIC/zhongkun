from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.model import UuidModel


class TimedTaskLock(UuidModel):
    class Task(models.TextChoices):
        METERING = 'metering', _('计量计费')
        BKT_MONTHLY = 'bkt-monthly', _('存储桶月度统计')
        REPORT_MONTHLY = 'report-monthly', _('月度报表')
        LOG_TIME_COUNT = 'log-time-count', _('日志时序统计')
        REQ_COUNT = 'req-count', _('服务请求量统计')
        SCAN = 'scan', _('安全扫描')
        SCREEN_HOST_CPUUSAGE = 'screen_host_cpuusage', _('大屏展示主机CPU使用率')
        ALERT_EMAIL = 'alert_email', _('告警邮件通知')
        ALERT_DINGTALK = 'alert_dingtalk', _('告警钉钉通知')

    class Status(models.TextChoices):
        NONE = 'none', _('无')
        RUNNING = 'running', _('执行中')

    task = models.CharField(verbose_name=_('定时任务'), max_length=32, choices=Task.choices)
    status = models.CharField(verbose_name=_('状态'), max_length=16, choices=Status.choices, default=Status.NONE.value)
    start_time = models.DateTimeField(verbose_name=_('执行开始时间'), null=True, blank=True, default=None)
    end_time = models.DateTimeField(verbose_name=_('执行结束时间'), null=True, blank=True, default=None)
    host = models.CharField(verbose_name=_('执行任务的节点IP'), max_length=64, blank=True, default='')
    run_desc = models.CharField(verbose_name=_('执行结果描述'), max_length=255, blank=True, default='')
    expire_time = models.DateTimeField(verbose_name=_('锁定过期时间'), null=True, blank=True, default=None)
    notify_time = models.DateTimeField(
        verbose_name=_('锁过期未释放通知时间'), null=True, blank=True, default=None,
        help_text=_('用于记录邮件通知发送时间，避免重复发送'))

    class Meta:
        db_table = 'global_timetasklock'
        ordering = ['id']
        verbose_name = _('定时任务状态锁')
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=('task',), name='unique_lock_task')
        ]

    def __str__(self):
        return f'[{self.get_status_display()}]({self.status})'

