from decimal import Decimal
from datetime import date, datetime, timedelta, time

from django.test import TransactionTestCase
from django.utils import timezone

from utils.test import get_or_create_user, get_or_create_organization
from utils.decimal_utils import quantize_10_2
from utils.time import utc
from utils.model import OwnerType
from apps.app_monitor.models import MonitorWebsite, MonitorWebsiteRecord, MonitorWebsiteBase, MonitorWebsiteVersion
from apps.app_order.tests import create_price
from apps.app_metering.measurers import MonitorWebsiteMeasurer
from apps.app_metering.models import MeteringMonitorWebsite, PaymentStatus, DailyStatementMonitorWebsite
from apps.app_metering.statement_generators import WebsiteMonitorStatementGenerater
from apps.app_metering.payment import MeteringPaymentManager
from apps.app_metering.pay_metering import PayMeteringWebsite
from apps.app_users.models import UserProfile
from apps.app_wallet.models import PayApp, PayAppService, PaymentHistory, CashCoupon
from core import errors
from apps.app_service.models import OrgDataCenter


def create_website_metadata(
        name: str, scheme: str, hostname: str, uri: str, is_tamper_resistant: bool,
        user_id, creation_time, remark: str = '', odc=None
):
    site = MonitorWebsite(
        name=name, scheme=scheme, hostname=hostname, uri=uri, is_tamper_resistant=is_tamper_resistant,
        remark=remark, user_id=user_id, creation=creation_time, modification=creation_time, odc=odc
    )
    site.save(force_insert=True)
    return site


def create_metering_site_metadata(
        site_id, site_name, date_,
        original_amount: Decimal, trade_amount: Decimal, daily_statement_id='',
        user_id='', username=''
):
    metering = MeteringMonitorWebsite(
        website_id=site_id,
        website_name=site_name,
        date=date_,
        hours=1,
        detection_count=0,
        tamper_resistant_count=1,
        security_count=0,
        user_id=user_id,
        username=username,
        creation_time=timezone.now(),
        original_amount=original_amount,
        trade_amount=trade_amount,
        daily_statement_id=daily_statement_id,
    )
    metering.save(force_insert=True)
    return metering


def create_site_statement_record(
        statement_date: date, original_amount, payable_amount,
        user_id: str = None, username: str = None, payment_status: str = None
):
    """
    创建日结算单记录
    """
    daily_statement = DailyStatementMonitorWebsite(
        date=statement_date,
        original_amount=original_amount,
        payable_amount=payable_amount,
        trade_amount=Decimal('0.00'),
        payment_status=payment_status if payment_status else PaymentStatus.UNPAID.value,
        payment_history_id='',
        user_id=user_id,
        username=username
    )

    try:
        daily_statement.save(force_insert=True)
    except Exception as e:
        raise e

    return daily_statement


def up_int(val, base=100):
    return int(val * base)


class MeteringWebsiteTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.price = create_price()

    def init_data_only_normal_site(self, now: datetime):
        ago_hour_time = now - timedelta(hours=1)    # utc时间00:00（北京时间08:00）之后的1hour之内，测试会通不过，site4会被计量
        meter_time = now - timedelta(days=1)
        ago_time = now - timedelta(days=2)

        # 计量24h
        site1 = create_website_metadata(
            name='site1',
            scheme='https://',
            hostname='127.0.0.1:8000',
            uri='/',
            user_id=self.user.id,
            creation_time=ago_time,
            is_tamper_resistant=False,
            remark='site1 remark'
        )
        # 计量 < 24h
        site2 = create_website_metadata(
            name='site2',
            scheme='https://',
            hostname='127.0.0.1:8888',
            uri='/2',
            user_id=self.user.id,
            creation_time=meter_time,
            is_tamper_resistant=True,
            remark='site2 remark'
        )

        # 不会计量
        site3 = create_website_metadata(
            name='site3',
            scheme='https://',
            hostname='baidu.com',
            uri='/a/b/c',
            user_id=self.user.id,
            creation_time=now,
            is_tamper_resistant=False,
            remark='site3 remark'
        )
        # utc时间00:00（北京时间08:00）之后的1hour之内，会被计量
        site4 = create_website_metadata(
            name='site4',
            scheme='https://',
            hostname='baidu.com',
            uri='/a/b/c',
            user_id=self.user.id,
            creation_time=ago_hour_time,
            is_tamper_resistant=True,
            remark='site4 remark'
        )
        # 24h，属于数据中心，不会计量
        odc = OrgDataCenter(name='odc1', name_en='odc en', organization=None)
        odc.save(force_insert=True)
        site5 = create_website_metadata(
            name='site5',
            scheme='https://',
            hostname='127.0.0.1:8000',
            uri='/',
            user_id=None,
            odc=odc,
            creation_time=ago_time,
            is_tamper_resistant=False,
            remark='site1 remark'
        )

        return site1, site2, site3, site4

    def do_assert_site(self, now: datetime, site1: MonitorWebsiteBase, site2: MonitorWebsiteBase):
        metering_date = (now - timedelta(days=1)).date()
        metering_end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)    # 计量结束时间
        measurer = MonitorWebsiteMeasurer(raise_exception=True)
        measurer.run()

        # utc时间00:00（北京时间08:00）之后的1hour之内，disk4会被计量
        utc_now = now.astimezone(utc)
        in_utc_0_1 = False
        if time(hour=0, minute=0, second=0) <= utc_now.time() <= time(hour=1, minute=0, second=0):
            in_utc_0_1 = True

        count = MeteringMonitorWebsite.objects.all().count()
        if in_utc_0_1:
            self.assertEqual(count, 3)
        else:
            self.assertEqual(count, 2)

        # site1
        metering = measurer.website_metering_exists(metering_date=metering_date, website_id=site1.id)
        self.assertIsNotNone(metering)
        self.assertEqual(up_int(metering.hours), up_int(24))
        self.assertEqual(metering.user_id, self.user.id)
        self.assertEqual(metering.username, self.user.username)

        original_amount1 = self.price.mntr_site_base
        trade_amount = original_amount1
        self.assertEqual(metering.original_amount, quantize_10_2(original_amount1))
        self.assertEqual(metering.trade_amount, trade_amount)

        # site2
        hours = (metering_end_time - site2.creation).total_seconds() / 3600
        metering = measurer.website_metering_exists(metering_date=metering_date, website_id=site2.id)
        self.assertIsNotNone(metering)
        self.assertEqual(up_int(metering.hours), up_int(hours))
        self.assertEqual(metering.user_id, self.user.id)
        self.assertEqual(metering.username, self.user.username)

        original_amount2 = (self.price.mntr_site_base + self.price.mntr_site_tamper) * Decimal.from_float(hours / 24)
        self.assertEqual(metering.original_amount, quantize_10_2(original_amount2))
        self.assertEqual(metering.trade_amount, quantize_10_2(original_amount2))

        MonitorWebsiteMeasurer(raise_exception=True).run()
        count = MeteringMonitorWebsite.objects.all().count()
        if in_utc_0_1:
            self.assertEqual(count, 3)
        else:
            self.assertEqual(count, 2)

    def test_normal_site(self):
        now = timezone.now()
        site1, site2, site3, site4 = self.init_data_only_normal_site(now)
        self.do_assert_site(now=now, site1=site1, site2=site2)

    def test_has_deleted_site(self):
        now = timezone.now()
        site1, site2, site3, site4 = self.init_data_only_normal_site(now)
        record1 = MonitorWebsiteRecord.create_record_for_website(site=site1)
        site1.delete()
        MonitorWebsiteRecord.create_record_for_website(site=site3)
        site3.delete()
        self.do_assert_site(now=now, site1=record1, site2=site2)


