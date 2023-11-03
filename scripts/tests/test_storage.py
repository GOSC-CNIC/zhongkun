import datetime
from decimal import Decimal

from django.utils import timezone
from django.test.testcases import TransactionTestCase

from utils.test import get_or_create_user, get_or_create_org_data_center
from utils.time import utc
from storage.models import ObjectsService, Bucket, BucketArchive
from metering.models import MeteringObjectStorage
from report.models import BucketStatsMonthly
from scripts.workers.storage_trend import (
    StorageSizeCounter, get_report_period_start_and_end,
)


class BucketStatsMonthlyTests(TransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='lilei@cnic.cn')
        self.user2 = get_or_create_user(username='tom@qq.com')

        self.period_start, self.period_end = get_report_period_start_and_end()
        self.period_date = datetime.date(
            year=self.period_end.year, month=self.period_end.month, day=1)
        self.period_start_time = datetime.datetime.combine(
            date=self.period_start,
            time=datetime.time(hour=0, minute=0, second=0, microsecond=0, tzinfo=utc))
        self.period_end_time = datetime.datetime.combine(
            date=self.period_end,
            time=datetime.time(hour=23, minute=59, second=59, microsecond=999999, tzinfo=utc))

    def init_bucket_data(self):
        odc = get_or_create_org_data_center()
        service1 = ObjectsService(
            name='service1', org_data_center_id=odc.id,
            endpoint_url='service1', username='', password=''
        )
        service1.save(force_insert=True)
        service2 = ObjectsService(
            name='service2', org_data_center_id=odc.id,
            endpoint_url='service2', username='', password=''
        )
        service2.save(force_insert=True)

        # 本周期前一个周期创建的
        u1_b1 = Bucket(name='bucket1', service_id=service1.id, user_id=self.user1.id,
                       creation_time=self.period_start_time - datetime.timedelta(days=20),
                       storage_size=1000, object_count=10)
        u1_b1.save(force_insert=True)
        u1_b2 = Bucket(name='bucket2', service_id=service1.id, user_id=self.user1.id,
                       creation_time=self.period_start_time - datetime.timedelta(days=10),
                       storage_size=2000, object_count=20)
        u1_b2.save(force_insert=True)
        # 本周期内
        u1_b3 = Bucket(name='bucket3', service_id=service2.id, user_id=self.user1.id,
                       creation_time=self.period_start_time + datetime.timedelta(days=10),
                       storage_size=3000, object_count=30)
        u1_b3.save(force_insert=True)
        u2_b4 = Bucket(name='bucket4', service_id=service1.id, user_id=self.user2.id,
                       creation_time=self.period_start_time + datetime.timedelta(days=20),
                       storage_size=4000, object_count=40)
        # 本周期后创建
        u2_b4.save(force_insert=True)
        u2_b5 = Bucket(name='bucket5', service_id=service1.id, user_id=self.user2.id,
                       creation_time=timezone.now(), storage_size=0, object_count=0)
        u2_b5.save(force_insert=True)

        return u1_b1, u1_b2, u1_b3, u2_b4, u2_b5

    @staticmethod
    def create_bucket_metering(_date, service_id, bucket_id: str, user, length: int):
        # 0,1 not in;  2,3,4,5,... in last month, when length < 28
        for i in range(length):
            ms = MeteringObjectStorage(
                storage=i,
                trade_amount=Decimal(f'{i}'),
                original_amount=Decimal(f'{2 * i}'),
                daily_statement_id='',
                service_id=service_id,
                storage_bucket_id=bucket_id,
                user_id=user.id,
                username=user.username,
                date=_date + datetime.timedelta(days=i - 2)
            )

            ms.save(force_insert=True)

    def init_bucket_meterings(self, period_start: datetime.date, u1_b1, u1_b2, u1_b3, u2_b4, u2_b5):
        # u1_b1, 2,3,4,5
        self.create_bucket_metering(
            _date=period_start, service_id=u1_b1.service_id, bucket_id=u1_b1.id, user=u1_b1.user, length=6)
        # u1_b2, 2,3,4,5,6
        self.create_bucket_metering(
            _date=period_start, service_id=u1_b2.service_id, bucket_id=u1_b2.id, user=u1_b2.user, length=7)
        # u1_b3, 2,3,4,5,6,7
        self.create_bucket_metering(
            _date=period_start, service_id=u1_b3.service_id, bucket_id=u1_b3.id, user=u1_b3.user, length=8)

        # u2_b4, 2,3,4,5,6,7,8
        self.create_bucket_metering(
            _date=period_start, service_id=u2_b4.service_id, bucket_id=u2_b4.id, user=u2_b4.user, length=9)

        # u2_b5, 2,3,4,5,6,7,8, 9
        self.create_bucket_metering(
            _date=period_start, service_id=u2_b5.service_id, bucket_id=u2_b5.id, user=u2_b5.user, length=10)

    def _do_assert_current_period(self, ssc: StorageSizeCounter, b1_id, b2_id, b3_id, b4_id, b5_id):
        self.assertEqual(4, BucketStatsMonthly.objects.count())
        b1_ins = ssc.get_bucket_stats_ins(bucket_id=b1_id, _date=self.period_date)
        self.assertEqual(b1_ins.size_byte, 1000)
        self.assertEqual(b1_ins.increment_byte, 0)
        self.assertEqual(b1_ins.object_count, 10)
        self.assertEqual(b1_ins.date.day, 1)
        self.assertEqual(b1_ins.original_amount, Decimal.from_float((2 + 3 + 4 + 5) * 2))
        self.assertEqual(b1_ins.increment_amount, Decimal.from_float((2 + 3 + 4 + 5) * 2))

        b2_ins = ssc.get_bucket_stats_ins(bucket_id=b2_id, _date=self.period_date)
        self.assertEqual(b2_ins.size_byte, 2000)
        self.assertEqual(b2_ins.increment_byte, 0)
        self.assertEqual(b2_ins.object_count, 20)
        self.assertEqual(b2_ins.original_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6) * 2))
        self.assertEqual(b2_ins.increment_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6) * 2))

        b3_ins = ssc.get_bucket_stats_ins(bucket_id=b3_id, _date=self.period_date)
        self.assertEqual(b3_ins.size_byte, 3000)
        self.assertEqual(b3_ins.increment_byte, 3000)
        self.assertEqual(b3_ins.object_count, 30)
        self.assertEqual(b3_ins.original_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7) * 2))
        self.assertEqual(b3_ins.increment_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7) * 2))

        b4_ins = ssc.get_bucket_stats_ins(bucket_id=b4_id, _date=self.period_date)
        self.assertEqual(b4_ins.size_byte, 4000)
        self.assertEqual(b4_ins.increment_byte, 4000)
        self.assertEqual(b4_ins.object_count, 40)
        self.assertEqual(b4_ins.original_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7 + 8) * 2))
        self.assertEqual(b4_ins.increment_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7 + 8) * 2))

        b5_ins = ssc.get_bucket_stats_ins(bucket_id=b5_id, _date=self.period_date)
        self.assertIsNone(b5_ins)

    def test_no_deleted(self):
        """
        测试没有删除的桶
        """
        # ----- init data ----
        u1_b1, u1_b2, u1_b3, u2_b4, u2_b5 = self.init_bucket_data()
        self.init_bucket_meterings(
            period_start=self.period_start, u1_b1=u1_b1, u1_b2=u1_b2, u1_b3=u1_b3, u2_b4=u2_b4, u2_b5=u2_b5)

        ssc = StorageSizeCounter()
        ssc.run()
        self.assertEqual(self.period_date.day, 1)
        self._do_assert_current_period(
            ssc=ssc, b1_id=u1_b1.id, b2_id=u1_b2.id, b3_id=u1_b3.id, b4_id=u2_b4.id, b5_id=u2_b5.id)

        u1_b1.object_count = 16
        u1_b1.storage_size = 1600
        u1_b1.save(update_fields=['object_count', 'storage_size'])

        u1_b2.object_count = 18
        u1_b2.storage_size = 1800
        u1_b2.save(update_fields=['object_count', 'storage_size'])

        u1_b3.object_count = 36
        u1_b3.storage_size = 3600
        u1_b3.save(update_fields=['object_count', 'storage_size'])

        u2_b4.object_count = 45
        u2_b4.storage_size = 4500
        u2_b4.save(update_fields=['object_count', 'storage_size'])

        u2_b5.object_count = 51
        u2_b5.storage_size = 5100
        u2_b5.save(update_fields=['object_count', 'storage_size'])

        next_period = ssc.period_end + datetime.timedelta(days=32)
        ssc = StorageSizeCounter(target_date=next_period)
        ok = ssc.run()
        self.assertFalse(ok)

        ssc.run(check_time=False)
        next_period_date = ssc.period_date
        self.assertEqual(9, BucketStatsMonthly.objects.count())
        b1_ins = ssc.get_bucket_stats_ins(bucket_id=u1_b1.id, _date=next_period_date)
        self.assertEqual(b1_ins.size_byte, 1600)
        self.assertEqual(b1_ins.increment_byte, 600)
        self.assertEqual(b1_ins.object_count, 16)
        self.assertEqual(b1_ins.date.day, 1)
        self.assertEqual(b1_ins.original_amount, Decimal('0.00'))
        self.assertEqual(b1_ins.increment_amount, -Decimal.from_float((2 + 3 + 4 + 5) * 2))

        b2_ins = ssc.get_bucket_stats_ins(bucket_id=u1_b2.id, _date=next_period_date)
        self.assertEqual(b2_ins.size_byte, 1800)
        self.assertEqual(b2_ins.increment_byte, -200)
        self.assertEqual(b2_ins.object_count, 18)
        self.assertEqual(b2_ins.original_amount, Decimal('0.00'))
        self.assertEqual(b2_ins.increment_amount, -Decimal.from_float((2 + 3 + 4 + 5 + 6) * 2))

        b3_ins = ssc.get_bucket_stats_ins(bucket_id=u1_b3.id, _date=next_period_date)
        self.assertEqual(b3_ins.size_byte, 3600)
        self.assertEqual(b3_ins.increment_byte, 600)
        self.assertEqual(b3_ins.object_count, 36)
        self.assertEqual(b3_ins.original_amount, Decimal('0.00'))
        self.assertEqual(b3_ins.increment_amount, -Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7) * 2))

        b4_ins = ssc.get_bucket_stats_ins(bucket_id=u2_b4.id, _date=next_period_date)
        self.assertEqual(b4_ins.size_byte, 4500)
        self.assertEqual(b4_ins.increment_byte, 500)
        self.assertEqual(b4_ins.object_count, 45)
        self.assertEqual(b4_ins.original_amount, Decimal('0.00'))
        self.assertEqual(b4_ins.increment_amount, -Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7 + 8) * 2))

        b5_ins = ssc.get_bucket_stats_ins(bucket_id=u2_b5.id, _date=next_period_date)
        self.assertEqual(b5_ins.size_byte, 5100)
        self.assertEqual(b5_ins.increment_byte, 5100)
        self.assertEqual(b5_ins.object_count, 51)
        self.assertEqual(b5_ins.original_amount, Decimal('0.00'))
        self.assertEqual(b5_ins.increment_amount, Decimal('0.00'))

    def test_has_deleted(self):
        """
        测试有删除的桶
        """
        # ----- init data ----
        u1_b1, u1_b2, u1_b3, u2_b4, u2_b5 = self.init_bucket_data()
        self.init_bucket_meterings(
            period_start=self.period_start, u1_b1=u1_b1, u1_b2=u1_b2, u1_b3=u1_b3, u2_b4=u2_b4, u2_b5=u2_b5)

        # 本周期前创建 本周期内删除
        u1_b2_id = u1_b2.id
        ok = u1_b2.do_archive(archiver='test')
        self.assertIs(ok, True)
        u1_ba2 = BucketArchive.objects.get(original_id=u1_b2_id)
        u1_ba2.delete_time = self.period_start_time + datetime.timedelta(days=10)
        u1_ba2.save(update_fields=['delete_time'])

        # 本周期内创建 本周期内删除
        u1_b3_id = u1_b3.id
        ok = u1_b3.do_archive(archiver='test')
        self.assertIs(ok, True)
        u1_ba3 = BucketArchive.objects.get(original_id=u1_b3_id)
        u1_ba3.delete_time = self.period_start_time + datetime.timedelta(days=25)
        u1_ba3.save(update_fields=['delete_time'])

        # 下周期创建，当前删除
        u2_b5_id = u2_b5.id
        ok = u2_b5.do_archive(archiver='test')
        self.assertIs(ok, True)
        u2_ba5 = BucketArchive.objects.get(original_id=u2_b5_id)

        ssc = StorageSizeCounter()
        ssc.run()
        self.assertEqual(self.period_date.day, 1)
        self.assertEqual(4, BucketStatsMonthly.objects.count())
        b1_ins = ssc.get_bucket_stats_ins(bucket_id=u1_b1.id, _date=self.period_date)
        self.assertEqual(b1_ins.size_byte, 1000)
        self.assertEqual(b1_ins.increment_byte, 0)
        self.assertEqual(b1_ins.object_count, 10)
        self.assertEqual(b1_ins.date.day, 1)
        self.assertEqual(b1_ins.original_amount, Decimal.from_float((2 + 3 + 4 + 5) * 2))
        self.assertEqual(b1_ins.increment_amount, Decimal.from_float((2 + 3 + 4 + 5) * 2))

        b2_ins = ssc.get_bucket_stats_ins(bucket_id=u1_ba2.original_id, _date=self.period_date)
        self.assertEqual(b2_ins.size_byte, 0)
        self.assertEqual(b2_ins.increment_byte, -2000)
        self.assertEqual(b2_ins.object_count, 0)
        self.assertEqual(b2_ins.original_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6) * 2))
        self.assertEqual(b2_ins.increment_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6) * 2))

        b3_ins = ssc.get_bucket_stats_ins(bucket_id=u1_ba3.original_id, _date=self.period_date)
        self.assertEqual(b3_ins.size_byte, 0)
        self.assertEqual(b3_ins.increment_byte, 0)
        self.assertEqual(b3_ins.object_count, 0)
        self.assertEqual(b3_ins.original_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7) * 2))
        self.assertEqual(b3_ins.increment_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7) * 2))

        b4_ins = ssc.get_bucket_stats_ins(bucket_id=u2_b4.id, _date=self.period_date)
        self.assertEqual(b4_ins.size_byte, 4000)
        self.assertEqual(b4_ins.increment_byte, 4000)
        self.assertEqual(b4_ins.object_count, 40)
        self.assertEqual(b4_ins.original_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7 + 8) * 2))
        self.assertEqual(b4_ins.increment_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7 + 8) * 2))

        b5_ins = ssc.get_bucket_stats_ins(bucket_id=u2_ba5.original_id, _date=self.period_date)
        self.assertIsNone(b5_ins)

        u1_b1.object_count = 16
        u1_b1.storage_size = 1600
        u1_b1.save(update_fields=['object_count', 'storage_size'])

        u1_ba2.object_count = 18
        u1_ba2.storage_size = 1800
        u1_ba2.save(update_fields=['object_count', 'storage_size'])

        u2_b4.object_count = 45
        u2_b4.storage_size = 4500
        u2_b4.save(update_fields=['object_count', 'storage_size'])

        u2_ba5.object_count = 51
        u2_ba5.storage_size = 5100
        u2_ba5.save(update_fields=['object_count', 'storage_size'])

        next_period = ssc.period_end + datetime.timedelta(days=32)
        ssc = StorageSizeCounter(target_date=next_period)
        ssc.run(check_time=False)
        next_period_date = ssc.period_date
        self.assertEqual(4 + 3, BucketStatsMonthly.objects.count())
        b1_ins = ssc.get_bucket_stats_ins(bucket_id=u1_b1.id, _date=next_period_date)
        self.assertEqual(b1_ins.size_byte, 1600)
        self.assertEqual(b1_ins.increment_byte, 600)
        self.assertEqual(b1_ins.object_count, 16)
        self.assertEqual(b1_ins.date.day, 1)
        self.assertEqual(b1_ins.original_amount, Decimal('0.00'))
        self.assertEqual(b1_ins.increment_amount, -Decimal.from_float((2 + 3 + 4 + 5) * 2))

        b2_ins = ssc.get_bucket_stats_ins(bucket_id=u1_ba2.original_id, _date=next_period_date)
        self.assertIsNone(b2_ins)

        b3_ins = ssc.get_bucket_stats_ins(bucket_id=u1_ba3.original_id, _date=next_period_date)
        self.assertIsNone(b3_ins)

        b4_ins = ssc.get_bucket_stats_ins(bucket_id=u2_b4.id, _date=next_period_date)
        self.assertEqual(b4_ins.size_byte, 4500)
        self.assertEqual(b4_ins.increment_byte, 500)
        self.assertEqual(b4_ins.object_count, 45)
        self.assertEqual(b4_ins.original_amount, Decimal('0.00'))
        self.assertEqual(b4_ins.increment_amount, -Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7 + 8) * 2))

        b5_ins = ssc.get_bucket_stats_ins(bucket_id=u2_ba5.original_id, _date=next_period_date)
        self.assertEqual(b5_ins.size_byte, 0)
        self.assertEqual(b5_ins.increment_byte, 0)
        self.assertEqual(b5_ins.object_count, 0)
        self.assertEqual(b5_ins.original_amount, Decimal('0.00'))
        self.assertEqual(b5_ins.increment_amount, Decimal('0.00'))
