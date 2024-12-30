from decimal import Decimal
from datetime import datetime, timedelta, time, timezone as dt_timezone

from django.test import TransactionTestCase
from django.utils import timezone as dj_timezone
from django.conf import settings
from django.urls import reverse

from utils.test import get_or_create_user, get_or_create_service, get_or_create_organization, MyAPITransactionTestCase
from utils.model import PayType, OwnerType, ResourceType
from utils.decimal_utils import quantize_10_2
from core import errors
from core import site_configs_manager
from apps.app_servers.models import Server, ServerArchive, ServiceConfig
from apps.app_vo.managers import VoManager
from apps.app_order.tests import create_price
from apps.app_order.models import Order
from apps.app_order.managers import OrderManager, ServerConfig, OrderPaymentManager
from apps.app_wallet.models import CashCoupon, PaymentHistory, PayAppService, PayApp
from apps.app_metering.measurers import ServerMeasurer
from apps.app_metering.models import MeteringServer, PaymentStatus, DailyStatementServer
from apps.app_metering.payment import MeteringPaymentManager
from apps.app_metering.statement_generators import GenerateDailyStatementServer
from apps.users.models import UserProfile

utc = dt_timezone.utc
PAY_APP_ID = site_configs_manager.get_pay_app_id(settings)


def create_server_metadata(
        service, user,
        vcpu: int, ram: int, disk_size: int, public_ip: bool,
        start_time, creation_time, vo_id=None,
        classification=Server.Classification.PERSONAL.value,
        task_status=Server.TASK_CREATED_OK,
        pay_type=PayType.PREPAID.value
):
    server = Server(
        service=service,
        instance_id='test',
        remarks='',
        user=user,
        vcpus=vcpu,
        ram=ram,
        disk_size=disk_size,
        ipv4='127.0.0.1',
        image='test-image',
        task_status=task_status,
        public_ip=public_ip,
        classification=classification,
        vo_id=vo_id,
        image_id='',
        image_desc='image desc',
        default_user='root',
        creation_time=creation_time,
        start_time=start_time,
        pay_type=pay_type
    )
    server.raw_default_password = ''
    server.save()
    return server


def create_metering_server_metadata(
        service, server_id, date_,
        original_amount: Decimal, trade_amount: Decimal, daily_statement_id='',
        owner_type=OwnerType.USER.value, user_id='', username='', vo_id='', vo_name='',
        pay_type=PayType.POSTPAID.value, 
        cpu_hours=0, ram_hours=0, disk_hours=0, public_ip_hours=0,
        snapshot_hours=0, upstream=0, downstream=0
):
    metering = MeteringServer(
        service=service,
        server_id=server_id,
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
        cpu_hours=cpu_hours,
        ram_hours=ram_hours,
        disk_hours=disk_hours,
        public_ip_hours=public_ip_hours,
        snapshot_hours=snapshot_hours,
        upstream=upstream,
        downstream=downstream
    )
    metering.save()
    return metering


def up_int(val, base=100):
    return int(val * base)


class MeteringServerTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()
        self.vo = VoManager().create_vo(user=self.user, name='test vo', company='test', description='test')
        self.price = create_price()

    def init_data_only_server(self, now: datetime):
        ago_hour_time = now - timedelta(hours=1)    # utc时间00:00（北京时间08:00）之后的1hour之内，测试会通不过，server4会被计量
        meter_time = now - timedelta(days=1)
        ago_time = now - timedelta(days=2)

        # 个人的 计量24h
        server1 = create_server_metadata(
            service=self.service,
            user=self.user,
            vcpu=4,
            ram=4,
            disk_size=100,
            public_ip=True,
            start_time=ago_time,
            creation_time=ago_time,
            pay_type=PayType.PREPAID.value
        )
        # vo的 计量 < 24h
        server2 = create_server_metadata(
            service=self.service,
            user=self.user,
            vcpu=3,
            ram=3,
            disk_size=88,
            public_ip=False,
            start_time=meter_time,
            creation_time=meter_time,
            classification=Server.Classification.VO.value,
            vo_id=self.vo.id,
            pay_type=PayType.POSTPAID.value
        )

        # vo的 不会计量
        server3 = create_server_metadata(
            service=self.service,
            user=self.user,
            vcpu=3,
            ram=3,
            disk_size=88,
            public_ip=False,
            start_time=meter_time,
            creation_time=meter_time,
            task_status=Server.TASK_CREATE_FAILED,
            classification=Server.Classification.VO.value,
            vo_id=self.vo.id
        )
        # 个人的 不会会计量
        server4 = create_server_metadata(
            service=self.service,
            user=self.user,
            vcpu=2,
            ram=2,
            disk_size=188,
            public_ip=False,
            start_time=ago_hour_time,
            creation_time=ago_hour_time
        )

        return server1, server2, server3, server4

    def do_assert_server(self, now: datetime, server1: Server, server2: Server, server1_hours: int = 0):
        metering_date = (now - timedelta(days=1)).date()
        metering_end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)    # 计量结束时间
        measurer = ServerMeasurer(raise_exception=True)
        measurer.run()

        # utc时间00:00（北京时间08:00）之后的1hour之内，server4会被计量
        utc_now = now.astimezone(utc)
        in_utc_0_1 = False
        if time(hour=0, minute=0, second=0) <= utc_now.time() <= time(hour=1, minute=0, second=0):
            in_utc_0_1 = True

        count = MeteringServer.objects.all().count()
        if in_utc_0_1:
            self.assertEqual(count, 3)
        else:
            self.assertEqual(count, 2)

        # server1
        metering = measurer.server_metering_exists(metering_date=metering_date, server_id=server1.id)
        self.assertIsNotNone(metering)
        self.assertEqual(up_int(metering.cpu_hours), up_int(server1.vcpus * 24))
        self.assertEqual(up_int(metering.ram_hours), up_int(server1.ram_gib * 24))
        self.assertEqual(up_int(metering.disk_hours), up_int(server1.disk_size * 24))
        self.assertEqual(metering.owner_type, metering.OwnerType.USER.value)
        self.assertEqual(metering.user_id, self.user.id)
        self.assertEqual(metering.username, self.user.username)
        if server1.public_ip:
            self.assertEqual(up_int(metering.public_ip_hours), up_int(24))
        else:
            self.assertEqual(up_int(metering.public_ip_hours), 0)

        original_amount1 = (self.price.vm_cpu * 4) + (self.price.vm_ram * 4) + (
                self.price.vm_disk * 100) + self.price.vm_pub_ip + self.price.vm_base
        trade_amount = original_amount1 * server1_hours
        original_amount1 = original_amount1 * 24
        self.assertEqual(metering.original_amount, quantize_10_2(original_amount1))
        self.assertEqual(metering.trade_amount, quantize_10_2(trade_amount))
        self.assertEqual(metering.pay_type, PayType.PREPAID.value)

        # server2
        hours = (metering_end_time - server2.creation_time).total_seconds() / 3600
        metering = measurer.server_metering_exists(metering_date=metering_date, server_id=server2.id)
        self.assertIsNotNone(metering)
        self.assertEqual(up_int(metering.cpu_hours), up_int(server2.vcpus * hours))
        self.assertEqual(up_int(metering.ram_hours), up_int(server2.ram_gib * hours))
        self.assertEqual(up_int(metering.disk_hours), up_int(server2.disk_size * hours))
        self.assertEqual(metering.owner_type, metering.OwnerType.VO.value)
        self.assertEqual(metering.vo_id, self.vo.id)
        self.assertEqual(metering.vo_name, self.vo.name)
        if server2.public_ip:
            self.assertEqual(up_int(metering.public_ip_hours), up_int(hours))
        else:
            self.assertEqual(up_int(metering.public_ip_hours), 0)

        original_amount2 = (self.price.vm_cpu * 3) + (self.price.vm_ram * 3) +\
                           (self.price.vm_disk * 88) + self.price.vm_base
        original_amount2 = original_amount2 * Decimal.from_float(hours)
        self.assertEqual(metering.original_amount, quantize_10_2(original_amount2))
        self.assertEqual(metering.trade_amount, quantize_10_2(original_amount2))
        # self.assertEqual(metering.pay_type, PayType.POSTPAID.value)

        measurer.run()
        count = MeteringServer.objects.all().count()
        if in_utc_0_1:
            self.assertEqual(count, 3)
        else:
            self.assertEqual(count, 2)

    def test_only_server(self):
        now = dj_timezone.now()
        server1, server2, server3, server4 = self.init_data_only_server(now)
        self.do_assert_server(now=now, server1=server1, server2=server2)

    def test_archive_server(self):
        now = dj_timezone.now()
        server1, server2, server3, server4 = self.init_data_only_server(now)

        server1_id = server1.id
        ok = server1.do_archive(archive_user=self.user)
        self.assertIs(ok, True)
        server1.id = server1_id
        self.do_assert_server(now=now, server1=server1, server2=server2)

    def test_archive_rebuild_server(self):
        now = dj_timezone.now()
        server1, server2, server3, server4 = self.init_data_only_server(now)

        server1_id = server1.id

        # 构建server1 计量日的rebuild记录
        archive = ServerArchive.init_archive_from_server(
            server=server1, archive_user=self.user, archive_type=ServerArchive.ArchiveType.REBUILD.value, commit=True)
        new_starttime = archive.deleted_time - timedelta(days=1)
        archive.deleted_time = new_starttime
        archive.save(update_fields=['deleted_time'])
        server1.start_time = archive.deleted_time
        server1.save(update_fields=['start_time'])

        ok = server1.do_archive(archive_user=self.user)
        self.assertIs(ok, True)
        server1.id = server1_id
        self.do_assert_server(now=now, server1=server1, server2=server2)

    def test_archive_rebuild_post2pre_server(self):
        self._rebuild_post2pre_server_test(test_archive=True)

    def test_rebuild_post2pre_server(self):
        self._rebuild_post2pre_server_test(test_archive=False)

    def _rebuild_post2pre_server_test(self, test_archive: bool):
        now = dj_timezone.now()
        today_srart = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_srart - timedelta(days=1)
        server1, server2, server3, server4 = self.init_data_only_server(now)

        # 按量付费
        server1_id = server1.id
        server1.pay_type = PayType.POSTPAID.value
        server1.save(update_fields=['pay_type'])

        # 构建server1 计量日的rebuild记录
        rebuild_log_time = yesterday_start + timedelta(hours=2)
        rebuild_log = ServerArchive.init_archive_from_server(
            server=server1, archive_user=self.user, archive_type=ServerArchive.ArchiveType.REBUILD.value,
            archive_time=rebuild_log_time, commit=True)
        server1.start_time = rebuild_log_time
        server1.save(update_fields=['start_time'])

        # 构建server1 计量日的付费方式变更记录，按量转包年包月
        post2pre_log_time = rebuild_log_time + timedelta(hours=6)
        post2pre_log = ServerArchive.init_archive_from_server(
            server=server1, archive_user=self.user, archive_type=ServerArchive.ArchiveType.POST2PRE.value,
            archive_time=post2pre_log_time, commit=True)
        server1.start_time = post2pre_log_time
        server1.pay_type = PayType.PREPAID.value
        server1.save(update_fields=['start_time', 'pay_type'])

        if test_archive:
            ok = server1.do_archive(archive_user=self.user)
            self.assertIs(ok, True)

        server1.id = server1_id

        # 构建server2 计量日后一天的付费方式变更记录，按量转包年包月
        ServerArchive.init_archive_from_server(
            server=server2, archive_user=self.user, archive_type=ServerArchive.ArchiveType.POST2PRE.value,
            archive_time=now, commit=True)
        server2.start_time = now
        server2.pay_type = PayType.PREPAID.value
        server2.save(update_fields=['start_time', 'pay_type'])

        server2_id = server2.id
        if test_archive:
            ok = server2.do_archive(archive_user=self.user)
            self.assertIs(ok, True)
            server2.id = server2_id

        self.do_assert_server(now=now, server1=server1, server2=server2, server1_hours=6)