class WebsitetatementTests(TransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user()
        self.user2 = UserProfile(id='user2', username='username2')
        self.user2.save(force_insert=True)

    def init_data(self, st_date: date):
        # user1
        for idx in range(1, 6):  # 1-5
            create_metering_site_metadata(
                site_id=f'user1-site_id{idx}',
                site_name=f'site_name{idx}',
                date_=st_date,
                user_id=self.user1.id,
                username=self.user1.username,
                original_amount=Decimal.from_float(idx + 0.1),
                trade_amount=Decimal.from_float(idx + 0.11),
            )
        # x days ago
        for idx in range(6, 10):  # 6-9
            create_metering_site_metadata(
                site_id=f'user1-site_id{idx}',
                site_name=f'site_name{idx}',
                date_=st_date - timedelta(days=idx),
                user_id=self.user1.id,
                username=self.user1.username,
                original_amount=Decimal.from_float(idx + 0.1),
                trade_amount=Decimal.from_float(idx + 0.11),
            )
        # x days after
        for idx in range(5, 11):  # 5-10
            create_metering_site_metadata(
                site_id=f'user1-site_id{idx}',
                site_name=f'site_name{idx}',
                date_=st_date + timedelta(days=idx),
                user_id=self.user1.id,
                username=self.user1.username,
                original_amount=Decimal.from_float(idx + 0.1),
                trade_amount=Decimal.from_float(idx + 0.11),
            )

        # user2
        for idx in range(13, 15):  # 13-14
            create_metering_site_metadata(
                site_id=f'user2-site_id{idx}',
                site_name=f'site_name{idx}',
                date_=st_date,
                user_id=self.user2.id,
                username=self.user2.username,
                original_amount=Decimal.from_float(idx + 0.1),
                trade_amount=Decimal.from_float(idx + 0.11),
            )
        # x days ago
        for idx in range(10, 13):  # 10-12
            create_metering_site_metadata(
                site_id=f'user2-site_id{idx}',
                site_name=f'site_name{idx}',
                date_=st_date - timedelta(days=idx),
                user_id=self.user2.id,
                username=self.user2.username,
                original_amount=Decimal.from_float(idx + 0.1),
                trade_amount=Decimal.from_float(idx + 0.11),
            )

        # x days after
        for idx in range(1, 18):  # 1-17
            create_metering_site_metadata(
                site_id=f'user2-site_id{idx}',
                site_name=f'site_name{idx}',
                date_=st_date + timedelta(days=idx),
                user_id=self.user2.id,
                username=self.user2.username,
                original_amount=Decimal.from_float(idx + 0.1),
                trade_amount=Decimal.from_float(idx + 0.11),
            )

    def do_assert_a_user_daily_statement(
            self, range_a, range_b, user, meterings, st_date
    ):
        original_amount = 0
        payable_amount = 0
        for idx in range(range_a, range_b):
            original_amount += Decimal(str(int(idx) + 0.1))
            payable_amount += Decimal(str(int(idx) + 0.11))

        daily_statement = WebsiteMonitorStatementGenerater.user_site_statement_exists(
            statement_date=st_date, user_id=user.id)
        self.assertIsNotNone(daily_statement)
        self.assertEqual(daily_statement.date, st_date)
        self.assertEqual(daily_statement.user_id, user.id)
        self.assertEqual(daily_statement.username, user.username)
        self.assertEqual(daily_statement.original_amount, original_amount)
        self.assertEqual(daily_statement.payable_amount, payable_amount)
        self.assertEqual(daily_statement.trade_amount, Decimal(0))
        self.assertEqual(daily_statement.payment_status, PaymentStatus.UNPAID.value)
        self.assertEqual(daily_statement.payment_history_id, '')

        cnt = 0
        for m in meterings:
            m: MeteringMonitorWebsite
            if (
                    m.user_id == user.id and m.date == st_date
            ):
                cnt += 1
                self.assertEqual(m.daily_statement_id, daily_statement.id)
            else:
                self.assertNotEqual(m.daily_statement_id, daily_statement.id)

        self.assertEqual(cnt, range_b - range_a)

    def test_daily_statement(self):
        st_date = date(year=2023, month=9, day=18)
        self.init_data(st_date=st_date)

        generate_daily_statement = WebsiteMonitorStatementGenerater(statement_date=st_date, raise_exception=True)
        generate_daily_statement.run()

        count = DailyStatementMonitorWebsite.objects.count()
        self.assertEqual(count, 2)

        meterings = MeteringMonitorWebsite.objects.all()

        # user1
        self.do_assert_a_user_daily_statement(
            range_a=1, range_b=6, user=self.user1, meterings=meterings, st_date=st_date
        )
        # user2
        self.do_assert_a_user_daily_statement(
            range_a=13, range_b=15, user=self.user2, meterings=meterings, st_date=st_date
        )

        # 追加数据后，二次运行
        create_metering_site_metadata(
            site_id='user1-site_id',
            site_name='site_name',
            date_=st_date,
            user_id=self.user1.id,
            username=self.user1.username,
            original_amount=Decimal('0.1'),
            trade_amount=Decimal('0.11'),
        )

        WebsiteMonitorStatementGenerater(statement_date=st_date, raise_exception=True).run()

        # 结算单数量不变，金额增加
        count = DailyStatementMonitorWebsite.objects.all().count()
        self.assertEqual(count, 2)

        meterings = MeteringMonitorWebsite.objects.all()
        self.do_assert_a_user_daily_statement(
            range_a=0, range_b=6, user=self.user1, meterings=meterings, st_date=st_date
        )


class MeteringPaymentManagerTests(TransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user()
        self.user2 = UserProfile(id='user2id', username='username2')
        self.user2.save(force_insert=True)

        # 余额支付有关配置
        app = PayApp(name='app')
        app.save()
        self.app = app
        po = get_or_create_organization(name='机构')
        po.save()
        self.app_service1 = PayAppService(
            name='website monitor', app=app, orgnazition=po
        )
        self.app_service1.save()
        self.app_service2 = PayAppService(
            name='website monitor2', app=app, orgnazition=po
        )
        self.app_service2.save()

        self.site_version_ins = MonitorWebsiteVersion.get_instance()
        self.site_version_ins.pay_app_service_id = self.app_service1.id
        self.site_version_ins.save(update_fields=['pay_app_service_id'])

    def test_pay_user_statement(self):
        pay_mgr = MeteringPaymentManager()
        payer_name = self.user1.username

        app_id = self.app.id
        # pay bill, invalid user id
        s_bill1 = create_site_statement_record(
            statement_date=timezone.now().date(),
            original_amount=Decimal('123.45'),
            payable_amount=Decimal('123.45'),
            user_id='user_id', username=payer_name
        )
        with self.assertRaises(errors.Error):
            pay_mgr.pay_daily_statement_bill(
                daily_statement=s_bill1, app_id=app_id, subject='站点监控计费',
                executor=self.user1.username, remark='')

        # pay bill, pay_type POSTPAID, when no enough balance
        s_bill1.user_id = self.user1.id
        s_bill1.save(update_fields=['user_id'])
        with self.assertRaises(errors.BalanceNotEnough):
            pay_mgr.pay_daily_statement_bill(
                daily_statement=s_bill1, app_id=app_id, subject='站点监控计费',
                executor=self.user1.username, remark='', required_enough_balance=True
            )

        # pay bill
        pay_mgr.pay_daily_statement_bill(
            daily_statement=s_bill1, app_id=app_id, subject='站点监控计费',
            executor='metering', remark='', required_enough_balance=False
        )
        user1_pointaccount = self.user1.userpointaccount
        user1_pointaccount.refresh_from_db()
        user_balance = user1_pointaccount.balance
        self.assertEqual(user_balance, Decimal('-123.45'))
        s_bill1.refresh_from_db()
        self.assertEqual(s_bill1.original_amount, Decimal('123.45'))
        self.assertEqual(s_bill1.trade_amount, Decimal('123.45'))
        self.assertEqual(s_bill1.payment_status, PaymentStatus.PAID.value)
        pay_history_id = s_bill1.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history.payable_amounts, Decimal('123.45'))
        self.assertEqual(pay_history.amounts, Decimal('-123.45'))
        self.assertEqual(pay_history.coupon_amount, Decimal('0'))
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.app_service_id, self.site_version_ins.pay_app_service_id)
        self.assertEqual(pay_history.instance_id, '')
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user1.id)
        self.assertEqual(pay_history.executor, 'metering')
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, user1_pointaccount.id)

        # pay bill
        s_bill2 = create_site_statement_record(
            statement_date=(timezone.now() - timedelta(days=1)).date(),
            original_amount=Decimal('223.45'),
            payable_amount=Decimal('0'),
            user_id=self.user1.id, username=payer_name
        )
        pay_mgr.pay_daily_statement_bill(
            daily_statement=s_bill2, app_id=app_id, subject='站点监控计费',
            executor=self.user1.username, remark='', required_enough_balance=False
        )
        s_bill2.refresh_from_db()
        user1_pointaccount.refresh_from_db()
        self.assertEqual(user1_pointaccount.balance, user_balance)
        self.assertEqual(s_bill2.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(s_bill2.original_amount, Decimal('223.45'))
        self.assertEqual(s_bill2.payable_amount, Decimal(0))
        self.assertEqual(s_bill2.trade_amount, Decimal(0))
        self.assertEqual(s_bill2.payment_history_id, '')

        # pay bill, user1
        s_bill3 = create_site_statement_record(
            statement_date=(timezone.now() - timedelta(days=2)).date(),
            original_amount=Decimal('66.88'),
            payable_amount=Decimal('66.88'),
            user_id=self.user1.id, username=self.user1.username
        )
        pay_mgr.pay_daily_statement_bill(
            daily_statement=s_bill3, app_id=app_id, subject='站点监控计费',
            executor='meter', remark='', required_enough_balance=False
        )
        user1_pointaccount.refresh_from_db()
        user_balance = user1_pointaccount.balance
        self.assertEqual(user_balance, Decimal('-123.45') - Decimal('66.88'))
        s_bill3.refresh_from_db()
        self.assertEqual(s_bill3.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(s_bill3.original_amount, Decimal('66.88'))
        self.assertEqual(s_bill3.trade_amount, Decimal('66.88'))

        pay_history_id = s_bill3.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.amounts, Decimal('-66.88'))
        self.assertEqual(pay_history.coupon_amount, Decimal('0'))
        self.assertEqual(pay_history.executor, 'meter')
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user1.id)
        self.assertEqual(pay_history.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history.payable_amounts, Decimal('66.88'))
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE.value)
        self.assertEqual(pay_history.payment_account, user1_pointaccount.id)
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.app_service_id, self.site_version_ins.pay_app_service_id)
        self.assertEqual(pay_history.instance_id, '')

        # ------- test coupon --------
        now_time = timezone.now()
        # 有效
        coupon1_user1 = CashCoupon(
            face_value=Decimal('20'),
            balance=Decimal('20'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.site_version_ins.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user1.id, vo_id=None
        )
        coupon1_user1.save(force_insert=True)

        # 有效，只适用于app_service2
        coupon2_user1 = CashCoupon(
            face_value=Decimal('33'),
            balance=Decimal('33'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.app_service2.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user1.id, vo_id=None
        )
        coupon2_user1.save(force_insert=True)

        # 有效, user2
        coupon3_u2 = CashCoupon(
            face_value=Decimal('50'),
            balance=Decimal('50'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.site_version_ins.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user2.id, vo_id=None
        )
        coupon3_u2.save(force_insert=True)

        # pay bill
        s_bill4 = create_site_statement_record(
            statement_date=(timezone.now() - timedelta(days=2)).date(),
            original_amount=Decimal('88.8'),
            payable_amount=Decimal('88.8'),
            user_id=self.user1.id, username=self.user1.username
        )

        user1_pointaccount.refresh_from_db()
        user_balance = user1_pointaccount.balance
        self.assertEqual(user_balance, Decimal('-190.33'))
        pay_mgr.pay_daily_statement_bill(
            daily_statement=s_bill4, app_id=app_id, subject='站点监控计费',
            executor=self.user1.username, remark='', required_enough_balance=False
        )
        user1_pointaccount.refresh_from_db()
        user_balance = user1_pointaccount.balance
        self.assertEqual(user_balance, Decimal('-190.33') - Decimal('88.8') + Decimal('20'))  # coupon 20
        s_bill4.refresh_from_db()
        self.assertEqual(s_bill4.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(s_bill4.original_amount, Decimal('88.8'))
        self.assertEqual(s_bill4.trade_amount, Decimal('88.8'))

        pay_history_id = s_bill4.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.amounts, Decimal('-68.8'))
        self.assertEqual(pay_history.coupon_amount, Decimal('-20'))
        self.assertEqual(pay_history.executor, self.user1.username)
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user1.id)
        self.assertEqual(pay_history.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history.payable_amounts, Decimal('88.8'))
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE_COUPON.value)
        self.assertEqual(pay_history.payment_account, user1_pointaccount.id)
        self.assertEqual(pay_history.payer_name, payer_name)
        self.assertEqual(pay_history.app_service_id, self.site_version_ins.pay_app_service_id)
        self.assertEqual(pay_history.instance_id, '')

        # pay bill, user2
        s_bill5 = create_site_statement_record(
            statement_date=(timezone.now() - timedelta(days=2)).date(),
            original_amount=Decimal('66.88'),
            payable_amount=Decimal('66.88'),
            user_id=self.user2.id, username=self.user2.username
        )
        pay_mgr.pay_daily_statement_bill(
            daily_statement=s_bill5, app_id=app_id, subject='站点监控计费',
            executor='meter2', remark='', required_enough_balance=False
        )
        user2_pointaccount = self.user2.userpointaccount
        user2_pointaccount.refresh_from_db()
        user2_balance = user2_pointaccount.balance
        self.assertEqual(user2_balance, Decimal('50') - Decimal('66.88'))
        s_bill5.refresh_from_db()
        self.assertEqual(s_bill5.payment_status, PaymentStatus.PAID.value)
        self.assertEqual(s_bill5.original_amount, Decimal('66.88'))
        self.assertEqual(s_bill5.trade_amount, Decimal('66.88'))

        pay_history_id = s_bill5.payment_history_id
        pay_history = PaymentHistory.objects.get(id=pay_history_id)
        pay_history.refresh_from_db()
        self.assertEqual(pay_history.amounts, Decimal('-16.88'))
        self.assertEqual(pay_history.coupon_amount, Decimal('-50'))
        self.assertEqual(pay_history.executor, 'meter2')
        self.assertEqual(pay_history.payer_type, OwnerType.USER.value)
        self.assertEqual(pay_history.payer_id, self.user2.id)
        self.assertEqual(pay_history.status, PaymentHistory.Status.SUCCESS.value)
        self.assertEqual(pay_history.payable_amounts, Decimal('66.88'))
        self.assertEqual(pay_history.payment_method, PaymentHistory.PaymentMethod.BALANCE_COUPON.value)
        self.assertEqual(pay_history.payment_account, user2_pointaccount.id)
        self.assertEqual(pay_history.payer_name, self.user2.username)
        self.assertEqual(pay_history.app_service_id, self.site_version_ins.pay_app_service_id)
        self.assertEqual(pay_history.instance_id, '')

    def test_script_pay(self):
        app_id = self.app.id
        mgr = PayMeteringWebsite(app_id=app_id)
        mgr.run()
        self.assertEqual(mgr.count, 0)
        self.assertEqual(mgr.success_count, 0)
        self.assertEqual(mgr.failed_count, 0)
        count = PaymentHistory.objects.count()
        self.assertEqual(count, 0)

        # user1
        s_bill1 = create_site_statement_record(
            statement_date=timezone.now().date(),
            original_amount=Decimal('123.45'),
            payable_amount=Decimal('123.45'),
            user_id=self.user1.id, username=self.user1.username
        )
        s_bill2 = create_site_statement_record(
            statement_date=(timezone.now() - timedelta(days=1)).date(),
            original_amount=Decimal('223.45'),
            payable_amount=Decimal('0'),
            user_id=self.user1.id, username=self.user1.username
        )
        s_bill3 = create_site_statement_record(
            statement_date=(timezone.now() - timedelta(days=2)).date(),
            original_amount=Decimal('66.88'),
            payable_amount=Decimal('66.88'),
            user_id=self.user1.id, username=self.user1.username
        )
        s_bill4 = create_site_statement_record(
            statement_date=(timezone.now() - timedelta(days=2)).date(),
            original_amount=Decimal('88.8'),
            payable_amount=Decimal('88.8'),
            user_id=self.user1.id, username=self.user1.username
        )

        # user2
        s_bill5 = create_site_statement_record(
            statement_date=timezone.now().date(),
            original_amount=Decimal('66.88'),
            payable_amount=Decimal('66.88'),
            user_id=self.user2.id, username=self.user2.username
        )

        now_time = timezone.now()
        # 有效
        coupon1_user1 = CashCoupon(
            face_value=Decimal('20'),
            balance=Decimal('20'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.site_version_ins.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user1.id, vo_id=None
        )
        coupon1_user1.save(force_insert=True)

        # 有效，只适用于app_service2
        coupon2_user1 = CashCoupon(
            face_value=Decimal('33'),
            balance=Decimal('33'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.app_service2.id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user1.id, vo_id=None
        )
        coupon2_user1.save(force_insert=True)

        # 有效, user2
        coupon3_u2 = CashCoupon(
            face_value=Decimal('50'),
            balance=Decimal('50'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.site_version_ins.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user2.id, vo_id=None
        )
        coupon3_u2.save(force_insert=True)

        # bill 1、5 only pay
        mgr = PayMeteringWebsite(app_id=app_id, pay_date=now_time.date())
        mgr.run()
        self.assertEqual(mgr.count, 2)
        self.assertEqual(mgr.success_count, 2)
        self.assertEqual(mgr.failed_count, 0)
        count = PaymentHistory.objects.count()
        self.assertEqual(count, 2)

        user1_pointaccount = self.user1.userpointaccount
        user1_pointaccount.refresh_from_db()
        self.assertEqual(user1_pointaccount.balance, Decimal('20') - Decimal('123.45'))
        s_bill1.refresh_from_db()
        self.assertEqual(s_bill1.original_amount, Decimal('123.45'))
        self.assertEqual(s_bill1.trade_amount, Decimal('123.45'))
        self.assertEqual(s_bill1.payment_status, PaymentStatus.PAID.value)

        user2_pointaccount = self.user2.userpointaccount
        user2_pointaccount.refresh_from_db()
        self.assertEqual(user2_pointaccount.balance, Decimal('50') - Decimal('66.88'))
        s_bill5.refresh_from_db()
        self.assertEqual(s_bill5.original_amount, Decimal('66.88'))
        self.assertEqual(s_bill5.trade_amount, Decimal('66.88'))
        self.assertEqual(s_bill5.payment_status, PaymentStatus.PAID.value)

        # bill 2\3\4 only pay
        mgr = PayMeteringWebsite(app_id=app_id, pay_date=None)
        mgr.run()
        self.assertEqual(mgr.count, 3)
        self.assertEqual(mgr.success_count, 3)
        self.assertEqual(mgr.failed_count, 0)
        count = PaymentHistory.objects.count()
        self.assertEqual(count, 2 + 2)  # bill2不扣费不产生支付记录

        user1_pointaccount.refresh_from_db()
        self.assertEqual(user1_pointaccount.balance,
                         Decimal('20') - Decimal('123.45') - Decimal('66.88') - Decimal('88.8'))

        s_bill2.refresh_from_db()
        self.assertEqual(s_bill2.original_amount, Decimal('223.45'))
        self.assertEqual(s_bill2.trade_amount, Decimal('0'))
        self.assertEqual(s_bill2.payment_status, PaymentStatus.PAID.value)
        s_bill3.refresh_from_db()
        self.assertEqual(s_bill3.original_amount, Decimal('66.88'))
        self.assertEqual(s_bill3.trade_amount, Decimal('66.88'))
        self.assertEqual(s_bill3.payment_status, PaymentStatus.PAID.value)
        s_bill4.refresh_from_db()
        self.assertEqual(s_bill4.original_amount, Decimal('88.8'))
        self.assertEqual(s_bill4.trade_amount, Decimal('88.8'))
        self.assertEqual(s_bill4.payment_status, PaymentStatus.PAID.value)

        user2_pointaccount.refresh_from_db()
        self.assertEqual(user2_pointaccount.balance, Decimal('50') - Decimal('66.88'))
