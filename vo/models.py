from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models import UserProfile as User
from utils.model import UuidModel


class VirtualOrganization(UuidModel):
    """
    虚拟组
    """
    MAX_NUMBER_OF_MEMBERS = 1000            # A vo group has an upper limit of group members.

    class Status(models.TextChoices):
        ACTIVE = 'active', _('活动的')
        DISABLE = 'disable', _('禁用')

    name = models.CharField(verbose_name=_('组名'), max_length=256)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    owner = models.ForeignKey(verbose_name=_('所有者'), to=User, related_name='owner_vo_set',
                              on_delete=models.CASCADE)
    members = models.ManyToManyField(to=User, through='VoMember', through_fields=('vo', 'user'),
                                     related_name='members_vo_set')
    company = models.CharField(verbose_name=_('单位'), max_length=256, default='')
    description = models.CharField(verbose_name=_('组描述'), max_length=1024, default='')
    status = models.CharField(verbose_name=_('状态'), max_length=32,
                              choices=Status.choices, default=Status.ACTIVE)
    deleted = models.BooleanField(verbose_name=_('删除'), default=False)
    # members_count = models.PositiveIntegerField(verbose_name=_('组员数量'), default=1)

    class Meta:
        db_table = 'virtual_organization'
        ordering = ['creation_time']
        verbose_name = _('项目组')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def is_member(self, user):
        return self.members.filter(id=user.id).exists()

    def is_owner(self, user):
        return self.owner_id == user.id

    def soft_delete(self):
        self.deleted = True
        self.save(update_fields=['deleted'])


class VoMember(UuidModel):
    class Role(models.TextChoices):
        LEADER = 'leader', _('组管理员')
        MEMBER = 'member', _('组员')

    user = models.ForeignKey(verbose_name=_('用户'), to=User, on_delete=models.CASCADE)
    vo = models.ForeignKey(verbose_name=_('组'), to=VirtualOrganization, on_delete=models.CASCADE)
    role = models.CharField(verbose_name=_('组角色'), max_length=16, choices=Role.choices,
                            default=Role.MEMBER)
    join_time = models.DateTimeField(verbose_name=_('加入时间'), auto_now_add=True)
    inviter = models.CharField(verbose_name=_('邀请人'), max_length=256, blank=True, default='')
    inviter_id = models.CharField(verbose_name=_('邀请人ID'), blank=True, editable=False, max_length=36)

    class Meta:
        db_table = 'vo_member'
        ordering = ['join_time']
        verbose_name = _('组成员关系')
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=('vo', 'user'), name='unique_together_vo_user')
        ]

    def __str__(self):
        return f'{self.user.username}[{self.get_role_display()}]'

    @property
    def is_leader_role(self):
        return self.role == self.Role.LEADER
