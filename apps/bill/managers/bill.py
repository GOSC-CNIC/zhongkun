from datetime import datetime
from decimal import Decimal

from django.utils.translation import gettext as _
from django.db.models import Sum

from core import errors
from bill.models import PaymentHistory, CashCouponPaymentHistory, TransactionBill, RefundRecord, PayAppService
from utils.model import OwnerType
from vo.managers import VoManager


class PaymentHistoryManager:
    @staticmethod
    def get_queryset():
        return PaymentHistory.objects.all()

    @staticmethod
    def get_payment_history_by_id(payment_id: str):
        payment = PaymentHistory.objects.filter(id=payment_id).first()
        if payment is None:
            raise errors.NotFound(message=_('支付记录不存在'))

        return payment

    @staticmethod
    def get_payment_history_by_order_id(app_id: str, order_id: str):
        payment = PaymentHistory.objects.filter(order_id=order_id, app_id=app_id).first()
        if payment is None:
            raise errors.NotFound(message=_('支付记录不存在'))

        return payment

    @staticmethod
    def get_payment_history(payment_id: str, user):
        """
        查询用户有访问权限的支付记录
        :return: PaymentHistory()
        :raises: Error
        """
        payment = PaymentHistory.objects.filter(id=payment_id).first()
        if payment is None:
            raise errors.NotFound(message=_('支付记录不存在'))

        if payment.payer_type == OwnerType.USER.value:
            if payment.payer_id != user.id:
                raise errors.AccessDenied(message=_('你没有此支付记录的访问权限'))
        elif payment.payer_type == OwnerType.VO.value:
            VoManager().get_has_read_perm_vo(vo_id=payment.payer_id, user=user)
        else:
            raise errors.ConflictError(message=_('支付记录拥有者类型未知'), code='UnknownOwnPayment')

        return payment

    def get_user_payment_history(
            self,
            user,
            status: str = None,
            time_start: datetime = None,
            time_end: datetime = None,
            app_service_id: str = None
    ):
        service_ids = [app_service_id, ] if app_service_id else None
        return self.filter_queryset(
            user_id=user.id, status=status, time_start=time_start, time_end=time_end, app_service_ids=service_ids
        )

    def get_vo_payment_history(
            self,
            user,
            vo_id: str,
            status: str = None,
            time_start: datetime = None,
            time_end: datetime = None,
            app_service_id: str = None
    ):
        """
        :raises: Error
        """
        VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
        service_ids = [app_service_id, ] if app_service_id else None
        return self.filter_queryset(
            vo_id=vo_id, status=status, time_start=time_start, time_end=time_end, app_service_ids=service_ids
        )

    def filter_queryset(
            self,
            user_id: str = None,
            vo_id: str = None,
            status: str = None,
            time_start: datetime = None,
            time_end: datetime = None,
            app_service_ids: list = None
    ):
        """
        支付记录查询集

        * user_id和vo_id不能同时查询
        * time_start和time_end必须同时为None 或者同时是有效时间，time_end > time_start

        :param user_id: 所属用户
        :param vo_id: 所属vo组
        :param status: 支付状态
        :param time_start: 支付时间段起（包含）
        :param time_end: 支付时间段止（不包含）
        :param app_service_ids: 所属APP服务
        :return:
            QuerySet
        :raises: Error
        """
        if status and status not in PaymentHistory.Status.values:
            raise errors.Error(message=_('无效的支付状态'))

        if user_id and vo_id:
            raise errors.Error(message=_('不能查询同时属于用户和vo组的支付记录'))

        queryset = self.get_queryset()
        if time_start is not None or time_end is not None:
            if not (time_start and time_end):
                raise errors.Error(message=_('time_start和time_end必须同时是有效时间'))

            if time_start >= time_end:
                raise errors.Error(message=_('时间time_end必须大于time_start'))
            queryset = queryset.filter(payment_time__gte=time_start, payment_time__lt=time_end)

        if app_service_ids:
            if len(app_service_ids) == 1:
                queryset = queryset.filter(app_service_id=app_service_ids[0])
            else:
                queryset = queryset.filter(app_service_id__in=app_service_ids)

        if user_id:
            queryset = queryset.filter(payer_id=user_id, payer_type=OwnerType.USER.value)

        if vo_id:
            queryset = queryset.filter(payer_id=vo_id, payer_type=OwnerType.VO.value)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-payment_time')

    def get_payment_history_detail(self, payment_id: str, user):
        payment = self.get_payment_history(payment_id=payment_id, user=user)
        qs = CashCouponPaymentHistory.objects.filter(payment_history_id=payment.id).all()
        coupon_historys = list(qs)
        return payment, coupon_historys


