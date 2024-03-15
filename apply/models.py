from django.db import models
from django.utils.translation import gettext_lazy as _

from utils.model import UuidModel, OwnerType
from users.models import UserProfile
from service.models import OrgDataCenter


class CouponApply(UuidModel):
    class Status(models.TextChoices):
        WAIT = 'wait', '待审批'
        CANCEL = 'cancel', _('取消')
        PENDING = 'pending', '审批中'
        REJECT = 'reject', '拒绝'
        PASS = 'pass', '通过'

    class ServiceType(models.TextChoices):
        SERVER = 'server', _('云主机')
        STORAGE = 'storage', _('对象存储')
        MONITOR_SITE = 'monitor-site', _('站点监控')
        SCAN = 'scan', _('安全扫描')

    # 券信息
    service_type = models.CharField(verbose_name=_('服务类型'), max_length=16, choices=ServiceType.choices)
    odc = models.ForeignKey(
        to=OrgDataCenter, verbose_name=_('数据中心'), on_delete=models.SET_NULL, null=True, blank=True, default=None)
    service_id = models.CharField(verbose_name=_('服务单元id'), max_length=36)
    service_name = models.CharField(verbose_name=_('服务单元名称'), max_length=255)
    service_name_en = models.CharField(verbose_name=_('服务单元英文名称'), max_length=255)
    pay_service_id = models.CharField(verbose_name=_('钱包结算单元id'), max_length=36)
    face_value = models.DecimalField(verbose_name=_('申请面额'), max_digits=10, decimal_places=2)
    expiration_time = models.DateTimeField(verbose_name=_('过期时间'))

    apply_desc = models.CharField(verbose_name=_('申请描述'), max_length=255)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    update_time = models.DateTimeField(verbose_name=_('更新时间'))
    user_id = models.CharField(verbose_name=_('申请人id'), max_length=36)
    username = models.CharField(verbose_name=_('申请人'), max_length=128)
    vo_id = models.CharField(verbose_name=_('项目组id'), max_length=36, blank=True, default='')
    vo_name = models.CharField(verbose_name=_('项目组名称'), max_length=128, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所属类型'), max_length=16, choices=OwnerType.choices)

    # 审批信息
    status = models.CharField(verbose_name=_('状态'), max_length=16, choices=Status.choices, default=Status.WAIT.value)
    approver = models.CharField(verbose_name=_('审批人'), max_length=128, blank=True, default='')
    reject_reason = models.CharField(verbose_name=_('拒绝原因'), max_length=255, blank=True, default='')
    approved_amount = models.DecimalField(verbose_name=_('审批通过金额'), max_digits=10, decimal_places=2)
    coupon_id = models.CharField(verbose_name=_('资源券id'), max_length=36, blank=True, default='')

    deleted = models.BooleanField(verbose_name=_('删除'), default=False)
    delete_user = models.CharField(verbose_name=_('删除人'), max_length=128, blank=True, default='')

    class Meta:
        db_table = 'apply_coupon'
        ordering = ['-creation_time']
        verbose_name = _('资源券申请')
        verbose_name_plural = verbose_name

        indexes = [
            models.Index(fields=('user_id',), name='idx_user_id'),
            models.Index(fields=('vo_id',), name='idx_vo_id')
        ]

    def __str__(self):
        return f'[{self.status}]({self.approved_amount}/{self.face_value}, {self.service_type}, {self.service_name})'
