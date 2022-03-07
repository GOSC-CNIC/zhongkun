from django.db import models
from django.utils.translation import gettext, gettext_lazy as _

from utils.model import UuidModel, OwnerType
from users.models import UserProfile
from vo.models import VirtualOrganization
from servers.models import Server
from service.models import ServiceConfig


class MeteringServer(UuidModel):
    """
    服务器云主机计量
    """
    OwnerType = OwnerType

    service = models.ForeignKey(to=ServiceConfig, verbose_name=_('服务'), related_name='+',
                                on_delete=models.DO_NOTHING, db_index=False)
    server_id = models.CharField(verbose_name=_('云服务器ID'), max_length=36)
    date = models.DateField(verbose_name=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)
    cpu_hours = models.FloatField(
        verbose_name=_('CPU Hour'), blank=True, default=0, help_text=_('云服务器的CPU Hour数'))
    ram_hours = models.FloatField(
        verbose_name=_('内存GiB Hour'), blank=True, default=0, help_text=_('云服务器的内存Gib Hour数'))
    disk_hours = models.FloatField(
        verbose_name=_('系统盘GiB Hour'), blank=True, default=0, help_text=_('云服务器的系统盘Gib Hour数'))
    public_ip_hours = models.FloatField(
        verbose_name=_('IP Hour'), blank=True, default=0, help_text=_('云服务器的公网IP Hour数'))
    snapshot_hours = models.FloatField(
        verbose_name=_('快照GiB Hour'), blank=True, default=0, help_text=_('云服务器的快照小时数'))
    upstream = models.FloatField(
        verbose_name=_('上行流量GiB'), blank=True, default=0, help_text=_('云服务器的上行流量Gib'))
    downstream = models.FloatField(
        verbose_name=_('下行流量GiB'), blank=True, default=0, help_text=_('云服务器的下行流量Gib'))
    pay_type = models.CharField(verbose_name=_('云服务器付费方式'), max_length=16, choices=Server.PayType.choices)

    class Meta:
        verbose_name = _('云服务器资源计量')
        verbose_name_plural = verbose_name
        db_table = 'metering_server'
        ordering = ['-creation_time']
        constraints = [
            models.constraints.UniqueConstraint(fields=['date', 'server_id'], name='unique_date_server')
        ]

    def __repr__(self):
        return gettext('云服务器资源计量') + f'[server id {self.server_id}]'
