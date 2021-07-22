from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from utils.model import UuidModel
from service.models import ServiceConfig, UserQuota

User = get_user_model()


class QuotaActivity(UuidModel):
    class Tag(models.TextChoices):
        BASE = 'base', _('普通配额')
        PROBATION = 'probation', _('试用配额')

    class Status(models.TextChoices):
        ACTIVE = 'active', _('活动中')
        CLOSED = 'closed', _('活动关闭')

    name = models.CharField(verbose_name=_('配额活动名称'), max_length=255)
    name_en = models.CharField(verbose_name=_('配额活动英文名称'), max_length=255)
    start_time = models.DateTimeField(verbose_name=_('活动开始时间'))
    end_time = models.DateTimeField(verbose_name=_('活动结束时间'))
    creation_time = models.DateTimeField(verbose_name=_('活动创建时间'), auto_now_add=True)
    count = models.IntegerField(verbose_name=_('总数量'), default=1)
    got_count = models.IntegerField(verbose_name=_('已领取数量'), default=0)
    times_per_user = models.IntegerField(verbose_name=_('每人可领取次数'), default=1, help_text=_('每个用户可领取次数'))
    status = models.CharField(verbose_name=_('活动状态'), max_length=16,
                              choices=Status.choices, default=Status.ACTIVE)
    deleted = models.BooleanField(verbose_name=_('已删除'), default=False)
    user = models.ForeignKey(to=User, related_name='+', on_delete=models.SET_NULL, null=True, verbose_name=_('创建人'))

    service = models.ForeignKey(to=ServiceConfig, on_delete=models.SET_NULL, null=True,
                                related_name='+', verbose_name=_('服务provider'))
    tag = models.CharField(verbose_name=_('配额类型'), max_length=32, choices=Tag.choices, default=Tag.PROBATION)
    cpus = models.IntegerField(verbose_name=_('虚拟cpu数量'), default=1)
    private_ip = models.IntegerField(verbose_name=_('私网IP数'), default=0)
    public_ip = models.IntegerField(verbose_name=_('公网IP数'), default=0)
    ram = models.IntegerField(verbose_name=_('内存大小(MB)'), default=1024)
    disk_size = models.IntegerField(verbose_name=_('总硬盘大小(GB)'), default=0)
    expiration_time = models.DateTimeField(verbose_name=_('配额过期时间'), help_text=_('过期后不能再用于创建资源'))
    duration_days = models.IntegerField(verbose_name=_('资源使用时长'), blank=True, default=365,
                                        help_text=_('使用此配额创建的资源的有效使用时长'))

    class Meta:
        db_table = 'quota_activity'
        ordering = ('-creation_time',)
        verbose_name = _('配额活动')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.name}[{self.count - self.got_count}/{self.count}]'

    def build_quota_obj(self, user_id) -> UserQuota:
        """
        构建一个quota对象，不更新数据库
        """
        quota = UserQuota()
        quota.user_id = user_id
        quota.service_id = self.service_id
        if self.tag == self.Tag.BASE:
            quota.tag = quota.TAG_BASE
        else:
            quota.tag = quota.TAG_PROBATION
        quota.vcpu_total = self.cpus
        quota.ram_total = self.ram
        quota.private_ip_total = self.private_ip
        quota.public_ip_total = self.public_ip
        quota.disk_size_total = self.disk_size
        quota.duration_days = self.duration_days
        quota.expiration_time = self.expiration_time
        return quota


class QuotaActivityGotRecord(UuidModel):
    got_time = models.DateTimeField(verbose_name=_('领取时间'), auto_now_add=True)
    user = models.ForeignKey(to=User, db_index=True, verbose_name=_('用户'),
                             on_delete=models.CASCADE, related_name='+')
    quota_activity = models.ForeignKey(to=QuotaActivity, db_index=True, verbose_name=_('配额活动'),
                                       on_delete=models.CASCADE, related_name='+')
    got_count = models.IntegerField(verbose_name=_('领取次数'), default=0)

    class Meta:
        db_table = 'quota_activity_got_record'
        ordering = ('-got_time',)
        verbose_name = _('配额活动领取记录')
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=('user', 'quota_activity'), name='unique_together_quota_activity_user')
        ]
