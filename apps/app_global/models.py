import ipaddress

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

from utils.model import UuidModel
from utils.iprestrict import convert_iprange


class TimedTaskLock(UuidModel):
    class Task(models.TextChoices):
        METERING = 'metering', _('计量计费')
        BKT_MONTHLY = 'bkt-monthly', _('存储桶月度统计')
        REPORT_MONTHLY = 'report-monthly', _('月度报表')
        LOG_TIME_COUNT = 'log-time-count', _('日志时序统计')
        REQ_COUNT = 'req-count', _('服务请求量统计')
        SCAN = 'scan', _('安全扫描')
        SCREEN_HOST_CPUUSAGE = 'screen_host_cpuusage', _('大屏展示主机CPU使用率')
        SCREEN_SERVICE_STATS = 'screen_service_stats', _('大屏展示服务单元统计数据')
        SCREEN_USER_OPERATE_LOG = 'scree_user_operate_log', _('大屏展示用户操作日志')
        SCREEN_HOST_NETFLOW = 'screen_host_netflow', _('大屏展示主机单元网络流量')
        ALERT_EMAIL = 'alert_email', _('告警邮件通知')
        ALERT_DINGTALK = 'alert_dingtalk', _('告警钉钉通知')
        NETFLOW_UPDATE_ELEMENT = 'netflow_update_element', _('流量图表元素更新')

    class Status(models.TextChoices):
        NONE = 'none', _('无')
        RUNNING = 'running', _('执行中')

    task = models.CharField(verbose_name=_('定时任务'), max_length=32, choices=Task.choices)
    status = models.CharField(verbose_name=_('状态'), max_length=16, choices=Status.choices, default=Status.NONE.value)
    start_time = models.DateTimeField(verbose_name=_('执行开始时间'), null=True, blank=True, default=None)
    end_time = models.DateTimeField(verbose_name=_('执行结束时间'), null=True, blank=True, default=None)
    host = models.CharField(verbose_name=_('执行任务的节点IP'), max_length=64, blank=True, default='')
    run_desc = models.CharField(verbose_name=_('执行结果描述'), max_length=255, blank=True, default='')
    expire_time = models.DateTimeField(verbose_name=_('锁定过期时间'), null=True, blank=True, default=None)
    notify_time = models.DateTimeField(
        verbose_name=_('锁过期未释放通知时间'), null=True, blank=True, default=None,
        help_text=_('用于记录邮件通知发送时间，避免重复发送'))

    class Meta:
        db_table = 'global_timetasklock'
        ordering = ['id']
        verbose_name = _('定时任务状态锁')
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=('task',), name='unique_lock_task')
        ]

    def __str__(self):
        return f'[{self.get_status_display()}]({self.status})'


class GlobalConfig(models.Model):
    class ConfigName(models.TextChoices):
        SITE_NAME = 'site_name', _('站点名称')
        SITE_NAME_EN = 'site_name_en', _('站点英文名称')
        SITE_FRONT_URL = 'site_front_url', _('站点前端地址')
        AAI_LOGIN_NAME = 'aai_login_name', _('AAI登录，名称')
        AAI_LOGIN_CLIENT_CALLBACK_URL = 'aai_login_client_callback_url', _('AAI登录，本服务认证回调地址')
        AAI_LOGIN_URL = 'aai_login_url', _('AAI登录，登录地址')
        AAI_LOGIN_TOKEN_URL = 'aai_login_token_url', _('AAI登录，token查询地址')
        AAI_LOGIN_USER_INFO_URL = 'aai_login_user_info_url', _('AAI登录，用户信息查询地址')
        AAI_LOGIN_CLIENT_ID = 'aai_login_client_id', _('AAI登录，客户端id')
        AAI_LOGIN_CLIENT_SECRET = 'aai_login_client_secret', _('AAI登录，客户端密钥')

    # 配置的默认值，自动创建配置参数记录时填充的默认值
    value_defaults = {
        ConfigName.SITE_NAME.value: 'YunKun',
        ConfigName.SITE_NAME_EN.value: 'YunKun',
        ConfigName.SITE_FRONT_URL.value: '',
        ConfigName.AAI_LOGIN_NAME.value: '中国科技云身份认证联盟(CSTCLOUD AAI)',
        ConfigName.AAI_LOGIN_CLIENT_CALLBACK_URL.value: 'https://{your hostname}/auth/callback/aai',
        ConfigName.AAI_LOGIN_URL.value: 'https://aai.cstcloud.net/oidc/authorize',
        ConfigName.AAI_LOGIN_TOKEN_URL.value: 'https://aai.cstcloud.net/oidc/token',
        ConfigName.AAI_LOGIN_USER_INFO_URL.value: 'https://aai.cstcloud.net/oidc/userinfo',
        ConfigName.AAI_LOGIN_CLIENT_ID.value: '',
        ConfigName.AAI_LOGIN_CLIENT_SECRET.value: '',

    }

    id = models.BigAutoField(primary_key=True)
    name = models.CharField(verbose_name=_('配置名称'), max_length=32, choices=ConfigName.choices)
    value = models.CharField(verbose_name=_('配置内容'), max_length=255, default='')
    remark = models.CharField(verbose_name=_('备注'), blank=True, max_length=255)
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'global_config'
        ordering = ['creation_time']
        verbose_name = _('站点参数')
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=('name',), name='unique_global_config_name')
        ]

    def __str__(self):
        return f'[{self.name}] {self.value}'


class IPAccessWhiteList(models.Model):
    class ModuleName(models.TextChoices):
        SCREEN = 'screen', _('大屏展示')
        EMAIL = 'email', _('邮件发送API')
        ALERT = 'alert-receiver', _('告警接收API')
        PORTAL = 'portal', _('Portal门户接口')

    id = models.BigAutoField(primary_key=True)
    module_name = models.CharField(
        verbose_name=_('功能模块'), max_length=32, choices=ModuleName.choices, help_text=_('此IP白名单适用的功能模块'))
    ip_value = models.CharField(
        verbose_name=_('IP'), max_length=100, help_text='192.168.1.1、 192.168.1.1/24、192.168.1.66 - 192.168.1.100')
    remark = models.CharField(verbose_name=_('备注'), max_length=255, blank=True, default='')
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    update_time = models.DateTimeField(verbose_name=_('更新时间'), auto_now=True)

    class Meta:
        db_table = 'global_ipaccesswhitelist'
        ordering = ['-creation_time']
        verbose_name = _('IP访问白名单')
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.id}({self.ip_value})'

    def clean(self):
        try:
            subnet = convert_iprange(self.ip_value)
        except Exception as exc:
            raise ValidationError({'ip_value': str(exc)})

        if isinstance(subnet, ipaddress.IPv4Network):
            self.ip_value = str(subnet)

        obj = IPAccessWhiteList.objects.exclude(id=self.id).filter(
            ip_value=self.ip_value, module_name=self.module_name).first()
        if obj:
            raise ValidationError({
                'ip_value': _('功能模块"{module_name}"已存在相同的IP白名单({value})').format(
                    module_name=self.get_module_name_display(), value=self.ip_value
                )})