class TransactionBillManager:
    @staticmethod
    def get_queryset():
        return TransactionBill.objects.all()

    @staticmethod
    def create_transaction_bill(
            subject: str, account: str, trade_type: str, trade_id: str,
            out_trade_no: str, trade_amounts: Decimal,
            amounts: Decimal, coupon_amount: Decimal, after_balance: Decimal,
            owner_type: str, owner_id: str, owner_name: str, app_service_id: str, app_id: str,
            remark: str, creation_time: datetime, operator: str = ''
    ):
        if trade_type not in TransactionBill.TradeType.values:
            raise errors.Error(message=_('创建交易流水账单记录错误，无效的交易类型"%(value)s"。') % {'value': trade_type})

        bill = TransactionBill(
            subject=subject,
            account=account,
            trade_type=trade_type,
            trade_id=trade_id,
            out_trade_no=out_trade_no,
            trade_amounts=trade_amounts,
            amounts=amounts,
            coupon_amount=coupon_amount,
            after_balance=after_balance,
            owner_type=owner_type,
            owner_id=owner_id,
            owner_name=owner_name,
            app_service_id=app_service_id,
            app_id=app_id,
            remark=remark,
            creation_time=creation_time,
            operator=operator
        )
        bill.save(force_insert=True)
        return bill

    def get_user_transaction_bill_queryset(
            self,
            user,
            trade_type: str = None,
            time_start: datetime = None,
            time_end: datetime = None,
            app_service_id: str = None
    ):
        service_ids = [app_service_id, ] if app_service_id else None
        return self.filter_queryset(
            user_id=user.id, trade_type=trade_type, time_start=time_start, time_end=time_end, app_service_ids=service_ids
        )

    def get_vo_transaction_bill_queryset(
            self,
            user,
            vo_id: str,
            trade_type: str = None,
            time_start: datetime = None,
            time_end: datetime = None,
            app_service_id: str = None
    ):
        """
        :raises: Error
        """
        VoManager().get_has_read_perm_vo(vo_id=vo_id, user=user)
        service_ids = [app_service_id, ] if app_service_id else None
        return self.filter_queryset(
            vo_id=vo_id, trade_type=trade_type, time_start=time_start, time_end=time_end, app_service_ids=service_ids
        )

    @staticmethod
    def filter_queryset(
            user_id: str = None,
            vo_id: str = None,
            trade_type: str = None,
            time_start: datetime = None,
            time_end: datetime = None,
            app_service_ids: list = None
    ):
        """
        交易流水查询集

        * user_id和vo_id不能同时查询
        * time_start和time_end必须同时为None 或者同时是有效时间，time_end > time_start

        :param user_id: 所属用户
        :param vo_id: 所属vo组
        :param trade_type: 交易类型
        :param time_start: 支付时间段起（包含）
        :param time_end: 支付时间段止（不包含）
        :param app_service_ids: 所属APP服务
        :return:
            QuerySet
        :raises: Error
        """
        if trade_type and trade_type not in TransactionBill.TradeType.values:
            raise errors.Error(message=_('无效的交易类型'))

        if user_id and vo_id:
            raise errors.Error(message=_('不能查询同时属于用户和vo组的支付记录'))

        queryset = TransactionBill.objects.all()
        if time_start is not None or time_end is not None:
            if not (time_start and time_end):
                raise errors.Error(message=_('time_start和time_end必须同时是有效时间'))

            if time_start >= time_end:
                raise errors.Error(message=_('时间time_end必须大于time_start'))
            queryset = queryset.filter(creation_time__gte=time_start, creation_time__lt=time_end)

        if app_service_ids:
            if len(app_service_ids) == 1:
                queryset = queryset.filter(app_service_id=app_service_ids[0])
            else:
                queryset = queryset.filter(app_service_id__in=app_service_ids)

        if user_id:
            queryset = queryset.filter(owner_id=user_id, owner_type=OwnerType.USER.value)

        if vo_id:
            queryset = queryset.filter(owner_id=vo_id, owner_type=OwnerType.VO.value)

        if trade_type:
            queryset = queryset.filter(trade_type=trade_type)

        return queryset.order_by('-creation_time')

    def admin_transaction_bill_queryset(
            self,
            admin_user,
            user_id: str,
            vo_id: str,
            trade_type: str = None,
            time_start: datetime = None,
            time_end: datetime = None,
            app_service_id: str = None
    ):
        """
        :raises: Error
        """
        service_ids = [app_service_id, ] if app_service_id else None
        if not admin_user.is_federal_admin():
            if app_service_id:
                app_service = PayAppService.objects.filter(id=app_service_id, users__id=admin_user.id).first()
                if app_service is None:
                    raise errors.AccessDenied(message=_('你没有指定app子服务的管理权限。'))
            else:
                app_service_ids = PayAppService.objects.filter(users__id=admin_user.id).values_list('id', flat=True)
                service_ids = list(app_service_ids)
                if not service_ids:
                    return TransactionBill.objects.none()

        return self.filter_queryset(
            vo_id=vo_id, user_id=user_id, trade_type=trade_type, time_start=time_start, time_end=time_end,
            app_service_ids=service_ids
        )

    @staticmethod
    def get_app_transaction_bill_queryset(
            app_id: str,
            trade_type: str,
            time_start: datetime,
            time_end: datetime
    ):
        """
        交易流水查询集

        * user_id和vo_id不能同时查询
        * time_start和time_end必须同时为None 或者同时是有效时间，time_end > time_start

        :param app_id: 所属app
        :param trade_type: 交易类型
        :param time_start: 交易时间段起（包含）
        :param time_end: 交易时间段止（不包含）
        :return:
            QuerySet
        :raises: Error
        """
        if trade_type and trade_type not in TransactionBill.TradeType.values:
            raise errors.Error(message=_('无效的交易类型'))

        queryset = TransactionBill.objects.filter(
            app_id=app_id, creation_time__gte=time_start, creation_time__lt=time_end).all()

        if trade_type:
            queryset = queryset.filter(trade_type=trade_type)
        else:
            queryset = queryset.filter(trade_type__in=[
                TransactionBill.TradeType.PAYMENT.value, TransactionBill.TradeType.REFUND.value])

        return queryset


