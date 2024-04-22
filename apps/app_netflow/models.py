from django.db import models
from utils.model import UuidModel
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError


# Create your models here.
class ChartModel(UuidModel):
    """
    端口流量图表 Item

       全部---|
             |---图表1
             |---图表2
             |---图表3
    """
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

    def __str__(self):
        return f'{self.instance_name} | {self.if_alias} | {self.device_ip} | {self.port_name}'

    class Meta:
        db_table = "netflow_chart"
        verbose_name = _("图表管理")
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
        blank=True,
        related_name="menu_set",
        related_query_name="menu",
        verbose_name=_('流量图表集')
    )
    level = models.PositiveSmallIntegerField(editable=False, null=False, default=0, verbose_name=_('菜单级别'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), default=-1, help_text=_('值越小排序越靠前'))
    remark = models.TextField(default='', null=True, blank=True, verbose_name=_('备注'))

    def __str__(self):
        return self.name

    def clean(self):
        root = self.__class__.objects.filter(father=None).first()
        if root:  # 存在根节点
            if self != root and not self.father:  # 当前节点非根节点
                raise ValidationError('请选择上级菜单')
            if self == root and self.father:  # 当前节点是根节点
                raise ValidationError('无法设置该菜单节点的上级菜单')
        else:  # 不存在根节点
            if self.name != '全部':
                raise ValidationError('请先创建菜单-全部')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.enforce_id()
        if self.__class__.objects.all().count() == 0:  # 根节点配置
            self.id = '0'
            self.level = 0
        elif not self.level:
            self.level = self.father.level + 1

        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields)

    class Meta:
        db_table = "netflow_menu"
        verbose_name = _("菜单管理")
        ordering = ['level', 'sort_weight']
        verbose_name_plural = verbose_name
        unique_together = (
            ('father', 'name')
        )


class RoleModel(UuidModel):
    """
    角色组管理：
        超管：可以修改所有节点，可以查看所有节点;
        管理员：可以查看所有节点;
        普通用户： 只可以看到特定图表，图表上方的隐私数据（两条备注）选择是否开放给用户（一条或者两个）;

    """
    name = models.CharField(max_length=255, verbose_name=_('组名称'))

    class Roles(models.TextChoices):
        ORDINARY = 'ordinary', _('普通用户')
        ADMIN = 'admin', _('管理员')
        SUPER_ADMIN = 'super-admin', _('超级管理员')

    role = models.CharField(
        verbose_name=_('组类别'), max_length=16, choices=Roles.choices, default=Roles.ORDINARY.value)

    charts = models.ManyToManyField(
        to='ChartModel',
        blank=True,
        related_name="role_set",
        related_query_name="role",
        verbose_name=_('图表权限')
    )
    users = models.ManyToManyField(
        "users.UserProfile",
        blank=True,
        verbose_name=_("组员"),
        related_name="netflow_role_set",
        related_query_name="netflow_role",
    )

    sort_weight = models.IntegerField(verbose_name=_('排序值'), null=False, help_text=_('值越小排序越靠前'))
    remark = models.TextField(default='', null=True, blank=True, verbose_name=_('备注'))

    def __str__(self):
        return self.name

    class Meta:
        db_table = "netflow_role"
        verbose_name = _("角色组管理")
        ordering = ['sort_weight']
        verbose_name_plural = verbose_name

# class MenuFirstModel(UuidModel):
#     """
#     一级菜单
#     """
#     name = models.CharField(max_length=255, verbose_name=_('名称'))
#     sort_weight = models.IntegerField(verbose_name=_('排序值'), null=False, help_text=_('值越小排序越靠前'))
#     remark = models.TextField(default='', null=True, blank=True, verbose_name=_('备注'))
#     chart = models.ManyToManyField(
#         to='ChartModel',
#         blank=True,
#         related_name="first_menu_set",
#         related_query_name="first_menu",
#         verbose_name=_('图表合集')
#     )
#
#     def __str__(self):
#         return self.name
#
#     class Meta:
#         db_table = "netflow_menu_first"
#         verbose_name = _("一级菜单")
#         ordering = ['sort_weight']
#         verbose_name_plural = verbose_name
#

# class MenuSecondModel(UuidModel):
#     """
#     二级菜单
#     """
#     category = models.ForeignKey(
#         null=True,
#         to='MenuFirstModel',
#         on_delete=models.SET_NULL,
#         related_name="second_menu_set",
#         related_query_name="second_menu",
#         verbose_name=_('一级菜单')
#     )
#     name = models.CharField(max_length=255, verbose_name=_('名称'))
#     chart = models.ManyToManyField(
#         to='ChartModel',
#         blank=True,
#         related_name="second_menu_set",
#         related_query_name="second_menu",
#         verbose_name=_('图表合集')
#     )
#     sort_weight = models.IntegerField(verbose_name=_('排序值'), null=False, help_text=_('值越小排序越靠前'))
#     remark = models.TextField(default='', null=True, blank=True, verbose_name=_('备注'))
#
#     def __str__(self):
#         return self.name
#
#     class Meta:
#         db_table = "netflow_menu_second"
#         verbose_name = _("二级菜单")
#         ordering = ['sort_weight']
#         verbose_name_plural = verbose_name
#
#
# class MenuThirdModel(UuidModel):
#     """
#     三级菜单
#     """
#     category = models.ForeignKey(
#         null=True,
#         to='MenuSecondModel',
#         on_delete=models.SET_NULL,
#         related_name="third_menu_set",
#         related_query_name="third_menu",
#         verbose_name=_('二级菜单')
#     )
#     name = models.CharField(max_length=255, verbose_name=_('名称'))
#     chart = models.ManyToManyField(
#         to='ChartModel',
#         blank=True,
#         related_name="third_menu_set",
#         related_query_name="third_menu",
#         verbose_name=_('图表合集')
#     )
#     sort_weight = models.IntegerField(verbose_name=_('排序值'), null=False, help_text=_('值越小排序越靠前'))
#     remark = models.TextField(default='', null=True, blank=True, verbose_name=_('备注'))
#
#     def __str__(self):
#         return self.name
#
#     class Meta:
#         db_table = "netflow_menu_third"
#         verbose_name = _("三级菜单")
#         ordering = ['sort_weight']
#         verbose_name_plural = verbose_name
#


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
