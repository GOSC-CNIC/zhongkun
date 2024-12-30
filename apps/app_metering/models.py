from decimal import Decimal

from django.db import models
from django.utils.translation import gettext, gettext_lazy as _

from utils.model import OwnerType, PayType, CustomIdModel
from utils import rand_utils
from apps.users.models import UserProfile
from apps.app_vo.models import VirtualOrganization
from apps.servers.models import Server
from apps.servers.models import ServiceConfig
from apps.storage.models import ObjectsService
from apps.app_monitor.models import MonitorWebsiteVersion


def short_uuid1_l25():
    return rand_utils.short_uuid1_25()


class PaymentStatus(models.TextChoices):
    UNPAID = 'unpaid', _('待支付')
    PAID = 'paid', _('已支付')
    CANCELLED = 'cancelled', _('作废')


class MeteringBase(CustomIdModel):
    original_amount = models.DecimalField(
        verbose_name=_('计费金额'), max_digits=10, decimal_places=2, default=Decimal(0))
    trade_amount = models.DecimalField(verbose_name=_('应付金额'), max_digits=10, decimal_places=2, default=Decimal(0))
    daily_statement_id = models.CharField(verbose_name=_('日结算单ID'), max_length=36, default='')

    class Meta:
        abstract = True

    def generate_id(self):
        return short_uuid1_l25()

    def is_owner_type_user(self):
        """
        所有者是否是用户，反之是vo组
        :return:
            True    # user
            False   # vo
            None    # invalid
        """
        raise NotImplemented('is_owner_type_user')

    def get_owner_id(self) -> str:
        """
        返回所有者的id, user id or vo id
        """
        raise NotImplemented('get_owner_id')

    def is_postpaid(self) -> bool:
        """
        是否是按量计费
        """
        raise NotImplemented('is_postpaid')

    def set_daily_statement_id(self, daily_statement_id: str = None):
        if self.daily_statement_id == daily_statement_id:
            return

        self.daily_statement_id = daily_statement_id if daily_statement_id else ''
        self.save(update_fields=['daily_statement_id'])


class MeteringServer(MeteringBase):
    """
    服务器云主机计量
    """
    OwnerType = OwnerType

    service = models.ForeignKey(to=ServiceConfig, verbose_name=_('服务'), related_name='+', null=True,
                                on_delete=models.SET_NULL, db_index=False)
    server_id = models.CharField(verbose_name=_('云服务器ID'), max_length=36)
    date = models.DateField(verbose_name=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)
    cpu_hours = models.FloatField(
        verbose_name=_('CPU Hour'), blank=True, default=0, help_text=_('云服务器的CPU Hour数'))
    ram_hours = models.FloatField(
        verbose_name=_('内存GiB Hour'), blank=True, default=0, help_text=_('云服务器的内存Gib Hour数'))
    disk_hours = models.FloatField(
        verbose_name=_('系统盘GiB Hour'), blank=True, default=0, help_text=_('云服务器的系统盘Gib Hour数'))
    public_ip_hours = models.FloatField(
        verbose_name=_('IP Hour'), blank=True, default=0, help_text=_('云服务器的公网IP Hour数'))
    snapshot_hours = models.FloatField(
        verbose_name=_('快照GiB Hour'), blank=True, default=0, help_text=_('云服务器的快照小时数'))
    upstream = models.FloatField(
        verbose_name=_('上行流量GiB'), blank=True, default=0, help_text=_('云服务器的上行流量Gib'))
    downstream = models.FloatField(
        verbose_name=_('下行流量GiB'), blank=True, default=0, help_text=_('云服务器的下行流量Gib'))
    pay_type = models.CharField(verbose_name=_('云服务器付费方式'), max_length=16, choices=PayType.choices)
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')
    vo_name = models.CharField(verbose_name=_('VO组名'), max_length=255, blank=True, default='')

    class Meta:
        verbose_name = _('云主机资源计量')
        verbose_name_plural = verbose_name
        db_table = 'metering_server'
        ordering = ['-creation_time']
        constraints = [
            models.constraints.UniqueConstraint(fields=['date', 'server_id'], name='unique_date_server')
        ]

    def __repr__(self):
        return gettext('云服务器资源计量') + f'[server id {self.server_id}]'

    def generate_id(self):
        return f's{short_uuid1_l25()}'       # 保证（订单号，云主机、云硬盘、对象存储计量id）唯一

    def is_owner_type_user(self):
        """
        所有者是否是用户，反之是vo组
        :return:
            True    # user
            False   # vo
            None    # invalid
        """
        if self.owner_type == OwnerType.USER.value:
            return True
        elif self.owner_type == OwnerType.VO.value:
            return False

        return None

    def get_owner_id(self) -> str:
        """
        返回所有者的id, user id or vo id
        """
        if self.is_owner_type_user():
            return self.user_id

        return self.vo_id

    def is_postpaid(self) -> bool:
        """
        是否是按量计费
        """
        return self.pay_type == PayType.POSTPAID.value


