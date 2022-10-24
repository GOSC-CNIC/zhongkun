from django.db import models
from django.utils.translation import gettext, gettext_lazy as _

from utils.model import CustomIdModel
from utils import rand_utils
from users.models import UserProfile


class Ticket(CustomIdModel):
    """
    工单
    """
    class ServiceType(models.TextChoices):
        ACCOUNT = 'account', _('账户')
        SERVER = 'server', _('云服务器')
        STORAGE = 'storage', _('对象存储')
        BILL = 'bill', _('计量账单')
        MONITOR = 'monitor', _('监控')
        HPC = 'hpc', _('高性能计算')
        HSC = 'hsc', _('高安全等级云')
        DEVELOP = 'develop', _('开发')
        OTHER = 'other', _('其他')

    class Status(models.TextChoices):
        OPEN = 'open', _('打开')
        CANCELED = 'canceled', _('已取消')
        PROGRESS = 'progress', _('处理中')
        RESOLVED = 'resolved', _('已解决')
        CLOSED = 'closed', _('已关闭')
        REOPENED = 'reopened', _('重新打开')

    class Severity(models.TextChoices):
        CRITICAL = 'critical', _('严重')
        HIGH = 'high', _('高')
        NORMAL = 'normal', _('一般')
        LOW = 'low', _('低')
        VERY_LOW = 'verylow', _('很低')

    title = models.CharField(verbose_name=_('标题'), max_length=250, help_text=_('疑问或问题的简述'))
    description = models.TextField(
        verbose_name=_('问题描述'), blank=True, default='',
        help_text=_('客户的疑问或问题的描述'),
    )
    status = models.CharField(
        verbose_name=_('状态'), max_length=16,
        choices=Status.choices, default=Status.OPEN.value
    )
    service_type = models.CharField(
        verbose_name=_('工单相关服务'), max_length=16,
        choices=ServiceType.choices, default=ServiceType.OTHER.value
    )
    severity = models.CharField(
        verbose_name=_('严重程度'), max_length=16, blank=True,
        choices=Severity.choices, default=Severity.NORMAL.value
    )
    submit_time = models.DateTimeField(
        verbose_name=_('提交时间'), blank=True, auto_now_add=True, help_text=_('工单提交的时间')
    )
    modified_time = models.DateTimeField(
        verbose_name=_('修改时间'), blank=True, auto_now=True, help_text=_('工单最近修改的时间')
    )
    submitter = models.ForeignKey(
        to=UserProfile, verbose_name=_('工单提交人'),
        related_name='+', on_delete=models.SET_NULL, null=True
    )
    username = models.CharField(verbose_name=_('提交人用户名'), max_length=128, blank=True, default='')
    contact = models.CharField(
        verbose_name=_('联系方式'), max_length=128, blank=True, default='',
        help_text=_('工单提交人联系方式'),
    )
    assigned_to = models.ForeignKey(
        to=UserProfile, verbose_name=_('分配给'),
        on_delete=models.SET_NULL, related_name='+',
        blank=True, null=True, default=None
    )
    # 在工单处理完成后，关闭工单时填充此工单的解决方案
    resolution = models.TextField(
        verbose_name=_('解决方案'), blank=True, default='',
        help_text=_('向客户提供的解决方案。'),
    )

    class Meta:
        db_table = 'ticket_ticket'
        ordering = ['-submit_time']
        verbose_name = _('工单')
        verbose_name_plural = verbose_name

    def __str__(self):
        return '%s %s' % (self.id, self.title)

    def generate_id(self) -> str:
        return rand_utils.timestamp20_rand4_sn()


