from datetime import datetime
from decimal import Decimal

from django.utils.translation import gettext as _
from django.db import transaction
from django.utils import timezone

from core import errors
from apps.app_wallet.models import Recharge, TransactionBill
from utils.model import OwnerType
from vo.managers import VoManager
from .payment import PaymentManager
from .bill import TransactionBillManager


class RechargeManager:
    @staticmethod
    def get_queryset():
        return Recharge.objects.all()

    @staticmethod
    def get_recharge_by_id(recharge_id: str):
        payment = Recharge.objects.filter(id=recharge_id).first()
        if payment is None:
            raise errors.NotFound(message=_('充值记录不存在'))

        return payment

    @staticmethod
    def get_recharge(recharge_id: str, user):
        """
        查询用户有访问权限的充值记录

        :return: Recharge()
        :raises: Error
        """
        recharge = Recharge.objects.filter(id=recharge_id).first()
        if recharge is None:
            raise errors.NotFound(message=_('充值记录不存在'))

        if recharge.owner_type == OwnerType.USER.value:
            if recharge.owner_id != user.id:
                raise errors.AccessDenied(message=_('你没有此充值记录的访问权限'))
        elif recharge.owner_type == OwnerType.VO.value:
            VoManager().get_has_read_perm_vo(vo_id=recharge.owner_id, user=user)
        else:
            raise errors.ConflictError(message=_('充值记录拥有者类型未知'), code='UnknownOwn')

        return recharge

    @staticmethod
    def create_wait_recharge(
            trade_channel: str, total_amount: Decimal, owner_type: str, owner_id: str, owner_name: str,
            remark: str, creation_time: datetime, executor: str
    ):
        """
        创建一个待支付的充值订单
        """
        if trade_channel not in Recharge.TradeChannel.values:
            raise errors.Error(message=_('创建充值订单错误，无效的交易渠道"%(value)s"。') % {'value': trade_channel})

        if owner_type not in OwnerType.values:
            raise errors.Error(message=_('创建充值订单错误，无效的所有者类型"%(value)s"。') % {'value': owner_type})

        if total_amount < Decimal('0.01'):
            raise errors.Error(message=_('创建充值订单错误，充值金额不得小于0.01"。'))

        recharge = Recharge(
            trade_channel=trade_channel,
            out_trade_no='',
            channel_account='',
            channel_fee=Decimal('0'),
            total_amount=total_amount,
            receipt_amount=Decimal('0'),
            creation_time=creation_time,
            success_time=None,
            status=Recharge.Status.WAIT.value,
            status_desc='',
            owner_type=owner_type,
            owner_id=owner_id,
            owner_name=owner_name,
            remark=remark,
            executor=executor,
            in_account=''
        )
        recharge.save(force_insert=True)
        return recharge

    @staticmethod
    def set_recharge_pay_success(
            recharge: Recharge, out_trade_no: str, channel_account: str,
            channel_fee: Decimal, receipt_amount: Decimal, success_time: datetime
    ):
        """
        设置充值订单支付（支付宝或微信支付）成功
        """
        recharge.out_trade_no = out_trade_no
        recharge.channel_account = channel_account
        recharge.channel_fee = channel_fee
        recharge.receipt_amount = receipt_amount
        recharge.success_time = success_time
        recharge.status = Recharge.Status.SUCCESS.value
        recharge.status_desc = '充值订单支付成功'

        recharge.save(update_fields=[
            'out_trade_no', 'channel_account', 'channel_fee', 'receipt_amount',
            'success_time', 'status', 'status_desc'
        ])
        return recharge

    @staticmethod
    def set_recharge_complete(
            recharge: Recharge, success_time: datetime, in_account: str
    ):
        """
        充值订单支付成功后，设置完成充值到用户或vo余额账户
        """
        recharge.success_time = success_time
        recharge.status = Recharge.Status.COMPLETE.value
        recharge.status_desc = _('充值完成')
        recharge.in_account = in_account

        recharge.save(update_fields=['success_time', 'status', 'status_desc', 'in_account'])
        return recharge

    @staticmethod
    def _pre_recharge(recharge: Recharge):
        if recharge.status != Recharge.Status.SUCCESS.value:
            raise errors.Error(message=_('必须是支付成功的充值订单才能充值到余额账户。'))

    def do_recharge_to_balance(self, recharge_id: str):
        """
        充值订单金额 充值 到余额账户

        :raises: Error
        """
        try:
            with transaction.atomic():
                recharge = Recharge.objects.select_for_update().filter(id=recharge_id).first()
                self._pre_recharge(recharge)
                self.__recharge_to_balance(recharge)
                return recharge
        except Exception as exc:
            raise errors.Error.from_error(exc)

    def __recharge_to_balance(self, recharge: Recharge):
        """
        已支付的充值订单的充值金额 充值 到余额账户
        * 此函数需放到事务中，确保数据的一致性 完整性
        """
        # 充值入账账户
        if recharge.owner_type == OwnerType.USER.value:
            account = PaymentManager.get_user_point_account(
                user_id=recharge.owner_id, select_for_update=True, is_create=False)
            if account is None:
                raise errors.ConflictError(message=_('无法完成充值，用户的余额账户未开通。'))
        else:
            account = PaymentManager.get_vo_point_account(
                vo_id=recharge.owner_id, select_for_update=True, is_create=False)
            if account is None:
                raise errors.ConflictError(message=_('无法完成充值，VO项目组的余额账户未开通。'))

        # 充值至余额账户
        if recharge.total_amount > Decimal('0'):
            account.balance = account.balance + recharge.total_amount
            account.save(update_fields=['balance'])

        # 充值订单完成
        nt = timezone.now()
        self.set_recharge_complete(recharge=recharge, success_time=nt, in_account=account.id)

        # 交易流水
        TransactionBillManager.create_transaction_bill(
            subject='余额充值', account=recharge.in_account,
            trade_type=TransactionBill.TradeType.RECHARGE.value,
            trade_id=recharge.id, out_trade_no=recharge.out_trade_no,
            trade_amounts=recharge.total_amount, amounts=recharge.total_amount,
            coupon_amount=Decimal('0'),  # 券金额
            after_balance=account.balance, owner_type=recharge.owner_type, owner_id=recharge.owner_id,
            owner_name=recharge.owner_name, app_service_id='', app_id='',
            remark=recharge.remark, creation_time=recharge.success_time, operator=recharge.executor
        )

        return recharge
