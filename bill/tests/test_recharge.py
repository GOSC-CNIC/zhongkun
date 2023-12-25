from decimal import Decimal

from django.urls import reverse

from utils.model import OwnerType
from utils.test import MyAPITransactionTestCase, get_or_create_user
from vo.models import VirtualOrganization
from bill.models import TransactionBill, Recharge
from bill.managers.payment import PaymentManager


class TradeRechargeTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user(username='lilei@cnic.cn')
        self.admin_user = get_or_create_user(username='tom@cnic.cn')
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user
        )
        self.vo.save()

    def test_manual_recharge(self):
        base_url = reverse('wallet-api:trade-recharge-manual')
        data = {
            "amount": "0.00",
            "username": "string",
            "vo_id": "string",
            "remark": "string"
        }
        r = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.admin_user)
        # AccessDenied
        r = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)
        self.admin_user.set_federal_admin()

        # InvalidAmount
        r = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidAmount', response=r)

        data['amount'] = '-1.23'
        r = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidAmount', response=r)

        data['amount'] = '0.008'
        r = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidAmount', response=r)

        # BadRequest
        r = self.client.post(base_url, data={
            "amount": "1.23",
            "username": "string",
            "vo_id": "string",
            "remark": "string"
        })
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)

        # UserNotExist
        r = self.client.post(base_url, data={
            "amount": "1.23",
            "username": "string",
            "remark": "string"
        })
        self.assertErrorResponse(status_code=404, code='UserNotExist', response=r)

        # VoNotExist
        r = self.client.post(base_url, data={
            "amount": "1.23",
            "vo_id": "string",
            "remark": "string"
        })
        self.assertErrorResponse(status_code=404, code='VoNotExist', response=r)

        # Conflict
        r = self.client.post(base_url, data={
            "amount": "1.23",
            "username": self.user.username,
            "remark": "string"
        })
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # Conflict
        r = self.client.post(base_url, data={
            "amount": "1.23",
            "vo_id": self.vo.id,
            "remark": "string"
        })
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # ------  user --------
        # 开通余额账户
        user_account = PaymentManager.get_user_point_account(user_id=self.user.id, is_create=True)
        self.assertEqual(user_account.balance, Decimal('0'))

        r = self.client.post(base_url, data={
            "amount": "1.23",
            "username": self.user.username,
            "remark": "string"
        })
        self.assertEqual(r.status_code, 200)
        recharge_id1 = r.data['recharge_id']
        recharge1 = Recharge.objects.get(id=recharge_id1)
        self.assertEqual(recharge1.total_amount, Decimal('1.23'))
        self.assertEqual(recharge1.receipt_amount, Decimal('0'))
        self.assertEqual(recharge1.channel_fee, Decimal('0'))
        self.assertEqual(recharge1.out_trade_no, '')
        self.assertEqual(recharge1.channel_account, '')
        self.assertEqual(recharge1.trade_channel, Recharge.TradeChannel.MANUAL.value)
        self.assertEqual(recharge1.status, Recharge.Status.COMPLETE.value)
        self.assertEqual(recharge1.in_account, user_account.id)
        self.assertEqual(recharge1.remark, "string")
        self.assertEqual(recharge1.executor, self.admin_user.username)
        self.assertEqual(recharge1.owner_type, OwnerType.USER.value)
        self.assertEqual(recharge1.owner_id, self.user.id)
        self.assertEqual(recharge1.owner_name, self.user.username)

        user_account.refresh_from_db()
        self.assertEqual(user_account.balance, Decimal('1.23'))

        # 交易流水确认
        bill: TransactionBill = TransactionBill.objects.filter(
            trade_type=TransactionBill.TradeType.RECHARGE.value, trade_id=recharge_id1).first()
        self.assertEqual(bill.account, user_account.id)
        self.assertEqual(bill.app_service_id, '')
        self.assertEqual(bill.app_id, '')
        self.assertEqual(bill.out_trade_no, '')
        self.assertEqual(bill.trade_amounts, Decimal('1.23'))
        self.assertEqual(bill.amounts, Decimal('1.23'))
        self.assertEqual(bill.coupon_amount, Decimal('0'))
        self.assertEqual(bill.after_balance, Decimal('1.23'))
        self.assertEqual(bill.owner_id, recharge1.owner_id)
        self.assertEqual(bill.owner_type, OwnerType.USER.value)

        # ------  vo --------
        # 开通余额账户
        vo_account = PaymentManager.get_vo_point_account(vo_id=self.vo.id, is_create=True)
        self.assertEqual(vo_account.balance, Decimal('0'))

        r = self.client.post(base_url, data={
            "amount": "66.88",
            "vo_id": self.vo.id,
            "remark": "vo remark"
        })
        self.assertEqual(r.status_code, 200)
        recharge_id2 = r.data['recharge_id']
        recharge2 = Recharge.objects.get(id=recharge_id2)
        self.assertEqual(recharge2.total_amount, Decimal('66.88'))
        self.assertEqual(recharge2.receipt_amount, Decimal('0'))
        self.assertEqual(recharge2.channel_fee, Decimal('0'))
        self.assertEqual(recharge2.out_trade_no, '')
        self.assertEqual(recharge2.channel_account, '')
        self.assertEqual(recharge2.trade_channel, Recharge.TradeChannel.MANUAL.value)
        self.assertEqual(recharge2.status, Recharge.Status.COMPLETE.value)
        self.assertEqual(recharge2.in_account, vo_account.id)
        self.assertEqual(recharge2.remark, "vo remark")
        self.assertEqual(recharge2.executor, self.admin_user.username)
        self.assertEqual(recharge2.owner_type, OwnerType.VO.value)
        self.assertEqual(recharge2.owner_id, self.vo.id)
        self.assertEqual(recharge2.owner_name, self.vo.name)

        vo_account.refresh_from_db()
        self.assertEqual(vo_account.balance, Decimal('66.88'))

        # 交易流水确认
        bill: TransactionBill = TransactionBill.objects.filter(
            trade_type=TransactionBill.TradeType.RECHARGE.value, trade_id=recharge_id2).first()
        self.assertEqual(bill.account, vo_account.id)
        self.assertEqual(bill.app_service_id, '')
        self.assertEqual(bill.app_id, '')
        self.assertEqual(bill.out_trade_no, '')
        self.assertEqual(bill.trade_amounts, Decimal('66.88'))
        self.assertEqual(bill.amounts, Decimal('66.88'))
        self.assertEqual(bill.coupon_amount, Decimal('0'))
        self.assertEqual(bill.after_balance, Decimal('66.88'))
        self.assertEqual(bill.owner_id, recharge2.owner_id)
        self.assertEqual(bill.owner_type, OwnerType.VO.value)
