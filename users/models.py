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

    class Roles(models.TextChoices):
        ORDINARY = 'ordinary', _('普通用户')
        VMS = 'vms-admin', _('云主机管理员')
        STORAGE = 'storage-admin', _('存储管理员')
        FEDERAL = 'federal-admin', _('联邦管理员')

    class SupporterRole(models.TextChoices):
        NONE = '', _('空')
        SUPPORTER = 'supporter', _('客服支持人员')

    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')
    telephone = models.CharField(verbose_name=_('电话'), max_length=11, default='')
    company = models.CharField(verbose_name=_('公司/单位'), max_length=255, default='')
    third_app = models.SmallIntegerField(verbose_name=_('第三方应用登录'), choices=THIRD_APP_CHOICES, default=NON_THIRD_APP)
    last_active = models.DateTimeField(verbose_name=_('最后活跃日期'), db_index=True, auto_now=True)
    role = models.JSONField(verbose_name=_('角色'), null=False, default=default_role,
                            help_text=f'角色选项(可多选)，{Roles.values}')
    # supporter_role = models.CharField(
    #     verbose_name=_('客服支持人员角色'), max_length=32, choices=SupporterRole.choices, default=SupporterRole.NONE.value)

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
        if 'role' in self.role and isinstance(self.role['role'], list):
            if self.Roles.FEDERAL in self.role['role']:
                return True

        return False

    def set_federal_admin(self) -> bool:
        """
        设为联邦管理员
        :raises: Exception
        """
        return self.set_role(self.Roles.FEDERAL)

    def set_role(self, role: str) -> bool:
        """
        设置用户角色

        :raises: Exception
        """
        if role not in self.Roles.values:
            raise Exception('无效的用户角色')

        if self.is_federal_admin():
            return True

        if 'role' in self.role and isinstance(self.role['role'], list):
            if role in self.role['role']:
                return True

            self.role['role'].append(role)
        else:
            self.role['role'] = [role]

        try:
            self.save(update_fields=['role'])
        except Exception as e:
            return False

        return True

    def unset_federal_admin(self) -> bool:
        """
        去除联邦管理员角色
        :raises: Exception
        """
        return self.unset_role(self.Roles.FEDERAL)

    def unset_role(self, role: str) -> bool:
        """
        设置用户角色

        :raises: Exception
        """
        if role not in self.Roles.values:
            raise Exception('无效的用户角色')

        if 'role' not in self.role or not isinstance(self.role['role'], list):
            return True

        if role not in self.role['role']:
            return True

        self.role['role'].remove(role)

        try:
            self.save(update_fields=['role'])
        except Exception as e:
            return False

        return True


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

    @classmethod
    def send_email(cls, subject: str, receivers: list, message: str, fail_silently=True):
        """
        发送用户激活邮件

        :param subject: 标题
        :param receivers: 接收者邮箱
        :param message: 邮件内容
        :param fail_silently: 是否抛出异常
        :return:
            Email()     # 发送成功
            None        # 发送失败
        """
        email = cls(
            subject=subject, receiver=receivers[0], message=message,
            sender=settings.EMAIL_HOST_USER,
            email_host=settings.EMAIL_HOST
        )

        ok = send_mail(
            subject=email.subject,  # 标题
            message=email.message,  # 内容
            from_email=email.sender,  # 发送者
            recipient_list=receivers,  # 接收者
            # html_message=self.message,    # 内容
            fail_silently=fail_silently,
        )
        if ok == 0:
            return None

        email.save(force_insert=True)  # 邮件记录
        return email