class MeteringDisk(MeteringBase):
    """
    云硬盘计量
    """
    OwnerType = OwnerType

    service = models.ForeignKey(to=ServiceConfig, verbose_name=_('服务'), related_name='+', null=True,
                                on_delete=models.SET_NULL, db_index=False)
    disk_id = models.CharField(verbose_name=_('云硬盘ID'), max_length=36)
    date = models.DateField(verbose_name=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)
    size_hours = models.FloatField(
        verbose_name=_('云硬盘GiB Hour'), blank=True, default=0, help_text=_('云硬盘Gib Hour数'))
    snapshot_hours = models.FloatField(
        verbose_name=_('快照GiB Hour'), blank=True, default=0, help_text=_('云硬盘快照GiB小时数'))
    pay_type = models.CharField(verbose_name=_('云硬盘付费方式'), max_length=16, choices=PayType.choices)
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')
    vo_name = models.CharField(verbose_name=_('VO组名'), max_length=255, blank=True, default='')

    class Meta:
        verbose_name = _('云硬盘资源计量')
        verbose_name_plural = verbose_name
        db_table = 'metering_disk'
        ordering = ['-creation_time']
        constraints = [
            models.constraints.UniqueConstraint(fields=['date', 'disk_id'], name='unique_date_disk')
        ]

    def __repr__(self):
        return gettext('云硬盘资源计量') + f'[disk id {self.disk_id}]'

    def generate_id(self):
        return f'd{short_uuid1_l25()}'       # 保证（订单号，云主机、云硬盘、对象存储计量id）唯一

    def is_owner_type_user(self):
        """
        所有者是否是用户，反之是vo组
        :return:
            True    # user
            False   # vo
            None    # invalid
        """
        if self.owner_type == OwnerType.USER.value:
            return True
        elif self.owner_type == OwnerType.VO.value:
            return False

        return None

    def get_owner_id(self) -> str:
        """
        返回所有者的id, user id or vo id
        """
        if self.is_owner_type_user():
            return self.user_id

        return self.vo_id

    def is_postpaid(self) -> bool:
        """
        是否是按量计费
        """
        return self.pay_type == PayType.POSTPAID.value


