from decimal import Decimal
from datetime import date, datetime, timedelta, time

from django.test import TransactionTestCase
from django.utils import timezone

from utils.test import get_or_create_user
from utils.decimal_utils import quantize_10_2
from utils.time import utc
from monitor.models import MonitorWebsite, MonitorWebsiteRecord, MonitorWebsiteBase
from order.models import Price
from metering.measurers import MonitorWebsiteMeasurer
from metering.models import MeteringMonitorWebsite, PaymentStatus, DailyStatementMonitorWebsite
from metering.generate_daily_statement import WebsiteMonitorStatementGenerater
from users.models import UserProfile


def create_website_metadata(
        name: str, scheme: str, hostname: str, uri: str, is_tamper_resistant: bool,
        user_id, creation_time, remark: str = ''
):
    site = MonitorWebsite(
        name=name, scheme=scheme, hostname=hostname, uri=uri, is_tamper_resistant=is_tamper_resistant,
        remark=remark, user_id=user_id, creation=creation_time, modification=creation_time
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


def up_int(val, base=100):
    return int(val * base)


class MeteringWebsiteTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.price = Price(
            vm_ram=Decimal('0.0'),
            vm_cpu=Decimal('0.0'),
            vm_disk=Decimal('0'),
            vm_pub_ip=Decimal('0'),
            vm_upstream=Decimal('0'),
            vm_downstream=Decimal('1'),
            vm_disk_snap=Decimal('0'),
            disk_size=Decimal('1.02'),
            disk_snap=Decimal('0.77'),
            obj_size=Decimal('0'),
            obj_upstream=Decimal('0'),
            obj_downstream=Decimal('0'),
            obj_replication=Decimal('0'),
            obj_get_request=Decimal('0'),
            obj_put_request=Decimal('0'),
            prepaid_discount=66,
            mntr_site_base=Decimal('0.3'),
            mntr_site_tamper=Decimal('0.2'),
            mntr_site_security=Decimal('0.5')
        )
        self.price.save()

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

        return site1, site2, site3, site4

    def do_assert_site(self, now: datetime, site1: MonitorWebsiteBase, site2: MonitorWebsiteBase):
        metering_date = (now - timedelta(days=1)).date()
        metering_end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)    # 计量结束时间
        measurer = MonitorWebsiteMeasurer(raise_exeption=True)
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

        MonitorWebsiteMeasurer(raise_exeption=True).run()
        count = MeteringMonitorWebsite.objects.all().count()
        if in_utc_0_1:
            self.assertEqual(count, 3)
        else:
            self.assertEqual(count, 2)

    def test_normal_disk(self):
        now = timezone.now()
        site1, site2, site3, site4 = self.init_data_only_normal_site(now)
        self.do_assert_site(now=now, site1=site1, site2=site2)

    def test_has_deleted_disk(self):
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
