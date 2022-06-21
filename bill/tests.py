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
from bill.models import CashCoupon
from service.models import ServiceConfig
from .models import PaymentHistory
from .managers import PaymentManager


class PaymentManagerTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()
        self.vo = VoManager().create_vo(user=self.user, name='test vo', company='test', description='test')
        self.service2 = ServiceConfig(
            name='test2', data_center_id=self.service.data_center_id, endpoint_url='test2', username='', password='',
            need_vpn=False
        )

    def test_pay_user_bill(self):
        pay_mgr = PaymentManager()
        payer_name = self.user.username

        # pay bill, invalid user id
        metering_bill_postpaid1 = MeteringServer(
            service_id=self.service.id,
            server_id='server_id2',
            date=timezone.now().date(),
            owner_type=OwnerType.USER.value,
            user_id='user_id',
            vo_id='',
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('123.45'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )
        metering_bill_postpaid1.save(force_insert=True)
        with self.assertRaises(errors.Error):
            pay_mgr.pay_metering_bill(
                metering_bill=metering_bill_postpaid1, app_id='app_id', subject='云服务器计费',
                executor=self.user.username, remark='')

        # pay bill, pay_type POSTPAID, when no enough balance
        metering_bill_postpaid1.user_id = self.user.id
        metering_bill_postpaid1.save(update_fields=['user_id'])
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_metering_bill(
                metering_bill=metering_bill_postpaid1, app_id='app_id', subject='云服务器计费',
                executor=self.user.username, remark='', required_enough_balance=True
            )

        # pay bill, pay_type POSTPAID
        pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_postpaid1, app_id='app_id', subject='云服务器计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        self.user.userpointaccount.refresh_from_db()
        user_balance = self.user.userpointaccount.balance
        self.assertEqual(user_balance, Decimal('-123.45'))
        metering_bill_postpaid1.refresh_from_db()
        self.assertEqual(metering_bill_postpaid1.original_amount, Decimal('123.45'))
        self.assertEqual(metering_bill_postpaid1.trade_amount, Decimal('123.45'))
        self.assertEqual(metering_bill_postpaid1.payment_status, PaymentStatus.PAID.value)
        pay_history_id = metering_bill_postpaid1.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history.amounts, Decimal('-123.45'))
        self.assertEqual(pay_history.coupon_amount, Decimal('0'))
        self.assertEqual(pay_history.before_payment, Decimal(0))
        self.assertEqual(pay_history.after_payment, Decimal('-123.45'))
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.resource_type, ResourceType.VM.value)
        self.assertEqual(pay_history.service_id, self.service.id)
        self.assertEqual(pay_history.instance_id, 'server_id2')
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
            payment_history_id=''
        )
        metering_bill_prepaid.save(force_insert=True)
        pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_prepaid, app_id='app_id', subject='云服务器计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        metering_bill_prepaid.refresh_from_db()
        self.user.userpointaccount.refresh_from_db()
        self.assertEqual(self.user.userpointaccount.balance, user_balance)
        self.assertEqual(metering_bill_prepaid.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_prepaid.original_amount, Decimal('223.45'))
        self.assertEqual(metering_bill_prepaid.trade_amount, Decimal(0))
        self.assertEqual(metering_bill_prepaid.payment_history_id, '')

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
            payment_history_id=''
        )
        metering_bill_postpaid2.save(force_insert=True)
        pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_postpaid2, app_id='app_id', subject='云服务器计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        self.user.userpointaccount.refresh_from_db()
        user_balance = self.user.userpointaccount.balance
        self.assertEqual(user_balance, Decimal('-123.45') - Decimal('66.88'))
        metering_bill_postpaid2.refresh_from_db()
        self.assertEqual(metering_bill_postpaid2.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_postpaid2.original_amount, Decimal('66.88'))
        self.assertEqual(metering_bill_postpaid2.trade_amount, Decimal('66.88'))

        pay_history_id = metering_bill_postpaid2.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.amounts, Decimal('-66.88'))
        self.assertEqual(pay_history.coupon_amount, Decimal('0'))
        self.assertEqual(pay_history.before_payment, Decimal('-123.45'))
        self.assertEqual(pay_history.after_payment, Decimal('-190.33'))
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

        # ------- test coupon --------
        now_time = timezone.now()
        # 有效, service
        coupon1_user = CashCoupon(
            face_value=Decimal('20'),
            balance=Decimal('20'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            service_id=self.service.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon1_user.save(force_insert=True)

        # 有效，只适用于service2
        coupon2_user = CashCoupon(
            face_value=Decimal('33'),
            balance=Decimal('33'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            service_id=self.service2.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon2_user.save(force_insert=True)

        # 有效, service
        coupon3_vo = CashCoupon(
            face_value=Decimal('50'),
            balance=Decimal('50'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            service_id=self.service.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon3_vo.save(force_insert=True)

        # pay bill, pay_type POSTPAID
        metering_bill_postpaid3 = MeteringServer(
            service_id=self.service.id,
            server_id='server3_id',
            date=(timezone.now() - timedelta(days=2)),
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id='',
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('88.8'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )
        metering_bill_postpaid3.save(force_insert=True)

        self.user.userpointaccount.refresh_from_db()
        user_balance = self.user.userpointaccount.balance
        self.assertEqual(user_balance, Decimal('-190.33'))
        pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_postpaid3, app_id='app_id', subject='云服务器计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        self.user.userpointaccount.refresh_from_db()
        user_balance = self.user.userpointaccount.balance
        self.assertEqual(user_balance, Decimal('-190.33') - Decimal('88.8') + Decimal('20'))  # coupon 20
        metering_bill_postpaid3.refresh_from_db()
        self.assertEqual(metering_bill_postpaid3.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_postpaid3.original_amount, Decimal('88.8'))
        self.assertEqual(metering_bill_postpaid3.trade_amount, Decimal('88.8'))

        pay_history_id = metering_bill_postpaid3.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.amounts, Decimal('-68.8'))
        self.assertEqual(pay_history.coupon_amount, Decimal('-20'))
        self.assertEqual(pay_history.before_payment, Decimal('-190.33'))
        self.assertEqual(pay_history.after_payment, Decimal('-259.13'))
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user.id)
        self.assertEqual(pay_history.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE_COUPON.value)
        self.assertEqual(pay_history.payment_account, self.user.userpointaccount.id)
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.resource_type, ResourceType.VM.value)
        self.assertEqual(pay_history.service_id, self.service.id)
        self.assertEqual(pay_history.instance_id, 'server3_id')

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
            payment_history_id=''
        )
        metering_bill_postpaid1.save(force_insert=True)
        with self.assertRaises(errors.Error):
            pay_mgr.pay_metering_bill(
                metering_bill=metering_bill_postpaid1, app_id='app_id', subject='云服务器计费',
                executor=self.user.username, remark=''
            )

        # pay bill, pay_type POSTPAID, when not enough balance
        metering_bill_postpaid1.vo_id = self.vo.id
        metering_bill_postpaid1.save(update_fields=['vo_id'])
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_metering_bill(
                metering_bill=metering_bill_postpaid1, app_id='app_id', subject='云服务器计费',
                executor=self.user.username, remark='', required_enough_balance=True
            )

        # pay bill, pay_type POSTPAID
        pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_postpaid1, app_id='app_id', subject='云服务器计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )

        user_balance = pay_mgr.get_vo_point_account(vo_id=self.vo.id).balance
        self.assertEqual(user_balance, Decimal('-123.45'))
        metering_bill_postpaid1.refresh_from_db()
        self.assertEqual(metering_bill_postpaid1.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_postpaid1.original_amount, Decimal('123.45'))
        self.assertEqual(metering_bill_postpaid1.trade_amount, Decimal('123.45'))
        pay_history_id = metering_bill_postpaid1.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
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
            payment_history_id=''
        )
        metering_bill_prepaid.save(force_insert=True)
        pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_prepaid, app_id='app_id', subject='云服务器计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        metering_bill_prepaid.refresh_from_db()
        self.assertEqual(metering_bill_prepaid.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_prepaid.original_amount, Decimal('223.45'))
        self.assertEqual(metering_bill_prepaid.trade_amount, Decimal(0))
        self.assertEqual(metering_bill_prepaid.payment_history_id, '')
        self.vo.vopointaccount.refresh_from_db()
        self.assertEqual(self.vo.vopointaccount.balance, Decimal('-123.45'))

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
            payment_history_id=''
        )
        metering_bill_postpaid2.save(force_insert=True)
        pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_postpaid2, app_id='app_id', subject='云服务器计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        self.vo.vopointaccount.refresh_from_db()
        self.assertEqual(self.vo.vopointaccount.balance, Decimal('-123.45') - Decimal('66.88'))
        metering_bill_postpaid2.refresh_from_db()
        self.assertEqual(metering_bill_postpaid2.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_postpaid2.original_amount, Decimal('66.88'))
        self.assertEqual(metering_bill_postpaid2.trade_amount, Decimal('66.88'))
        pay_history_id = metering_bill_postpaid2.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
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
            payment_history_id=''
        )
        metering_bill_paid.save(force_insert=True)
        with self.assertRaises(errors.Error):
            pay_mgr.pay_metering_bill(
                metering_bill=metering_bill_paid, app_id='app_id', subject='云服务器计费',
                executor=self.user.username, remark=''
            )

        metering_bill_paid.payment_status = PaymentStatus.CANCELLED.value
        metering_bill_paid.save(update_fields=['payment_status'])
        with self.assertRaises(errors.Error):
            pay_mgr.pay_metering_bill(
                metering_bill=metering_bill_paid, app_id='app_id', subject='云服务器计费',
                executor=self.user.username, remark=''
            )

        # ------- test coupon --------
        now_time = timezone.now()
        # 有效, service
        coupon1_vo = CashCoupon(
            face_value=Decimal('20'),
            balance=Decimal('20'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            service_id=self.service.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon1_vo.save(force_insert=True)

        # 有效，service2
        coupon2_vo = CashCoupon(
            face_value=Decimal('33'),
            balance=Decimal('33'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            service_id=self.service2.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon2_vo.save(force_insert=True)

        # 有效, service
        coupon3_user = CashCoupon(
            face_value=Decimal('50'),
            balance=Decimal('50'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            service_id=self.service.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon3_user.save(force_insert=True)

        # pay bill, pay_type POSTPAID
        metering_bill_postpaid3 = MeteringServer(
            service_id=self.service.id,
            server_id='server3_id',
            date=(timezone.now() - timedelta(days=2)),
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id=self.vo.id,
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('88.8'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )
        metering_bill_postpaid3.save(force_insert=True)

        self.vo.vopointaccount.refresh_from_db()
        vo_balance = self.vo.vopointaccount.balance
        self.assertEqual(vo_balance, Decimal('-123.45') - Decimal('66.88'))
        pay_mgr.pay_metering_bill(
            metering_bill=metering_bill_postpaid3, app_id='app_id', subject='云服务器计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        self.vo.vopointaccount.refresh_from_db()
        vo_balance = self.vo.vopointaccount.balance
        self.assertEqual(vo_balance, Decimal('-190.33') - Decimal('88.8') + Decimal('20'))  # coupon 20
        metering_bill_postpaid3.refresh_from_db()
        self.assertEqual(metering_bill_postpaid3.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(metering_bill_postpaid3.original_amount, Decimal('88.8'))
        self.assertEqual(metering_bill_postpaid3.trade_amount, Decimal('88.8'))

        pay_history_id = metering_bill_postpaid3.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.amounts, Decimal('-68.8'))
        self.assertEqual(pay_history.coupon_amount, Decimal('-20'))
        self.assertEqual(pay_history.before_payment, Decimal('-190.33'))
        self.assertEqual(pay_history.after_payment, Decimal('-259.13'))
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history.payer_id, self.vo.id)
        self.assertEqual(pay_history.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE_COUPON.value)
        self.assertEqual(pay_history.payment_account, self.vo.vopointaccount.id)
        self.assertEqual(pay_history.payer_name, self.vo.name)
        self.assertEqual(pay_history.resource_type, ResourceType.VM.value)
        self.assertEqual(pay_history.service_id, self.service.id)
        self.assertEqual(pay_history.instance_id, 'server3_id')

    def test_pay_order_no_coupon(self):
        pay_mgr = PaymentManager()
        order1 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UNPAID.value,
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
            pay_mgr.pay_order(
                order=order1, app_id='app_id', subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=None, only_coupon=False,
                required_enough_balance=True
            )

        pay_mgr.get_user_point_account(user_id=self.user.id)
        self.assertEqual(self.user.userpointaccount.balance, Decimal(0))
        order1 = pay_mgr.pay_order(
            order=order1, app_id='app_id', subject='云服务器计费',
            executor=self.user.username, remark='',
            coupon_ids=None, only_coupon=False,
            required_enough_balance=False
        )
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
            status=Order.Status.UNPAID.value,
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
            pay_mgr.pay_order(
                order=order2, app_id='app_id', subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=None, only_coupon=False,
                required_enough_balance=True
            )

        pay_mgr.get_vo_point_account(vo_id=self.vo.id)
        self.assertEqual(self.vo.vopointaccount.balance, Decimal(0))
        order2 = pay_mgr.pay_order(
            order=order2, app_id='app_id', subject='云服务器计费',
            executor=self.user.username, remark='',
            coupon_ids=None, only_coupon=False,
            required_enough_balance=False
        )
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

    def test_user_pay_order_with_coupon(self):
        pay_mgr = PaymentManager()
        account = pay_mgr.get_user_point_account(self.user.id)
        account.balance = Decimal('200')
        account.save(update_fields=['balance'])
        order1 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UNPAID.value,
            total_amount=Decimal('100'),
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

        order2 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UNPAID.value,
            total_amount=Decimal('288.88'),
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
            service_id=self.service.id,
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
            service_id=self.service.id,
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
            service_id=self.service2.id,
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
            service_id=self.service.id,
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
            service_id=self.service.id,
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
            service_id=self.service.id,
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
            service_id=self.service.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon7_user.save(force_insert=True)

        # 指定不存在的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id='app_id', subject='云服务器计费',
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
                order=order1, app_id='app_id', subject='云服务器计费',
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
                order=order1, app_id='app_id', subject='云服务器计费',
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
                order=order1, app_id='app_id', subject='云服务器计费',
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
                order=order1, app_id='app_id', subject='云服务器计费',
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
                order=order1, app_id='app_id', subject='云服务器计费',
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
                order=order1, app_id='app_id', subject='云服务器计费',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_user.id, coupon2_user.id
                ], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponBalanceNotEnough')

        # 指定券+账户余额支付，券余额45（20 + 25），订单金额 100
        pay_mgr.pay_order(
            order=order1, app_id='app_id', subject='云服务器计费',
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
        self.assertEqual(order1.payment_method, Order.PaymentMethod.BALANCE.value)
        self.assertEqual(order1.pay_amount, Decimal('100'))
        self.assertIsInstance(order1.payment_time, datetime)

        # 支付记录确认
        pay_history1 = PaymentHistory.objects.filter(order_id=order1.id).first()
        self.assertEqual(pay_history1.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history1.amounts, Decimal('-55'))
        self.assertEqual(pay_history1.coupon_amount, Decimal('-45'))
        self.assertEqual(pay_history1.before_payment, Decimal('200'))
        self.assertEqual(pay_history1.after_payment, Decimal('145'))
        self.assertEqual(pay_history1.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history1.payer_id, self.user.id)
        self.assertEqual(pay_history1.payer_name, self.user.username)
        self.assertEqual(pay_history1.executor, self.user.username)
        self.assertEqual(pay_history1.payment_method, PaymentHistory.PaymentMethod.BALANCE_COUPON.value)
        self.assertEqual(pay_history1.payment_account, user_account.id)
        self.assertEqual(pay_history1.resource_type, ResourceType.VM.value)
        self.assertEqual(pay_history1.service_id, self.service.id)
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

        # 支付已支付状态的订单
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id='app_id', subject='云服务器',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'OrderPaid')

        # --------- pay order2 test ----------
        # 不指定券，只用券支付
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order2, app_id='app_id', subject='云服务器',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponBalanceNotEnough')

        # 余额不足
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order2, app_id='app_id', subject='云服务器',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'BalanceNotEnough')

        # 订单金额 288.88
        pay_mgr.pay_order(
            order=order2, app_id='app_id', subject='云服务器',
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

        # 支付记录确认
        pay_history2 = PaymentHistory.objects.filter(order_id=order2.id).first()
        self.assertEqual(pay_history2.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history2.amounts, Decimal('-288.88'))
        self.assertEqual(pay_history2.coupon_amount, Decimal('0'))
        self.assertEqual(pay_history2.before_payment, Decimal('145'))
        self.assertEqual(pay_history2.after_payment, Decimal('-143.88'))
        self.assertEqual(pay_history2.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history2.payer_id, self.user.id)
        self.assertEqual(pay_history2.payer_name, self.user.username)
        self.assertEqual(pay_history2.executor, self.user.username)
        self.assertEqual(pay_history2.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history2.payment_account, user_account.id)
        self.assertEqual(pay_history2.resource_type, ResourceType.VM.value)
        self.assertEqual(pay_history2.service_id, self.service.id)
        self.assertEqual(pay_history2.instance_id, '')
        # 券支付记录
        cc_historys = pay_history2.cashcouponpaymenthistory_set.all().order_by('creation_time')
        self.assertEqual(len(cc_historys), 0)

    def test_vo_pay_order_with_coupon(self):
        pay_mgr = PaymentManager()
        account = pay_mgr.get_vo_point_account(self.vo.id)
        account.balance = Decimal('200')
        account.save(update_fields=['balance'])
        order1 = Order(
            order_type=Order.OrderType.NEW,
            status=Order.Status.UNPAID.value,
            total_amount=Decimal('100'),
            service_id=self.service.id,
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
            service_id=self.service.id,
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
            service_id=self.service.id,
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
            service_id=self.service.id,
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
            service_id=self.service2.id,
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
            service_id=self.service.id,
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
            service_id=self.service.id,
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
            service_id=self.service.id,
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
            service_id=self.service.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon7_user.save(force_insert=True)

        # 指定不存在的券
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id='app_id', subject='云服务器',
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
                order=order1, app_id='app_id', subject='云服务器',
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
                order=order1, app_id='app_id', subject='资源订单',
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
                order=order1, app_id='app_id', subject='资源订单',
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
                order=order1, app_id='app_id', subject='资源订单',
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
                order=order1, app_id='app_id', subject='资源订单',
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
                order=order1, app_id='app_id', subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[
                    coupon1_vo.id, coupon2_vo.id
                ], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponBalanceNotEnough')

        # 指定券+账户余额支付，券余额45（20 + 25），订单金额 100
        pay_mgr.pay_order(
            order=order1, app_id='app_id', subject='资源订单',
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
        self.assertEqual(order1.payment_method, Order.PaymentMethod.BALANCE.value)
        self.assertEqual(order1.pay_amount, Decimal('100'))
        self.assertIsInstance(order1.payment_time, datetime)

        # 支付记录确认
        pay_history1 = PaymentHistory.objects.filter(order_id=order1.id).first()
        self.assertEqual(pay_history1.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history1.amounts, Decimal('-55'))
        self.assertEqual(pay_history1.coupon_amount, Decimal('-45'))
        self.assertEqual(pay_history1.before_payment, Decimal('200'))
        self.assertEqual(pay_history1.after_payment, Decimal('145'))
        self.assertEqual(pay_history1.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history1.payer_id, self.vo.id)
        self.assertEqual(pay_history1.payer_name, self.vo.name)
        self.assertEqual(pay_history1.executor, self.user.username)
        self.assertEqual(pay_history1.payment_method, PaymentHistory.PaymentMethod.BALANCE_COUPON.value)
        self.assertEqual(pay_history1.payment_account, vo_account.id)
        self.assertEqual(pay_history1.resource_type, ResourceType.VM.value)
        self.assertEqual(pay_history1.service_id, self.service.id)
        self.assertEqual(pay_history1.instance_id, '')
        self.assertEqual(pay_history1.app_id, 'app_id')
        self.assertEqual(pay_history1.subject, '资源订单')
        # 券支付记录
        cc_historys = pay_history1.cashcouponpaymenthistory_set.all().order_by('creation_time')
        self.assertEqual(cc_historys[0].payment_history_id, pay_history1.id)
        self.assertEqual(cc_historys[0].cash_coupon_id, coupon1_vo.id)
        self.assertEqual(cc_historys[0].before_payment, Decimal('20'))
        self.assertEqual(cc_historys[0].amounts, Decimal('-20'))
        self.assertEqual(cc_historys[0].after_payment, Decimal('0'))
        self.assertEqual(cc_historys[1].payment_history_id, pay_history1.id)
        self.assertEqual(cc_historys[1].cash_coupon_id, coupon2_vo.id)
        self.assertEqual(cc_historys[1].before_payment, Decimal('25'))
        self.assertEqual(cc_historys[1].amounts, Decimal('-25'))
        self.assertEqual(cc_historys[1].after_payment, Decimal('0'))

        # 支付已支付状态的订单
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order1, app_id='app_id', subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'OrderPaid')

        # --------- pay order2 test ----------
        # 不指定券，只用券支付
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order2, app_id='app_id', subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=True,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'CouponBalanceNotEnough')

        # 余额不足
        with self.assertRaises(errors.Error) as cm:
            pay_mgr.pay_order(
                order=order2, app_id='app_id', subject='资源订单',
                executor=self.user.username, remark='',
                coupon_ids=[], only_coupon=False,
                required_enough_balance=True
            )
        self.assertEqual(cm.exception.code, 'BalanceNotEnough')

        # 订单金额 288.88
        pay_mgr.pay_order(
            order=order2, app_id='app_id', subject='资源订单',
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

        # 支付记录确认
        pay_history2 = PaymentHistory.objects.filter(order_id=order2.id).first()
        self.assertEqual(pay_history2.type, PaymentHistory.Type.PAYMENT)
        self.assertEqual(pay_history2.amounts, Decimal('-288.88'))
        self.assertEqual(pay_history2.coupon_amount, Decimal('0'))
        self.assertEqual(pay_history2.before_payment, Decimal('145'))
        self.assertEqual(pay_history2.after_payment, Decimal('-143.88'))
        self.assertEqual(pay_history2.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history2.payer_id, self.vo.id)
        self.assertEqual(pay_history2.payer_name, self.vo.name)
        self.assertEqual(pay_history2.executor, self.user.username)
        self.assertEqual(pay_history2.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history2.payment_account, vo_account.id)
        self.assertEqual(pay_history2.resource_type, ResourceType.VM.value)
        self.assertEqual(pay_history2.service_id, self.service.id)
        self.assertEqual(pay_history2.instance_id, '')
        self.assertEqual(pay_history2.app_id, 'app_id')
        self.assertEqual(pay_history2.subject, '资源订单')
        # 券支付记录
        cc_historys = pay_history2.cashcouponpaymenthistory_set.all().order_by('creation_time')
        self.assertEqual(len(cc_historys), 0)
