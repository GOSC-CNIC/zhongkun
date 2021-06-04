from uuid import uuid1

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _

from utils.model import UuidModel


def default_role():
    return {'role': []}


class UserProfile(AbstractUser):
    """
    自定义用户模型
    """
    NON_THIRD_APP = 0
    LOCAL_USER = NON_THIRD_APP
    THIRD_APP_KJY = 1   # 第三方科技云通行证

    THIRD_APP_CHOICES = (
        (LOCAL_USER, '本地用户'),
        (THIRD_APP_KJY, '科技云通行证')
    )

    ROLE_ORDINARY = 'ordinary'
    ROLE_VMS = 'vms-admin'
    ROLE_STORAGE = 'storage-admin'
    ROLE_FEDERAL = 'federal-admin'

    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')
    telephone = models.CharField(verbose_name=_('电话'), max_length=11, default='')
    company = models.CharField(verbose_name=_('公司/单位'), max_length=255, default='')
    third_app = models.SmallIntegerField(verbose_name=_('第三方应用登录'), choices=THIRD_APP_CHOICES, default=NON_THIRD_APP)
    last_active = models.DateTimeField(verbose_name=_('最后活跃日期'), db_index=True, auto_now=True)
    role = models.JSONField(verbose_name=_('角色'), null=False, default=default_role,
                            help_text=f'角色选项(可多选)，{[ROLE_ORDINARY, ROLE_VMS, ROLE_STORAGE, ROLE_FEDERAL]}')

    def get_full_name(self):
        if self.last_name.encode('UTF-8').isalpha() and self.first_name.encode('UTF-8').isalpha():
            return f'{self.first_name} {self.last_name}'.strip()

        return f'{self.last_name}{self.first_name}'.strip()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = str(uuid1())

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def is_federal_admin(self):
        """
        是否是联邦管理员
        """
        if hasattr(self.role, 'role') and isinstance(self.role['role'], list):
            if self.ROLE_FEDERAL in self.role['role']:
                return True

        return False


class Email(UuidModel):
    """
    邮件
    """
    email_host = models.CharField(max_length=255, verbose_name=_('邮件服务'))
    subject = models.CharField(max_length=255, verbose_name=_('标题'))
    sender = models.EmailField(verbose_name=_('发送者'), default='')
    receiver = models.EmailField(verbose_name=_('接收者'))
    message = models.TextField(verbose_name=_('邮件内容'))
    send_time = models.DateTimeField(verbose_name=_('发送时间'), auto_now_add=True)

    class Meta:
        ordering = ['-send_time']
        verbose_name = _('邮件')
        verbose_name_plural = verbose_name

    def send_email(self, subject='GOSC', receiver=None, message=None):
        """
        发送用户激活邮件

        :param subject: 标题
        :param receiver: 接收者邮箱
        :param message: 邮件内容
        :return: True(发送成功)；False(发送失败)
        """
        self.subject = subject
        if receiver:
            self.receiver = receiver
        if message:
            self.message = message

        self.sender = settings.EMAIL_HOST_USER
        self.email_host = settings.EMAIL_HOST

        ok = send_mail(
            subject=self.subject,  # 标题
            message=self.message,  # 内容
            from_email=self.sender,  # 发送者
            recipient_list=[self.receiver],  # 接收者
            # html_message=self.message,        # 内容
            fail_silently=True,  # 不抛出异常
        )
        if ok == 0:
            return False

        self.save()  # 邮件记录
        return True
