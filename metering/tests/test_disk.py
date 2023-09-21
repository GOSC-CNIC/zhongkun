from decimal import Decimal
from datetime import date, datetime, timedelta, time

from django.test import TransactionTestCase
from django.utils import timezone

from utils.test import get_or_create_user, get_or_create_service
from utils.model import PayType, OwnerType
from utils.decimal_utils import quantize_10_2
from utils import rand_utils
from utils.time import utc
from core import errors
from servers.models import Disk, DiskChangeLog
from vo.managers import VoManager
from order.models import Price
from bill.models import CashCoupon, PaymentHistory, PayAppService, PayApp, PayOrgnazition
from service.models import ServiceConfig
from metering.measurers import DiskMeasurer
from metering.models import PaymentStatus, DailyStatementDisk, MeteringDisk
from metering.payment import MeteringPaymentManager
from metering.statement_generators import DiskDailyStatementGenerater
from users.models import UserProfile


def create_disk_metadata(
        service_id: str, azone_id: str, disk_size: int,
        pay_type: str, classification: str, user_id, vo_id,
        creation_time, expiration_time=None, remarks: str = '',
        server_id=None, disk_id: str = None, instance_id: str = None,
        lock: str = None, start_time=None, task_status: str = ''
):
    disk = Disk(
        id=disk_id,
        name='',
        instance_id=instance_id if instance_id else rand_utils.short_uuid1_25(),
        instance_name=rand_utils.short_uuid1_25(),
        size=disk_size,
        service_id=service_id,
        azone_id=azone_id,
        azone_name='azone_name',
        quota_type=Disk.QuotaType.PRIVATE.value,
        creation_time=creation_time,
        remarks=remarks,
        task_status=task_status if task_status else Disk.TaskStatus.CREATING.value,
        expiration_time=expiration_time,
        start_time=start_time if start_time else creation_time,
        pay_type=pay_type,
        classification=classification,
        user_id=user_id,
        vo_id=vo_id,
        lock=lock if lock else Disk.Lock.FREE.value,
        deleted=False,
        server_id=server_id,
        mountpoint='',
    )
    disk.save(force_insert=True)
    return disk


def create_metering_disk_metadata(
        service, disk_id, date_,
        original_amount: Decimal, trade_amount: Decimal, daily_statement_id='',
        owner_type=OwnerType.USER.value, user_id='', username='', vo_id='', vo_name='',
        pay_type=PayType.POSTPAID.value, size_hours=0
):
    metering = MeteringDisk(
        service=service,
        disk_id=disk_id,
        date=date_,
        owner_type=owner_type,
        user_id=user_id,
        username=username,
        vo_id=vo_id,
        vo_name=vo_name,
        original_amount=original_amount,
        trade_amount=trade_amount,
        daily_statement_id=daily_statement_id,
        pay_type=pay_type,
        size_hours=size_hours
    )
    metering.save(force_insert=True)
    return metering


def up_int(val, base=100):
    return int(val * base)


class MeteringDiskTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()
        self.vo = VoManager().create_vo(user=self.user, name='test vo', company='test', description='test')
        self.price = Price(
            vm_ram=Decimal('0.012'),
            vm_cpu=Decimal('0.066'),
            vm_disk=Decimal('0.122'),
            vm_pub_ip=Decimal('0.66'),
            vm_upstream=Decimal('0.33'),
            vm_downstream=Decimal('1.44'),
            vm_disk_snap=Decimal('0.65'),
            disk_size=Decimal('1.02'),
            disk_snap=Decimal('0.77'),
            obj_size=Decimal('0'),
            obj_upstream=Decimal('0'),
            obj_downstream=Decimal('0'),
            obj_replication=Decimal('0'),
            obj_get_request=Decimal('0'),
            obj_put_request=Decimal('0'),
            prepaid_discount=66
        )
        self.price.save()

    def init_data_only_normal_disk(self, now: datetime):
        ago_hour_time = now - timedelta(hours=1)    # utc时间00:00（北京时间08:00）之后的1hour之内，测试会通不过，server4会被计量
        meter_time = now - timedelta(days=1)
        ago_time = now - timedelta(days=2)

        # 个人的 计量24h
        disk1 = create_disk_metadata(
            service_id=self.service.id,
            azone_id='1',
            pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value,
            user_id=self.user.id,
            vo_id=None,
            disk_size=100,
            start_time=ago_time,
            creation_time=ago_time,
            task_status=Disk.TaskStatus.OK.value
        )
        # vo的 计量 < 24h
        disk2 = create_disk_metadata(
            service_id=self.service.id,
            azone_id='1',
            pay_type=PayType.POSTPAID.value,
            classification=Disk.Classification.VO.value,
            user_id=self.user.id,
            vo_id=self.vo.id,
            disk_size=88,
            start_time=meter_time,
            creation_time=meter_time,
            task_status=Disk.TaskStatus.OK.value
        )

        # vo的 不会计量
        disk3 = create_disk_metadata(
            service_id=self.service.id,
            azone_id='1',
            pay_type=PayType.POSTPAID.value,
            classification=Disk.Classification.VO.value,
            user_id=self.user.id,
            vo_id=self.vo.id,
            disk_size=88,
            start_time=meter_time,
            creation_time=meter_time,
            task_status=Disk.TaskStatus.FAILED.value
        )
        # 个人的 不会会计量
        disk4 = create_disk_metadata(
            service_id=self.service.id,
            azone_id='1',
            pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value,
            user_id=self.user.id,
            vo_id=None,
            disk_size=188,
            start_time=ago_hour_time,
            creation_time=ago_hour_time,
            task_status=Disk.TaskStatus.OK.value
        )

        return disk1, disk2, disk3, disk4

    def do_assert_disk(self, now: datetime, disk1: Disk, disk2: Disk, disk1_hours: int = 0):
        metering_date = (now - timedelta(days=1)).date()
        metering_end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)    # 计量结束时间
        measurer = DiskMeasurer(raise_exception=True)
        measurer.run()

        # utc时间00:00（北京时间08:00）之后的1hour之内，disk4会被计量
        utc_now = now.astimezone(utc)
        in_utc_0_1 = False
        if time(hour=0, minute=0, second=0) <= utc_now.time() <= time(hour=1, minute=0, second=0):
            in_utc_0_1 = True

        count = MeteringDisk.objects.all().count()
        if in_utc_0_1:
            self.assertEqual(count, 3)
        else:
            self.assertEqual(count, 2)

        # disk1
        metering = measurer.disk_metering_exists(metering_date=metering_date, disk_id=disk1.id)
        self.assertIsNotNone(metering)
        self.assertEqual(up_int(metering.size_hours), up_int(disk1.size * 24))
        self.assertEqual(metering.owner_type, metering.OwnerType.USER.value)
        self.assertEqual(metering.user_id, self.user.id)
        self.assertEqual(metering.username, self.user.username)

        original_amount1 = self.price.disk_size * 100
        trade_amount = original_amount1 * Decimal.from_float(disk1_hours / 24)
        self.assertEqual(metering.original_amount, quantize_10_2(original_amount1))
        self.assertEqual(metering.trade_amount, trade_amount)
        self.assertEqual(metering.pay_type, PayType.PREPAID.value)

        # disk2
        hours = (metering_end_time - disk2.creation_time).total_seconds() / 3600
        metering = measurer.disk_metering_exists(metering_date=metering_date, disk_id=disk2.id)
        self.assertIsNotNone(metering)
        self.assertEqual(up_int(metering.size_hours), up_int(disk2.size * hours))
        self.assertEqual(metering.owner_type, metering.OwnerType.VO.value)
        self.assertEqual(metering.vo_id, self.vo.id)
        self.assertEqual(metering.vo_name, self.vo.name)

        original_amount2 = self.price.disk_size * Decimal.from_float(hours / 24 * 88)
        self.assertEqual(metering.original_amount, quantize_10_2(original_amount2))
        self.assertEqual(metering.trade_amount, quantize_10_2(original_amount2))
        # self.assertEqual(metering.pay_type, PayType.POSTPAID.value)

        DiskMeasurer(raise_exception=True).run()
        count = MeteringDisk.objects.all().count()
        if in_utc_0_1:
            self.assertEqual(count, 3)
        else:
            self.assertEqual(count, 2)

    def test_normal_disk(self):
        now = timezone.now()
        disk1, disk2, disk3, disk4 = self.init_data_only_normal_disk(now)
        self.do_assert_disk(now=now, disk1=disk1, disk2=disk2)

    def test_has_deleted_disk(self):
        now = timezone.now()
        disk1, disk2, disk3, disk4 = self.init_data_only_normal_disk(now)

        server1_id = disk1.id
        disk1: Disk
        ok = disk1.do_soft_delete(deleted_user=self.user.username)
        self.assertIs(ok, True)
        disk1.id = server1_id
        self.do_assert_disk(now=now, disk1=disk1, disk2=disk2)

    def test_post2pre_server_test(self):
        self._test_post2pre_server_test(test_deleted=False)

    def test_post2pre_deleted_server_test(self):
        self._test_post2pre_server_test(test_deleted=True)

    def _test_post2pre_server_test(self, test_deleted: bool):
        now = timezone.now()
        today_srart = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_srart - timedelta(days=1)
        disk1, disk2, disk3, disk4 = self.init_data_only_normal_disk(now)

        # 按量付费
        disk1.pay_type = PayType.POSTPAID.value
        disk1.save(update_fields=['pay_type'])

        # 构建 disk1 计量日的付费方式变更记录，按量转包年包月
        post2pre_log_time = yesterday_start + timedelta(hours=6)
        DiskChangeLog.add_change_log_for_disk(
            disk=disk1, log_type=DiskChangeLog.LogType.POST2PRE.value,
            change_time=post2pre_log_time, change_user=self.user.username, save_db=True)
        disk1.start_time = post2pre_log_time
        disk1.pay_type = PayType.PREPAID.value
        disk1.save(update_fields=['start_time', 'pay_type'])

        if test_deleted:
            ok = disk1.do_soft_delete(deleted_user=self.user.username, raise_exception=False)
            self.assertIs(ok, True)

        # 构建 disk2 计量日后一天的付费方式变更记录，按量转包年包月
        DiskChangeLog.add_change_log_for_disk(
            disk=disk2, log_type=DiskChangeLog.LogType.POST2PRE.value,
            change_time=now, change_user=self.user.username, save_db=True)
        disk2.start_time = now
        disk2.pay_type = PayType.PREPAID.value
        disk2.save(update_fields=['start_time', 'pay_type'])

        if test_deleted:
            ok = disk2.do_soft_delete(deleted_user=self.user.username, raise_exception=False)
            self.assertIs(ok, True)

        self.do_assert_disk(now=now, disk1=disk1, disk2=disk2, disk1_hours=6)


class MeteringPaymentManagerTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()

        # 余额支付有关配置
        app = PayApp(name='app')
        app.save()
        self.app = app
        po = PayOrgnazition(name='机构')
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
            name='test2', data_center_id=self.service.data_center_id, endpoint_url='test2', username='', password='',
            need_vpn=False, pay_app_service_id=self.app_service2.id
        )
        self.service2.save()

    def test_pay_user_disk_statement(self):
        pay_mgr = MeteringPaymentManager()
        payer_name = self.user.username

        app_id = self.app.id
        # pay bill, invalid user id
        dss_bill1 = DailyStatementDisk(
            service_id=self.service.id,
            date=timezone.now().date(),
            owner_type=OwnerType.USER.value,
            user_id='user_id',
            vo_id='',
            original_amount=Decimal('123.45'),
            payable_amount=Decimal('123.45'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )
        dss_bill1.save(force_insert=True)
        with self.assertRaises(errors.Error):
            pay_mgr.pay_daily_statement_bill(
                daily_statement=dss_bill1, app_id=app_id, subject='云硬盘计费',
                executor=self.user.username, remark='')

        # pay bill, pay_type POSTPAID, when no enough balance
        dss_bill1.user_id = self.user.id
        dss_bill1.save(update_fields=['user_id'])
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_daily_statement_bill(
                daily_statement=dss_bill1, app_id=app_id, subject='云硬盘计费',
                executor=self.user.username, remark='', required_enough_balance=True
            )

        # pay bill, pay_type POSTPAID
        pay_mgr.pay_daily_statement_bill(
            daily_statement=dss_bill1, app_id=app_id, subject='云硬盘计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        self.user.userpointaccount.refresh_from_db()
        user_balance = self.user.userpointaccount.balance
        self.assertEqual(user_balance, Decimal('-123.45'))
        dss_bill1.refresh_from_db()
        self.assertEqual(dss_bill1.original_amount, Decimal('123.45'))
        self.assertEqual(dss_bill1.trade_amount, Decimal('123.45'))
        self.assertEqual(dss_bill1.payment_status, PaymentStatus.PAID.value)
        pay_history_id = dss_bill1.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history.payable_amounts, Decimal('123.45'))
        self.assertEqual(pay_history.amounts, Decimal('-123.45'))
        self.assertEqual(pay_history.coupon_amount, Decimal('0'))
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history.instance_id, '')
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user.id)
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, self.user.userpointaccount.id)

        # pay bill
        dss_bill2 = DailyStatementDisk(
            service_id=self.service.id,
            date=(timezone.now() - timedelta(days=1)).date(),
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id='',
            original_amount=Decimal('223.45'),
            payable_amount=Decimal('0'),
            trade_amount=Decimal('0'),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )
        dss_bill2.save(force_insert=True)
        pay_mgr.pay_daily_statement_bill(
            daily_statement=dss_bill2, app_id=app_id, subject='云硬盘计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        dss_bill2.refresh_from_db()
        self.user.userpointaccount.refresh_from_db()
        self.assertEqual(self.user.userpointaccount.balance, user_balance)
        self.assertEqual(dss_bill2.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(dss_bill2.original_amount, Decimal('223.45'))
        self.assertEqual(dss_bill2.payable_amount, Decimal(0))
        self.assertEqual(dss_bill2.trade_amount, Decimal(0))
        self.assertEqual(dss_bill2.payment_history_id, '')

        # pay bill, pay_type POSTPAID
        dss_bill3 = DailyStatementDisk(
            service_id=self.service.id,
            date=(timezone.now() - timedelta(days=2)),
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id='',
            original_amount=Decimal('66.88'),
            payable_amount=Decimal('66.88'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )
        dss_bill3.save(force_insert=True)
        pay_mgr.pay_daily_statement_bill(
            daily_statement=dss_bill3, app_id=app_id, subject='云硬盘计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        self.user.userpointaccount.refresh_from_db()
        user_balance = self.user.userpointaccount.balance
        self.assertEqual(user_balance, Decimal('-123.45') - Decimal('66.88'))
        dss_bill3.refresh_from_db()
        self.assertEqual(dss_bill3.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(dss_bill3.original_amount, Decimal('66.88'))
        self.assertEqual(dss_bill3.trade_amount, Decimal('66.88'))

        pay_history_id = dss_bill3.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.amounts, Decimal('-66.88'))
        self.assertEqual(pay_history.coupon_amount, Decimal('0'))
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user.id)
        self.assertEqual(pay_history.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history.payable_amounts, Decimal('66.88'))
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, self.user.userpointaccount.id)
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history.instance_id, '')

        # ------- test coupon --------
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

        # 有效，只适用于service2
        coupon2_user = CashCoupon(
            face_value=Decimal('33'),
            balance=Decimal('33'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service2.pay_app_service_id,
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
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.VO.value,
            user_id=None, vo_id=self.vo.id
        )
        coupon3_vo.save(force_insert=True)

        # pay bill, pay_type POSTPAID
        dss_bill4 = DailyStatementDisk(
            service_id=self.service.id,
            date=(timezone.now() - timedelta(days=2)),
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            vo_id='',
            original_amount=Decimal('88.8'),
            payable_amount=Decimal('88.8'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )
        dss_bill4.save(force_insert=True)

        self.user.userpointaccount.refresh_from_db()
        user_balance = self.user.userpointaccount.balance
        self.assertEqual(user_balance, Decimal('-190.33'))
        pay_mgr.pay_daily_statement_bill(
            daily_statement=dss_bill4, app_id=app_id, subject='云硬盘计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        self.user.userpointaccount.refresh_from_db()
        user_balance = self.user.userpointaccount.balance
        self.assertEqual(user_balance, Decimal('-190.33') - Decimal('88.8') + Decimal('20'))  # coupon 20
        dss_bill4.refresh_from_db()
        self.assertEqual(dss_bill4.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(dss_bill4.original_amount, Decimal('88.8'))
        self.assertEqual(dss_bill4.trade_amount, Decimal('88.8'))

        pay_history_id = dss_bill4.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.amounts, Decimal('-68.8'))
        self.assertEqual(pay_history.coupon_amount, Decimal('-20'))
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user.id)
        self.assertEqual(pay_history.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history.payable_amounts, Decimal('88.8'))
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE_COUPON.value)
        self.assertEqual(pay_history.payment_account, self.user.userpointaccount.id)
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history.instance_id, '')

    def test_pay_vo_disk_statement(self):
        pay_mgr = MeteringPaymentManager()
        payer_name = self.vo.name
        app_id = self.app.id

        # pay bill, invalid vo id
        dss_bill1 = DailyStatementDisk(
            service_id=self.service.id,
            date=timezone.now().date(),
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id='vo_id',
            original_amount=Decimal('123.45'),
            payable_amount=Decimal('123.45'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )
        dss_bill1.save(force_insert=True)
        with self.assertRaises(errors.Error):
            pay_mgr.pay_daily_statement_bill(
                daily_statement=dss_bill1, app_id=app_id, subject='云硬盘计费',
                executor=self.user.username, remark=''
            )

        # pay bill, pay_type POSTPAID, when not enough balance
        dss_bill1.vo_id = self.vo.id
        dss_bill1.save(update_fields=['vo_id'])
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_daily_statement_bill(
                daily_statement=dss_bill1, app_id=app_id, subject='云硬盘计费',
                executor=self.user.username, remark='', required_enough_balance=True
            )

        # pay bill, pay_type POSTPAID
        pay_mgr.pay_daily_statement_bill(
            daily_statement=dss_bill1, app_id=app_id, subject='云硬盘计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )

        user_balance = pay_mgr.payment.get_vo_point_account(vo_id=self.vo.id).balance
        self.assertEqual(user_balance, Decimal('-123.45'))
        dss_bill1.refresh_from_db()
        self.assertEqual(dss_bill1.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(dss_bill1.original_amount, Decimal('123.45'))
        self.assertEqual(dss_bill1.trade_amount, Decimal('123.45'))
        pay_history_id = dss_bill1.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history.payer_id, self.vo.id)
        self.assertEqual(pay_history.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history.payable_amounts, Decimal('123.45'))
        self.assertEqual(pay_history.amounts, Decimal('-123.45'))
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, self.vo.vopointaccount.id)
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history.instance_id, '')

        # pay bill, pay_type PREPAID
        dss_bill2 = DailyStatementDisk(
            service_id=self.service.id,
            date=(timezone.now() - timedelta(days=1)).date(),
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id=self.vo.id,
            original_amount=Decimal('223.45'),
            payable_amount=Decimal(0),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )
        dss_bill2.save(force_insert=True)
        pay_mgr.pay_daily_statement_bill(
            daily_statement=dss_bill2, app_id=app_id, subject='云硬盘计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        dss_bill2.refresh_from_db()
        self.assertEqual(dss_bill2.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(dss_bill2.original_amount, Decimal('223.45'))
        self.assertEqual(dss_bill2.trade_amount, Decimal(0))
        self.assertEqual(dss_bill2.payment_history_id, '')
        self.vo.vopointaccount.refresh_from_db()
        self.assertEqual(self.vo.vopointaccount.balance, Decimal('-123.45'))

        # pay bill, pay_type POSTPAID
        dss_bill3 = DailyStatementDisk(
            service_id=self.service.id,
            date=(timezone.now() - timedelta(days=2)),
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id=self.vo.id,
            original_amount=Decimal('66.88'),
            payable_amount=Decimal('66.88'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )
        dss_bill3.save(force_insert=True)
        pay_mgr.pay_daily_statement_bill(
            daily_statement=dss_bill3, app_id=app_id, subject='云硬盘计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        self.vo.vopointaccount.refresh_from_db()
        self.assertEqual(self.vo.vopointaccount.balance, Decimal('-123.45') - Decimal('66.88'))
        dss_bill3.refresh_from_db()
        self.assertEqual(dss_bill3.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(dss_bill3.original_amount, Decimal('66.88'))
        self.assertEqual(dss_bill3.trade_amount, Decimal('66.88'))
        pay_history_id = dss_bill3.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history.payer_id, self.vo.id)
        self.assertEqual(pay_history.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history.payable_amounts, Decimal('66.88'))
        self.assertEqual(pay_history.amounts, Decimal('-66.88'))
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, self.vo.vopointaccount.id)
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history.instance_id, '')

        # pay bill, status PAID
        dss_bill4_paid = DailyStatementDisk(
            service_id=self.service.id,
            date=(timezone.now() - timedelta(days=3)),
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id=self.vo.id,
            original_amount=Decimal('166.88'),
            payable_amount=Decimal('166.88'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.PAID.value,
            payment_history_id=''
        )
        dss_bill4_paid.save(force_insert=True)
        with self.assertRaises(errors.Error):
            pay_mgr.pay_daily_statement_bill(
                daily_statement=dss_bill4_paid, app_id=app_id, subject='云硬盘计费',
                executor=self.user.username, remark=''
            )

        dss_bill4_paid.payment_status = PaymentStatus.CANCELLED.value
        dss_bill4_paid.save(update_fields=['payment_status'])
        with self.assertRaises(errors.Error):
            pay_mgr.pay_daily_statement_bill(
                daily_statement=dss_bill4_paid, app_id=app_id, subject='云硬盘计费',
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
            app_service_id=self.service.pay_app_service_id,
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
            app_service_id=self.service2.pay_app_service_id,
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
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon3_user.save(force_insert=True)

        # pay bill
        dss_bill5 = DailyStatementDisk(
            service_id=self.service.id,
            date=(timezone.now() - timedelta(days=2)),
            owner_type=OwnerType.VO.value,
            user_id='',
            vo_id=self.vo.id,
            original_amount=Decimal('88.8'),
            payable_amount=Decimal('88.8'),
            trade_amount=Decimal(0),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=''
        )
        dss_bill5.save(force_insert=True)

        self.vo.vopointaccount.refresh_from_db()
        vo_balance = self.vo.vopointaccount.balance
        self.assertEqual(vo_balance, Decimal('-123.45') - Decimal('66.88'))
        pay_mgr.pay_daily_statement_bill(
            daily_statement=dss_bill5, app_id=app_id, subject='云硬盘计费',
            executor=self.user.username, remark='', required_enough_balance=False
        )
        self.vo.vopointaccount.refresh_from_db()
        vo_balance = self.vo.vopointaccount.balance
        self.assertEqual(vo_balance, Decimal('-190.33') - Decimal('88.8') + Decimal('20'))  # coupon 20
        dss_bill5.refresh_from_db()
        self.assertEqual(dss_bill5.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(dss_bill5.original_amount, Decimal('88.8'))
        self.assertEqual(dss_bill5.trade_amount, Decimal('88.8'))

        pay_history_id = dss_bill5.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.amounts, Decimal('-68.8'))
        self.assertEqual(pay_history.coupon_amount, Decimal('-20'))
        self.assertEqual(pay_history.executor, self.user.username)
        self.assertEqual(pay_history.payer_type, OwnerType.VO.value)
        self.assertEqual(pay_history.payer_id, self.vo.id)
        self.assertEqual(pay_history.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history.payable_amounts, Decimal('88.8'))
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE_COUPON.value)
        self.assertEqual(pay_history.payment_account, self.vo.vopointaccount.id)
        self.assertEqual(pay_history.payer_name, self.vo.name)
        self.assertEqual(pay_history.app_service_id, self.service.pay_app_service_id)
        self.assertEqual(pay_history.instance_id, '')


class DiskStatementTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.user2 = UserProfile(id='user2', username='username2')
        self.user2.save(force_insert=True)

        self.vo = VoManager().create_vo(user=self.user, name='vo', company='vo', description='test')
        self.vo2 = VoManager().create_vo(user=self.user, name='vo2', company='vo2', description='test')
        
        self.service = get_or_create_service()
        self.service2 = ServiceConfig(
            name='service2', data_center_id=self.service.data_center_id,
            endpoint_url='service2', username='', password='',
            need_vpn=False
        )
        self.service2.save(force_insert=True)
        self.service3 = ServiceConfig(
            name='service3', data_center_id=self.service.data_center_id,
            endpoint_url='service3', username='', password='',
            need_vpn=False
        )
        self.service3.save(force_insert=True)

    def init_data(self, st_date: date):
        n_st_date = date(year=2022, month=1, day=2)

        # --- user:
        # self.user-self.service
        for idx in range(1, 6):     # 1-5
            create_metering_disk_metadata(
                service=self.service,
                disk_id='disk' + str(idx),
                date_=st_date,
                owner_type=OwnerType.USER.value,
                user_id=self.user.id,
                username=self.user.username,
                vo_id='test',
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )
        # self.user-self.service2
        for idx in range(6, 10):     # 6-9
            create_metering_disk_metadata(
                service=self.service2,
                disk_id='disk' + str(idx),
                date_=st_date,
                owner_type=OwnerType.USER.value,
                user_id=self.user.id,
                username=self.user.username,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )     
        # self.user-self.service3
        for idx in range(10, 11):     # 10
            create_metering_disk_metadata(
                service=self.service3,
                disk_id='disk' + str(idx),
                date_=st_date,
                owner_type=OwnerType.USER.value,
                user_id=self.user.id,
                username=self.user.username,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )     

        for idx in range(11, 12):     # 11 无效date
            create_metering_disk_metadata(
                service=self.service3,
                disk_id='disk' + str(idx),
                date_=n_st_date,
                owner_type=OwnerType.USER.value,
                user_id=self.user.id,
                username=self.user.username,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )   
        for idx in range(12, 13):     # 12 不计入的pay_type
            create_metering_disk_metadata(
                service=self.service3,
                disk_id='disk' + str(idx),
                date_=st_date,
                owner_type=OwnerType.USER.value,
                user_id=self.user.id,
                username=self.user.username,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.PREPAID.value
            )      

        # self.user2-self.service
        for idx in range(13, 15):     # 13-14
            create_metering_disk_metadata(
                service=self.service,
                disk_id='disk' + str(idx),
                date_=st_date,
                owner_type=OwnerType.USER.value,
                user_id=self.user2.id,
                username=self.user2.username,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )

        # --- vo:
        # self.vo-self.service
        for idx in range(15, 20):     # 15-19
            create_metering_disk_metadata(
                service=self.service,
                disk_id='disk' + str(idx),
                date_=st_date,
                owner_type=OwnerType.VO.value,
                vo_id=self.vo.id,
                vo_name=self.vo.name,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )
        # self.vo-self.service2
        for idx in range(20, 24):     # 20-23
            vo_name = self.vo.name if idx % 2 == 0 else 'testvo'
            create_metering_disk_metadata(
                service=self.service2,
                disk_id='disk' + str(idx),
                date_=st_date,
                owner_type=OwnerType.VO.value,
                vo_id=self.vo.id,
                vo_name=vo_name,
                user_id='test',
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )
        # self.vo-self.service3
        for idx in range(24, 25):     # 24
            create_metering_disk_metadata(
                service=self.service3,
                disk_id='disk' + str(idx),
                date_=st_date,
                owner_type=OwnerType.VO.value,
                vo_id=self.vo.id,
                vo_name=self.vo.name,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )
        for idx in range(25, 26):     # 25 无效date
            create_metering_disk_metadata(
                service=self.service3,
                disk_id='disk' + str(idx),
                date_=n_st_date,
                owner_type=OwnerType.VO.value,
                vo_id=self.vo.id,
                vo_name=self.vo.name,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )
        for idx in range(26, 27):     # 26 无效pay_type
            create_metering_disk_metadata(
                service=self.service3,
                disk_id='disk' + str(idx),
                date_=st_date,
                owner_type=OwnerType.VO.value,
                vo_id=self.vo.id,
                vo_name=self.vo.name,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.PREPAID.value
            )
        # self.vo2-self.service
        for idx in range(27, 30):     # 27-29
            create_metering_disk_metadata(
                service=self.service,
                disk_id='disk' + str(idx),
                date_=st_date,
                owner_type=OwnerType.VO.value,
                vo_id=self.vo2.id,
                vo_name=self.vo2.name,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )

    def do_assert_a_user_daily_statement(
            self, range_a, range_b, user, service: ServiceConfig, meterings, st_date
    ):
        original_amount = 0
        payable_amount = 0
        for idx in range(range_a, range_b):
            original_amount += Decimal(str(int(idx)+0.1))
            payable_amount += Decimal(str(int(idx)+0.11))

        daily_statement = DiskDailyStatementGenerater.user_disk_statement_exists(
            statement_date=st_date, service_id=service.id, user_id=user.id)
        self.assertIsNotNone(daily_statement)
        self.assertEqual(daily_statement.date, st_date)
        self.assertEqual(daily_statement.owner_type, OwnerType.USER.value)
        self.assertEqual(daily_statement.user_id, user.id)
        self.assertEqual(daily_statement.username, user.username)
        self.assertEqual(daily_statement.service_id, service.id)
        self.assertEqual(daily_statement.original_amount, original_amount)
        self.assertEqual(daily_statement.payable_amount, payable_amount)
        self.assertEqual(daily_statement.trade_amount, Decimal(0))
        self.assertEqual(daily_statement.payment_status, PaymentStatus.UNPAID.value)
        self.assertEqual(daily_statement.payment_history_id, '')

        cnt = 0
        for m in meterings:
            m: MeteringDisk
            if (
                    m.user_id == user.id and m.service_id == service.id and m.date == st_date and
                    m.pay_type == PayType.POSTPAID.value
            ):
                cnt += 1
                self.assertEqual(m.daily_statement_id, daily_statement.id)
            else:
                self.assertNotEqual(m.daily_statement_id, daily_statement.id)

        self.assertEqual(cnt, range_b-range_a)

    def do_assert_a_vo_daily_statement(
            self, range_a, range_b, vo, service: ServiceConfig, meterings, st_date
    ):
        original_amount = 0
        payable_amount = 0
        for idx in range(range_a, range_b):
            original_amount += Decimal(str(int(idx)+0.1))
            payable_amount += Decimal(str(int(idx)+0.11))

        daily_statement = DiskDailyStatementGenerater.vo_disk_statement_exists(
            statement_date=st_date, service_id=service.id, vo_id=vo.id)
        self.assertIsNotNone(daily_statement)
        self.assertEqual(daily_statement.date, st_date)
        self.assertEqual(daily_statement.owner_type, OwnerType.VO.value)
        self.assertEqual(daily_statement.vo_id, vo.id)
        self.assertEqual(daily_statement.vo_name, vo.name)
        self.assertEqual(daily_statement.service, service)
        self.assertEqual(daily_statement.payment_status, PaymentStatus.UNPAID.value)
        self.assertEqual(daily_statement.payment_history_id, '')
        self.assertEqual(daily_statement.original_amount, original_amount)
        self.assertEqual(daily_statement.payable_amount, payable_amount)
        self.assertEqual(daily_statement.trade_amount, Decimal(0))

        cnt = 0
        for m in meterings:
            m: MeteringDisk
            if (
                    m.vo_id == vo.id and m.service.id == service.id and m.date == st_date
                    and m.pay_type == PayType.POSTPAID.value
            ):
                cnt += 1
                self.assertEqual(m.daily_statement_id, daily_statement.id)
            else:
                self.assertNotEqual(m.daily_statement_id, daily_statement.id)

        self.assertEqual(cnt, range_b-range_a)

    def test_daily_statement(self):
        st_date = date(year=2022, month=1, day=1)
        self.init_data(st_date=st_date)

        generate_daily_statement = DiskDailyStatementGenerater(statement_date=st_date, raise_exception=True)
        generate_daily_statement.run()

        count = DailyStatementDisk.objects.all().count()
        self.assertEqual(count, 8)

        meterings = MeteringDisk.objects.all()

        # 2022.01.01-user-service
        self.do_assert_a_user_daily_statement(
            range_a=1, range_b=6, user=self.user, service=self.service,
            meterings=meterings, st_date=st_date
        )
        # 2022.01.01-user-service2
        self.do_assert_a_user_daily_statement(
            range_a=6, range_b=10, user=self.user, service=self.service2,
            meterings=meterings, st_date=st_date
        )
        # 2022.01.01-user-service3
        self.do_assert_a_user_daily_statement(
            range_a=10, range_b=11, user=self.user, service=self.service3,
            meterings=meterings, st_date=st_date
        )
        # 2022.01.01-user2-service
        self.do_assert_a_user_daily_statement(
            range_a=13, range_b=15, user=self.user2, service=self.service,
            meterings=meterings, st_date=st_date
        )
        # 2022.01.01-vo-service
        self.do_assert_a_vo_daily_statement(
            range_a=15, range_b=20, vo=self.vo, service=self.service,
            meterings=meterings, st_date=st_date
        )
        # 2022.01.01-vo-service2
        self.do_assert_a_vo_daily_statement(
            range_a=20, range_b=24, vo=self.vo, service=self.service2,
            meterings=meterings, st_date=st_date
        )
        # 2022.01.01-vo-service3
        self.do_assert_a_vo_daily_statement(
            range_a=24, range_b=25, vo=self.vo, service=self.service3,
            meterings=meterings, st_date=st_date
        )
        # 2022.01.01-vo2-service
        self.do_assert_a_vo_daily_statement(
            range_a=27, range_b=30, vo=self.vo2, service=self.service,
            meterings=meterings, st_date=st_date
        )

        # 无效date和pay_type
        cnt = 0
        for m in meterings:
            if m.date != st_date or m.pay_type != PayType.POSTPAID.value:
                cnt += 1
                self.assertEqual(m.daily_statement_id, '')

        self.assertEqual(cnt, 4)

        # 追加数据后，二次运行
        # 2022.01.01-user-service
        create_metering_disk_metadata(
            service=self.service,
            disk_id='disk_user_added',
            date_=st_date,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            username=self.user.username,
            original_amount=Decimal('0.1'),
            trade_amount=Decimal('0.11'),
            pay_type=PayType.POSTPAID.value
        )

        # 2022.01.01-vo-service
        create_metering_disk_metadata(
            service=self.service,
            disk_id='disk_vo_added',
            date_=st_date,
            owner_type=OwnerType.VO.value,
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            original_amount=Decimal('14.1'),
            trade_amount=Decimal('14.11'),
            pay_type=PayType.POSTPAID.value
        )
        DiskDailyStatementGenerater(statement_date=st_date, raise_exception=True).run()

        # 结算单数量不变，金额增加
        count = DailyStatementDisk.objects.all().count()
        self.assertEqual(count, 8)

        meterings = MeteringDisk.objects.all()
        # 2022.01.01-user-service
        self.do_assert_a_user_daily_statement(
            range_a=0, range_b=6, user=self.user, service=self.service,
            meterings=meterings, st_date=st_date
        )
        # 2022.01.01-vo-service
        self.do_assert_a_vo_daily_statement(
            range_a=14, range_b=20, vo=self.vo, service=self.service,
            meterings=meterings, st_date=st_date
        )
        # 2022.01.01-vo2-service
        self.do_assert_a_vo_daily_statement(
            range_a=27, range_b=30, vo=self.vo2, service=self.service,
            meterings=meterings, st_date=st_date
        )
