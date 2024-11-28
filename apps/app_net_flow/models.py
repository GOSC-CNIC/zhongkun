import json
from django.db import models
from utils.model import UuidModel
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.contrib.admin.models import ADDITION
from django.contrib.admin.models import DELETION
from django.contrib.admin.models import CHANGE
from django.contrib.admin.models import ACTION_FLAG_CHOICES
from django.contrib.admin.models import LogEntryManager
from django.conf import settings
from django.utils.translation import gettext
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.utils.text import get_text_list


# Create your models here.
class ChartModel(UuidModel):
    """
    端口流量图表 Item

       全部---|
             |---图表1
             |---图表2
             |---图表3
    """
    title = models.CharField(max_length=255, null=True, blank=True, default='', verbose_name=_('标题'))
    instance_uuid = models.CharField(max_length=255, null=True, blank=True, default='', )
    instance_name = models.CharField(max_length=255, null=True, blank=True, default='', )
    if_alias = models.CharField(max_length=255, null=True, blank=True, default='', verbose_name=_('别名'))
    if_address = models.CharField(max_length=255, null=True, blank=True, default='', )
    device_ip = models.CharField(max_length=255, null=False, blank=False, default='', verbose_name=_('IP'))
    port_name = models.CharField(max_length=255, null=False, blank=False, default='', verbose_name=_('端口'))
    class_uuid = models.CharField(max_length=255, null=True, blank=True, default='', )
    class_name = models.CharField(max_length=255, null=True, blank=True, default='', )
    band_width = models.PositiveIntegerField(default=0, verbose_name=_('带宽'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=-1, help_text=_('值越小排序越靠前'))
    remark = models.TextField(null=True, blank=True, default='', verbose_name=_('备注'))
    creation = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    modification = models.DateTimeField(verbose_name=_('修改时间'), auto_now=True)
    is_reverse = models.BooleanField(default=False, verbose_name=_('上传流量和下载流量是否反转'))

    def __str__(self):
        return f'{self.instance_name} | {self.if_alias} | {self.device_ip} | {self.port_name}'

    class Meta:
        db_table = "netflow_chart"
        verbose_name = _("元素管理")
        ordering = ['sort_weight']
        verbose_name_plural = verbose_name
        unique_together = (
            ('device_ip', 'port_name')
        )


class MenuModel(UuidModel):
    """
    菜单栏
    """
    name = models.CharField(max_length=255, verbose_name=_('名称'))
    father = models.ForeignKey(
        null=True,
        blank=True,
        to='self',
        on_delete=models.SET_NULL,
        related_name="sub_categories",
        related_query_name="children",
        verbose_name=_('上级菜单')
    )
    charts = models.ManyToManyField(
        to='ChartModel',
        through='Menu2Chart',
        through_fields=('menu', 'chart'),
        related_name="menu_set",
        related_query_name="menu",
        verbose_name=_('流量图表集')
    )
    members = models.ManyToManyField(
        to='users.UserProfile',
        through='Menu2Member',
        through_fields=('menu', 'member'),
        related_name="netflow_group_set",
        related_query_name="netflow_group",
        verbose_name=_('组员')
    )
    level = models.IntegerField(editable=False, null=False, default=-1, verbose_name=_('组级别'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=-1, help_text=_('值越小排序越靠前'))
    remark = models.TextField(default='', null=True, blank=True, verbose_name=_('备注'))

    def __str__(self):
        return self.name

    def clean(self):
        root = self.__class__.objects.filter(father=None).first()
        if root:  # 存在根节点
            if self != root and not self.father:  # 当前节点是子节点节点 且没有上级分组
                raise ValidationError({"father_id": _('请选择上级分组')})
            if self != root and self == self.father:  # 不能设置自身为上级分组
                raise ValidationError({"father_id": _('无法设置自身为上级分组')})
            if self == root and self.father:  # 当前节点是根节点
                raise ValidationError({"father_id": _('无法设置`根节点`的上级分组')})
            if self.father.level + 1 >= 3:
                raise ValidationError({"father_id": _("仅支持三层组结构")})
        else:  # 不存在根节点
            if self.name != '全部':
                raise ValidationError(_('请先创建分组-全部'))

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.enforce_id()
        if self.__class__.objects.count() == 0:  # 根节点配置
            self.id = 'root'
        elif self.father:  # 子节点
            self.level = self.father.level + 1
        self.full_clean()
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields)

    class Meta:
        db_table = "netflow_menu"
        verbose_name = _("组结构管理")
        ordering = ['level', 'sort_weight']
        verbose_name_plural = verbose_name
        unique_together = (
            ('father', 'name')
        )


class Menu2Chart(UuidModel):
    menu = models.ForeignKey(to='MenuModel', null=False, on_delete=models.DO_NOTHING, verbose_name='组')
    chart = models.ForeignKey(to='ChartModel', null=False, on_delete=models.DO_NOTHING, verbose_name='组元素')
    remark = models.CharField(max_length=255, null=False, blank=True, default='', verbose_name=_('备注'))
    admin_remark = models.CharField(max_length=255, null=False, blank=True, default='', verbose_name=_('管理员备注'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'),
                                      null=False,
                                      blank=True,
                                      default=-1,
                                      help_text=_('值越小排序越靠前'))

    def __str__(self):
        return f'{self.menu} | {self.chart}'

    class Meta:
        db_table = "netflow_menu2chart"
        verbose_name = _("组-元素")
        ordering = ['sort_weight']
        verbose_name_plural = verbose_name
        unique_together = (
            ('menu', 'chart')
        )


class Menu2Member(UuidModel):
    """
    组成员
    """
    menu = models.ForeignKey(to='MenuModel', null=False, on_delete=models.DO_NOTHING, verbose_name='组')
    member = models.ForeignKey(to='users.UserProfile', null=False, on_delete=models.DO_NOTHING, verbose_name='组成员')

    class Roles(models.TextChoices):
        ORDINARY = 'ordinary', _('组员')
        GROUP_ADMIN = 'group-admin', _('网络流量组管理员')

    role = models.CharField(
        verbose_name=_('角色'), max_length=16, choices=Roles.choices, default=Roles.ORDINARY.value)
    inviter = models.CharField(max_length=128, editable=False, verbose_name=_('邀请人'))
    creation = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    modification = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    def __str__(self):
        return '{} | {}'.format(self.menu, self.member)

    class Meta:
        db_table = "netflow_menu2member"
        verbose_name = _("组-成员")
        ordering = ['creation', 'modification']
        verbose_name_plural = verbose_name
        unique_together = (
            ('menu', 'member')
        )


class GlobalAdminModel(UuidModel):
    member = models.OneToOneField(
        to='users.UserProfile',
        null=False,
        on_delete=models.DO_NOTHING,
        verbose_name=_('用户'))

    class Roles(models.TextChoices):
        ADMIN = 'admin', _('网络流量运维管理员')
        SUPER_ADMIN = 'super-admin', _('网络流量超级管理员')

    role = models.CharField(
        verbose_name=_('角色'), max_length=16, choices=Roles.choices, default=Roles.ADMIN.value)
    inviter = models.CharField(max_length=128, default='', editable=False, verbose_name=_('邀请人'))
    creation = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    modification = models.DateTimeField(verbose_name='修改时间', auto_now=True)

    def __str__(self):
        return f"网络流量全局管理员 | {self.member}"

    class Meta:
        db_table = "netflow_globaladmin"
        verbose_name = _("01_网络流量全局用户角色")
        ordering = ['creation', 'modification']
        verbose_name_plural = verbose_name


class NetflowLogEntryModel(UuidModel):
    action_time = models.DateTimeField(
        _("action time"),
        default=timezone.now,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        models.CASCADE,
        verbose_name=_("user"),
    )
    content_type = models.ForeignKey(
        ContentType,
        models.SET_NULL,
        verbose_name=_("content type"),
        blank=True,
        null=True,
    )
    object_id = models.TextField(_("object id"), blank=True, null=True)
    object_repr = models.CharField(_("object repr"), max_length=200)
    action_flag = models.PositiveSmallIntegerField(
        _("action flag"), choices=ACTION_FLAG_CHOICES
    )
    change_message = models.TextField(_("change message"), blank=True)

    objects = LogEntryManager()

    class Meta:
        verbose_name = _("流量模块操作日志")
        db_table = "netflow_action_log"
        ordering = ["-action_time"]
        verbose_name_plural = verbose_name

    def __repr__(self):
        return str(self.action_time)

    def __str__(self):
        if self.is_addition():
            return gettext("Added “%(object)s”.") % {"object": self.object_repr}
        elif self.is_change():
            return gettext("Changed “%(object)s” — %(changes)s") % {
                "object": self.object_repr,
                "changes": self.get_change_message(),
            }
        elif self.is_deletion():
            return gettext("Deleted “%(object)s.”") % {"object": self.object_repr}

        return gettext("LogEntry Object")

    def is_addition(self):
        return self.action_flag == ADDITION

    def is_change(self):
        return self.action_flag == CHANGE

    def is_deletion(self):
        return self.action_flag == DELETION

    def get_change_message(self):
        """
        If self.change_message is a JSON structure, interpret it as a change
        string, properly translated.
        """
        if self.change_message and self.change_message[0] == "[":
            try:
                change_message = json.loads(self.change_message)
            except json.JSONDecodeError:
                return self.change_message
            messages = []
            for sub_message in change_message:
                if "added" in sub_message:
                    if sub_message["added"]:
                        sub_message["added"]["name"] = gettext(
                            sub_message["added"]["name"]
                        )
                        messages.append(
                            gettext("Added {name} “{object}”.").format(
                                **sub_message["added"]
                            )
                        )
                    else:
                        messages.append(gettext("Added."))

                elif "changed" in sub_message:
                    sub_message["changed"]["fields"] = get_text_list(
                        [
                            gettext(field_name)
                            for field_name in sub_message["changed"]["fields"]
                        ],
                        gettext("and"),
                    )
                    if "name" in sub_message["changed"]:
                        sub_message["changed"]["name"] = gettext(
                            sub_message["changed"]["name"]
                        )
                        messages.append(
                            gettext("Changed {fields} for {name} “{object}”.").format(
                                **sub_message["changed"]
                            )
                        )
                    else:
                        messages.append(
                            gettext("Changed {fields}.").format(
                                **sub_message["changed"]
                            )
                        )

                elif "deleted" in sub_message:
                    sub_message["deleted"]["name"] = gettext(
                        sub_message["deleted"]["name"]
                    )
                    messages.append(
                        gettext("Deleted {name} “{object}”.").format(
                            **sub_message["deleted"]
                        )
                    )

            change_message = " ".join(msg[0].upper() + msg[1:] for msg in messages)
            return change_message or gettext("No fields changed.")
        else:
            return self.change_message

# class RoleModel(UuidModel):
#     """
#     角色组管理：
#         超管：可以修改所有节点，可以查看所有节点;
#         管理员：可以查看所有节点;
#         普通用户： 只可以看到特定图表，图表上方的隐私数据（两条备注）选择是否开放给用户（一条或者两个）;
#
#     """
#     name = models.CharField(max_length=255, verbose_name=_('组名称'))
#
#     class Roles(models.TextChoices):
#         ORDINARY = 'ordinary', _('普通用户')
#         ADMIN = 'admin', _('管理员')
#         SUPER_ADMIN = 'super-admin', _('超级管理员')
#
#     role = models.CharField(
#         verbose_name=_('组类别'), max_length=16, choices=Roles.choices, default=Roles.ORDINARY.value)
#     users = models.ManyToManyField(
#         "users.UserProfile",
#         blank=True,
#         verbose_name=_("组员"),
#         related_name="netflow_role_set",
#         related_query_name="netflow_role",
#     )
#
#     sort_weight = models.IntegerField(verbose_name=_('排序值'), null=False, help_text=_('值越小排序越靠前'))
#     remark = models.TextField(default='', null=True, blank=True, verbose_name=_('备注'))
#
#     def __str__(self):
#         return self.name
#
#     class Meta:
#         db_table = "netflow_role"
#         verbose_name = _("角色组管理")
#         ordering = ['sort_weight']
#         verbose_name_plural = verbose_name


# class CollectCategoryModel(UuidModel):
#     """
#     收藏夹分类
#     """
#     name = models.CharField(max_length=100, verbose_name=_('类别'))
#     sort_weight = models.IntegerField(verbose_name=_('排序值'), null=False, help_text=_('值越小排序越靠前'))
#     remark = models.TextField(default='', verbose_name=_('备注'))
#
#     class Meta:
#         db_table = "netflow_collect_category"
#         verbose_name = _("收藏夹分类")
#         ordering = ['sort_weight']
#         verbose_name_plural = verbose_name


# class ChartCollectModel(UuidModel):
#     """
#     用户关注的数据图表 可以进行收藏
#     """
#     category = models.ForeignKey(
#         to='CollectCategoryModel',
#         on_delete=models.SET_NULL,
#         related_name="collect_list",
#         related_query_name="collect",
#         verbose_name=_('收藏夹类别')
#     )
#
#     chart = models.ManyToManyField(
#         to='ChartModel',
#         blank=True,
#         on_delete=models.DO_NOTHING,
#         related_name="collect_list",
#         related_query_name="collect",
#         verbose_name=_('图表合集')
#     )
#
#     user = models.OneToOneField(
#         null=False,
#         to="users.UserProfile",
#         unique=True,
#         on_delete=models.DO_NOTHING,
#         related_name="chart_collect",
#         verbose_name=_('用户')
#     )
#
#     class Meta:
#         db_table = "chart_collect"
#         verbose_name = _("个人收藏")
#         ordering = ['sort_weight']
#         verbose_name_plural = verbose_name
