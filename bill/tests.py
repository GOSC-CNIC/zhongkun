from decimal import Decimal
from datetime import timedelta, datetime

from django.test import TransactionTestCase
from django.utils import timezone

from core import errors
from utils.test import get_or_create_user, get_or_create_service
from utils.model import OwnerType, PayType
from order.models import ResourceType, Order
from vo.managers import VoManager
from metering.models import MeteringServer, MeteringDisk, PaymentStatus
from .models import PaymentHistory
from .managers import PaymentManager


class PaymentManagerTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()
        self.vo = VoManager().create_vo(user=self.user, name='test vo', company='test', description='test')

    def test_pay_user_bill(self):
        pay_mgr = PaymentManager()
        payer_name = self.user.username

        # pay bill, invalid user id
        metering_bill_postpaid1 = MeteringServer(
            service_id=self.service.id,
            server_id='server_id',
            date=timezone.now().date(),
            owner_type=OwnerType.USER.value,
            user_id='user_id',
            vo_id='',
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('123.45'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=None
        )
        metering_bill_postpaid1.save(force_insert=True)
        with self.assertRaises(errors.Error):
            pay_mgr.pay_metering_bill(metering_bill=metering_bill_postpaid1, executor=self.user.username, remark='')

        # pay bill, pay_type POSTPAID, when no enough balance
        metering_bill_postpaid1.user_id = self.user.id
        metering_bill_postpaid1.save(update_fields=['user_id'])
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_metering_bill(
                metering_bill=metering_bill_postpaid1, executor=self.user.username, remark='',
                required_enough_balance=True
            )

        # pay bill, pay_type POSTPAID
        balance = pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_postpaid1, executor=self.user.username, remark='',
            required_enough_balance=False
        )
        self.assertEqual(balance, Decimal('-123.45'))
        user_balance = balance
        metering_bill_postpaid1.refresh_from_db()
        self.assertEqual(metering_bill_postpaid1.original_amount, Decimal('123.45'))
        self.assertEqual(metering_bill_postpaid1.trade_amount, Decimal('123.45'))
        self.assertEqual(metering_bill_postpaid1.payment_status, PaymentStatus.PAID.value)
        pay_history = metering_bill_postpaid1.payment_history
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history.amounts, Decimal('-123.45'))
        self.assertEqual(pay_history.before_payment, Decimal(0))
        self.assertEqual(pay_history.after_payment, Decimal('-123.45'))
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.resource_type, ResourceType.VM.value)
        self.assertEqual(pay_history.service_id, self.service.id)
        self.assertEqual(pay_history.instance_id, 'server_id')
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user.id)
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, self.user.userpointaccount.id)

        # pay bill, pay_type PREPAID
        metering_bill_prepaid = MeteringServer(
            service_id=self.service.id,
            server_id='server_id',
            date=(timezone.now() - timedelta(days=1)).date(),
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id='',
            pay_type=PayType.PREPAID.value,
            original_amount=Decimal('223.45'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=None
        )
        metering_bill_prepaid.save(force_insert=True)
        balance2 = pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_prepaid, executor=self.user.username, remark='',
            required_enough_balance=False
        )
        self.assertIs(balance2, None)
        metering_bill_prepaid.refresh_from_db()
        self.user.userpointaccount.refresh_from_db()
        self.assertEqual(self.user.userpointaccount.balance, user_balance)
        self.assertEqual(metering_bill_prepaid.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_prepaid.original_amount, Decimal('223.45'))
        self.assertEqual(metering_bill_prepaid.trade_amount, Decimal(0))
        self.assertIs(metering_bill_prepaid.payment_history, None)

        # pay bill, pay_type POSTPAID
        metering_bill_postpaid2 = MeteringServer(
            service_id=self.service.id,
            server_id='server2_id',
            date=(timezone.now() - timedelta(days=2)),
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id='',
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('66.88'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=None
        )
        metering_bill_postpaid2.save(force_insert=True)
        balance3 = pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_postpaid2, executor=self.user.username, remark='',
            required_enough_balance=False
        )
        self.assertEqual(balance3, user_balance - Decimal('66.88'))
        user_balance = balance3
        metering_bill_postpaid2.refresh_from_db()
        self.assertEqual(metering_bill_postpaid2.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_postpaid2.original_amount, Decimal('66.88'))
        self.assertEqual(metering_bill_postpaid2.trade_amount, Decimal('66.88'))
        self.user.userpointaccount.refresh_from_db()
        self.assertEqual(self.user.userpointaccount.balance, user_balance)

        pay_history = metering_bill_postpaid2.payment_history
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.amounts, Decimal('-66.88'))
        self.assertEqual(pay_history.before_payment, Decimal('-123.45'))
        self.assertEqual(pay_history.after_payment, Decimal('-123.45') - Decimal('66.88'))
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user.id)
        self.assertEqual(pay_history.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, self.user.userpointaccount.id)
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.resource_type, ResourceType.VM.value)
        self.assertEqual(pay_history.service_id, self.service.id)
        self.assertEqual(pay_history.instance_id, 'server2_id')

    def test_pay_vo_bill(self):
        pay_mgr = PaymentManager()
        payer_name = self.vo.name

        # pay bill, invalid vo id
        metering_bill_postpaid1 = MeteringDisk(
            service_id=self.service.id,
            disk_id='disk_id',
            date=timezone.now().date(),
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id='vo_id',
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('123.45'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=None
        )
        metering_bill_postpaid1.save(force_insert=True)
        with self.assertRaises(errors.Error):
            pay_mgr.pay_metering_bill(metering_bill=metering_bill_postpaid1, executor=self.user.username, remark='')

        # pay bill, pay_type POSTPAID, when not enough balance
        metering_bill_postpaid1.vo_id = self.vo.id
        metering_bill_postpaid1.save(update_fields=['vo_id'])
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_metering_bill(
                metering_bill=metering_bill_postpaid1, executor=self.user.username, remark='',
                required_enough_balance=True
            )

        # pay bill, pay_type POSTPAID
        balance = pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_postpaid1, executor=self.user.username, remark='',
            required_enough_balance=False
        )
        self.assertEqual(balance, Decimal('-123.45'))
        user_balance = balance
        metering_bill_postpaid1.refresh_from_db()
        self.assertEqual(metering_bill_postpaid1.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_postpaid1.original_amount, Decimal('123.45'))
        self.assertEqual(metering_bill_postpaid1.trade_amount, Decimal('123.45'))
        pay_history = metering_bill_postpaid1.payment_history
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history.payer_id, self.vo.id)
        self.assertEqual(pay_history.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history.amounts, Decimal('-123.45'))
        self.assertEqual(pay_history.before_payment, Decimal(0))
        self.assertEqual(pay_history.after_payment, Decimal('-123.45'))
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, self.vo.vopointaccount.id)
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.resource_type, ResourceType.DISK.value)
        self.assertEqual(pay_history.service_id, self.service.id)
        self.assertEqual(pay_history.instance_id, 'disk_id')

        # pay bill, pay_type PREPAID
        metering_bill_prepaid = MeteringDisk(
            service_id=self.service.id,
            disk_id='disk_id',
            date=(timezone.now() - timedelta(days=1)).date(),
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id=self.vo.id,
            pay_type=PayType.PREPAID.value,
            original_amount=Decimal('223.45'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=None
        )
        metering_bill_prepaid.save(force_insert=True)
        balance2 = pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_prepaid, executor=self.user.username, remark='',
            required_enough_balance=False
        )
        self.assertIs(balance2, None)
        metering_bill_prepaid.refresh_from_db()
        self.assertEqual(metering_bill_prepaid.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_prepaid.original_amount, Decimal('223.45'))
        self.assertEqual(metering_bill_prepaid.trade_amount, Decimal(0))
        self.assertIs(metering_bill_prepaid.payment_history, None)
        self.vo.vopointaccount.refresh_from_db()
        self.assertEqual(self.vo.vopointaccount.balance, user_balance)

        # pay bill, pay_type POSTPAID
        metering_bill_postpaid2 = MeteringDisk(
            service_id=self.service.id,
            disk_id='disk2_id',
            date=(timezone.now() - timedelta(days=2)),
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id=self.vo.id,
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('66.88'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=None
        )
        metering_bill_postpaid2.save(force_insert=True)
        balance3 = pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_postpaid2, executor=self.user.username, remark='',
            required_enough_balance=False
        )
        self.assertEqual(balance3, user_balance - Decimal('66.88'))
        user_balance = balance3
        self.vo.vopointaccount.refresh_from_db()
        self.assertEqual(self.vo.vopointaccount.balance, user_balance)
        metering_bill_postpaid2.refresh_from_db()
        self.assertEqual(metering_bill_postpaid2.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_postpaid2.original_amount, Decimal('66.88'))
        self.assertEqual(metering_bill_postpaid2.trade_amount, Decimal('66.88'))
        pay_history = metering_bill_postpaid2.payment_history
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history.payer_id, self.vo.id)
        self.assertEqual(pay_history.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history.amounts, Decimal('-66.88'))
        self.assertEqual(pay_history.before_payment, Decimal('-123.45'))
        self.assertEqual(pay_history.after_payment, Decimal('-123.45') - Decimal('66.88'))
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, self.vo.vopointaccount.id)
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.resource_type, ResourceType.DISK.value)
        self.assertEqual(pay_history.service_id, self.service.id)
        self.assertEqual(pay_history.instance_id, 'disk2_id')

        # pay bill, status PAID
        metering_bill_paid = MeteringDisk(
            service_id=self.service.id,
            disk_id='disk3_id',
            date=(timezone.now() - timedelta(days=3)),
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id=self.vo.id,
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('166.88'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.PAID.value,
            payment_history_id=None
        )
        metering_bill_paid.save(force_insert=True)
        with self.assertRaises(errors.Error):
            pay_mgr.pay_metering_bill(
                metering_bill=metering_bill_paid, executor=self.user.username, remark='')

        metering_bill_paid.payment_status = PaymentStatus.CANCELLED.value
        metering_bill_paid.save(update_fields=['payment_status'])
        with self.assertRaises(errors.Error):
            pay_mgr.pay_metering_bill(
                metering_bill=metering_bill_paid, executor=self.user.username, remark='')

    def test_pay_order(self):
        pay_mgr = PaymentManager()
        order1 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UPPAID.value,
            total_amount=Decimal('123.45'),
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

        # user order, no enough balance, when required enough balance
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_order(order=order1, executor=self.user.username, remark='', required_enough_balance=True)

        pay_mgr.get_user_point_account(user_id=self.user.id)
        self.assertEqual(self.user.userpointaccount.balance, Decimal(0))
        order1 = pay_mgr.pay_order(order=order1, executor=self.user.username, remark='', required_enough_balance=False)
        self.user.userpointaccount.refresh_from_db()
        self.assertEqual(self.user.userpointaccount.balance, Decimal('-123.45'))
        self.assertEqual(order1.status, Order.Status.PAID.value)
        self.assertEqual(order1.payment_method, Order.PaymentMethod.BALANCE.value)
        self.assertEqual(order1.pay_amount, Decimal('123.45'))
        self.assertIsInstance(order1.payment_time, datetime)
        pay_history = PaymentHistory.objects.filter(order_id=order1.id).first()
        self.assertEqual(pay_history.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history.amounts, Decimal('-123.45'))
        self.assertEqual(pay_history.before_payment, Decimal(0))
        self.assertEqual(pay_history.after_payment, Decimal('-123.45'))
        self.assertEqual(pay_history.payer_name, self.user.username)
        self.assertEqual(pay_history.resource_type, ResourceType.VM.value)
        self.assertEqual(pay_history.service_id, self.service.id)
        self.assertEqual(pay_history.instance_id, '')
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user.id)
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, self.user.userpointaccount.id)

        order2 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UPPAID.value,
            total_amount=Decimal('321.45'),
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
            pay_mgr.pay_order(order=order2, executor=self.user.username, remark='', required_enough_balance=True)

        pay_mgr.get_vo_point_account(vo_id=self.vo.id)
        self.assertEqual(self.vo.vopointaccount.balance, Decimal(0))
        order2 = pay_mgr.pay_order(order=order2, executor=self.user.username, remark='', required_enough_balance=False)
        self.vo.vopointaccount.refresh_from_db()
        self.assertEqual(self.vo.vopointaccount.balance, Decimal('-321.45'))
        self.assertEqual(order2.status, Order.Status.PAID.value)
        self.assertEqual(order2.payment_method, Order.PaymentMethod.BALANCE.value)
        self.assertEqual(order2.pay_amount, Decimal('321.45'))
        self.assertIsInstance(order2.payment_time, datetime)
        pay_history2 = PaymentHistory.objects.filter(order_id=order2.id).first()
        self.assertEqual(pay_history2.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history2.amounts, Decimal('-321.45'))
        self.assertEqual(pay_history2.before_payment, Decimal(0))
        self.assertEqual(pay_history2.after_payment, Decimal('-321.45'))
        self.assertEqual(pay_history2.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history2.payer_id, self.vo.id)
        self.assertEqual(pay_history2.payer_name, self.vo.name)
        self.assertEqual(pay_history2.executor, self.user.username)
        self.assertEqual(pay_history2.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history2.payment_account, self.vo.vopointaccount.id)
        self.assertEqual(pay_history2.resource_type, ResourceType.DISK.value)
        self.assertEqual(pay_history2.service_id, self.service.id)
        self.assertEqual(pay_history2.instance_id, '')
