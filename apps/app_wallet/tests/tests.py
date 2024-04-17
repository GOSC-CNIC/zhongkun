from decimal import Decimal
from datetime import timedelta, datetime

from django.test import TransactionTestCase
from django.utils import timezone

from core import errors
from utils.test import get_or_create_user, get_or_create_service, get_or_create_organization
from utils.model import OwnerType, PayType
from utils.decimal_utils import quantize_10_2
from apps.order.models import ResourceType, Order
from apps.order.managers import OrderPaymentManager
from apps.vo.managers import VoManager
from apps.servers.models import ServiceConfig
from apps.app_wallet.models import (
    CashCoupon, CashCouponActivity, CashCouponPaymentHistory, RefundRecord,
    PaymentHistory, PayAppService, PayApp, TransactionBill
)
from apps.app_wallet.managers import PaymentManager, CashCouponActivityManager


class PaymentManagerTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()

        # 余额支付有关配置
        app = PayApp(name='app')
        app.save()
        self.app = app
        po = get_or_create_organization(name='机构')
        po.save()
        self.app_service1 = PayAppService(
            name='service1', app=app, orgnazition=po
        )
        self.app_service1.save()
        self.app_service2 = PayAppService(
            name='service2', app=app, orgnazition=po
        )
        self.app_service2.save()

        self.service.pay_app_service_id = self.app_service1.id
        self.service.save(update_fields=['pay_app_service_id'])

        self.vo = VoManager().create_vo(user=self.user, name='test vo', company='test', description='test')
        self.service2 = ServiceConfig(
            name='test2', org_data_center_id=self.service.org_data_center_id, endpoint_url='test2',
            username='', password='', need_vpn=False, pay_app_service_id=self.app_service2.id
        )
        self.service2.save()

    def test_pay_order_no_coupon(self):
        pay_mgr = OrderPaymentManager()
        order1 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UNPAID.value,
            total_amount=Decimal('123.45'),
            payable_amount=Decimal('123.45'),
            app_service_id=self.service.pay_app_service_id,
            service_id=self.service.id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config={},
            period=10, pay_type=PayType.PREPAID,
            user_id=self.user.id, username=self.user.username,
            vo_id='', vo_name='',
            owner_type=OwnerType.USER.value
        )
        order1.save(force_insert=True)

        app_id = self.app.id
        # user order, no enough balance, when required enough balance
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=None, only_coupon=False,
                required_enough_balance=True
            )

        pay_mgr.payment.get_user_point_account(user_id=self.user.id)
        self.assertEqual(self.user.userpointaccount.balance, Decimal(0))
        order1 = pay_mgr.pay_order(
            order=order1, app_id=app_id, subject='云服务器计费',
            executor=self.user.username, remark='',
            coupon_ids=None, only_coupon=False,
            required_enough_balance=False
        )
        self.user.userpointaccount.refresh_from_db()
        self.assertEqual(self.user.userpointaccount.balance, Decimal('-123.45'))
        self.assertEqual(order1.status, Order.Status.PAID.value)
        self.assertEqual(order1.payment_method, Order.PaymentMethod.BALANCE.value)
        self.assertEqual(order1.payable_amount, Decimal('123.45'))
        self.assertEqual(order1.pay_amount, Decimal('123.45'))
        self.assertEqual(order1.balance_amount, Decimal('123.45'))
        self.assertEqual(order1.coupon_amount, Decimal('0'))
        self.assertIsInstance(order1.payment_time, datetime)
        pay_history = PaymentHistory.objects.filter(order_id=order1.id).first()
        self.assertEqual(pay_history.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history.payable_amounts, Decimal('123.45'))
        self.assertEqual(pay_history.amounts, Decimal('-123.45'))
        self.assertEqual(pay_history.payer_name, self.user.username)
        self.assertEqual(pay_history.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history.instance_id, '')
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user.id)
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, self.user.userpointaccount.id)

        # 交易流水
        tbills = TransactionBill.objects.all()
        tbill: TransactionBill = tbills[0]
        self.assertEqual(tbill.account, self.user.userpointaccount.id)
        self.assertEqual(tbill.coupon_amount, Decimal('0'))
        self.assertEqual(tbill.amounts, Decimal('-123.45'))
        self.assertEqual(tbill.after_balance, Decimal('-123.45'))
        self.assertEqual(tbill.owner_type, OwnerType.USER.value)
        self.assertEqual(tbill.owner_id, self.user.id)
        self.assertEqual(tbill.owner_name, self.user.username)
        self.assertEqual(tbill.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(tbill.app_id, pay_history.app_id)
        self.assertEqual(tbill.trade_type, TransactionBill.TradeType.PAYMENT.value)
        self.assertEqual(tbill.trade_id, pay_history.id)

        order2 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UNPAID.value,
            total_amount=Decimal('421.45'),
            payable_amount=Decimal('321.45'),
            app_service_id=self.service.pay_app_service_id,
            service_id=self.service.id,
            service_name=self.service.name,
            resource_type=ResourceType.DISK.value,
            instance_config={},
            period=10, pay_type=PayType.PREPAID,
            user_id='', username='',
            vo_id=self.vo.id, vo_name=self.vo.name,
            owner_type=OwnerType.VO.value
        )
        order2.save(force_insert=True)

        # vo order, no enough balance, when required enough balance
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_order(
                order=order2, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=None, only_coupon=False,
                required_enough_balance=True
            )

        pay_mgr.payment.get_vo_point_account(vo_id=self.vo.id)
        self.assertEqual(self.vo.vopointaccount.balance, Decimal(0))
        order2 = pay_mgr.pay_order(
            order=order2, app_id=app_id, subject='云服务器计费',
            executor=self.user.username, remark='',
            coupon_ids=None, only_coupon=False,
            required_enough_balance=False
        )
        self.vo.vopointaccount.refresh_from_db()
        order2.refresh_from_db()
        self.assertEqual(self.vo.vopointaccount.balance, Decimal('-321.45'))
        self.assertEqual(order2.status, Order.Status.PAID.value)
        self.assertEqual(order2.payment_method, Order.PaymentMethod.BALANCE.value)
        self.assertEqual(order2.pay_amount, Decimal('321.45'))
        self.assertEqual(order2.balance_amount, Decimal('321.45'))
        self.assertEqual(order2.coupon_amount, Decimal('0'))
        self.assertIsInstance(order2.payment_time, datetime)
        pay_history2 = PaymentHistory.objects.filter(order_id=order2.id).first()
        self.assertEqual(pay_history2.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history2.payable_amounts, Decimal('321.45'))
        self.assertEqual(pay_history2.amounts, Decimal('-321.45'))
        self.assertEqual(pay_history2.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history2.payer_id, self.vo.id)
        self.assertEqual(pay_history2.payer_name, self.vo.name)
        self.assertEqual(pay_history2.executor, self.user.username)
        self.assertEqual(pay_history2.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history2.payment_account, self.vo.vopointaccount.id)
        self.assertEqual(pay_history2.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history2.instance_id, '')

        # 交易流水
        tbills = TransactionBill.objects.filter(
            trade_type=TransactionBill.TradeType.PAYMENT.value, trade_id=pay_history2.id).all()
        tbill: TransactionBill = tbills[0]
        self.assertEqual(tbill.account, self.vo.vopointaccount.id)
        self.assertEqual(tbill.coupon_amount, Decimal('0'))
        self.assertEqual(tbill.amounts, Decimal('-321.45'))
        self.assertEqual(tbill.after_balance, Decimal('-321.45'))
        self.assertEqual(tbill.owner_type, OwnerType.VO.value)
        self.assertEqual(tbill.owner_id, self.vo.id)
        self.assertEqual(tbill.owner_name, self.vo.name)
        self.assertEqual(tbill.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(tbill.app_id, pay_history2.app_id)
        self.assertEqual(tbill.trade_type, TransactionBill.TradeType.PAYMENT.value)
        self.assertEqual(tbill.trade_id, pay_history2.id)

    def test_user_pay_order_with_coupon(self):
        pay_mgr = OrderPaymentManager()
        account = PaymentManager().get_user_point_account(self.user.id)
        account.balance = Decimal('200')
        account.save(update_fields=['balance'])
        order1 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UNPAID.value,
            total_amount=Decimal('100'),
            payable_amount=Decimal('100'),
            service_id=self.service.id,
            app_service_id=self.service.pay_app_service_id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config={},
            period=10, pay_type=PayType.PREPAID,
            user_id=self.user.id, username=self.user.username,
            vo_id='', vo_name='',
            owner_type=OwnerType.USER.value
        )
        order1.save(force_insert=True)

        order2 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UNPAID.value,
            total_amount=Decimal('388.88'),
            payable_amount=Decimal('288.88'),
            app_service_id=self.service.pay_app_service_id,
            service_id=self.service.id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config={},
            period=10, pay_type=PayType.PREPAID,
            user_id=self.user.id, username=self.user.username,
            vo_id='', vo_name='',
            owner_type=OwnerType.USER.value
        )
        order2.save(force_insert=True)

        now_time = timezone.now()
        # 有效, service
        coupon1_user = CashCoupon(
            face_value=Decimal('20'),
            balance=Decimal('20'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon1_user.save(force_insert=True)

        # 有效, service
        coupon2_user = CashCoupon(
            face_value=Decimal('25'),
            balance=Decimal('25'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon2_user.save(force_insert=True)

        # 有效，只适用于service2
        coupon3_user = CashCoupon(
            face_value=Decimal('33'),
            balance=Decimal('33'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service2.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon3_user.save(force_insert=True)

        # 过期, service
        coupon4_user = CashCoupon(
            face_value=Decimal('40'),
            balance=Decimal('40'),
            effective_time=now_time - timedelta(days=10),
            expiration_time=now_time - timedelta(days=1),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon4_user.save(force_insert=True)

        # 时间未生效, service
        coupon5_user = CashCoupon(
            face_value=Decimal('45'),
            balance=Decimal('45'),
            effective_time=now_time + timedelta(days=1),
            expiration_time=now_time + timedelta(days=11),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon5_user.save(force_insert=True)

        # 有效, service
        coupon6_vo = CashCoupon(
            face_value=Decimal('50'),
            balance=Decimal('50'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon6_vo.save(force_insert=True)

        # 有效,service, 余额0
        coupon7_user = CashCoupon(
            face_value=Decimal('20'),
            balance=Decimal('0'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon7_user.save(force_insert=True)

        app_id = self.app.id
        # 指定不存在的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_user.id, 'notfound'
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'NoSuchCoupon')

        # 指定不属于自己的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_user.id, coupon6_vo.id
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'NoSuchCoupon')

        # 指定未生效的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_user.id, coupon5_user.id
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'NotEffective')

        # 指定过期的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_user.id, coupon4_user.id
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'ExpiredCoupon')

        # 指定不适用服务的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_user.id, coupon3_user.id
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponNotApplicable')

        # 指定余额为0的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_user.id, coupon7_user.id
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponNoBalance')

        # 只用指定券支付，券余额50（20 + 30），订单金额 100
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_user.id, coupon2_user.id
                ], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponBalanceNotEnough')

        # 指定券+账户余额支付，券余额45（20 + 25），订单金额 100
        pay_mgr.pay_order(
            order=order1, app_id=app_id, subject='云服务器计费',
            executor=self.user.username, remark='',
            coupon_ids=[
                coupon1_user.id, coupon2_user.id
            ], only_coupon=False,
            required_enough_balance=True
        )

        user_account = self.user.userpointaccount
        user_account.refresh_from_db()
        self.assertEqual(user_account.balance, Decimal('145'))
        # 券的扣费确认
        coupon1_user.refresh_from_db()
        self.assertEqual(coupon1_user.balance, Decimal('0'))
        coupon2_user.refresh_from_db()
        self.assertEqual(coupon2_user.balance, Decimal('0'))

        order1.refresh_from_db()
        self.assertEqual(order1.status, Order.Status.PAID.value)
        self.assertEqual(order1.payment_method, Order.PaymentMethod.MIXED.value)
        self.assertEqual(order1.payable_amount, Decimal('100'))
        self.assertEqual(order1.pay_amount, Decimal('100'))
        self.assertIsInstance(order1.payment_time, datetime)
        self.assertEqual(order1.balance_amount, Decimal('55'))
        self.assertEqual(order1.coupon_amount, Decimal('45'))

        # 支付记录确认
        pay_history1 = PaymentHistory.objects.filter(order_id=order1.id).first()
        self.assertEqual(pay_history1.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history1.payable_amounts, Decimal('100'))
        self.assertEqual(pay_history1.amounts, Decimal('-55'))
        self.assertEqual(pay_history1.coupon_amount, Decimal('-45'))
        self.assertEqual(pay_history1.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history1.payer_id, self.user.id)
        self.assertEqual(pay_history1.payer_name, self.user.username)
        self.assertEqual(pay_history1.executor, self.user.username)
        self.assertEqual(pay_history1.payment_method, PaymentHistory.PaymentMethod.BALANCE_COUPON.value)
        self.assertEqual(pay_history1.payment_account, user_account.id)
        self.assertEqual(pay_history1.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history1.instance_id, '')
        # 券支付记录
        cc_historys = pay_history1.cashcouponpaymenthistory_set.all().order_by('creation_time')
        self.assertEqual(cc_historys[0].payment_history_id, pay_history1.id)
        self.assertEqual(cc_historys[0].cash_coupon_id, coupon1_user.id)
        self.assertEqual(cc_historys[0].before_payment, Decimal('20'))
        self.assertEqual(cc_historys[0].amounts, Decimal('-20'))
        self.assertEqual(cc_historys[0].after_payment, Decimal('0'))
        self.assertEqual(cc_historys[1].payment_history_id, pay_history1.id)
        self.assertEqual(cc_historys[1].cash_coupon_id, coupon2_user.id)
        self.assertEqual(cc_historys[1].before_payment, Decimal('25'))
        self.assertEqual(cc_historys[1].amounts, Decimal('-25'))
        self.assertEqual(cc_historys[1].after_payment, Decimal('0'))

        # 交易流水
        tbills = TransactionBill.objects.filter(
            trade_type=TransactionBill.TradeType.PAYMENT.value, trade_id=pay_history1.id).all()
        tbill: TransactionBill = tbills[0]
        self.assertEqual(tbill.account, self.user.userpointaccount.id)
        self.assertEqual(tbill.coupon_amount, Decimal('-45'))
        self.assertEqual(tbill.amounts, Decimal('-55'))
        self.assertEqual(tbill.after_balance, Decimal('145'))
        self.assertEqual(tbill.owner_type, OwnerType.USER.value)
        self.assertEqual(tbill.owner_id, self.user.id)
        self.assertEqual(tbill.owner_name, self.user.username)
        self.assertEqual(tbill.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(tbill.app_id, pay_history1.app_id)
        self.assertEqual(tbill.trade_type, TransactionBill.TradeType.PAYMENT.value)
        self.assertEqual(tbill.trade_id, pay_history1.id)

        # 支付已支付状态的订单
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='云服务器',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'OrderPaid')

        # --------- pay order2 test ----------
        # 不指定券，只用券支付
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order2, app_id=app_id, subject='云服务器',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponBalanceNotEnough')

        # 余额不足
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order2, app_id=app_id, subject='云服务器',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'BalanceNotEnough')

        # 订单金额 288.88
        pay_mgr.pay_order(
            order=order2, app_id=app_id, subject='云服务器',
            executor=self.user.username, remark='',
            coupon_ids=[], only_coupon=False,
            required_enough_balance=False
        )

        user_account = self.user.userpointaccount
        user_account.refresh_from_db()
        self.assertEqual(user_account.balance, Decimal('-143.88'))
        order2.refresh_from_db()
        self.assertEqual(order2.status, Order.Status.PAID.value)
        self.assertEqual(order2.payment_method, Order.PaymentMethod.BALANCE.value)
        self.assertEqual(order2.pay_amount, Decimal('288.88'))
        self.assertIsInstance(order2.payment_time, datetime)
        self.assertEqual(order2.balance_amount, Decimal('288.88'))
        self.assertEqual(order2.coupon_amount, Decimal('0'))

        # 支付记录确认
        pay_history2 = PaymentHistory.objects.filter(order_id=order2.id).first()
        self.assertEqual(pay_history2.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history2.payable_amounts, Decimal('288.88'))
        self.assertEqual(pay_history2.amounts, Decimal('-288.88'))
        self.assertEqual(pay_history2.coupon_amount, Decimal('0'))
        self.assertEqual(pay_history2.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history2.payer_id, self.user.id)
        self.assertEqual(pay_history2.payer_name, self.user.username)
        self.assertEqual(pay_history2.executor, self.user.username)
        self.assertEqual(pay_history2.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history2.payment_account, user_account.id)
        self.assertEqual(pay_history2.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history2.instance_id, '')
        # 券支付记录
        cc_historys = pay_history2.cashcouponpaymenthistory_set.all().order_by('creation_time')
        self.assertEqual(len(cc_historys), 0)

        # 交易流水
        tbills = TransactionBill.objects.filter(
            trade_type=TransactionBill.TradeType.PAYMENT.value, trade_id=pay_history2.id).all()
        tbill: TransactionBill = tbills[0]
        self.assertEqual(tbill.account, self.user.userpointaccount.id)
        self.assertEqual(tbill.coupon_amount, Decimal('0'))
        self.assertEqual(tbill.amounts, Decimal('-288.88'))
        self.assertEqual(tbill.after_balance, Decimal('-143.88'))
        self.assertEqual(tbill.owner_type, OwnerType.USER.value)
        self.assertEqual(tbill.owner_id, self.user.id)
        self.assertEqual(tbill.owner_name, self.user.username)
        self.assertEqual(tbill.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(tbill.app_id, pay_history2.app_id)
        self.assertEqual(tbill.trade_type, TransactionBill.TradeType.PAYMENT.value)
        self.assertEqual(tbill.trade_id, pay_history2.id)

    def test_vo_pay_order_with_coupon(self):
        pay_mgr = OrderPaymentManager()
        account = pay_mgr.payment.get_vo_point_account(self.vo.id)
        account.balance = Decimal('200')
        account.save(update_fields=['balance'])
        order1 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UNPAID.value,
            payable_amount=Decimal('100'),
            service_id=self.service.id,
            app_service_id=self.service.pay_app_service_id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config={},
            period=10, pay_type=PayType.PREPAID,
            user_id='', username='',
            vo_id=self.vo.id, vo_name=self.vo.name,
            owner_type=OwnerType.VO.value
        )
        order1.save(force_insert=True)

        order2 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UNPAID.value,
            total_amount=Decimal('288.88'),
            payable_amount=Decimal('288.88'),
            service_id=self.service.id,
            app_service_id=self.service.pay_app_service_id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config={},
            period=10, pay_type=PayType.PREPAID,
            user_id='', username='',
            vo_id=self.vo.id, vo_name=self.vo.name,
            owner_type=OwnerType.VO.value
        )
        order2.save(force_insert=True)

        now_time = timezone.now()
        # 有效, service
        coupon1_vo = CashCoupon(
            face_value=Decimal('20'),
            balance=Decimal('20'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon1_vo.save(force_insert=True)

        # 有效, service
        coupon2_vo = CashCoupon(
            face_value=Decimal('25'),
            balance=Decimal('25'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon2_vo.save(force_insert=True)

        # 有效，只适用于service2
        coupon3_vo = CashCoupon(
            face_value=Decimal('33'),
            balance=Decimal('33'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service2.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon3_vo.save(force_insert=True)

        # 过期, service
        coupon4_vo = CashCoupon(
            face_value=Decimal('40'),
            balance=Decimal('40'),
            effective_time=now_time - timedelta(days=10),
            expiration_time=now_time - timedelta(days=1),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon4_vo.save(force_insert=True)

        # 时间未生效, service
        coupon5_vo = CashCoupon(
            face_value=Decimal('45'),
            balance=Decimal('45'),
            effective_time=now_time + timedelta(days=1),
            expiration_time=now_time + timedelta(days=11),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon5_vo.save(force_insert=True)

        # 有效, service, 余额0
        coupon6_vo = CashCoupon(
            face_value=Decimal('20'),
            balance=Decimal('0'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon6_vo.save(force_insert=True)

        # 有效, service
        coupon7_user = CashCoupon(
            face_value=Decimal('50'),
            balance=Decimal('50'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon7_user.save(force_insert=True)

        app_id = self.app.id
        # 指定不存在的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='云服务器',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_vo.id, 'notfound'
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'NoSuchCoupon')

        # 指定不属于自己的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='云服务器',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_vo.id, coupon7_user.id
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'NoSuchCoupon')

        # 指定未生效的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_vo.id, coupon5_vo.id
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'NotEffective')

        # 指定过期的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_vo.id, coupon4_vo.id
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'ExpiredCoupon')

        # 指定不适用资源类型的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_vo.id, coupon3_vo.id
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponNotApplicable')

        # 指定余额为0的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_vo.id, coupon6_vo.id
                ], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponNoBalance')

        # 只用指定券支付，券余额50（20 + 30），订单金额 100
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_vo.id, coupon2_vo.id
                ], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponBalanceNotEnough')

        # 指定券+账户余额支付，券余额45（20 + 25），订单金额 100
        pay_mgr.pay_order(
            order=order1, app_id=app_id, subject='资源订单',
            executor=self.user.username, remark='',
            coupon_ids=[
                coupon1_vo.id, coupon2_vo.id
            ], only_coupon=False,
            required_enough_balance=True
        )

        vo_account = self.vo.vopointaccount
        vo_account.refresh_from_db()
        self.assertEqual(vo_account.balance, Decimal('145'))
        # 券的扣费确认
        coupon1_vo.refresh_from_db()
        self.assertEqual(coupon1_vo.balance, Decimal('0'))
        coupon2_vo.refresh_from_db()
        self.assertEqual(coupon2_vo.balance, Decimal('0'))

        order1.refresh_from_db()
        self.assertEqual(order1.status, Order.Status.PAID.value)
        self.assertEqual(order1.payment_method, Order.PaymentMethod.MIXED.value)
        self.assertEqual(order1.payable_amount, Decimal('100'))
        self.assertEqual(order1.pay_amount, Decimal('100'))
        self.assertIsInstance(order1.payment_time, datetime)
        self.assertEqual(order1.balance_amount, Decimal('55'))
        self.assertEqual(order1.coupon_amount, Decimal('45'))

        # 支付记录确认
        pay_history1 = PaymentHistory.objects.filter(order_id=order1.id).first()
        self.assertEqual(pay_history1.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history1.payable_amounts, Decimal('100'))
        self.assertEqual(pay_history1.amounts, Decimal('-55'))
        self.assertEqual(pay_history1.coupon_amount, Decimal('-45'))
        self.assertEqual(pay_history1.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history1.payer_id, self.vo.id)
        self.assertEqual(pay_history1.payer_name, self.vo.name)
        self.assertEqual(pay_history1.executor, self.user.username)
        self.assertEqual(pay_history1.payment_method, PaymentHistory.PaymentMethod.BALANCE_COUPON.value)
        self.assertEqual(pay_history1.payment_account, vo_account.id)
        self.assertEqual(pay_history1.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history1.instance_id, '')
        self.assertEqual(pay_history1.app_id, app_id)
        self.assertEqual(pay_history1.subject, '资源订单')
        # 券支付记录
        cc_historys = pay_history1.cashcouponpaymenthistory_set.all().order_by('creation_time')
        self.assertEqual(cc_historys[0].payment_history_id, pay_history1.id)
        self.assertIsNone(cc_historys[0].refund_history_id)
        self.assertEqual(cc_historys[0].cash_coupon_id, coupon1_vo.id)
        self.assertEqual(cc_historys[0].before_payment, Decimal('20'))
        self.assertEqual(cc_historys[0].amounts, Decimal('-20'))
        self.assertEqual(cc_historys[0].after_payment, Decimal('0'))
        self.assertEqual(cc_historys[1].payment_history_id, pay_history1.id)
        self.assertIsNone(cc_historys[1].refund_history_id)
        self.assertEqual(cc_historys[1].cash_coupon_id, coupon2_vo.id)
        self.assertEqual(cc_historys[1].before_payment, Decimal('25'))
        self.assertEqual(cc_historys[1].amounts, Decimal('-25'))
        self.assertEqual(cc_historys[1].after_payment, Decimal('0'))

        # 交易流水
        tbills = TransactionBill.objects.filter(
            trade_type=TransactionBill.TradeType.PAYMENT.value, trade_id=pay_history1.id).all()
        tbill: TransactionBill = tbills[0]
        self.assertEqual(tbill.account, self.vo.vopointaccount.id)
        self.assertEqual(tbill.coupon_amount, Decimal('-45'))
        self.assertEqual(tbill.amounts, Decimal('-55'))
        self.assertEqual(tbill.after_balance, Decimal('145'))
        self.assertEqual(tbill.owner_type, OwnerType.VO.value)
        self.assertEqual(tbill.owner_id, self.vo.id)
        self.assertEqual(tbill.owner_name, self.vo.name)
        self.assertEqual(tbill.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(tbill.app_id, pay_history1.app_id)
        self.assertEqual(tbill.trade_type, TransactionBill.TradeType.PAYMENT.value)
        self.assertEqual(tbill.trade_id, pay_history1.id)

        # 支付已支付状态的订单
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id=app_id, subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'OrderPaid')

        # --------- pay order2 test ----------
        # 不指定券，只用券支付
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order2, app_id=app_id, subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponBalanceNotEnough')

        # 余额不足
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order2, app_id=app_id, subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'BalanceNotEnough')

        # 订单金额 288.88
        pay_mgr.pay_order(
            order=order2, app_id=app_id, subject='资源订单',
            executor=self.user.username, remark='',
            coupon_ids=[], only_coupon=False,
            required_enough_balance=False
        )

        vo_account = self.vo.vopointaccount
        vo_account.refresh_from_db()
        self.assertEqual(vo_account.balance, Decimal('-143.88'))
        order2.refresh_from_db()
        self.assertEqual(order2.status, Order.Status.PAID.value)
        self.assertEqual(order2.payment_method, Order.PaymentMethod.BALANCE.value)
        self.assertEqual(order2.pay_amount, Decimal('288.88'))
        self.assertIsInstance(order2.payment_time, datetime)
        self.assertEqual(order2.balance_amount, Decimal('288.88'))
        self.assertEqual(order2.coupon_amount, Decimal('0'))

        # 支付记录确认
        pay_history2 = PaymentHistory.objects.filter(order_id=order2.id).first()
        self.assertEqual(pay_history2.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history2.payable_amounts, Decimal('288.88'))
        self.assertEqual(pay_history2.amounts, Decimal('-288.88'))
        self.assertEqual(pay_history2.coupon_amount, Decimal('0'))
        self.assertEqual(pay_history2.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history2.payer_id, self.vo.id)
        self.assertEqual(pay_history2.payer_name, self.vo.name)
        self.assertEqual(pay_history2.executor, self.user.username)
        self.assertEqual(pay_history2.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history2.payment_account, vo_account.id)
        self.assertEqual(pay_history2.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history2.instance_id, '')
        self.assertEqual(pay_history2.app_id, app_id)
        self.assertEqual(pay_history2.subject, '资源订单')
        # 券支付记录
        cc_historys = pay_history2.cashcouponpaymenthistory_set.all().order_by('creation_time')
        self.assertEqual(len(cc_historys), 0)

        # 交易流水
        tbills = TransactionBill.objects.filter(
            trade_type=TransactionBill.TradeType.PAYMENT.value, trade_id=pay_history2.id).all()
        tbill: TransactionBill = tbills[0]
        self.assertEqual(tbill.account, self.vo.vopointaccount.id)
        self.assertEqual(tbill.coupon_amount, Decimal('0'))
        self.assertEqual(tbill.amounts, Decimal('-288.88'))
        self.assertEqual(tbill.after_balance, Decimal('-143.88'))
        self.assertEqual(tbill.owner_type, OwnerType.VO.value)
        self.assertEqual(tbill.owner_id, self.vo.id)
        self.assertEqual(tbill.owner_name, self.vo.name)
        self.assertEqual(tbill.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(tbill.app_id, pay_history2.app_id)
        self.assertEqual(tbill.trade_type, TransactionBill.TradeType.PAYMENT.value)
        self.assertEqual(tbill.trade_id, pay_history2.id)

    def test_has_enough_balance_user(self):
        pm = PaymentManager()
        # no coupon, no enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('10'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

        # no coupon, 不欠费
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('0'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        userpointaccount = self.user.userpointaccount
        userpointaccount.balance = Decimal('20')
        userpointaccount.save(update_fields=['balance'])

        # no coupon, enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('10'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        # no coupon, no enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('21'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

        # no coupon, 不欠费enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('0'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        # create coupon
        now_time = timezone.now()
        # 有效, service
        coupon1_user = CashCoupon(
            face_value=Decimal('20'),
            balance=Decimal('20'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon1_user.save(force_insert=True)

        # 过期, service
        coupon2_user = CashCoupon(
            face_value=Decimal('25'),
            balance=Decimal('25'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time - timedelta(days=1),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon2_user.save(force_insert=True)

        # has coupon, balance 20 + coupon 20, enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('30'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        # has coupon, balance 20 + coupon 20, no enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('41'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

        # has coupon, 不欠费enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('0'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        userpointaccount = self.user.userpointaccount
        userpointaccount.balance = Decimal('-25')
        userpointaccount.save(update_fields=['balance'])

        # has coupon, balance -25 + coupon 20, enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('20'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        # has coupon, balance -25 + coupon 20, no enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('21'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

        # has coupon, 不欠费enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('0'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        coupon1_user.balance = Decimal('0')
        coupon1_user.save(update_fields=['balance'])

        # has coupon, balance -25 + coupon 0, not enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('1'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

        # has coupon, 欠费not enough balance
        ok = pm.has_enough_balance_user(
            user_id=self.user.id, money_amount=Decimal('0'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

    def test_has_enough_balance_vo(self):
        pm = PaymentManager()
        # no coupon, no enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('10'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

        # no coupon, 不欠费
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('0'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        vopointaccount = self.vo.vopointaccount
        vopointaccount.balance = Decimal('20')
        vopointaccount.save(update_fields=['balance'])

        # no coupon, enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('10'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        # no coupon, no enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('21'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

        # no coupon, 不欠费enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('0'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        # create coupon
        now_time = timezone.now()
        # 有效, service
        coupon1_vo = CashCoupon(
            face_value=Decimal('20'),
            balance=Decimal('20'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            vo_id=self.vo.id, user_id=None
        )
        coupon1_vo.save(force_insert=True)

        # 过期, service
        coupon2_vo = CashCoupon(
            face_value=Decimal('25'),
            balance=Decimal('25'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time - timedelta(days=1),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            vo_id=self.vo.id, user_id=None
        )
        coupon2_vo.save(force_insert=True)

        # has coupon, balance 20 + coupon 20, enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('30'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        # has coupon, balance 20 + coupon 20, no enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('41'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

        # has coupon, 不欠费enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('0'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        vopointaccount = self.vo.vopointaccount
        vopointaccount.balance = Decimal('-25')
        vopointaccount.save(update_fields=['balance'])

        # has coupon, balance -25 + coupon 20, enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('20'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        # has coupon, balance -25 + coupon 20, no enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('21'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

        # has coupon, 不欠费enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('0'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, True)

        coupon1_vo.balance = Decimal('0')
        coupon1_vo.save(update_fields=['balance'])

        # has coupon, balance -25 + coupon 0, not enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('1'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

        # has coupon, 欠费not enough balance
        ok = pm.has_enough_balance_vo(
            vo_id=self.vo.id, money_amount=Decimal('0'), with_coupons=True, app_service_id=self.app_service1.id
        )
        self.assertEqual(ok, False)

    def test_refund(self):
        now_time = timezone.now()
        user = self.user
        user_account = PaymentManager.get_user_point_account(user_id=user.id, is_create=True)
        coupon1_user = CashCoupon(
            face_value=Decimal('120'),
            balance=Decimal('20'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon1_user.save(force_insert=True)

        # 有效, service
        coupon2_user = CashCoupon(
            face_value=Decimal('25'),
            balance=Decimal('5'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon2_user.save(force_insert=True)

        # 有效，只适用于service2
        coupon3_user = CashCoupon(
            face_value=Decimal('33'),
            balance=Decimal('23'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service2.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon3_user.save(force_insert=True)

        # 过期, service
        coupon4_vo = CashCoupon(
            face_value=Decimal('400'),
            balance=Decimal('20'),
            effective_time=now_time - timedelta(days=10),
            expiration_time=now_time - timedelta(days=1),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon4_vo.save(force_insert=True)

        payment1 = PaymentHistory(
            payment_account='',
            payment_method=PaymentHistory.PaymentMethod.BALANCE_COUPON.value,
            executor='executor',
            payer_id=user.id,
            payer_name=user.username,
            payer_type=OwnerType.USER.value,
            payable_amounts=Decimal('100.00'),
            amounts=Decimal('-60.00'),
            coupon_amount=Decimal('-40.00'),
            status=PaymentHistory.Status.SUCCESS.value,
            status_desc='支付成功',
            remark='remark',
            order_id='order_id',
            app_service_id='',
            instance_id='',
            app_id=self.app.id,
            subject='subject',
            creation_time=timezone.now(),
            payment_time=timezone.now()
        )
        payment1.save(force_insert=True)

        ccph1 = CashCouponPaymentHistory(
                payment_history_id=payment1.id,
                refund_history_id=None,
                cash_coupon_id=coupon1_user.id,
                amounts=Decimal('-25'),
                before_payment=Decimal('60.00'),
                after_payment=Decimal('35.00')
            )
        ccph1.save(force_insert=True)
        ccph2 = CashCouponPaymentHistory(
            payment_history_id=payment1.id,
            refund_history_id=None,
            cash_coupon_id=coupon2_user.id,
            amounts=Decimal('-15'),
            before_payment=Decimal('25.00'),
            after_payment=Decimal('10.00')
        )
        ccph2.save(force_insert=True)

        self.assertEqual(CashCouponPaymentHistory.objects.count(), 2)
        self.assertEqual(RefundRecord.objects.count(), 0)
        self.assertEqual(TransactionBill.objects.count(), 0)
        refund1 = PaymentManager().refund_for_payment(
            app_id=self.app.id, payment_history=payment1, out_refund_id='out_refund_id1', refund_reason='test',
            refund_amounts=Decimal('60.00'), remark='test remark', is_refund_coupon=True
        )
        self.assertEqual(CashCouponPaymentHistory.objects.count(), 2 + 2)
        self.assertEqual(RefundRecord.objects.count(), 1)
        self.assertEqual(TransactionBill.objects.count(), 1)

        user_account.refresh_from_db()
        self.assertEqual(user_account.balance, Decimal(60/100 * 60))
        refund1.refresh_from_db()
        self.assertEqual(refund1.total_amounts, Decimal('100.00'))
        self.assertEqual(refund1.refund_amounts, Decimal('60.00'))
        self.assertEqual(refund1.real_refund, quantize_10_2(Decimal(60/100 * 60)))
        self.assertEqual(refund1.coupon_refund, quantize_10_2(Decimal(40/100 * 60)))
        qs = CashCouponPaymentHistory.objects.filter(refund_history_id=refund1.id).order_by('-amounts')
        refund1_ccph1, refund1_ccph2 = list(qs)
        self.assertEqual(refund1_ccph1.amounts, quantize_10_2(refund1.coupon_refund * Decimal.from_float(25 / 40)))
        self.assertEqual(refund1_ccph1.payment_history_id, payment1.id)
        self.assertEqual(refund1_ccph1.before_payment, Decimal('20'))
        self.assertEqual(refund1_ccph1.after_payment, Decimal('20') + refund1_ccph1.amounts)
        self.assertEqual(refund1_ccph2.amounts, quantize_10_2(refund1.coupon_refund * Decimal.from_float(15 / 40)))
        self.assertEqual(refund1_ccph2.payment_history_id, payment1.id)

        coupon1_user.refresh_from_db()
        self.assertEqual(coupon1_user.balance, refund1_ccph1.amounts + Decimal('20'))
        coupon2_user.refresh_from_db()
        self.assertEqual(coupon2_user.balance, refund1_ccph2.amounts + Decimal('5'))

        tbill1 = TransactionBill.objects.order_by('-creation_time').first()
        self.assertEqual(tbill1.trade_amounts, Decimal('60.00'))
        self.assertEqual(tbill1.amounts, refund1.real_refund)
        self.assertEqual(tbill1.coupon_amount, refund1.coupon_refund)

        refund2 = PaymentManager().refund_for_payment(
            app_id=self.app.id, payment_history=payment1, out_refund_id='out_refund_id2', refund_reason='test2',
            refund_amounts=Decimal('20.00'), remark='test remark2', is_refund_coupon=True
        )
        self.assertEqual(CashCouponPaymentHistory.objects.count(), 2 + 4)
        self.assertEqual(RefundRecord.objects.count(), 2)
        self.assertEqual(TransactionBill.objects.count(), 2)

        user_account.refresh_from_db()
        self.assertEqual(user_account.balance, Decimal(60 / 100 * 60) + Decimal(60 / 100 * 20))
        refund2.refresh_from_db()
        self.assertEqual(refund2.total_amounts, Decimal('100.00'))
        self.assertEqual(refund2.refund_amounts, Decimal('20.00'))
        self.assertEqual(refund2.real_refund, quantize_10_2(Decimal(60 / 100 * 20)))
        self.assertEqual(refund2.coupon_refund, quantize_10_2(Decimal(40 / 100 * 20)))

        qs = CashCouponPaymentHistory.objects.filter(refund_history_id=refund2.id).order_by('-amounts')
        refund2_ccph1, refund2_ccph2 = list(qs)
        self.assertEqual(refund2_ccph1.amounts, quantize_10_2(refund2.coupon_refund * Decimal.from_float(25 / 40)))
        self.assertEqual(refund2_ccph2.amounts, quantize_10_2(refund2.coupon_refund * Decimal.from_float(15 / 40)))
        self.assertEqual(refund2_ccph1.payment_history_id, payment1.id)
        self.assertEqual(refund2_ccph2.payment_history_id, payment1.id)

        coupon1_user.refresh_from_db()
        self.assertEqual(coupon1_user.balance, refund1_ccph1.amounts + refund2_ccph1.amounts + Decimal('20'))
        coupon2_user.refresh_from_db()
        self.assertEqual(coupon2_user.balance, refund1_ccph2.amounts + refund2_ccph2.amounts + Decimal('5'))

        tbill2 = TransactionBill.objects.order_by('-creation_time').first()
        self.assertEqual(tbill2.trade_amounts, Decimal('20.00'))
        self.assertEqual(tbill2.amounts, refund2.real_refund)
        self.assertEqual(tbill2.coupon_amount, refund2.coupon_refund)

        with self.assertRaises(errors.RefundAmountsExceedTotal):
            PaymentManager().refund_for_payment(
                app_id=self.app.id, payment_history=payment1, out_refund_id='out_refund_id3', refund_reason='test3',
                refund_amounts=Decimal('20.01'), remark='test remark3', is_refund_coupon=True
            )

        # -- vo --
        vo_account = PaymentManager.get_vo_point_account(vo_id=self.vo.id)
        payment2 = PaymentHistory(
            payment_account='',
            payment_method=PaymentHistory.PaymentMethod.BALANCE_COUPON.value,
            executor='executor',
            payer_id=self.vo.id,
            payer_name=self.vo.name,
            payer_type=OwnerType.VO.value,
            payable_amounts=Decimal('200.00'),
            amounts=Decimal('0.00'),
            coupon_amount=Decimal('-200.00'),
            status=PaymentHistory.Status.SUCCESS.value,
            status_desc='支付成功',
            remark='remark vo',
            order_id='order_id1',
            app_service_id='',
            instance_id='',
            app_id=self.app.id,
            subject='subject2',
            creation_time=timezone.now(),
            payment_time=timezone.now()
        )
        payment2.save(force_insert=True)

        ccph3 = CashCouponPaymentHistory(
            payment_history_id=payment2.id,
            refund_history_id=None,
            cash_coupon_id=coupon4_vo.id,
            amounts=Decimal('-200'),
            before_payment=Decimal('220.00'),
            after_payment=Decimal('20.00')
        )
        ccph3.save(force_insert=True)

        self.assertEqual(CashCouponPaymentHistory.objects.count(), 7)
        self.assertEqual(RefundRecord.objects.count(), 2)
        self.assertEqual(TransactionBill.objects.count(), 2)
        refund3 = PaymentManager().refund_for_payment(
            app_id=self.app.id, payment_history=payment2, out_refund_id='out_refund_id3', refund_reason='test',
            refund_amounts=Decimal('200.00'), remark='test remark', is_refund_coupon=True
        )
        self.assertEqual(CashCouponPaymentHistory.objects.count(), 7 + 1)
        self.assertEqual(RefundRecord.objects.count(), 3)
        self.assertEqual(TransactionBill.objects.count(), 3)

        vo_account.refresh_from_db()
        self.assertEqual(vo_account.balance, Decimal('0'))
        refund3.refresh_from_db()
        self.assertEqual(refund3.total_amounts, Decimal('200.00'))
        self.assertEqual(refund3.refund_amounts, Decimal('200.00'))
        self.assertEqual(refund3.real_refund, Decimal('0.00'))
        self.assertEqual(refund3.coupon_refund, Decimal('200'))
        qs = CashCouponPaymentHistory.objects.filter(refund_history_id=refund3.id).order_by('-amounts')
        refund3_ccph1: CashCouponPaymentHistory = list(qs)[0]
        self.assertEqual(refund3_ccph1.amounts, Decimal('200'))
        self.assertEqual(refund3_ccph1.payment_history_id, payment2.id)
        self.assertEqual(refund3_ccph1.before_payment, Decimal('20'))
        self.assertEqual(refund3_ccph1.after_payment, Decimal('220'))

        coupon4_vo.refresh_from_db()
        self.assertEqual(coupon4_vo.balance, refund3_ccph1.amounts + Decimal('20'))

        tbill3 = TransactionBill.objects.order_by('-creation_time').first()
        self.assertEqual(tbill3.trade_amounts, Decimal('200.00'))
        self.assertEqual(tbill3.amounts, refund3.real_refund)
        self.assertEqual(tbill3.coupon_amount, refund3.coupon_refund)


class CashCouponActivityTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()

        # 余额支付有关配置
        app = PayApp(name='app')
        app.save()
        po = get_or_create_organization(name='机构')
        po.save()
        self.app_service1 = PayAppService(
            name='service1', app=app, orgnazition=po, service_id=self.service.id
        )
        self.app_service1.save()
        self.service.pay_app_service_id = self.app_service1.id
        self.service.save(update_fields=['pay_app_service_id'])

    def test_create_coupons_for_template(self):
        now_time = timezone.now()
        activity = CashCouponActivity(
            face_value=Decimal('668'),
            effective_time=now_time,
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.app_service1.id,
            grant_total=10,
            granted_count=0
        )
        activity.save(force_insert=True)
        ccam = CashCouponActivityManager()
        with self.assertRaises(errors.NotFound):
            ccam.create_coupons_for_template(activity_id='sss', user=self.user, max_count=2)

        with self.assertRaises(errors.AccessDenied):
            ccam.create_coupons_for_template(activity_id=activity.id, user=self.user, max_count=2)

        # app_serive跟service的管理员权限无关
        self.service.users.add(self.user)
        with self.assertRaises(errors.AccessDenied):
            ccam.create_coupons_for_template(activity_id=activity.id, user=self.user, max_count=2)

        self.app_service1.users.add(self.user)
        ay, c, err = ccam.create_coupons_for_template(activity_id=activity.id, user=self.user, max_count=2)
        self.assertEqual(c, 2)
        count = CashCoupon.objects.filter(activity_id=activity.id).count()
        self.assertEqual(count, 2)
        self.assertEqual(ay.granted_count, 2)
        self.assertEqual(ay.grant_status, CashCouponActivity.GrantStatus.GRANT.value)

        self.app_service1.users.remove(self.user)
        with self.assertRaises(errors.AccessDenied):
            ccam.create_coupons_for_template(activity_id=activity.id, user=self.user, max_count=2)

        self.app_service1.users.add(self.user)
        ay, c, err = ccam.create_coupons_for_template(activity_id=activity.id, user=self.user, max_count=2)
        self.assertEqual(c, 2)
        self.assertEqual(ay.granted_count, 4)
        self.assertEqual(ay.grant_status, CashCouponActivity.GrantStatus.GRANT.value)

        ay, c, err = ccam.create_coupons_for_template(activity_id=activity.id, user=self.user, max_count=10)
        self.assertEqual(c, 6)
        self.assertEqual(ay.granted_count, 10)
        self.assertEqual(ay.grant_status, CashCouponActivity.GrantStatus.COMPLETED.value)
        count = CashCoupon.objects.filter(activity_id=activity.id).count()
        self.assertEqual(count, 10)

        coupon = CashCoupon.objects.filter(activity_id=activity.id).first()
        self.assertEqual(coupon.face_value, activity.face_value)
        self.assertEqual(coupon.balance, activity.face_value)
        self.assertEqual(coupon.effective_time, activity.effective_time)
        self.assertEqual(coupon.expiration_time, activity.expiration_time)
