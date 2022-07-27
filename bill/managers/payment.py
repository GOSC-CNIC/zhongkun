from decimal import Decimal
from typing import List

from django.utils.translation import gettext as _
from django.db import transaction

from core import errors
from utils.model import OwnerType
from bill.models import (
    PaymentHistory, UserPointAccount, VoPointAccount, CashCouponPaymentHistory, CashCoupon,
    PayAppService
)
from .cash_coupon import CashCouponManager


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
            with_coupons: bool, app_service_id: str
    ):
        """
        用户是否有足够的余额

        * 如果使用券，要同时指定with_coupons和app_service_id

        :param vo_id: vo id
        :param money_amount: Decimal('0')可以判断是否欠费
        :param with_coupons: 是否用券
        :param app_service_id: service_id对应的余额结算中app service id
        :return:
            True        # 满足
            False
        """
        if money_amount < Decimal('0'):
            return errors.InvalidArgument(message=_('查询是否有足够的余额，金额不能小于0'))

        user_account = self.get_user_point_account(user_id=user_id)
        if not with_coupons:
            return user_account.balance >= money_amount

        coupons = CashCouponManager().get_user_cash_coupons(
            user_id=user_id, coupon_ids=None, select_for_update=False
        )

        # 适用的券
        usable_coupons, unusable_coupons = CashCouponManager.sorting_usable_coupons(
            coupons=coupons, app_service_id=app_service_id
        )

        total_coupon_balance = Decimal('0')
        for c in usable_coupons:
            total_coupon_balance += c.balance

        if total_coupon_balance <= Decimal('0'):  # 没有可用有券
            return user_account.balance >= money_amount

        if user_account.balance >= Decimal('0'):  # 有余额（正），券余额+余额
            total_balance = total_coupon_balance + user_account.balance
        else:
            total_balance = total_coupon_balance    # 没余额（负或0），券余额

        return total_balance >= money_amount

    def has_enough_balance_vo(
            self, vo_id: str, money_amount: Decimal,
            with_coupons: bool, app_service_id: str
    ):
        """
        vo组是否有足够的余额

        * 如果使用券，要同时指定with_coupons和app_service_id

        :param vo_id: vo id
        :param money_amount: Decimal('0')可以判断是否欠费
        :param with_coupons: 是否用券
        :param app_service_id: service_id对应的余额结算中app service id
        :return:
            True        # 满足
            False
        """
        if money_amount < Decimal('0'):
            return errors.InvalidArgument(message=_('查询是否有足够的余额，金额不能小于0'))

        vo_account = self.get_vo_point_account(vo_id=vo_id)
        if not with_coupons:
            return vo_account.balance >= money_amount

        coupons = CashCouponManager().get_vo_cash_coupons(
            vo_id=vo_id, coupon_ids=None, select_for_update=False
        )
        # 适用的券
        usable_coupons, unusable_coupons = CashCouponManager.sorting_usable_coupons(
            coupons=coupons, app_service_id=app_service_id
        )

        total_coupon_balance = Decimal('0')
        for c in usable_coupons:
            total_coupon_balance += c.balance

        if total_coupon_balance <= Decimal('0'):  # 没有可用有券
            return vo_account.balance >= money_amount

        if vo_account.balance >= Decimal('0'):  # 有余额（正），券余额+余额
            total_balance = total_coupon_balance + vo_account.balance
        else:
            total_balance = total_coupon_balance  # 没余额（负或0），券余额

        return total_balance >= money_amount

    def pay_by_user(
            self, user_id: str,
            app_id: str,
            subject: str,
            amounts: Decimal,
            executor: str,
            remark: str,
            order_id: str,
            app_service_id: str,
            resource_type: str,
            instance_id: str,
            coupon_ids: list = None,
            only_coupon: bool = False,
            required_enough_balance: bool = True
    ):
        """
        * coupon_ids: 支付使用指定id的券；None(不指定券，使用所有券)；[](空，指定不使用券)；
        :return:
            PaymentHistory()
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
                app_service_id=app_service_id,
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
            app_service_id: str,
            resource_type: str,
            instance_id: str,
            coupon_ids: List[CashCoupon] = None,
            only_coupon: bool = False,
            required_enough_balance: bool = True
    ):
        """
        * coupon_ids: 支付使用指定id的券；None(不指定券，使用所有券)；[](空，指定不使用券)；
        :return:
            PaymentHistory()
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
                app_service_id=app_service_id,
                instance_id=instance_id,
                only_coupon=only_coupon,
                required_enough_balance=required_enough_balance
            )

    def _pre_pay_by_user_or_vo(
            self, user_id: str,
            vo_id: str,
            app_id: str,
            app_service_id: str,
            order_id: str,
            coupon_ids: List[CashCoupon] = None
    ):
        """
        支付前检查验证

        :param coupon_ids: 支付使用指定id的券；None(不指定券，使用所有券)；[](空，指定不使用券)；
        :raises: Error
        """
        if user_id and vo_id:
            raise errors.ConflictError(message=_('不能能同时指定参数"user_id"和“vo_id”，无法确认使用用户还是vo组账户支付'))

        app_service = PayAppService.objects.filter(id=app_service_id).first()
        if app_service is None:
            raise errors.ConflictError(
                message=_('无效的app_service_id，指定的APP子服务不存在'), code='InvalidAppServiceId'
            )

        if app_service.app_id != app_id:
            raise errors.ConflictError(
                message=_('无效的app_service_id，指定的APP子服务不属于你的APP'), code='InvalidAppServiceId'
            )

        ok = PaymentHistory.objects.filter(
            order_id=order_id, app_id=app_id, type=PaymentHistory.Type.PAYMENT.value).exists()
        if ok:
            raise errors.ConflictError(
                message=_('已存在订单编号为%(value)s的交易记录') % {'value': order_id}, code='OrderIdExist'
            )

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
            coupons=coupons, app_service_id=app_service_id
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
            app_service_id: str,
            resource_type: str,
            instance_id: str,
            coupon_ids: List[CashCoupon],
            only_coupon: bool = False,
            required_enough_balance: bool = True
    ):
        """
        * 发生错误时，函数中已操作修改的数据库数据不会手动回滚，此函数需要在事务中调用以保证数据一致性
        :return:
            PaymentHistory()
        """
        account, usable_coupons, payer_id, payer_name, payer_type = self._pre_pay_by_user_or_vo(
            user_id=user_id, vo_id=vo_id, coupon_ids=coupon_ids, app_service_id=app_service_id,
            app_id=app_id, order_id=order_id
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
            app_service_id=app_service_id,
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
        :return:
            [CashCouponPaymentHistory()]

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
        cc_historys = []
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
            cc_historys.append(ccph)

            if remain_pay_amount <= Decimal('0'):
                break

        if remain_pay_amount > Decimal('0'):
            raise errors.BalanceNotEnough(message=_('未能从代金券中扣除完指定金额'), code='DeductFormCouponsNotEnough')

        return cc_historys