class TicketChange(CustomIdModel):
    """
    对工单的任何更改动作（如标题、优先级等）在此处进行跟踪，关联到一个工单跟进（FollowUp）以便于显示。
    """
    class TicketField(models.TextChoices):
        TITLE = 'title', _('工单标题')
        STATUS = 'status', _('工单状态')
        SEVERITY = 'severity', _('工单严重程度')
        DESCRIPTION = 'description', _('工单描述')
        ASSIGNED_TO = 'assigned_to', _('工单流转处理人')

    ticket_field = models.CharField(verbose_name=_('字段'), max_length=32, choices=TicketField.choices)
    old_value = models.TextField(verbose_name=_('旧值'), blank=True, default='')
    new_value = models.TextField(verbose_name=_('新值'), blank=True, default='')

    class Meta:
        db_table = 'ticket_change'
        verbose_name = _('工单更改')
        verbose_name_plural = verbose_name

    def generate_id(self) -> str:
        return rand_utils.timestamp20_rand4_sn()

    def __str__(self):
        field_disp = '%s ' % self.get_ticket_field_display()
        return self._display_template(
            field_disp=field_disp, old_value_disp=self.old_value, new_value_disp=self.new_value)

    @staticmethod
    def _display_template(field_disp: str, old_value_disp: str, new_value_disp: str) -> str:
        """
        变更展示模板

        :param field_disp: 变更字段展示信息
        :param old_value_disp: 旧值展示信息，可为空
        :param new_value_disp: 新值展示信息，可为空
        """
        out = '%s ' % field_disp
        if not new_value_disp:
            out += gettext('移除')
        elif not old_value_disp:
            out += gettext('更改为 "%s"') % new_value_disp
        else:
            out += gettext('从 "%(old_value)s" 更改为 "%(new_value)s"') % {
                'old_value': old_value_disp,
                'new_value': new_value_disp
            }

        return out

    @staticmethod
    def _dict_from_choices(choices):
        return {item.value: item.label for item in choices}

    @property
    def display(self):
        field_disp = self.get_ticket_field_display()

        if self.ticket_field == self.TicketField.STATUS.value:
            d = self._dict_from_choices(Ticket.Status)
            old_value_disp = d.get(self.old_value, self.old_value)
            new_value_disp = d.get(self.new_value, self.new_value)
            return self._display_template(
                field_disp=field_disp, old_value_disp=old_value_disp, new_value_disp=new_value_disp)
        elif self.ticket_field == self.TicketField.SEVERITY:
            d = self._dict_from_choices(Ticket.Severity)
            old_value_disp = d.get(self.old_value, self.old_value)
            new_value_disp = d.get(self.new_value, self.new_value)
            return self._display_template(
                field_disp=field_disp, old_value_disp=old_value_disp, new_value_disp=new_value_disp)
        elif (len(self.old_value) + len(self.new_value)) <= 200:
            return self._display_template(
                field_disp=field_disp, old_value_disp=self.old_value, new_value_disp=self.new_value)
        else:
            return gettext('%s 发生了更改') % field_disp


class FollowUp(CustomIdModel):
    """
    工单跟进回复/或修改工单的动作
    """
    class FuType(models.TextChoices):
        REPLY = 'reply', _('回复')
        ACTION = 'action', _('变更动作')

    ticket = models.ForeignKey(
        to=Ticket, verbose_name=_('工单'),
        on_delete=models.CASCADE, related_name='+'
    )
    submit_time = models.DateTimeField(
        verbose_name=_('提交时间'), blank=True, auto_now_add=True, help_text=_('工单跟进回复提交的时间')
    )
    title = models.CharField(verbose_name=_('标题'), max_length=250, default='', help_text=_('自动填充，比如工单变更的描述'))
    comment = models.TextField(verbose_name=_('评论'), default='')
    user = models.ForeignKey(
        to=UserProfile, verbose_name=_('用户'),
        on_delete=models.SET_NULL, blank=True, null=True
    )
    fu_type = models.CharField(
        verbose_name=_('跟进类型'), max_length=16,
        choices=FuType.choices, default=FuType.REPLY.value
    )
    # fu_type为“变更动作”时，添加关联工单变更
    ticket_change = models.OneToOneField(
        to=TicketChange, verbose_name=_('工单更改'),
        null=True, blank=True, default=None,
        related_name='+', on_delete=models.SET_NULL
    )

    class Meta:
        db_table = 'ticket_followup'
        ordering = ['-submit_time']
        verbose_name = _('工单跟进回复')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title

    def generate_id(self) -> str:
        return rand_utils.timestamp20_rand4_sn()
