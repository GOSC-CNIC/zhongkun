from decimal import Decimal
from typing import List

from django.utils.translation import gettext as _
from django.utils import timezone
from django.db import transaction

from core import errors
from utils.model import OwnerType
from utils.decimal_utils import quantize_10_2
from bill.models import (
    PaymentHistory, UserPointAccount, VoPointAccount, CashCouponPaymentHistory, CashCoupon,
    PayAppService, TransactionBill, RefundRecord
)
from bill.managers.bill import TransactionBillManager, RefundRecordManager
from .cash_coupon import CashCouponManager


class PaymentManager:
    @staticmethod
    def get_user_point_account(user_id: str, select_for_update: bool = False, is_create: bool = True):
        """
        :param user_id:
        :param select_for_update: 是否加锁
        :param is_create: 账户不存在是否创建
        :return:
            UserPointAccount() or None
        """
        if select_for_update:
            user_account = UserPointAccount.objects.select_for_update().select_related('user').filter(
                user_id=user_id).first()
        else:
            user_account = UserPointAccount.objects.select_related('user').filter(user_id=user_id).first()

        if user_account is None and is_create:
            upa = UserPointAccount(user_id=user_id, balance=Decimal(0))
            upa.save(force_insert=True)
            if select_for_update:
                user_account = UserPointAccount.objects.select_for_update().select_related('user').filter(
                    user_id=user_id).first()
            else:
                user_account = upa

        return user_account

    @staticmethod
    def get_vo_point_account(vo_id: str, select_for_update: bool = False, is_create: bool = True):
        """
        :param vo_id:
        :param select_for_update: 是否加锁
        :param is_create: 账户不存在是否创建
        :return:
            VoPointAccount() or None
        """
        if select_for_update:
            vo_account = VoPointAccount.objects.select_for_update().select_related('vo').filter(vo_id=vo_id).first()
        else:
            vo_account = VoPointAccount.objects.select_related('vo').filter(vo_id=vo_id).first()

        if vo_account is None and is_create:
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

        :param user_id: user id
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

        ok = PaymentHistory.objects.filter(order_id=order_id, app_id=app_id).exists()
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
                raise errors.BalanceNotEnough(message=_('资源券的余额不足'), code='CouponBalanceNotEnough')
        elif required_enough_balance:
            if amounts > (total_coupon_balance + account.balance):
                raise errors.BalanceNotEnough()

        if (
            only_coupon or                      # 只用资源券支付
            total_coupon_balance >= amounts     # 资源券余额足够支付
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
            payable_amounts=amounts,
            amounts=-account_amount,
            coupon_amount=-coupon_amount,
            status=PaymentHistory.Status.SUCCESS.value,
            status_desc=_('支付成功'),
            remark=remark,
            order_id=order_id,
            app_service_id=app_service_id,
            instance_id=instance_id,
            app_id=app_id,
            subject=subject,
            creation_time=timezone.now(),
            payment_time=timezone.now()
        )
        pay_history.save(force_insert=True)
        if coupon_amount > Decimal('0'):
            self._deduct_form_coupons(coupons=usable_coupons, money_amount=coupon_amount, pay_history_id=pay_history.id)

        # 交易流水
        tbill = TransactionBillManager.create_transaction_bill(
            subject=subject, account=payment_account, trade_type=TransactionBill.TradeType.PAYMENT.value,
            trade_id=pay_history.id, out_trade_no=pay_history.order_id, trade_amounts=-pay_history.payable_amounts,
            amounts=pay_history.amounts, coupon_amount=pay_history.coupon_amount,
            after_balance=after_payment, owner_type=pay_history.payer_type, owner_id=pay_history.payer_id,
            owner_name=pay_history.payer_name, app_service_id=pay_history.app_service_id, app_id=pay_history.app_id,
            remark=remark, creation_time=pay_history.payment_time, operator=pay_history.executor
        )
        return pay_history

    @staticmethod
    def _deduct_form_coupons(coupons: List[CashCoupon], money_amount: Decimal, pay_history_id: str):
        """
        顺序从指定资源券中扣除金额

        * 发生错误时，函数中已操作修改的数据库数据不会手动回滚，此函数需要在事务中调用以保证数据一致性

        :param coupons: 资源券列表
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
            raise errors.BalanceNotEnough(message=_('资源券余额不足抵扣支付金额'), code='CouponBalanceNotEnough')

        # 资源券扣款记录
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
            raise errors.BalanceNotEnough(message=_('未能从资源券中扣除完指定金额'), code='DeductFormCouponsNotEnough')

        return cc_historys

    def refund_for_payment(
            self,
            app_id: str,
            payment_history: PaymentHistory,
            out_refund_id: str,
            refund_amounts: Decimal,
            refund_reason: str,
            remark: str,
    ):
        """
        支付订单 发起一笔退款

        :return: RefundRecord()

        :raises: Error
        """
        owner_id = payment_history.payer_id
        owner_name = payment_history.payer_name
        owner_type = payment_history.payer_type

        refund, created, return_exc = self._create_refund_record_pre_refund(
            app_id=app_id, payment_history=payment_history,
            out_refund_id=out_refund_id,
            refund_amounts=refund_amounts,
            refund_reason=refund_reason,
            remark=remark,
            owner_id=owner_id,
            owner_name=owner_name,
            owner_type=owner_type
        )
        # 退款，可能是旧的退款，也可能是本次新的退款
        refund_new = self._refund(refund_id=refund.id)

        # 本次新的退款，返回退款结果
        if created:
            # 退款未发生错误，返回最新的退款记录
            if refund_new is not None:
                return refund_new

            # 退款发生错误，返回待退款状态，让用户稍后查询确认
            refund.status = RefundRecord.Status.WAIT.value
            return refund

        # 是旧退款， 返回本次退款请求的错误
        raise return_exc

    @staticmethod
    def _create_refund_record_pre_refund(
            app_id,
            payment_history: PaymentHistory,
            out_refund_id: str,
            refund_amounts: Decimal,
            refund_reason: str,
            remark: str,
            owner_id: str,
            owner_name: str,
            owner_type: str
    ):
        """
        检查是否满足退款条件，并创建退款记录单

        :param app_id:
        :param payment_history: 退款记录对象实例
        :param out_refund_id: 外部app的退款单号
        :param refund_amounts: 退款金额
        :param refund_reason: 退款原因
        :param remark: 备注信息
        :param owner_id: 退款账户所有人id; user id or vo id
        :param owner_name: 退款账户所有人名称; username or vo name
        :param owner_type: 所有人类型；user or vo
        :return: (
            refund,     # RefundRecord
            created,    # bool；True(新的退款，exc=None); False(旧退款记录，触发继续旧的退款，本次退款请求返回exc)
            exc         # Error
        )

        :raises: Error
        """
        if payment_history.app_id != app_id:
            raise errors.NotOwnTrade()

        if payment_history.status != PaymentHistory.Status.SUCCESS.value:
            raise errors.TradeStatusInvalid(message=_('非支付成功状态的交易订单无法退款。'))

        # 退款的支付订单支付总金额
        paid_amounts = -(payment_history.amounts + payment_history.coupon_amount)
        if refund_amounts > paid_amounts:
            raise errors.RefundAmountsExceedTotal()

        with transaction.atomic():
            pay_history = PaymentHistory.objects.select_for_update().filter(id=payment_history.id).first()
            refund_rd = RefundRecord.objects.filter(app_id=app_id, out_refund_id=out_refund_id).first()
            if refund_rd is not None:
                if refund_rd.status in [RefundRecord.Status.SUCCESS.value, RefundRecord.Status.CLOSED.value]:
                    raise errors.OutRefundIdExists(extend_msg=f'status={refund_rd.status}')

                # 退款失败和待退款时，退款对应的支付记录不是当前支付记录，退款单号已存在
                if refund_rd.trade_id != payment_history.id:
                    raise errors.OutRefundIdExists(extend_msg=f'status={refund_rd.status}')

                # 待退款状态，返回退款单号已存在错误，继续完成旧退款记录
                if refund_rd.status == RefundRecord.Status.WAIT.value:
                    return refund_rd, False, errors.OutRefundIdExists(extend_msg=f'status={refund_rd.status}')

                # 退款失败状态的删除，创建新的退款记录完成退款
                if refund_rd.status == RefundRecord.Status.ERROR.value:
                    refund_rd.delete()

            # 已退款金额
            refunded_total_amounts = RefundRecordManager.get_trade_refunded_total_amounts(
                app_id=app_id, trade_id=pay_history.id
            )

            # 退款总金额 超出了 支付订单支付总金额
            if (refunded_total_amounts + refund_amounts) > paid_amounts:
                raise errors.RefundAmountsExceedTotal()

            # 余额和券应退款金额计算
            real_refund = ((-payment_history.amounts) / paid_amounts) * refund_amounts
            real_refund = quantize_10_2(real_refund)
            coupon_refund = refund_amounts - real_refund
            coupon_refund = quantize_10_2(coupon_refund)

            refund = RefundRecord(
                app_id=app_id,
                trade_id=pay_history.id,
                out_order_id=pay_history.order_id,
                out_refund_id=out_refund_id,
                refund_reason=refund_reason,
                total_amounts=paid_amounts,
                refund_amounts=refund_amounts,
                real_refund=real_refund,
                coupon_refund=coupon_refund,
                creation_time=timezone.now(),
                success_time=None,
                status=RefundRecord.Status.WAIT.value,
                status_desc='',
                remark=remark,
                app_service_id=pay_history.app_service_id,
                in_account='',
                owner_id=owner_id,
                owner_name=owner_name,
                owner_type=owner_type,
                operator=''
            )
            refund.save(force_insert=True)
            return refund, True, None

    def _refund(self, refund_id: str):
        """
        不能抛出错误，返回新的退款记录状态

        :return:
            RefundRecord() or None      # None: 退款记录不存在
        """
        try:
            with transaction.atomic():
                refund = RefundRecord.objects.select_for_update().filter(id=refund_id).first()
                if refund is None:
                    return None

                if refund.status != RefundRecord.Status.WAIT.value:
                    return refund

                refund = self.__refund(refund=refund)
        except Exception as exc:
            refund = RefundRecord.objects.filter(id=refund_id).first()
            if refund is None:
                return None

            refund.status = RefundRecord.Status.ERROR.value
            msg = str(exc)
            refund.status_desc = msg[0:254]
            refund.save(update_fields=['status', 'status_desc'])

        return refund

    def __refund(self, refund: RefundRecord):
        """
        退款，生成交易流水，次函数必须放在一个事务保证数据一致性
        """
        # 退款入账账户
        if refund.owner_type == OwnerType.USER.value:
            account = self.get_user_point_account(user_id=refund.owner_id, select_for_update=True, is_create=False)
            if account is None:
                raise errors.ConflictError(message=_('无法完成退款，用户的余额账户未开通。'))
        else:
            account = self.get_vo_point_account(vo_id=refund.owner_id, select_for_update=True, is_create=False)
            if account is None:
                raise errors.ConflictError(message=_('无法完成退款，VO项目组的余额账户未开通。'))

        # 退款至余额账户
        if refund.real_refund > Decimal('0'):
            account.balance = account.balance + refund.real_refund
            account.save(update_fields=['balance'])

        # 退款记录
        refund.set_refund_sucsess(in_account=account.id)

        # 交易流水
        TransactionBillManager.create_transaction_bill(
            subject=refund.refund_reason, account=refund.in_account,
            trade_type=TransactionBill.TradeType.REFUND.value,
            trade_id=refund.id, out_trade_no=refund.out_refund_id,
            trade_amounts=refund.refund_amounts, amounts=refund.real_refund,
            coupon_amount=refund.coupon_refund,  # 券金额不退
            after_balance=account.balance, owner_type=refund.owner_type, owner_id=refund.owner_id,
            owner_name=refund.owner_name, app_service_id=refund.app_service_id, app_id=refund.app_id,
            remark=refund.remark, creation_time=refund.success_time, operator=refund.operator
        )

        return refund
