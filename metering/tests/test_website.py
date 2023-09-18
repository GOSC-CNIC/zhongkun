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
from metering.models import MeteringMonitorWebsite


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
