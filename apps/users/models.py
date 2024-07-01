from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.mail import send_mail
from django.utils.translation import gettext_lazy as _
from django.utils import timezone as dj_timezone

from utils.model import UuidModel
from utils.rand_utils import short_uuid1_25


class UserProfile(AbstractUser):
    """
    自定义用户模型
    """
    class ThirdApp(models.IntegerChoices):
        LOCAL_USER = 0, _('本地用户')
        KJY_PASSPORT = 1, _('科技云通行证')
        AAI = 2, _('身份认证联盟AAI')

    class Roles(models.TextChoices):
        ORDINARY = 'ordinary', _('普通用户')
        FEDERAL = 'federal-admin', _('联邦管理员')

    class SupporterRole(models.TextChoices):
        NONE = '', _('空')
        SUPPORTER = 'supporter', _('客服支持人员')

    id = models.CharField(blank=True, editable=False, max_length=36, primary_key=True, verbose_name='ID')
    telephone = models.CharField(verbose_name=_('电话'), max_length=11, default='')
    company = models.CharField(verbose_name=_('公司/单位'), max_length=255, default='')
    third_app = models.SmallIntegerField(
        verbose_name=_('第三方应用登录'), choices=ThirdApp.choices, default=ThirdApp.LOCAL_USER.value)
    last_active = models.DateTimeField(verbose_name=_('最后活跃日期'), db_index=True, auto_now=True)
    is_fed_admin = models.BooleanField(verbose_name=_('联邦管理员'), default=False)
    # supporter_role = models.CharField(
    #     verbose_name=_('客服支持人员角色'), max_length=32, choices=SupporterRole.choices, default=SupporterRole.NONE.value)

    def get_full_name(self):
        if self.last_name.encode('UTF-8').isalpha() and self.first_name.encode('UTF-8').isalpha():
            return f'{self.first_name} {self.last_name}'.strip()

        return f'{self.last_name}{self.first_name}'.strip()

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if not self.id:
            self.id = short_uuid1_25()

        super().save(force_insert=force_insert, force_update=force_update, using=using, update_fields=update_fields)

    def is_federal_admin(self):
        """
        是否是联邦管理员
        """
        return self.is_fed_admin

    def set_federal_admin(self) -> bool:
        """
        设为联邦管理员
        :raises: Exception
        """
        return self.set_fed_admin(is_fed=True)

    def unset_federal_admin(self) -> bool:
        """
        去除联邦管理员角色
        :raises: Exception
        """
        return self.set_fed_admin(is_fed=False)

    def set_fed_admin(self, is_fed: bool):
        if self.is_fed_admin is not is_fed:
            self.is_fed_admin = is_fed
            try:
                self.save(update_fields=['is_fed_admin'])
            except Exception as exc:
                return False

        return True


class Email(UuidModel):
    """
    邮件
    """
    class Tag(models.TextChoices):
        YEAR = 'year', _('年度报表')
        MONTH = 'month', _('月度报表')
        TICKET = 'ticket', _('工单通知')
        COUPON = 'coupon', _('资源券通知')
        RES_EXP = 'res-exp', _('资源过期通知')
        ARREAR = 'arrear', _('欠费通知')
        API = 'api', _('API请求')
        OTHER = 'other', _('其他')

    class Status(models.TextChoices):
        WAIT = 'wait', _('待发送')
        SUCCESS = 'success', _('发送成功')
        FAILED = 'failed', _('发送失败')

    email_host = models.CharField(max_length=255, verbose_name=_('邮件服务'))
    subject = models.CharField(max_length=255, verbose_name=_('标题'))
    sender = models.EmailField(verbose_name=_('发送者'), default='')
    receiver = models.CharField(verbose_name=_('接收者'), max_length=254)
    message = models.TextField(verbose_name=_('邮件内容'))
    send_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    tag = models.CharField(verbose_name=_('标签'), max_length=16, choices=Tag.choices, default=Tag.OTHER.value)
    is_html = models.BooleanField(verbose_name='html格式信息', default=False)
    status = models.CharField(
        verbose_name=_('发送状态'), max_length=16, choices=Status.choices, default=Status.SUCCESS.value)
    status_desc = models.CharField(max_length=255, verbose_name=_('状态描述'), default='')
    success_time = models.DateTimeField(verbose_name=_('成功发送时间'), null=True, blank=True, default=None)
    remote_ip = models.CharField(max_length=64, verbose_name=_('客户端ip'), default='')
    is_feint = models.BooleanField(verbose_name=_('假动作，不真实发送'), default=False)

    class Meta:
        ordering = ['-send_time']
        verbose_name = _('邮件')
        verbose_name_plural = verbose_name

    @classmethod
    def send_email(cls, subject: str, receivers: list, message: str, tag: str, html_message: str = None,
                   fail_silently=True, save_db: bool = True, remote_ip: str = '', is_feint: bool = False):
        """
        发送邮件

        :param subject: 标题
        :param receivers: 接收者邮箱
        :param tag: 标签
        :param message: 邮件内容
        :param html_message: html格式的邮件内容
        :param fail_silently: 是否抛出异常
        :param save_db: True(保存邮件记录到数据库)；False(不保存)
        :param remote_ip: 客户端ip地址
        :param is_feint: True(假动作，只入库不真实发送)；False(真实发送邮件)
        :return:
            Email()     # 发送成功
            None        # 发送失败
        """
        receiver_str = ';'.join(receivers)
        if len(receiver_str) >= 254:
            receiver_str = receiver_str[:254]
            receiver_str = receiver_str.rsplit(';', maxsplit=1)[0]

        email = cls(
            subject=subject, receiver=receiver_str, message=message,
            sender=settings.EMAIL_HOST_USER,
            email_host=settings.EMAIL_HOST,
            tag=tag, is_html=False, status=cls.Status.WAIT.value, status_desc='', success_time=None,
            remote_ip=remote_ip, is_feint=is_feint
        )
        if html_message:
            email.message = html_message
            email.is_html = True
            message = ''

        if save_db:
            email.save(force_insert=True)  # 邮件记录

        if is_feint:    # 假动作，不真实发送
            return email

        try:
            ok = send_mail(
                subject=email.subject,  # 标题
                message=message,  # 内容
                from_email=email.sender,  # 发送者
                recipient_list=receivers,  # 接收者
                html_message=html_message,    # 内容
                fail_silently=False,
            )
            if ok == 0:
                raise Exception('failed')
        except Exception as exc:
            email.set_send_failed(desc=str(exc), save_db=save_db)
            if not fail_silently:
                raise exc

            return None

        email.set_send_success(desc='', save_db=save_db)
        return email

    def set_send_failed(self, desc: str, save_db: bool = True):
        self.status = self.Status.FAILED.value
        self.status_desc = desc
        self.success_time = None
        if save_db:
            self.save(update_fields=['status', 'success_time', 'status_desc'])

    def set_send_success(self, desc: str, save_db: bool = True):
        self.status = self.Status.SUCCESS.value
        self.success_time = dj_timezone.now()
        self.status_desc = desc
        if save_db:
            self.save(update_fields=['status', 'success_time', 'status_desc'])