class MeteringPaymentManagerTests(TransactionTestCase):
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

    def test_pay_user_daily_statement_server(self):
        pay_mgr = MeteringPaymentManager()
        payer_name = self.user.username

        app_id = self.app.id
        # pay bill, invalid user id
        dss_bill1 = DailyStatementServer(
            service_id=self.service.id,
            date=dj_timezone.now().date(),
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
                daily_statement=dss_bill1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='')

        # pay bill, pay_type POSTPAID, when no enough balance
        dss_bill1.user_id = self.user.id
        dss_bill1.save(update_fields=['user_id'])
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_daily_statement_bill(
                daily_statement=dss_bill1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='', required_enough_balance=True
            )

        # pay bill, pay_type POSTPAID
        pay_mgr.pay_daily_statement_bill(
            daily_statement=dss_bill1, app_id=app_id, subject='云服务器计费',
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
        dss_bill2 = DailyStatementServer(
            service_id=self.service.id,
            date=(dj_timezone.now() - timedelta(days=1)).date(),
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
            daily_statement=dss_bill2, app_id=app_id, subject='云服务器计费',
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
        dss_bill3 = DailyStatementServer(
            service_id=self.service.id,
            date=(dj_timezone.now() - timedelta(days=2)),
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
            daily_statement=dss_bill3, app_id=app_id, subject='云服务器计费',
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
        now_time = dj_timezone.now()
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
        dss_bill4 = DailyStatementServer(
            service_id=self.service.id,
            date=(dj_timezone.now() - timedelta(days=2)),
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
            daily_statement=dss_bill4, app_id=app_id, subject='云服务器计费',
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

    def test_pay_vo_daily_statement_server(self):
        pay_mgr = MeteringPaymentManager()
        payer_name = self.vo.name
        app_id = self.app.id

        # pay bill, invalid vo id
        dss_bill1 = DailyStatementServer(
            service_id=self.service.id,
            date=dj_timezone.now().date(),
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
                daily_statement=dss_bill1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark=''
            )

        # pay bill, pay_type POSTPAID, when not enough balance
        dss_bill1.vo_id = self.vo.id
        dss_bill1.save(update_fields=['vo_id'])
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_daily_statement_bill(
                daily_statement=dss_bill1, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark='', required_enough_balance=True
            )

        # pay bill, pay_type POSTPAID
        pay_mgr.pay_daily_statement_bill(
            daily_statement=dss_bill1, app_id=app_id, subject='云服务器计费',
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
        dss_bill2 = DailyStatementServer(
            service_id=self.service.id,
            date=(dj_timezone.now() - timedelta(days=1)).date(),
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
            daily_statement=dss_bill2, app_id=app_id, subject='云服务器计费',
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
        dss_bill3 = DailyStatementServer(
            service_id=self.service.id,
            date=(dj_timezone.now() - timedelta(days=2)),
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
            daily_statement=dss_bill3, app_id=app_id, subject='云服务器计费',
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
        dss_bill4_paid = DailyStatementServer(
            service_id=self.service.id,
            date=(dj_timezone.now() - timedelta(days=3)),
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
                daily_statement=dss_bill4_paid, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark=''
            )

        dss_bill4_paid.payment_status = PaymentStatus.CANCELLED.value
        dss_bill4_paid.save(update_fields=['payment_status'])
        with self.assertRaises(errors.Error):
            pay_mgr.pay_daily_statement_bill(
                daily_statement=dss_bill4_paid, app_id=app_id, subject='云服务器计费',
                executor=self.user.username, remark=''
            )

        # ------- test coupon --------
        now_time = dj_timezone.now()
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
        dss_bill5 = DailyStatementServer(
            service_id=self.service.id,
            date=(dj_timezone.now() - timedelta(days=2)),
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
            daily_statement=dss_bill5, app_id=app_id, subject='云服务器计费',
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


class DailyStatementTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.user2 = UserProfile(id='user2', username='username2')
        self.user2.save(force_insert=True)

        self.vo = VoManager().create_vo(user=self.user, name='vo', company='vo', description='test')
        self.vo2 = VoManager().create_vo(user=self.user, name='vo2', company='vo2', description='test')
        
        self.service = get_or_create_service()
        self.service2 = ServiceConfig(
            name='service2', org_data_center_id=self.service.org_data_center_id,
            endpoint_url='service2', username='', password='',
            need_vpn=False
        )
        self.service2.save(force_insert=True)
        self.service3 = ServiceConfig(
            name='service3', org_data_center_id=self.service.org_data_center_id,
            endpoint_url='service3', username='', password='',
            need_vpn=False
        )
        self.service3.save(force_insert=True)

    def init_data(self, st_date: str = '2022-01-01'):
        n_st_date = '2022-01-02'

        # --- user:
        # self.user-self.service
        for idx in range(1, 6):     # 1-5
            create_metering_server_metadata(
                service=self.service,
                server_id='server' + str(idx),
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
            create_metering_server_metadata(
                service=self.service2,
                server_id='server' + str(idx),
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
            create_metering_server_metadata(
                service=self.service3,
                server_id='server' + str(idx),
                date_=st_date,
                owner_type=OwnerType.USER.value,
                user_id=self.user.id,
                username=self.user.username,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )     

        for idx in range(11, 12):     # 11 无效date
            create_metering_server_metadata(
                service=self.service3,
                server_id='server' + str(idx),
                date_=n_st_date,
                owner_type=OwnerType.USER.value,
                user_id=self.user.id,
                username=self.user.username,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )   
        for idx in range(12, 13):     # 12 无效pay_type
            create_metering_server_metadata(
                service=self.service3,
                server_id='server' + str(idx),
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
            create_metering_server_metadata(
                service=self.service,
                server_id='server' + str(idx),
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
            create_metering_server_metadata(
                service=self.service,
                server_id='server' + str(idx),
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
            create_metering_server_metadata(
                service=self.service2,
                server_id='server' + str(idx),
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
            create_metering_server_metadata(
                service=self.service3,
                server_id='server' + str(idx),
                date_=st_date,
                owner_type=OwnerType.VO.value,
                vo_id=self.vo.id,
                vo_name=self.vo.name,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )
        for idx in range(25, 26):     # 25 无效date
            create_metering_server_metadata(
                service=self.service3,
                server_id='server' + str(idx),
                date_=n_st_date,
                owner_type=OwnerType.VO.value,
                vo_id=self.vo.id,
                vo_name=self.vo.name,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )
        for idx in range(26, 27):     # 26 无效pay_type
            create_metering_server_metadata(
                service=self.service3,
                server_id='server' + str(idx),
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
            create_metering_server_metadata(
                service=self.service,
                server_id='server' + str(idx),
                date_=st_date,
                owner_type=OwnerType.VO.value,
                vo_id=self.vo2.id,
                vo_name=self.vo2.name,
                original_amount=Decimal.from_float(idx+0.1),
                trade_amount=Decimal.from_float(idx+0.11),
                pay_type=PayType.POSTPAID.value
            )

    def do_assert_a_user_daily_statement(
            self, range_a, range_b, user, service, generate_daily_statement, meterings, st_date
    ):
        original_amount = 0
        payable_amount = 0
        for idx in range(range_a, range_b):
            original_amount += Decimal(str(int(idx)+0.1))
            payable_amount += Decimal(str(int(idx)+0.11))
        daily_statement = generate_daily_statement.user_daily_statement_exists(
            statement_date=st_date, service_id=service.id, user_id=user.id)
        self.assertIsNotNone(daily_statement)
        self.assertEqual(daily_statement.date, st_date)
        self.assertEqual(daily_statement.owner_type, OwnerType.USER.value)
        self.assertEqual(daily_statement.user_id, user.id)
        self.assertEqual(daily_statement.username, user.username)
        self.assertEqual(daily_statement.service, service)
        self.assertEqual(daily_statement.original_amount, original_amount)
        self.assertEqual(daily_statement.payable_amount, payable_amount)
        self.assertEqual(daily_statement.trade_amount, Decimal(0))
        self.assertEqual(daily_statement.payment_status, PaymentStatus.UNPAID.value)
        self.assertEqual(daily_statement.payment_history_id, '')

        cnt = 0
        for m in meterings:
            if (
                    m.user_id == user.id and m.service == service and m.date == st_date and
                    m.pay_type == PayType.POSTPAID.value
            ):
                cnt += 1
                self.assertEqual(m.daily_statement_id, daily_statement.id)
            else:
                self.assertNotEqual(m.daily_statement_id, daily_statement.id)
        self.assertEqual(cnt, range_b-range_a)

    def do_assert_a_vo_daily_statement(
            self, range_a, range_b, vo, service, generate_daily_statement, meterings, st_date
    ):
        original_amount = 0
        payable_amount = 0
        for idx in range(range_a, range_b):
            original_amount += Decimal(str(int(idx)+0.1))
            payable_amount += Decimal(str(int(idx)+0.11))
        daily_statement = generate_daily_statement.vo_daily_statement_exists(
            statement_date=st_date, service_id=service.id, vo_id=vo.id)
        self.assertIsNotNone(daily_statement)
        self.assertEqual(daily_statement.date, st_date)
        self.assertEqual(daily_statement.owner_type, OwnerType.VO.value)
        self.assertEqual(daily_statement.vo_id, vo.id)
        self.assertEqual(daily_statement.vo_name, vo.name)
        self.assertEqual(daily_statement.service, service)
        self.assertEqual(daily_statement.original_amount, original_amount)
        self.assertEqual(daily_statement.payable_amount, payable_amount)
        self.assertEqual(daily_statement.trade_amount, Decimal(0))
        self.assertEqual(daily_statement.payment_status, PaymentStatus.UNPAID.value)
        self.assertEqual(daily_statement.payment_history_id, '')

        cnt = 0
        for m in meterings:
            if m.vo_id == vo.id and m.service == service and m.date == st_date and m.pay_type == PayType.POSTPAID.value:
                cnt += 1
                self.assertEqual(m.daily_statement_id, daily_statement.id)
            else:
                self.assertNotEqual(m.daily_statement_id, daily_statement.id)
        self.assertEqual(cnt, range_b-range_a)

    def test_daily_statement(self, st_date: str = '2022-01-01'):
        self.init_data(st_date=st_date)

        st_date = datetime.strptime(st_date, '%Y-%m-%d').date()
        generate_daily_statement = GenerateDailyStatementServer(statement_date=st_date, raise_exception=True)
        generate_daily_statement.run()

        count = DailyStatementServer.objects.all().count()
        self.assertEqual(count, 8)

        meterings = MeteringServer.objects.all()

        # 2022.01.01-user-service
        self.do_assert_a_user_daily_statement(
            range_a=1, range_b=6, user=self.user, service=self.service,
            generate_daily_statement=generate_daily_statement, meterings=meterings, st_date=st_date
        )
        # 2022.01.01-user-service2
        self.do_assert_a_user_daily_statement(
            range_a=6, range_b=10, user=self.user, service=self.service2,
            generate_daily_statement=generate_daily_statement, meterings=meterings, st_date=st_date
        )
        # 2022.01.01-user-service3
        self.do_assert_a_user_daily_statement(
            range_a=10, range_b=11, user=self.user, service=self.service3,
            generate_daily_statement=generate_daily_statement, meterings=meterings, st_date=st_date
        )
        # 2022.01.01-user2-service
        self.do_assert_a_user_daily_statement(
            range_a=13, range_b=15, user=self.user2, service=self.service,
            generate_daily_statement=generate_daily_statement, meterings=meterings, st_date=st_date
        )
        # 2022.01.01-vo-service
        self.do_assert_a_vo_daily_statement(
            range_a=15, range_b=20, vo=self.vo, service=self.service,
            generate_daily_statement=generate_daily_statement, meterings=meterings, st_date=st_date
        )
        # 2022.01.01-vo-service2
        self.do_assert_a_vo_daily_statement(
            range_a=20, range_b=24, vo=self.vo, service=self.service2,
            generate_daily_statement=generate_daily_statement, meterings=meterings, st_date=st_date
        )
        # 2022.01.01-vo-service3
        self.do_assert_a_vo_daily_statement(
            range_a=24, range_b=25, vo=self.vo, service=self.service3,
            generate_daily_statement=generate_daily_statement, meterings=meterings, st_date=st_date
        )
        # 2022.01.01-vo2-service
        self.do_assert_a_vo_daily_statement(
            range_a=27, range_b=30, vo=self.vo2, service=self.service,
            generate_daily_statement=generate_daily_statement, meterings=meterings, st_date=st_date
        )

        # 无效date和pay_type
        cnt = 0
        for m in meterings:
            if m.date != st_date or m.pay_type != PayType.POSTPAID.value:
                cnt += 1
                self.assertEqual(m.daily_statement_id, '')
        self.assertEqual(cnt, 4)

        # 异常：二次运行
        # 2022.01.01-user-service
        added_metering = create_metering_server_metadata(   
            service=self.service,
            server_id='server_user_added',
            date_=st_date,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id,
            username=self.user.username,
            original_amount=Decimal('0.1'),
            trade_amount=Decimal('0.11'),
            pay_type=PayType.POSTPAID.value
        )
        original_amount = added_metering.original_amount
        payable_amount = added_metering.trade_amount
        for idx in range(1, 6):
            original_amount += Decimal(str(int(idx)+0.1))
            payable_amount += Decimal(str(int(idx)+0.11))

        generate_daily_statement2 = GenerateDailyStatementServer(statement_date=st_date, raise_exception=True)
        generate_daily_statement2.run()
        daily_statement2 = generate_daily_statement2.user_daily_statement_exists(
            statement_date=st_date, service_id=self.service.id, user_id=self.user.id)
        self.assertEqual(daily_statement2.original_amount, original_amount)
        self.assertEqual(daily_statement2.payable_amount, payable_amount)

        # 2022.01.01-vo-service
        added_metering = create_metering_server_metadata(   
            service=self.service,
            server_id='server_vo_added',
            date_=st_date,
            owner_type=OwnerType.VO.value,
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            original_amount=Decimal('0.2'),
            trade_amount=Decimal('0.22'),
            pay_type=PayType.POSTPAID.value
        )
        original_amount = added_metering.original_amount
        payable_amount = added_metering.trade_amount
        for idx in range(15, 20):
            original_amount += Decimal(str(int(idx)+0.1))
            payable_amount += Decimal(str(int(idx)+0.11))

        generate_daily_statement3 = GenerateDailyStatementServer(statement_date=st_date, raise_exception=True)
        generate_daily_statement3.run()
        daily_statement3 = generate_daily_statement3.vo_daily_statement_exists(
            statement_date=st_date, service_id=self.service.id, vo_id=self.vo.id)
        self.assertEqual(daily_statement3.original_amount, original_amount)
        self.assertEqual(daily_statement3.payable_amount, payable_amount)


class ServerStatementTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.user2 = UserProfile(id='user2', username='username2')
        self.user2.save(force_insert=True)

        self.service = get_or_create_service()

        self.price = create_price()

        # 余额支付有关配置
        self.app = PayApp(name='app', id=PAY_APP_ID)
        self.app.save(force_insert=True)
        app_service1 = PayAppService(
            id='123', name='service1', app=self.app,
            orgnazition=self.service.org_data_center.organization, service_id=self.service.id
        )
        app_service1.save(force_insert=True)
        self.app_service1 = app_service1
        self.service.pay_app_service_id = app_service1.id
        self.service.save(update_fields=['pay_app_service_id'])

    def test_settlement(self):
        nt = dj_timezone.now()
        today = nt.date()
        server1 = create_server_metadata(
            service=self.service,
            user=self.user,
            vcpu=4,
            ram=4,
            disk_size=100,
            public_ip=True,
            start_time=nt,
            creation_time=nt,
            pay_type=PayType.PREPAID.value
        )
        server2 = create_server_metadata(
            service=self.service,
            user=self.user2,
            vcpu=8,
            ram=16,
            disk_size=100,
            public_ip=True,
            start_time=nt,
            creation_time=nt,
            pay_type=PayType.POSTPAID.value
        )

        coupon1 = CashCoupon(
            face_value=Decimal('66.6'),
            balance=Decimal('66.6'),
            effective_time=nt - timedelta(days=1),
            expiration_time=nt + timedelta(days=1),
            status=CashCoupon.Status.AVAILABLE.value,
            app_service_id=self.app_service1.id,
            user=self.user2, owner_type=OwnerType.USER.value
        )
        coupon1.save(force_insert=True)

        # order
        order_instance_config = ServerConfig(
            vm_cpu=2, vm_ram=2, systemdisk_size=100, public_ip=True,
            image_id='image_id', image_name='', network_id='network_id', network_name='',
            azone_id='azone_id', azone_name='azone_name', flavor_id=''
        )
        order, resource_list = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=self.service.pay_app_service_id,
            service_id=self.service.id,
            service_name='test',
            resource_type=ResourceType.VM.value,
            instance_config=order_instance_config,
            period=2,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.PREPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='', vo_name='',
            owner_type=OwnerType.USER.value
        )
        resource_list[0].instance_id = server1.id
        resource_list[0].save(update_fields=['instance_id'])
        subject = order.build_subject()
        order = OrderPaymentManager().pay_order(
            order=order, app_id=site_configs_manager.get_pay_app_id(settings), subject=subject,
            executor=self.user.username, remark='',
            coupon_ids=[], only_coupon=False,
            required_enough_balance=False
        )

        # metering
        metering1 = MeteringServer(
            original_amount=Decimal('1.11'),
            trade_amount=Decimal('1.11'),
            daily_statement_id='',
            service_id=self.service.id,
            server_id=server1.id,
            date=today,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
            pay_type=PayType.PREPAID.value
        )
        metering1.save(force_insert=True)
        metering2 = MeteringServer(
            original_amount=Decimal('2.22'),
            trade_amount=Decimal('2.11'),
            daily_statement_id='',
            service_id=self.service.id,
            server_id=server2.id,
            date=today,
            user_id=self.user2.id,
            username=self.user2.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
            pay_type=PayType.POSTPAID.value
        )
        metering2.save(force_insert=True)
        dss2 = DailyStatementServer(
            original_amount='2.22',
            payable_amount='2.22',
            trade_amount='2.22',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=today,
            user_id=self.user2.id,
            username=self.user2.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
        )
        dss2.save(force_insert=True)
        metering2.set_daily_statement_id(dss2.id)
        MeteringPaymentManager().pay_daily_statement_bill(
            daily_statement=dss2, app_id=PAY_APP_ID, subject='metering', executor='metering', remark='',
            required_enough_balance=True
        )

        base_url = reverse('metering-api:last-settlement-server-detail', kwargs={'server_id': 'tes6'})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user2)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 404)

        base_url = reverse('metering-api:last-settlement-server-detail', kwargs={'server_id': server1.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)

        self.client.logout()
        self.client.force_login(self.user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server', 'settlement'], response.data)
        self.assertKeysIn([
            "id", "name", "vcpus", "ram", "ram_gib", "ipv4",
            "public_ip", "image", "creation_time",
            "remarks", "service", 'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
            "center_quota", "classification", "vo_id", "user", 'vo',
            "image_id", "image_desc", "default_user", "default_password",
            "lock", "pay_type"], response.data['server'])
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['server']['service'])
        self.assertKeysIn(['order', 'payment'], response.data['settlement'])
        self.assertKeysIn([
            "id", "order_type", "status", "total_amount", "pay_amount",
            "service_id", "service_name", "resource_type", "instance_config",
            "period", "period_unit", "start_time", "end_time",
            "payment_time", "pay_type", "creation_time", "user_id", "username", 'number',
            "vo_id", "vo_name", "owner_type", "cancelled_time", "app_service_id", 'trading_status'
        ], response.data['settlement']['order'])
        self.assertIsNotNone(response.data['settlement']['payment'])
        self.assertKeysIn([
            "id", "payment_method", "executor", "payer_id", "payer_name",
            "payer_type", "amounts", "coupon_amount",
            "payment_time", "remark", "order_id", "subject", "app_service_id", "app_id",
            "status", 'status_desc', 'creation_time', 'payable_amounts'
        ], response.data['settlement']['payment'])
        self.assertIsInstance(response.data['settlement']['payment']['coupon_historys'], list)
        self.assertEqual(len(response.data['settlement']['payment']['coupon_historys']), 0)

        base_url = reverse('metering-api:last-settlement-server-detail', kwargs={'server_id': server2.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)

        response = self.client.get(f'{base_url}?as-admin=true')
        self.assertEqual(response.status_code, 403)
        self.service.users.add(self.user)

        response = self.client.get(f'{base_url}?as-admin=true')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server', 'settlement'], response.data)
        self.assertKeysIn([
            "id", "name", "vcpus", "ram", "ram_gib", "ipv4",
            "public_ip", "image", "creation_time",
            "remarks", "service", 'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
            "center_quota", "classification", "vo_id", "user", 'vo',
            "image_id", "image_desc", "default_user", "default_password",
            "lock", "pay_type"
        ], response.data['server'])
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['server']['service'])
        self.assertKeysIn(['metering', 'daily_statement', 'payment'], response.data['settlement'])
        self.assertKeysIn([
            "id", "original_amount", "trade_amount",
            "daily_statement_id", "service_id", "server_id", "date",
            "creation_time", "user_id", "vo_id", "owner_type",
            "cpu_hours", "ram_hours", "disk_hours", "public_ip_hours",
            "snapshot_hours", "upstream", "downstream", "pay_type",
            "username", "vo_name"
        ], response.data['settlement']['metering'])
        self.assertKeysIn([
            "id", "original_amount", "payable_amount", "trade_amount",
            "payment_status", "payment_history_id", "service", "date", "creation_time",
            "user_id", "username", "vo_id", "vo_name", "owner_type"
        ], response.data['settlement']['daily_statement'])
        self.assertIsNotNone(response.data['settlement']['payment'])
        self.assertKeysIn([
            "id", "payment_method", "executor", "payer_id", "payer_name",
            "payer_type", "amounts", "coupon_amount",
            "payment_time", "remark", "order_id", "subject", "app_service_id", "app_id",
            "status", 'status_desc', 'creation_time', 'payable_amounts'
        ], response.data['settlement']['payment'])
        self.assertIsInstance(response.data['settlement']['payment']['coupon_historys'], list)
        self.assertEqual(len(response.data['settlement']['payment']['coupon_historys']), 1)
        self.assertKeysIn([
            'cash_coupon_id', 'amounts', 'before_payment', 'after_payment', 'creation_time', 'cash_coupon'
        ], response.data['settlement']['payment']['coupon_historys'][0])
        self.assertKeysIn([
            "id", "face_value", "creation_time", "effective_time", "expiration_time",
            "balance", "status", "granted_time", "issuer",
            "owner_type", "app_service", "user", "vo", "activity", 'remark'
        ], response.data['settlement']['payment']['coupon_historys'][0]['cash_coupon'])
        self.assertKeysIn([
            "id", "name", "name_en", "service_id", "category"
        ], response.data['settlement']['payment']['coupon_historys'][0]['cash_coupon']['app_service'])