class MeteringObjectStorage(MeteringBase):
    """
    对象存储计量
    """
    service = models.ForeignKey(to=ObjectsService, verbose_name=_('服务'), related_name='+', null=True,
                                on_delete=models.SET_NULL, db_index=False)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True)
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')
    storage_bucket_id = models.CharField(
        verbose_name=_('存储桶实例ID'), max_length=36, default='', help_text=_('对象存储中间件存储桶实例id'))
    bucket_name = models.CharField(verbose_name=_('存储桶名称'), max_length=63)
    date = models.DateField(verbose_name=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    storage = models.FloatField(
        verbose_name=_('存储容量GiB*hours'), blank=True, default=0, help_text=_('存储桶的存储容量GiB小时数'))
    storage_byte = models.BigIntegerField(
        verbose_name=_('存储容量(字节)'), blank=True, default=0, help_text=_('计量时存储桶的存储容量字节数'))
    downstream = models.FloatField(
        verbose_name=_('下行流量GiB'), blank=True, default=0, help_text=_('存储桶的下行流量GiB'))
    replication = models.FloatField(
        verbose_name=_('同步流量GiB'), blank=True, default=0, help_text=_('存储桶的同步流量GiB'))
    get_request = models.IntegerField(verbose_name=_('get请求次数'), default=0, help_text=_('存储桶的get请求次数'))
    put_request = models.IntegerField(verbose_name=_('put请求次数'), default=0, help_text=_('存储桶的put请求次数'))
    billed_network_flow = models.FloatField(
        verbose_name=_('计费流量GiB'), blank=True, default=0, help_text=_('存储桶的计费流量GiB'))
    unbilled_network_flow = models.FloatField(
        verbose_name=_('非计费流量GiB'), blank=True, default=0, help_text=_('存储桶的非计费流量GiB'))

    class Meta:
        verbose_name = _('对象存储资源计量')
        verbose_name_plural = verbose_name
        db_table = 'metering_object_storage'
        ordering = ['-creation_time']
        constraints = [
            models.constraints.UniqueConstraint(
                fields=['date', 'storage_bucket_id'], name='unique_date_bucket'
            )
        ]

    def generate_id(self):
        return f'b{short_uuid1_l25()}'       # 保证（订单号，云主机、云硬盘、对象存储计量id）唯一

    def is_owner_type_user(self):
        """
        所有者是否是用户
        """
        return True

    def get_owner_id(self) -> str:
        """
        返回所有者的id, user id
        """
        return self.user_id

    def is_postpaid(self) -> bool:
        """
        是否是按量计费
        """
        return True


class MeteringMonitorWebsite(MeteringBase):
    """
    站点监控计量
    """
    website_id = models.CharField(verbose_name=_('监控站点ID'), max_length=36)
    website_name = models.CharField(verbose_name=_('监控站点名称'), max_length=255)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True)
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')
    date = models.DateField(verbose_name=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'))
    hours = models.FloatField(
        verbose_name=_('监控小时数'), blank=True, default=0, help_text=_('小时数'))
    detection_count = models.PositiveIntegerField(verbose_name=_('探测次数'), default=0)
    tamper_resistant_count = models.PositiveIntegerField(
        verbose_name=_('是否防篡改'), default=0, help_text=_('防篡改探测次数，记录站点监控是否设置防篡改监控服务'))
    security_count = models.PositiveIntegerField(
        verbose_name=_('是否安全扫描'), default=0, help_text=_('安全扫描次数，记录站点监控是否设置安全扫描服务'))

    class Meta:
        verbose_name = _('站点监控计量')
        verbose_name_plural = verbose_name
        db_table = 'metering_monitor_website'
        ordering = ['-creation_time']
        constraints = [
            models.constraints.UniqueConstraint(
                fields=['website_id', 'date'], name='unique_website_date'
            )
        ]

    def is_owner_type_user(self):
        """
        所有者是否是用户
        """
        return True

    def get_owner_id(self) -> str:
        """
        返回所有者的id, user id
        """
        return self.user_id

    def is_postpaid(self) -> bool:
        """
        是否是按量计费
        """
        return True


class DailyStatementBase(CustomIdModel):
    original_amount = models.DecimalField(
        verbose_name=_('计费金额'), max_digits=10, decimal_places=2, default=Decimal(0))
    payable_amount = models.DecimalField(verbose_name=_('应付金额'), max_digits=10, decimal_places=2, default=Decimal(0))
    trade_amount = models.DecimalField(verbose_name=_('实付金额'), max_digits=10, decimal_places=2, default=Decimal(0))
    payment_status = models.CharField(
        verbose_name=_('支付状态'), max_length=16, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID.value)
    payment_history_id = models.CharField(verbose_name=_('支付记录ID'), max_length=36, blank=True, default='')

    class Meta:
        abstract = True

    def generate_id(self):
        return short_uuid1_l25()

    def is_owner_type_user(self):
        """
        所有者是否是用户，反之是vo组
        :return:
            True    # user
            False   # vo
            None    # invalid
        """
        raise NotImplemented('is_owner_type_user')

    def get_owner_id(self) -> str:
        """
        返回所有者的id, user id or vo id
        """
        raise NotImplemented('get_owner_id')

    def set_paid(self, trade_amount: Decimal = None, payment_history_id: str = None):
        self.payment_history_id = payment_history_id if payment_history_id else ''
        self.trade_amount = self.payable_amount if trade_amount is None else trade_amount
        self.payment_status = PaymentStatus.PAID.value
        self.save(update_fields=['payment_history_id', 'trade_amount', 'payment_status'])

    def get_pay_app_service_id(self) -> str:
        """
        所属服务对应的余额结算中的app服务id
        """
        raise NotImplemented('get_pay_app_service_id')


class DailyStatementServer(DailyStatementBase):
    service = models.ForeignKey(to=ServiceConfig, verbose_name=_('服务'), related_name='+', null=True,
                                on_delete=models.SET_NULL, db_index=False)
    date = models.DateField(verbose_name=_('计费日期'), help_text=_('资源使用计量计费的日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    vo_name = models.CharField(verbose_name=_('VO组名'), max_length=255, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)

    class Meta:
        verbose_name = _('云主机每日账单')
        verbose_name_plural = verbose_name
        db_table = 'daily_statement_server'
        ordering = ['-creation_time']

    def generate_id(self):
        return f's{short_uuid1_l25()}'       # 保证（订单号，云主机、云硬盘、对象存储计量id）唯一

    def get_pay_app_service_id(self) -> str:
        """
        所属服务对应的余额结算中的app服务id
        """
        if self.service:
            return self.service.pay_app_service_id

        return ''

    def is_owner_type_user(self):
        """
        所有者是否是用户，反之是vo组
        :return:
            True    # user
            False   # vo
            None    # invalid
        """
        if self.owner_type == OwnerType.USER.value:
            return True
        elif self.owner_type == OwnerType.VO.value:
            return False

        return None

    def get_owner_id(self) -> str:
        """
        返回所有者的id, user id or vo id
        """
        if self.is_owner_type_user():
            return self.user_id

        return self.vo_id


class DailyStatementObjectStorage(DailyStatementBase):
    service = models.ForeignKey(to=ObjectsService, verbose_name=_('对象存储服务单元'), related_name='+', null=True,
                                on_delete=models.SET_NULL, db_index=False)
    date = models.DateField(verbose_name=_('计费日期'), help_text=_('资源使用计量计费的日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')

    class Meta:
        verbose_name = _('对象存储每日账单')
        verbose_name_plural = verbose_name
        db_table = 'daily_statement_storage'
        ordering = ['-creation_time']

    def generate_id(self):
        return f'o{short_uuid1_l25()}'       # 保证（订单号，云主机、云硬盘、对象存储计量id）唯一

    def get_pay_app_service_id(self) -> str:
        """
        所属服务对应的余额结算中的app服务id
        """
        if self.service:
            return self.service.pay_app_service_id

        return ''

    def is_owner_type_user(self):
        """
        所有者是否是用户，反之是vo组
        :return:
            True    # user
            False   # vo
            None    # invalid
        """
        return True

    def get_owner_id(self) -> str:
        """
        返回所有者的id, user id or vo id
        """
        return self.user_id


class DailyStatementDisk(DailyStatementBase):
    service = models.ForeignKey(to=ServiceConfig, verbose_name=_('服务单元'), related_name='+', null=True,
                                on_delete=models.SET_NULL, db_constraint=False, db_index=False)
    date = models.DateField(verbose_name=_('计费日期'), help_text=_('资源使用计量计费的日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')
    vo_id = models.CharField(verbose_name=_('VO组ID'), max_length=36, blank=True, default='')
    vo_name = models.CharField(verbose_name=_('VO组名'), max_length=255, blank=True, default='')
    owner_type = models.CharField(verbose_name=_('所有者类型'), max_length=8, choices=OwnerType.choices)

    class Meta:
        verbose_name = _('云硬盘每日账单')
        verbose_name_plural = verbose_name
        db_table = 'daily_statement_disk'
        ordering = ['-creation_time']

    def generate_id(self):
        return f'd{short_uuid1_l25()}'       # 保证（订单号，云主机、云硬盘、对象存储计量id）唯一

    def get_pay_app_service_id(self) -> str:
        """
        所属服务对应的余额结算中的app服务id
        """
        if self.service:
            return self.service.pay_app_service_id

        return ''

    def is_owner_type_user(self):
        """
        所有者是否是用户，反之是vo组
        :return:
            True    # user
            False   # vo
            None    # invalid
        """
        if self.owner_type == OwnerType.USER.value:
            return True
        elif self.owner_type == OwnerType.VO.value:
            return False

        return None

    def get_owner_id(self) -> str:
        """
        返回所有者的id, user id or vo id
        """
        if self.is_owner_type_user():
            return self.user_id

        return self.vo_id


class DailyStatementMonitorWebsite(DailyStatementBase):
    date = models.DateField(verbose_name=_('计费日期'), help_text=_('资源使用计量计费的日期'))
    creation_time = models.DateTimeField(verbose_name=_('创建时间'), auto_now_add=True)
    user_id = models.CharField(verbose_name=_('用户ID'), max_length=36, blank=True, default='')
    username = models.CharField(verbose_name=_('用户名'), max_length=128, blank=True, default='')

    class Meta:
        verbose_name = _('站点监控每日账单')
        verbose_name_plural = verbose_name
        db_table = 'daily_statement_mntr_site'
        ordering = ['-creation_time']

    def generate_id(self):
        return f'mw{short_uuid1_l25()}'       # 保证（订单号，云主机、云硬盘、对象存储、站点监控日结算单id）唯一

    def get_pay_app_service_id(self) -> str:
        """
        所属服务对应的余额结算中的app服务id
        """
        ins = MonitorWebsiteVersion.get_instance()
        return ins.pay_app_service_id

    def is_owner_type_user(self):
        """
        所有者是否是用户，反之是vo组
        :return:
            True    # user
        """
        return True

    def get_owner_id(self) -> str:
        """
        返回所有者的id, user id or vo id
        """
        return self.user_id
