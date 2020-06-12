import random
import string

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from tinymce import models as tiny_models

User = get_user_model()
app_name = 'vpn'


def rand_string(length=10):
    """
    生成随机字符串

    :param length: 字符串长度
    :return:
        str
    """
    if length <= 0:
        return ''

    return ''.join(random.sample(string.ascii_letters + string.digits, length))


class VPNAuth(models.Model):
    """
    VPN登录认证model
    """
    id = models.AutoField(verbose_name='ID', primary_key=True)
    user = models.OneToOneField(to=User, on_delete=models.CASCADE, related_name='vpn_auth', verbose_name='用户')
    password = models.CharField(verbose_name='VPN口令', max_length=20, default='')
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    modified_time = models.DateTimeField(auto_now=True, verbose_name='修改时间')

    class Meta:
        db_table = 'vpn_auth'     # 数据库表名
        ordering = ('-id',)
        verbose_name = 'VPN口令'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'<VPNAuth>{self.password}'

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if not self.password or len(self.password) < 6:
            self.password = rand_string()

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def reset_password(self, password):
        if self.password == password:
            return True

        self.password = password
        try:
            self.save(update_fields=['password', 'modified_time'])
        except Exception as e:
            return False

        return True

    def check_password(self, password):
        return self.password == password


class Article(models.Model):
    """
    文章模型
    """
    LANG_UNKNOWN = 0
    LANG_CHINESE = 1
    LANG_ENGLISH = 2
    LANG_CHOICES = (
        (LANG_CHINESE, _('中文')),
        (LANG_ENGLISH, _('英文')),
    )

    LANG_MAP = {
        'zh-hans': LANG_CHINESE,
        'en': LANG_ENGLISH
    }

    TOPIC_VPN_USAGE = 1
    TOPIC_CHOICES = (
        (TOPIC_VPN_USAGE, _('VPN使用方法')),
    )

    id = models.AutoField(primary_key=True, verbose_name='ID')
    topic = models.SmallIntegerField(choices=TOPIC_CHOICES, default=TOPIC_VPN_USAGE, verbose_name=_('主题'))
    lang = models.SmallIntegerField(choices=LANG_CHOICES, default=LANG_CHINESE, verbose_name=_('语言'))
    title = models.CharField(max_length=255, verbose_name=_('标题'))
    summary = models.CharField(max_length=255, default='', blank=True, verbose_name=_('概述'),
                               help_text=_('可以为空'))
    author = models.CharField(max_length=255, blank=True, default='', verbose_name=_('作者'))
    content = tiny_models.HTMLField(default='', verbose_name=_('正文内容'))
    create_time = models.DateTimeField(auto_now_add=True, verbose_name=_('创建时间'))
    modify_time = models.DateTimeField(auto_now=True, verbose_name=_('修改时间'))
    enable = models.BooleanField(default=False, verbose_name=_('发布状态'),
                                 help_text=_('是否发布可见，默认不发布可见，一般在文章编辑完成后再发布可见'))

    class Meta:
        indexes = [
            models.Index(fields=('title',), name='idx_article_title'),
            models.Index(fields=('create_time',), name='idx_article_create_time'),
        ]
        unique_together = ['topic', 'lang']
        ordering = ['-id']
        verbose_name = _('文章')
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title

    def __repr__(self):
        return f'<Article>{self.title}'

    @staticmethod
    def get_lang_value_by_code(lang_code: str):
        """
        获取语言简码对应的文章语言字段的值

        :param lang_code: 语言简码
        :return: int
            >0   # success
            0   # not found
        """
        try:
            return Article.LANG_MAP[lang_code]
        except KeyError as e:
            return Article.LANG_UNKNOWN
