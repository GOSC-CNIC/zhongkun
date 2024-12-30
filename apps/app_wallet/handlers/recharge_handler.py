from decimal import Decimal

from django.utils.translation import gettext as _
from django.utils import timezone
from django.db import transaction
from rest_framework.response import Response

from core import errors
from apps.api.viewsets import serializer_error_msg
from apps.app_wallet.apiviews import TradeGenericViewSet
from apps.app_wallet import trade_serializers
from apps.app_wallet.models import Recharge
from apps.app_wallet.managers.recharge import RechargeManager
from apps.app_wallet.managers.payment import PaymentManager
from apps.app_users import managers as user_manager
from apps.app_vo.managers import VoManager
from utils.model import OwnerType


class RechargeHandler:
    @staticmethod
    def manual_recharge(view: TradeGenericViewSet, request):
        executor = request.user

        if not executor.is_federal_admin():
            return view.exception_response(exc=errors.AccessDenied(message=_('你没有充值权限')))

        try:
            data = RechargeHandler.manual_recharge_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        vo = data['vo']
        recharge_user = data['user']
        remark = data['remark']
        amount = data['amount']

        if recharge_user:
            owner_type = OwnerType.USER.value
            owner_id = recharge_user.id
            owner_name = recharge_user.username
        else:
            owner_type = OwnerType.VO.value
            owner_id = vo.id
            owner_name = vo.name

        try:
            nt = timezone.now()
            with transaction.atomic():
                recharge = RechargeManager.create_wait_recharge(
                    trade_channel=Recharge.TradeChannel.MANUAL.value, total_amount=amount,
                    owner_type=owner_type, owner_id=owner_id, owner_name=owner_name,
                    remark=remark, creation_time=nt, executor=executor.username
                )
                RechargeManager.set_recharge_pay_success(
                    recharge=recharge, out_trade_no='', channel_account='',
                    channel_fee=Decimal('0'), receipt_amount=Decimal('0'), success_time=nt
                )
                RechargeManager().do_recharge_to_balance(recharge_id=recharge.id)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={'recharge_id': recharge.id})

    @staticmethod
    def manual_recharge_validate_params(request) -> dict:
        serializer = trade_serializers.RechargeManualSerializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'amount' in s_errors:
                exc = errors.BadRequest(
                    message=_('充值金额无效。') + s_errors['amount'][0], code='InvalidAmount')
            elif 'remark' in s_errors:
                exc = errors.BadRequest(
                    message=_('备注信息无效。') + s_errors['remark'][0], code='InvalidRemark')
            else:
                msg = serializer_error_msg(serializer.errors)
                exc = errors.BadRequest(message=msg)

            raise exc

        data = serializer.validated_data
        vo_id = data['vo_id']
        username = data['username']
        remark = data['remark']
        amount = data['amount']

        if amount < Decimal('0.01'):
            raise errors.BadRequest(message=_('充值金额无效，金额最小0.01。'), code='InvalidAmount')

        if vo_id and username:
            raise errors.BadRequest(message=_('不允许同时指定参数“username”和“vo_id”'))

        user = None
        vo = None
        if username:
            try:
                user = user_manager.get_user_by_name(username=username)
            except errors.UserNotExist:
                raise errors.UserNotExist(message=_('指定的用户“%(value)s”不存在') % {'value': username})

            account = PaymentManager.get_user_point_account(user_id=user.id, select_for_update=False, is_create=False)
            if account is None:
                raise errors.ConflictError(message=_('无法充值，用户的余额账户未开通。'))
        elif vo_id:
            vo = VoManager.get_vo_by_id(vo_id)
            if vo is None:
                raise errors.VoNotExist(message=_('指定的VO组“%(value)s”不存在') % {'value': vo_id})

            account = PaymentManager.get_vo_point_account(vo_id=vo.id, select_for_update=False, is_create=False)
            if account is None:
                raise errors.ConflictError(message=_('无法充值，用户的余额账户未开通。'))
        else:
            raise errors.BadRequest(message=_('必须指定充值用户或者vo组'))

        return {
            'amount': amount,
            'vo': vo,
            'user': user,
            'remark': remark
        }
