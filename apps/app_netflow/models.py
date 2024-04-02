from django.db import models
from utils.model import UuidModel
from django.utils.translation import gettext_lazy as _


# Create your models here.
class ChartModel(UuidModel):
    """
    图表 Item

       全部---|
             |---图表1
             |---图标2
             |---图标3
    """
    name = models.CharField(max_length=100, verbose_name=_('图表名称'))
    expression = models.CharField(max_length=100, verbose_name=_('表达式'))
    mapping = models.TextField(blank=True, null=True, verbose_name=_("映射"))
    default = models.CharField(max_length=30, null=True, blank=True, default='', verbose_name=_("默认值"))
    unit = models.CharField(max_length=25, verbose_name=_('单位'))
    status = models.BooleanField(default=True, verbose_name=_("启用状态"))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), null=False, help_text=_('值越小排序越靠前'))
    remark = models.TextField(default='', null=True, blank=True, verbose_name=_('备注'))

    def __str__(self):
        return self.name

    class Meta:
        db_table = "netflow_chart"
        verbose_name = _("流量图表")
        ordering = ['sort_weight']
        verbose_name_plural = verbose_name


class MenuCategoryModel(UuidModel):
    """
    菜单栏 一级分类
    全部* 出口 机构 端口 项目 IP
    """
    name = models.CharField(max_length=255, verbose_name=_('名称'))
    sort_weight = models.IntegerField(verbose_name=_('排序值'), null=False, help_text=_('值越小排序越靠前'))
    remark = models.TextField(default='', null=True, blank=True, verbose_name=_('备注'))

    def __str__(self):
        return self.name

    class Meta:
        db_table = "netflow_menu_category"
        verbose_name = _("菜单栏一级分类")
        ordering = ['sort_weight']
        verbose_name_plural = verbose_name


class MenuModel(UuidModel):
    """
    菜单栏 二级分类
    全部---|
          |---机构---|
                    |----机构1
                    |----机构2
          |---出口---|
                    |----出口1
                    |----出口2

          |---组织---|
                    |---组织1
                    |---组织2
                    |---组织3

    """
    name = models.CharField(max_length=255, verbose_name=_('名称'))
    category = models.ForeignKey(
        null=True,
        to='MenuCategoryModel',
        on_delete=models.SET_NULL,
        related_name="sub_categories",
        related_query_name="sub_category",
        verbose_name=_('类别')
    )
    chart = models.ManyToManyField(
        to='ChartModel',
        blank=True,
        related_name="menu_list",
        related_query_name="menu",
        verbose_name=_('图表合集')
    )
    # 超管人员
    # administrators = models.ManyToManyField(
    #     to='users.UserProfile',
    #     on_delete=models.DO_NOTHING,
    #     related_name="admin_flow_organization_list",
    #     related_query_name="admin_flow_organization",
    #     verbose_name=_('超级管理员')
    # )
    sort_weight = models.IntegerField(verbose_name=_('排序值'), null=False, help_text=_('值越小排序越靠前'))
    remark = models.TextField(default='', null=True, blank=True, verbose_name=_('备注'))

    def __str__(self):
        return self.name

    class Meta:
        db_table = "netflow_menu"
        verbose_name = _("菜单栏")
        ordering = ['sort_weight']
        verbose_name_plural = verbose_name

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
