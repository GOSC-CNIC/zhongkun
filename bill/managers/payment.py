from decimal import Decimal
from typing import List

from django.utils.translation import gettext as _
from django.db import transaction

from core import errors
from utils.model import OwnerType
from bill.models import PaymentHistory, UserPointAccount, VoPointAccount, CashCouponPaymentHistory
from metering.models import MeteringBase, PaymentStatus
from order.models import Order
from activity.managers import CashCouponManager
from activity.models import CashCoupon


class PaymentManager:
    @staticmethod
    def get_user_point_account(user_id: str, select_for_update: bool = False):
        if select_for_update:
            user_account = UserPointAccount.objects.select_for_update().select_related('user').filter(
                user_id=user_id).first()
        else:
            user_account = UserPointAccount.objects.select_related('user').filter(user_id=user_id).first()

        if user_account is None:
            upa = UserPointAccount(user_id=user_id, balance=Decimal(0))
            upa.save(force_insert=True)
            if select_for_update:
                user_account = UserPointAccount.objects.select_for_update().select_related('user').filter(
                    user_id=user_id).first()
            else:
                user_account = upa

        return user_account

    @staticmethod
    def get_vo_point_account(vo_id: str, select_for_update: bool = False):
        if select_for_update:
            vo_account = VoPointAccount.objects.select_for_update().select_related('vo').filter(vo_id=vo_id).first()
        else:
            vo_account = VoPointAccount.objects.select_related('vo').filter(vo_id=vo_id).first()

        if vo_account is None:
            vpa = VoPointAccount(vo_id=vo_id, balance=Decimal(0))
            vpa.save(force_insert=True)
            if select_for_update:
                vo_account = VoPointAccount.objects.select_for_update().select_related('vo').filter(
                    vo_id=vo_id).first()
            else:
                vo_account = vpa

        return vo_account

    def has_enough_balance_user(
            self, user_id: str, money_amount: Decimal,
            with_coupons: bool, service_id: str
    ):
        """
        用户是否有足够的余额
        :return:
            True        # 满足
            False
        """
        user_account = self.get_user_point_account(user_id=user_id)
        total_coupon_balance = user_account.balance
        if with_coupons:
            coupons = CashCouponManager().get_user_cash_coupons(
                user_id=user_id, coupon_ids=None, select_for_update=False
            )

            # 适用的券
            usable_coupons, unusable_coupons = CashCouponManager.sorting_usable_coupons(
                coupons=coupons, service_id=service_id
            )

            for c in usable_coupons:
                total_coupon_balance += c.balance

        return total_coupon_balance >= money_amount

    def has_enough_balance_vo(
            self, vo_id: str, money_amount: Decimal,
            with_coupons: bool, service_id: str
    ):
        """
        vo组是否有足够的余额
        :return:
            True        # 满足
            False
        """
        vo_account = self.get_vo_point_account(vo_id=vo_id)
        total_coupon_balance = vo_account.balance
        if with_coupons:
            coupons = CashCouponManager().get_vo_cash_coupons(
                vo_id=vo_id, coupon_ids=None, select_for_update=False
            )
            # 适用的券
            usable_coupons, unusable_coupons = CashCouponManager.sorting_usable_coupons(
                coupons=coupons, service_id=service_id
            )

            for c in usable_coupons:
                total_coupon_balance += c.balance

        return total_coupon_balance >= money_amount

    @staticmethod
    def _pre_payment_bill_inspect(metering_bill: MeteringBase, remark: str):
        """
        支付bill前检查

        :raises: Error
        """
        # bill status
        if metering_bill.payment_status == PaymentStatus.PAID.value:
            raise errors.Error(message=_('不能支付已支付状态的账单'))
        elif metering_bill.payment_status == PaymentStatus.CANCELLED.value:
            raise errors.Error(message=_('不能支付作废状态的账单'))
        elif metering_bill.payment_status != PaymentStatus.UNPAID.value:
            raise errors.Error(message=_('只允许支付待支付状态的账单'))

        if metering_bill.is_owner_type_user() is None:
            raise errors.Error(message=_('支付人类型无效'))

        if len(remark) >= 255:
            raise errors.Error(message=_('备注信息超出允许长度'))

    def pay_metering_bill(
            self, metering_bill: MeteringBase, app_id: str, subject: str,
            executor: str, remark: str, required_enough_balance: bool = True
    ):
        """
        支付计量计费账单

        :param metering_bill: MeteringBase子类对象
        :param app_id:
        :param subject: 标题
        :param executor: bill支付的执行人
        :param remark: 支付记录备注信息
        :param required_enough_balance: 是否要求余额必须足够支付，默认True(必须有足够的余额支付)，False(允许余额为负)
        :return: None
        :raises: Error
        """
        with transaction.atomic():
            bill = type(metering_bill).objects.select_for_update().get(id=metering_bill.id)
            return self._pay_metering_bill(
                metering_bill=bill, app_id=app_id, subject=subject,
                executor=executor, remark=remark,
                required_enough_balance=required_enough_balance
            )

    def _pay_metering_bill(
            self, metering_bill: MeteringBase, app_id: str, subject: str,
            executor: str, remark: str, required_enough_balance: bool
    ):
        """
        支付计量计费账单

        :param metering_bill: MeteringBase子类对象
        :param executor: bill支付的执行人
        :param remark: 备注信息
        :return: None
        :raises: Error, BalanceNotEnough
        """
        self._pre_payment_bill_inspect(metering_bill=metering_bill, remark=remark)
        if not metering_bill.is_postpaid():
            try:
                metering_bill.set_paid(trade_amount=Decimal(0))
            except Exception as e:
                raise errors.Error(message=_('计量计费账单更新为已支付状态时错误.') + str(e))

            return None

        try:
            owner_id = metering_bill.get_owner_id()
            service_id = metering_bill.get_service_id()
            instance_id = metering_bill.get_instance_id()
            resource_type = metering_bill.get_resource_type()
            order_id = metering_bill.id
            if metering_bill.is_owner_type_user():
                pay_history = self.pay_by_user(
                    user_id=owner_id, app_id=app_id, subject=subject,
                    amounts=metering_bill.original_amount, executor=executor,
                    remark=remark, order_id=order_id,
                    service_id=service_id, resource_type=resource_type, instance_id=instance_id,
                    required_enough_balance=required_enough_balance,
                    coupon_ids=None, only_coupon=False
                )
            else:
                pay_history = self.pay_by_vo(
                    vo_id=owner_id, app_id=app_id, subject=subject,
                    amounts=metering_bill.original_amount, executor=executor,
                    remark=remark, order_id=order_id,
                    service_id=service_id, resource_type=resource_type, instance_id=instance_id,
                    required_enough_balance=required_enough_balance,
                    coupon_ids=None, only_coupon=False
                )

            # 订单支付状态
            pay_amount = -(pay_history.amounts + pay_history.coupon_amount)
            # 账单支付状态
            metering_bill.set_paid(trade_amount=pay_amount, payment_history_id=pay_history.id)
        except errors.Error as exc:
            raise exc
        except Exception as exc:
            raise errors.Error.from_error(exc)

    def pay_order(
            self, order,
            app_id: str,
            subject: str,
            executor: str,
            remark: str,
            coupon_ids: list = None,
            only_coupon: bool = False,
            required_enough_balance: bool = True
    ):
        """
        支付一个订单

        :param order: Order()
        :param app_id:
        :param subject: 标题
        :param executor: 支付执行人
        :param remark: 支付记录备注信息
        :param coupon_ids: 支付使用指定id的券；None(不指定券，使用所有券)；[](空，指定不使用券，只使用余额)；
        :param only_coupon: True(只是用代金券支付)
        :param required_enough_balance: 是否要求余额必须足够支付，默认True(必须有足够的余额支付)，False(允许余额为负)
        :return: Order()
        :raises: Error, BalanceNotEnough
        """
        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().get(id=order.id)
                order = self._pay_order(
                    order=order, app_id=app_id, subject=subject,
                    executor=executor, remark=remark,
                    coupon_ids=coupon_ids, only_coupon=only_coupon,
                    required_enough_balance=required_enough_balance
                )
                return order
        except errors.Error as exc:
            raise exc
        except Exception as exc:
            raise errors.Error.from_error(exc)

    def _pay_order(
            self, order: Order,
            app_id: str,
            subject: str,
            executor: str,
            remark: str,
            coupon_ids: list,
            only_coupon: bool,
            required_enough_balance: bool
    ):
        """
        支付一个订单

        :raises: Error
        """
        self._pre_pay_order(order=order, remark=remark)
        if order.total_amount == Decimal(0):
            # 订单支付状态
            order.set_paid(pay_amount=order.total_amount, payment_method=Order.PaymentMethod.UNKNOWN.value)
            return order

        if order.owner_type == OwnerType.USER.value:
            pay_history = self.pay_by_user(
                user_id=order.user_id, app_id=app_id, subject=subject,
                amounts=order.total_amount, executor=executor,
                remark=remark, order_id=order.id,
                service_id=order.service_id, resource_type=order.resource_type, instance_id='',
                required_enough_balance=required_enough_balance,
                coupon_ids=coupon_ids, only_coupon=only_coupon
            )
        else:
            pay_history = self.pay_by_vo(
                vo_id=order.vo_id, app_id=app_id, subject=subject,
                amounts=order.total_amount, executor=executor,
                remark=remark, order_id=order.id,
                service_id=order.service_id, resource_type=order.resource_type, instance_id='',
                required_enough_balance=required_enough_balance,
                coupon_ids=coupon_ids, only_coupon=only_coupon
            )

        # 订单支付状态
        pay_amount = -(pay_history.amounts + pay_history.coupon_amount)
        if pay_history.amounts == Decimal('0'):
            payment_method = Order.PaymentMethod.CASH_COUPON.value
        else:
            payment_method = Order.PaymentMethod.BALANCE.value
        order.set_paid(pay_amount=pay_amount, payment_method=payment_method)
        return order

    @staticmethod
    def _pre_pay_order(order: Order, remark: str):
        """
        :raises: Error
        """
        if order.status == Order.Status.PAID.value:
            raise errors.OrderPaid(_('不能支付已支付状态的订单'))
        elif order.status == Order.Status.CANCELLED.value:
            raise errors.OrderCancelled(message=_('不能支付作废状态的订单'))
        elif order.status != PaymentStatus.UNPAID.value:
            raise errors.OrderNotUnpaid(message=_('只允许支付待支付状态的订单'))

        if order.trading_status == order.TradingStatus.CLOSED.value:
            raise errors.OrderTradingClosed(message=_('订单交易已关闭'))
        elif order.trading_status == order.TradingStatus.COMPLETED.value:
            raise errors.OrderTradingCompleted(message=_('订单交易已完成'))
        if order.trading_status != Order.TradingStatus.OPENING.value:
            raise errors.Error(message=_('订单未处于交易中'))

        if order.owner_type not in OwnerType.values:
            raise errors.Error(message=_('订单所有者类型无效'))

        if len(remark) >= 255:
            raise errors.Error(message=_('备注信息超出允许长度'))

    def pay_by_user(
            self, user_id: str,
            app_id: str,
            subject: str,
            amounts: Decimal,
            executor: str,
            remark: str,
            order_id: str,
            service_id: str,
            resource_type: str,
            instance_id: str,
            coupon_ids: list = None,
            only_coupon: bool = False,
            required_enough_balance: bool = True
    ):
        """
        * coupon_ids: 支付使用指定id的券；None(不指定券，使用所有券)；[](空，指定不使用券)；
        """
        with transaction.atomic():
            return self._pay_by_user_or_vo(
                user_id=user_id,
                vo_id='',
                app_id=app_id,
                subject=subject,
                amounts=amounts,
                coupon_ids=coupon_ids,
                executor=executor,
                remark=remark,
                order_id=order_id,
                resource_type=resource_type,
                service_id=service_id,
                instance_id=instance_id,
                only_coupon=only_coupon,
                required_enough_balance=required_enough_balance
            )

    def pay_by_vo(
            self, vo_id: str,
            app_id: str,
            subject: str,
            amounts: Decimal,
            executor: str,
            remark: str,
            order_id: str,
            service_id: str,
            resource_type: str,
            instance_id: str,
            coupon_ids: List[CashCoupon] = None,
            only_coupon: bool = False,
            required_enough_balance: bool = True
    ):
        """
        * coupon_ids: 支付使用指定id的券；None(不指定券，使用所有券)；[](空，指定不使用券)；
        """
        with transaction.atomic():
            return self._pay_by_user_or_vo(
                user_id='',
                vo_id=vo_id,
                app_id=app_id,
                subject=subject,
                amounts=amounts,
                coupon_ids=coupon_ids,
                executor=executor,
                remark=remark,
                order_id=order_id,
                resource_type=resource_type,
                service_id=service_id,
                instance_id=instance_id,
                only_coupon=only_coupon,
                required_enough_balance=required_enough_balance
            )

    def _pre_pay_by_user_or_vo(
            self, user_id: str,
            vo_id: str,
            service_id: str,
            coupon_ids: List[CashCoupon] = None
    ):
        """
        支付前检查验证

        :param coupon_ids: 支付使用指定id的券；None(不指定券，使用所有券)；[](空，指定不使用券)；
        :raises: Error
        """
        if user_id and vo_id:
            raise errors.ConflictError(message=_('不能能同时指定参数"user_id"和“vo_id”，无法确认使用用户还是vo组账户支付'))

        if vo_id:
            coupons = CashCouponManager().get_vo_cash_coupons(
                vo_id=vo_id, coupon_ids=coupon_ids, select_for_update=True
            )
            account = self.get_vo_point_account(vo_id=vo_id, select_for_update=True)
            payer_id = vo_id
            payer_name = account.vo.name
            payer_type = OwnerType.VO.value
        else:
            coupons = CashCouponManager().get_user_cash_coupons(
                user_id=user_id, coupon_ids=coupon_ids, select_for_update=True
            )
            account = self.get_user_point_account(user_id=user_id, select_for_update=True)
            payer_id = user_id
            payer_name = account.user.username
            payer_type = OwnerType.USER.value

        # 适用的券
        usable_coupons, unusable_coupons = CashCouponManager.sorting_usable_coupons(
            coupons=coupons, service_id=service_id
        )
        if coupon_ids:
            if unusable_coupons:
                raise errors.ConflictError(
                    message=_('指定的券%(value)s不能用于此服务资源的支付') % {'value': unusable_coupons[0].id},
                    code='CouponNotApplicable'
                )

            for c in usable_coupons:
                if c.balance <= Decimal(0):
                    raise errors.ConflictError(
                        message=_('指定的券%(value)s没有可用余额') % {'value': usable_coupons[0].id},
                        code='CouponNoBalance'
                    )

        return (
            account, usable_coupons, payer_id, payer_name, payer_type
        )

    def _pay_by_user_or_vo(
            self,
            user_id: str,
            vo_id: str,
            app_id: str,
            subject: str,
            amounts: Decimal,
            executor: str,
            remark: str,
            order_id: str,
            service_id: str,
            resource_type: str,
            instance_id: str,
            coupon_ids: List[CashCoupon],
            only_coupon: bool = False,
            required_enough_balance: bool = True
    ):
        """
        * 发生错误时，函数中已操作修改的数据库数据不会手动回滚，此函数需要在事务中调用以保证数据一致性
        """
        account, usable_coupons, payer_id, payer_name, payer_type = self._pre_pay_by_user_or_vo(
            user_id=user_id, vo_id=vo_id, coupon_ids=coupon_ids, service_id=service_id
        )

        total_coupon_balance = Decimal(0)
        for c in usable_coupons:
            total_coupon_balance += c.balance

        if only_coupon:
            if amounts > total_coupon_balance:
                raise errors.BalanceNotEnough(message=_('代金券的余额不足'), code='CouponBalanceNotEnough')
        elif required_enough_balance:
            if amounts > (total_coupon_balance + account.balance):
                raise errors.BalanceNotEnough()

        if (
            only_coupon or                      # 只用代金券支付
            total_coupon_balance >= amounts     # 代金券余额足够支付
        ):
            payment_method = PaymentHistory.PaymentMethod.CASH_COUPON.value
            coupon_amount = amounts
            account_amount = Decimal(0)  # 账户余额扣款额
            payment_account = ''
        elif total_coupon_balance <= Decimal(0):    # 无可用券,只用余额支付
            payment_method = PaymentHistory.PaymentMethod.BALANCE.value
            coupon_amount = Decimal(0)  # 券扣款额
            account_amount = amounts
            payment_account = account.id
        else:           # 券+余额一起支付
            payment_method = PaymentHistory.PaymentMethod.BALANCE_COUPON.value
            coupon_amount = total_coupon_balance
            account_amount = amounts - coupon_amount
            payment_account = account.id

        # 账户扣款
        before_payment = account.balance
        after_payment = before_payment - account_amount
        if account.balance != after_payment:
            account.balance = after_payment
            account.save(update_fields=['balance'])

        # 支付记录
        pay_history = PaymentHistory(
            payment_account=payment_account,
            payment_method=payment_method,
            executor=executor,
            payer_id=payer_id,
            payer_name=payer_name,
            payer_type=payer_type,
            amounts=-account_amount,
            coupon_amount=-coupon_amount,
            before_payment=before_payment,
            after_payment=after_payment,
            type=PaymentHistory.Type.PAYMENT.value,
            remark=remark,
            order_id=order_id,
            resource_type=resource_type,
            service_id=service_id,
            instance_id=instance_id,
            app_id=app_id,
            subject=subject
        )
        pay_history.save(force_insert=True)
        if coupon_amount > Decimal('0'):
            self._deduct_form_coupons(coupons=usable_coupons, money_amount=coupon_amount, pay_history_id=pay_history.id)

        return pay_history

    @staticmethod
    def _deduct_form_coupons(coupons: List[CashCoupon], money_amount: Decimal, pay_history_id: str):
        """
        顺序从指定代金券中扣除金额

        * 发生错误时，函数中已操作修改的数据库数据不会手动回滚，此函数需要在事务中调用以保证数据一致性

        :param coupons: 代金券列表
        :param money_amount: 扣除金额
        :param pay_history_id: 支付记录id

        :raises: Error(Conflict、CouponBalanceNotEnough、CouponBalanceNotEnough)
        """
        if money_amount <= Decimal(0):
            raise errors.ConflictError(message="扣费金额必须大于0")

        total_coupon_balance = Decimal(0)
        for c in coupons:
            total_coupon_balance += c.balance

        if money_amount > total_coupon_balance:
            raise errors.BalanceNotEnough(message=_('代金券余额不足抵扣支付金额'), code='CouponBalanceNotEnough')

        # 代金券扣款记录
        remain_pay_amount = money_amount
        for coupon in coupons:
            if coupon.balance <= Decimal('0'):
                continue

            if coupon.balance >= remain_pay_amount:
                pay_amount = remain_pay_amount
                before_payment = coupon.balance
                after_payment = before_payment - pay_amount
                remain_pay_amount = Decimal('0')
            else:
                pay_amount = coupon.balance
                before_payment = coupon.balance
                after_payment = Decimal('0')
                remain_pay_amount = remain_pay_amount - pay_amount

            coupon.balance = after_payment
            coupon.save(update_fields=['balance'])
            ccph = CashCouponPaymentHistory(
                payment_history_id=pay_history_id,
                cash_coupon_id=coupon.id,
                amounts=-pay_amount,
                before_payment=before_payment,
                after_payment=after_payment
            )
            ccph.save(force_insert=True)

            if remain_pay_amount <= Decimal('0'):
                break

        if remain_pay_amount > Decimal('0'):
            raise errors.BalanceNotEnough(message=_('未能从代金券中扣除完指定金额'), code='DeductFormCouponsNotEnough')
