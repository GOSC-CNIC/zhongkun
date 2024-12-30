from decimal import Decimal

from django.utils.translation import gettext as _

from rest_framework.response import Response

from core import errors
from core.aai.authentication import CreateUserJWTAuthentication
from core.aai.jwt import JWTInvalidError
from apps.api.viewsets import serializer_error_msg
from apps.app_wallet.apiviews import PaySignGenericViewSet
from apps.app_wallet import trade_serializers
from apps.app_wallet.trade_serializers import PaymentHistorySerializer
from apps.app_wallet.managers.payment import PaymentManager
from apps.app_wallet.managers.bill import PaymentHistoryManager, RefundRecordManager
from apps.app_wallet.models import PaymentHistory
from apps.app_users.models import UserProfile
from utils.decimal_utils import quantize_10_2


class TradeHandler:
    @staticmethod
    def trade_pay(view: PaySignGenericViewSet, request, kwargs):
        """
        扣费

        :return: Response()
        """
        try:
            app = view.check_request_sign(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = TradeHandler._trade_pay_validate(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        subject = data.get('subject')
        order_id = data.get('order_id')
        amounts = data.get('amounts')
        app_service_id = data.get('app_service_id')
        user = data.get('user')
        remark = data.get('remark')

        try:
            history = PaymentManager().pay_by_user(
                user_id=user.id,
                app_id=app.id,
                subject=subject,
                amounts=amounts,
                executor='',
                remark=remark,
                order_id=order_id,
                app_service_id=app_service_id,
                instance_id=''
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        s = PaymentHistorySerializer(instance=history)
        return Response(data=s.data)

    @staticmethod
    def _trade_pay_validate(view, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise errors.BadRequest(msg)

        data = serializer.validated_data
        amounts = data.get('amounts')
        aai_jwt = data.get('aai_jwt')

        if amounts <= Decimal('0'):
            raise errors.BadRequest(message=_('交易金额必须大于0'))

        try:
            auth = CreateUserJWTAuthentication()
            token = auth.get_validated_token(raw_token=aai_jwt)
            user = auth.get_user(validated_token=token)
        except JWTInvalidError as exc:
            raise errors.BadRequest(message=exc.message, code=exc.code)
        except Exception as exc:
            raise errors.Error.from_error(exc)

        data['user'] = user
        return data

    @staticmethod
    def _trade_charge_validate(view, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise errors.BadRequest(msg)

        data = serializer.validated_data
        amounts = data.get('amounts')
        username = data.get('username')

        if amounts <= Decimal('0'):
            raise errors.BadRequest(message=_('交易金额必须大于0'))

        user = UserProfile.objects.filter(username=username).first()
        if user is None:
            raise errors.NotFound(message=_('指定的付款人不存在'), code='NoSuchBalanceAccount')

        data['user'] = user
        return data

    @staticmethod
    def trade_charge(view: PaySignGenericViewSet, request, kwargs):
        """
        扣费

        :return: Response()
        """
        try:
            app = view.check_request_sign(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = TradeHandler._trade_charge_validate(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        subject = data.get('subject')
        order_id = data.get('order_id')
        amounts = data.get('amounts')
        app_service_id = data.get('app_service_id')
        user = data.get('user')
        remark = data.get('remark')

        try:
            history = PaymentManager().pay_by_user(
                user_id=user.id,
                app_id=app.id,
                subject=subject,
                amounts=amounts,
                executor='',
                remark=remark,
                order_id=order_id,
                app_service_id=app_service_id,
                instance_id=''
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        s = PaymentHistorySerializer(instance=history)
        return Response(data=s.data)

    @staticmethod
    def _add_refunded_amounts(data: dict, app_id: str, phistory: PaymentHistory):
        """
        支付记录增加已退款金额信息
        """
        if phistory.status in [PaymentHistory.Status.WAIT.value, PaymentHistory.Status.ERROR.value]:
            refunded_total_amounts = Decimal('0')
        else:
            # 已退款金额
            refunded_total_amounts = RefundRecordManager.get_trade_refunded_total_amounts(
                app_id=app_id, trade_id=phistory.id
            )

        refunded_amounts = quantize_10_2(refunded_total_amounts)
        data['refunded_amounts'] = '{:f}'.format(refunded_amounts)

        return data

    @staticmethod
    def trade_query_trade_id(view: PaySignGenericViewSet, request, kwargs):
        """
        查询交易记录

        :return: Response()
        """
        try:
            app = view.check_request_sign(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        trade_id = kwargs.get('trade_id', '')
        query_refunded = request.query_params.get('query_refunded', None)

        try:
            phistory = PaymentHistoryManager.get_payment_history_by_id(payment_id=trade_id)
        except errors.NotFound:
            return view.exception_response(errors.NotFound(
                message=_('查询的交易记录不存在'), code='NoSuchTrade'
            ))

        if phistory.app_id != app.id:
            return view.exception_response(errors.NotFound(
                message=_('无权访问此交易记录'), code='NotOwnTrade'
            ))

        s = PaymentHistorySerializer(instance=phistory)
        data = s.data
        if query_refunded is not None:
            data = TradeHandler._add_refunded_amounts(data=data, app_id=app.id, phistory=phistory)

        return Response(data=data)

    @staticmethod
    def trade_query_order_id(view: PaySignGenericViewSet, request, kwargs):
        """
        通过订单id查询交易记录

        :return: Response()
        """
        try:
            app = view.check_request_sign(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        order_id = kwargs.get('order_id', '')
        query_refunded = request.query_params.get('query_refunded', None)
        try:
            phistory = PaymentHistoryManager.get_payment_history_by_order_id(order_id=order_id, app_id=app.id)
        except errors.NotFound:
            return view.exception_response(errors.NotFound(
                message=_('查询的交易记录不存在'), code='NoSuchTrade'
            ))

        s = PaymentHistorySerializer(instance=phistory)
        data = s.data
        if query_refunded is not None:
            data = TradeHandler._add_refunded_amounts(data=data, app_id=app.id, phistory=phistory)

        return Response(data=data)

    @staticmethod
    def trade_refund(view: PaySignGenericViewSet, request, kwargs):
        """
        退款

        :return: Response()
        """
        try:
            app = view.check_request_sign(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = TradeHandler._trade_refund_validate(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        trade_id = data.get('trade_id')
        out_order_id = data.get('out_order_id')
        refund_amount = data.get('refund_amount')
        out_refund_id = data.get('out_refund_id')
        refund_reason = data.get('refund_reason')
        remark = data.get('remark')

        if trade_id:
            try:
                payment_history = PaymentHistoryManager.get_payment_history_by_id(trade_id)
            except errors.NotFound:
                return view.exception_response(exc=errors.NoSuchTrade())
        else:
            try:
                payment_history = PaymentHistoryManager.get_payment_history_by_order_id(
                    app_id=app.id, order_id=out_order_id)
            except errors.NotFound:
                return view.exception_response(exc=errors.NoSuchOutOrderId())

        try:
            refund = PaymentManager().refund_for_payment(
                app_id=app.id,
                payment_history=payment_history,
                out_refund_id=out_refund_id,
                refund_amounts=refund_amount,
                refund_reason=refund_reason,
                remark=remark,
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        s = trade_serializers.RefundRecordSerializer(instance=refund)
        return Response(data=s.data)

    @staticmethod
    def _trade_refund_validate(view, request):
        """
        :raises: Error
        out_refund_id
        trade_id

        out_order_id
        refund_amount
        refund_reason
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'refund_amount' in s_errors:
                exc = errors.BadRequest(
                    message=_('退款金额无效。') + s_errors['refund_amount'][0], code='InvalidRefundAmount')
            elif 'refund_reason' in s_errors:
                exc = errors.BadRequest(
                    message=_('退款原因无效。') + s_errors['refund_reason'][0], code='InvalidRefundReason')
            elif 'remark' in s_errors:
                exc = errors.BadRequest(
                    message=_('备注信息无效。') + s_errors['remark'][0], code='InvalidRemark')
            else:
                msg = serializer_error_msg(serializer.errors)
                exc = errors.BadRequest(message=msg)

            raise exc

        data = serializer.validated_data
        trade_id = data.get('trade_id')
        out_order_id = data.get('out_order_id')
        refund_amount = data.get('refund_amount')
        out_refund_id = data.get('out_refund_id')
        refund_reason = data.get('refund_reason')
        remark = data.get('remark')

        if refund_amount <= Decimal('0'):
            raise errors.BadRequest(message=_('退款金额必须大于0'), code='InvalidRefundAmount')

        if not trade_id and not out_order_id:
            raise errors.BadRequest(message=_('订单编号或者订单的交易编号必须提供一个。'), code='MissingTradeId')

        return {
            'trade_id': trade_id,
            'out_order_id': out_order_id,
            'refund_amount': refund_amount,
            'out_refund_id': out_refund_id,
            'refund_reason': refund_reason,
            'remark': remark
        }

    @staticmethod
    def trade_refund_query(view: PaySignGenericViewSet, request, kwargs):
        """
        退款查询

        :return: Response()
        """
        refund_id = request.query_params.get('refund_id', None)
        out_refund_id = request.query_params.get('out_refund_id', None)

        if not refund_id and not out_refund_id:
            return view.exception_response(exc=errors.BadRequest(
                message=_('外部退款单号或者钱包退款的交易编号必须提供一个。'), code='MissingTradeId'))

        try:
            app = view.check_request_sign(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        if refund_id:
            try:
                refund = RefundRecordManager.get_refund_by_id(refund_id)
            except errors.NotFound:
                return view.exception_response(exc=errors.NoSuchTrade())
        else:
            try:
                refund = RefundRecordManager.get_refund_by_out_refund_id(
                    app_id=app.id, out_refund_id=out_refund_id)
            except errors.NotFound:
                return view.exception_response(exc=errors.NoSuchOutRefundId())

        if refund.app_id != app.id:
            return view.exception_response(exc=errors.NotOwnTrade())

        s = trade_serializers.RefundRecordSerializer(instance=refund)
        return Response(data=s.data)
