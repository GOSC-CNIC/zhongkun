from decimal import Decimal
from datetime import timedelta, datetime

from django.utils.translation import gettext as _
from django.utils import timezone
from django.db import transaction

from utils.model import OwnerType, PayType
from utils import rand_utils
from vo.managers import VoManager
from core import errors
from order.models import Order, Resource, ResourceType
from .instance_configs import BaseConfig, ServerConfig, DiskConfig, BucketConfig
from .price import PriceManager


class OrderManager:
    def create_order(
            self, order_type,
            service_id,
            pay_app_service_id: str,
            service_name,
            resource_type,
            instance_config,
            period,
            pay_type,
            user_id,
            username,
            vo_id,
            vo_name,
            owner_type,
            remark: str = ''
    ) -> (Order, Resource):
        """
        提交一个订单

        :instance_config: BaseConfig
        :return:
            order, resource

        :raises: Error
        """
        instance_id = rand_utils.short_uuid1_25()
        if resource_type == ResourceType.VM.value:
            instance_id += '-i'
        elif resource_type == ResourceType.DISK.value:
            instance_id += '-d'
        else:
            pass

        return self.create_order_for_resource(
            order_type=order_type, pay_type=pay_type,
            pay_app_service_id=pay_app_service_id, service_id=service_id, service_name=service_name,
            resource_type=resource_type, instance_id=instance_id, instance_config=instance_config,
            period=period, start_time=None, end_time=None,
            user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type,
            instance_remark=remark
        )

    def create_renew_order(
            self,
            pay_app_service_id: str, service_id, service_name,
            resource_type, instance_id: str, instance_config,
            period, start_time: datetime, end_time: datetime,
            user_id, username, vo_id, vo_name, owner_type
    ) -> (Order, Resource):
        """
        提交一个续费订单

        如果指定续费时长period, 必须start_time = end_time = None；
        如果指定续费到期日期，start_time 和 end_time必须同时有效， period=0

        :instance_id: 续费的实例id of (server, disk)
        :instance_config: BaseConfig
        :return:
            order, resource

        :raises: Error
        """
        return self.create_order_for_resource(
            order_type=Order.OrderType.RENEWAL.value, pay_type=PayType.PREPAID.value,
            pay_app_service_id=pay_app_service_id, service_id=service_id, service_name=service_name,
            resource_type=resource_type, instance_id=instance_id, instance_config=instance_config,
            period=period, start_time=start_time, end_time=end_time,
            user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type,
            instance_remark='renew'
        )

    def create_change_pay_type_order(
            self, pay_type: str,
            pay_app_service_id: str, service_id, service_name,
            resource_type, instance_id: str, instance_config,
            period, user_id, username, vo_id, vo_name, owner_type
    ) -> (Order, Resource):
        """
        提交一个修改计费方式订单

        :pay_type: prepaid(按量转包年包月)，postpaid(包年包月转按量)
        :instance_id: 续费的实例id of (server, disk)
        :instance_config: BaseConfig
        :return:
            order, resource

        :raises: Error
        """
        if pay_type == PayType.PREPAID.value:
            order_type = Order.OrderType.POST2PRE.value
        # elif pay_type == PayType.POSTPAID.value:
        #     order_type = Order.OrderType.PRE2POST.value
        else:
            raise errors.Error(message='invalid pay_type')

        return self.create_order_for_resource(
            order_type=order_type, pay_type=pay_type,
            pay_app_service_id=pay_app_service_id, service_id=service_id, service_name=service_name,
            resource_type=resource_type, instance_id=instance_id, instance_config=instance_config,
            period=period, start_time=None, end_time=None,
            user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type,
            instance_remark='post2prepaid'
        )

    def create_order_for_resource(
            self, order_type, pay_type,
            pay_app_service_id: str, service_id, service_name,
            resource_type, instance_id: str, instance_config,
            period: int, start_time, end_time,
            user_id, username, vo_id, vo_name, owner_type,
            instance_remark: str = ''
    ) -> (Order, Resource):
        """
        为资源实例提交一个订单，新购、续费、按量转包年包月

        # 续费
            * 如果指定续费时长period, 必须start_time = end_time = None；
            * 如果指定续费到期日期，start_time 和 end_time必须同时有效， period=0
        # 新购、按量转包年包月
            * 只能指定续费时长period, 必须start_time = end_time = None；

        :order_type: 订单类型
        :pay_type: 资源付费方式，预付费时会跟时长和资源类型配置计算金额
        :pay_app_service_id: 资源实例所属服务单元对应的余额结算里的app子服务id
        :service_id: 资源实例所属服务单元id
        :resource_type: 资源实例类型
        :instance_id: 资源实例id of (server, disk)
        :instance_config: BaseConfig
        :period: 时长，月数
        :return:
            order, resource

        :raises: Error
        """
        if period and (start_time or end_time):
            raise errors.Error(message=_('无法创建订单，不能同时指定时段起止时间和时长。'))

        if start_time or end_time:
            if not (start_time and end_time):
                raise errors.Error(message=_('无法创建订单，必须同时指定时段起始和终止时间。'))

            if period and period != 0:
                raise errors.Error(message=_('无法创建订单，不能同时指定时段起止时间和时长。'))

            if end_time <= start_time:
                raise errors.Error(message=_('无法创建订单，时间段不合法，时段终止时间不应小于起始时间。'))

            delta = end_time - start_time
            days = delta.days + delta.seconds / (3600 * 24)
            period = 0
        elif period:
            if period <= 0:
                raise errors.Error(message=_('无法创建订单，时长必须大于0。'))

            days = 0
        elif period == 0:   # 新购按量付费
            days = 0
        else:
            raise errors.Error(message=_('无法创建订单，必须指定时段或者时长。'))

        if owner_type not in OwnerType.values:
            raise errors.Error(message=_('无法创建订单，订单所属类型无效'))

        if resource_type not in ResourceType.values:
            raise errors.Error(message=_('无法创建订单，资源类型无效'))

        if order_type not in Order.OrderType.values:
            raise errors.Error(message=_('无法创建订单，订单类型无效或不支持'))

        if pay_type not in PayType.values:
            raise errors.Error(message=_('无法创建订单，资源计费方式pay_type无效'))
        if pay_type == PayType.PREPAID.value:         # 预付费
            if period == 0 and days == 0:
                raise errors.Error(message=_('无法创建订单，必须指定时段或者时长。'))
            total_amount, trade_price = self.calculate_amount_money(
                resource_type=resource_type, config=instance_config, is_prepaid=True, period=period, days=days)
        else:
            total_amount = trade_price = Decimal(0)

        order = Order(
            order_type=order_type,
            status=Order.Status.UNPAID.value,
            total_amount=total_amount,
            payable_amount=trade_price,
            pay_amount=Decimal('0'),
            balance_amount=Decimal('0'),
            coupon_amount=Decimal('0'),
            app_service_id=pay_app_service_id,
            service_id=service_id,
            service_name=service_name,
            resource_type=resource_type,
            instance_config=instance_config.to_dict(),
            period=period,
            pay_type=pay_type,
            payment_time=None,
            start_time=start_time,
            end_time=end_time,
            user_id=user_id,
            username=username,
            vo_id=vo_id,
            vo_name=vo_name,
            owner_type=owner_type,
            deleted=False,
            trading_status=Order.TradingStatus.OPENING.value,
            completion_time=None
        )

        with transaction.atomic():
            order.save(force_insert=True)
            resource = Resource(
                order=order, resource_type=resource_type,
                instance_id=instance_id, instance_remark=instance_remark, desc=''
            )
            resource.save(force_insert=True)

        return order, resource

    @staticmethod
    def calculate_amount_money(
            resource_type, config: BaseConfig, is_prepaid, period: int, days: float
    ) -> (Decimal, Decimal):
        """
        计算资源金额
        总时长 = period + days

        :param resource_type: 资源类型， vm、disk
        :param config: 资源配置
        :param is_prepaid: True(预付费)， False(按量计费)
        :param period: 预付费时长（月）
        :param days: 预付费时长天数
        """
        if resource_type == ResourceType.VM.value:
            if not isinstance(config, ServerConfig):
                raise errors.Error(message=_('无法计算资源金额，资源类型和资源规格配置不匹配'))

            original_price, trade_price = PriceManager().describe_server_price(
                ram_mib=config.vm_ram_mib, cpu=config.vm_cpu, disk_gib=config.vm_systemdisk_size,
                public_ip=config.vm_public_ip, is_prepaid=is_prepaid, period=period, days=days
            )
        elif resource_type == ResourceType.DISK.value:
            if not isinstance(config, DiskConfig):
                raise errors.Error(message=_('无法计算资源金额，资源类型和资源规格配置不匹配'))

            original_price, trade_price = PriceManager().describe_disk_price(
                size_gib=config.disk_size, is_prepaid=is_prepaid, period=period, days=days
            )
        elif resource_type == ResourceType.BUCKET.value:
            if not isinstance(config, BucketConfig):
                raise errors.Error(message=_('无法计算资源金额，资源类型和资源规格配置不匹配'))

            original_price = trade_price = Decimal(0)
        else:
            raise errors.Error(message=_('无法计算资源金额，资源类型无效'))

        return original_price, trade_price

    @staticmethod
    def get_order_queryset():
        return Order.objects.all()

    def filter_order_queryset(
            self, resource_type: str, order_type: str, status: str, time_start, time_end,
            user_id: str = None, vo_id: str = None
    ):
        """
        查询用户或vo组的订单查询集
        """
        queryset = self.get_order_queryset()
        if user_id:
            queryset = queryset.filter(user_id=user_id, owner_type=OwnerType.USER.value)

        if vo_id:
            queryset = queryset.filter(vo_id=vo_id, owner_type=OwnerType.VO.value)

        if time_start:
            queryset = queryset.filter(creation_time__gte=time_start)

        if time_end:
            queryset = queryset.filter(creation_time__lte=time_end)

        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)

        if order_type:
            queryset = queryset.filter(order_type=order_type)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-creation_time')

    def filter_vo_order_queryset(
            self, resource_type: str, order_type: str, status: str, time_start, time_end, user, vo_id: str
    ):
        """
        查询vo组的订单查询集

        :raises: AccessDenied
        """
        self._has_vo_permission(vo_id=vo_id, user=user)
        return self.filter_order_queryset(
            resource_type=resource_type, order_type=order_type, status=status, time_start=time_start,
            time_end=time_end, vo_id=vo_id
        )

    @staticmethod
    def get_order(order_id: str, select_for_update: bool = False):
        if select_for_update:
            return Order.objects.filter(id=order_id).select_for_update().first()

        return Order.objects.filter(id=order_id).first()

    @staticmethod
    def get_resource(resource_id: str, select_for_update: bool = False):
        if select_for_update:
            return Resource.objects.filter(id=resource_id).select_for_update().first()

        return Resource.objects.filter(id=resource_id).first()

    def get_order_detail(self, order_id: str, user, check_permission: bool = True, read_only: bool = True):
        """
        查询订单详情

        :param order_id: 订单id
        :param user: 用户对象
        :param check_permission: 是否检测权限
        :param read_only: 用于vo组权限检测；True：只需要访问权限；False: 需要管理权限
        :return:
            order, resources
        """
        order = self.get_order(order_id=order_id)
        if order is None:
            raise errors.NotFound(_('订单不存在'))

        # check permission
        if check_permission:
            if order.owner_type == OwnerType.USER.value:
                if order.user_id and order.user_id != user.id:
                    raise errors.AccessDenied(message=_('您没有此订单访问权限'))
            elif order.vo_id:
                self._has_vo_permission(vo_id=order.vo_id, user=user, read_only=read_only)

        resources = Resource.objects.filter(order_id=order_id).all()
        resources = list(resources)
        return order, resources

    @staticmethod
    def _has_vo_permission(vo_id, user, read_only: bool = True):
        """
        是否有vo组的权限

        :raises: AccessDenied
        """
        try:
            if read_only:
                VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
            else:
                VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=user)
        except errors.Error as exc:
            raise errors.AccessDenied(message=exc.message)

    @staticmethod
    def set_order_resource_deliver_ok(order: Order, resource: Resource, start_time, due_time, instance_id: str = None):
        """
        订单资源交付成功， 更新订单信息

        :return:
            order, resource    # success

        :raises: Error
        """
        message = ''
        with transaction.atomic():
            order = Order.objects.filter(id=order.id).select_for_update().first()
            if order.trading_status in [order.TradingStatus.CLOSED, order.TradingStatus.COMPLETED]:
                raise errors.Error(message=_('交易关闭和交易完成状态的订单不允许修改'))

            update_fields = ['trading_status']
            if order.pay_type != PayType.POSTPAID.value:
                order.start_time = start_time
                order.end_time = due_time
                update_fields += ['start_time', 'end_time']

            order.trading_status = order.TradingStatus.COMPLETED.value
            try:
                order.save(update_fields=update_fields)
            except Exception as e:
                message = _('更新订单交易状态失败') + str(e)

            resource.instance_status = resource.InstanceStatus.SUCCESS.value
            resource.desc = 'success'
            resource.delivered_time = timezone.now()
            update_fields = ['instance_status', 'desc', 'delivered_time']
            if instance_id:
                resource.instance_id = instance_id
                update_fields.append('instance_id')
            try:
                resource.save(update_fields=update_fields)
            except Exception as e:
                message += _('更新订单的资源交付结果失败') + str(e)

        if message:
            raise errors.Error(message=message)

        return order, resource

    @staticmethod
    def set_order_resource_deliver_failed(order: Order, resource: Resource, failed_msg: str):
        """
        订单资源交付失败， 更新订单信息

        :return:
            order, resource    # success

        :raises: Error
        """
        message = ''
        if len(failed_msg) >= 255:
            failed_msg = failed_msg[:255]

        with transaction.atomic():
            order = Order.objects.filter(id=order.id).select_for_update().first()
            if order.trading_status in [order.TradingStatus.CLOSED, order.TradingStatus.COMPLETED]:
                raise errors.Error(message=_('交易关闭和交易完成状态的订单不允许修改'))

            try:
                resource.instance_status = resource.InstanceStatus.FAILED.value
                resource.desc = failed_msg
                resource.save(update_fields=['instance_status', 'desc'])
            except Exception as e:
                message = _('更新订单的资源创建结果失败') + str(e)

            order.trading_status = order.TradingStatus.UNDELIVERED.value
            try:
                order.save(update_fields=['trading_status'])
            except Exception as e:
                message += _('更新订单交易状态失败') + str(e)

        if message:
            return errors.Error(message=message)

        return order, resource

    def cancel_order(self, order_id: str, user):
        """
        取消作废订单

        :return:
            order
        :raises: Error
        """
        order, resources = OrderManager().get_order_detail(
            order_id=order_id, user=user, check_permission=True, read_only=False
        )

        return self.do_cancel_order(order_id=order.id, resources=resources)

    def do_cancel_order(self, order_id: str, resources: list = None):
        try:
            with transaction.atomic():
                order = self.get_order(order_id=order_id, select_for_update=True)
                if order.trading_status == order.TradingStatus.CLOSED.value:
                    raise errors.OrderTradingClosed(message=_('订单交易已关闭'))
                elif order.trading_status == order.TradingStatus.COMPLETED.value:
                    raise errors.OrderTradingCompleted(message=_('订单交易已完成'))

                if order.status == Order.Status.PAID.value:
                    raise errors.OrderPaid(message=_('订单已支付'))
                elif order.status == Order.Status.CANCELLED.value:
                    raise errors.OrderCancelled(message=_('订单已作废'))
                elif order.status == Order.Status.REFUND.value:
                    raise errors.OrderRefund(message=_('订单已退款'))
                elif order.status != Order.Status.UNPAID.value:
                    raise errors.OrderStatusUnknown(message=_('未知状态的订单'))

                if resources:
                    resource = resources[0]
                    resource = self.get_resource(resource_id=resource.id, select_for_update=True)

                    time_now = timezone.now()
                    if resource.last_deliver_time is not None:
                        delta = time_now - resource.last_deliver_time
                        if delta < timedelta(minutes=2):
                            raise errors.TryAgainLater(message=_('为避免可能正在交付订单资源，请稍后重试'))
                try:
                    order.set_cancel()
                except Exception as e:
                    raise errors.Error(message=_('更新订单状态错误。') + str(e))

                return order
        except errors.Error as exc:
            raise exc
        except Exception as exc:
            raise errors.Error(message=str(exc))