class RefundRecordManager:
    @staticmethod
    def get_queryset():
        return RefundRecord.objects.all()

    @staticmethod
    def get_refund_by_id(refund_id: str):
        refund = RefundRecord.objects.filter(id=refund_id).first()
        if refund is None:
            raise errors.NotFound(message=_('退款记录不存在'))

        return refund

    @staticmethod
    def get_refund_by_out_refund_id(app_id: str, out_refund_id: str):
        refund = RefundRecord.objects.filter(out_refund_id=out_refund_id, app_id=app_id).first()
        if refund is None:
            raise errors.NotFound(message=_('退款记录不存在'))

        return refund

    @staticmethod
    def get_trade_refunded_total_amounts(app_id: str, trade_id: str) -> Decimal:
        """
        查询支付交易已退款的总金额
        """
        # 已退款金额
        r = RefundRecord.objects.filter(
            trade_id=trade_id, app_id=app_id,
            status__in=[RefundRecord.Status.SUCCESS.value, RefundRecord.Status.WAIT.value]
        ).aggregate(refund_total_amounts=Sum('refund_amounts'))
        refunded_total_amounts = r.get('refund_total_amounts', Decimal('0'))
        if refunded_total_amounts is None:
            refunded_total_amounts = Decimal('0')
        elif not isinstance(refunded_total_amounts, Decimal):
            refunded_total_amounts = Decimal.from_float(refunded_total_amounts)

        return refunded_total_amounts
