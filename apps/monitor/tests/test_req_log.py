import random
from datetime import timedelta

from django.utils import timezone
from django.test.testcases import TransactionTestCase
from monitor.req_workers import ServiceReqCounter, LogSiteReqCounter
from monitor.models import TotalReqNum, LogSite, LogSiteTimeReqNum


class ServiceReqCounterTests(TransactionTestCase):
    def setUp(self):
        pass

    def test_req_num(self):
        def get_sites_req_num(sites: dict, new_until_time, hours: int):
            return hours * 2

        req_ins = TotalReqNum.get_instance()
        self.assertEqual(req_ins.req_num, 0)
        req_ins.until_time = timezone.now() - timedelta(hours=1)
        req_ins.save(update_fields=['until_time'])

        req_counter = ServiceReqCounter()
        req_counter.get_sites_req_num = get_sites_req_num

        # 不更新
        count_hours = req_counter.run()
        self.assertEqual(count_hours, 0)
        req_ins.refresh_from_db()
        self.assertNotEqual(req_counter.new_until_time, req_ins.until_time)
        self.assertEqual(req_ins.req_num, 0)
        now_hour_start_time = req_counter.new_until_time

        # -2h
        req_counter.new_until_time = req_counter.new_until_time - timedelta(hours=2)
        count_hours = req_counter.run()
        self.assertEqual(count_hours, 0)
        req_ins.refresh_from_db()
        self.assertNotEqual(req_counter.new_until_time, req_ins.until_time)
        self.assertEqual(req_ins.req_num, 0)

        # 1h
        req_counter.new_until_time = now_hour_start_time + timedelta(hours=1)
        count_hours = req_counter.run()
        self.assertEqual(count_hours, 1)
        req_ins.refresh_from_db()
        self.assertEqual(req_counter.new_until_time, req_ins.until_time)
        self.assertEqual(req_ins.req_num, 2)

        # 6h
        req_counter.new_until_time = req_counter.new_until_time + timedelta(hours=6)
        count_hours = req_counter.run()
        self.assertEqual(count_hours, 6)
        req_ins.refresh_from_db()
        self.assertEqual(req_counter.new_until_time, req_ins.until_time)
        self.assertEqual(req_ins.req_num, 2 + 2 * 6)

        # 26h
        req_counter.new_until_time = req_counter.new_until_time + timedelta(hours=26)
        count_hours = req_counter.run()
        self.assertEqual(count_hours, 24)
        req_ins.refresh_from_db()
        self.assertEqual(req_counter.new_until_time, req_ins.until_time)
        self.assertEqual(req_ins.req_num, 2 + 2 * 6 + 24 * 2)
        pre_until_time = req_ins.until_time

        # 不更新
        req_counter.new_until_time = now_hour_start_time
        count_hours = req_counter.run()
        self.assertEqual(count_hours, 0)
        req_ins.refresh_from_db()
        self.assertEqual(pre_until_time, req_ins.until_time)
        self.assertEqual(req_ins.req_num, 2 + 2 * 6 + 24 * 2)


class LogSiteTimeCounterTests(TransactionTestCase):

    @staticmethod
    def init_data(now_ts: int, cycle_minutes: int):
        site1 = LogSite(name='site1', name_en='site1 en', log_type=LogSite.LogType.HTTP.value, sort_weight=0)
        site1.save(force_insert=True)
        site2 = LogSite(name='site2', name_en='site2 en', log_type=LogSite.LogType.HTTP.value, sort_weight=0)
        site2.save(force_insert=True)
        site3 = LogSite(name='site3', name_en='site3 en', log_type=LogSite.LogType.NAT.value, sort_weight=0)
        site3.save(force_insert=True)
        site4 = LogSite(name='site4', name_en='site4 en', log_type=LogSite.LogType.NAT.value, sort_weight=0)
        site4.save(force_insert=True)
        site5 = LogSite(name='site5', name_en='site5 en', log_type=LogSite.LogType.NAT.value, sort_weight=0)
        site5.save(force_insert=True)

        ts_2hours = range(now_ts - 3600 * 2, now_ts, 60 * cycle_minutes)
        # site1, 全正常
        for ts in ts_2hours:
            LogSiteTimeReqNum(timestamp=ts, count=random.randint(0, 1000), site_id=site1.id).save(force_insert=True)

        # site2, 存在零星无效
        for ts in ts_2hours:
            LogSiteTimeReqNum(timestamp=ts, count=random.randint(-10, 100), site_id=site2.id).save(force_insert=True)

        # site3, 大部分都无效
        for ts in ts_2hours:
            LogSiteTimeReqNum(timestamp=ts, count=random.randint(-10, 1), site_id=site3.id).save(force_insert=True)

        # site4, 中间一小部分连续无效
        ts_l4 = list(ts_2hours)
        idx_4_3 = len(ts_l4) * 3 // 4
        idx_8_7 = (idx_4_3 + len(ts_l4)) // 2
        # 前3/4 - 后1/4中间部分无效
        site3_invalid_tss = ts_l4[idx_4_3:idx_8_7]
        for ts in site3_invalid_tss:
            LogSiteTimeReqNum(timestamp=ts, count=random.randint(-10, -1), site_id=site4.id).save(force_insert=True)

        for ts in (ts_l4[0:idx_4_3] + ts_l4[idx_8_7:]):
            LogSiteTimeReqNum(timestamp=ts, count=random.randint(0, 100), site_id=site4.id).save(force_insert=True)

        # site5, 最后一小部分连续无效
        ts_l5 = list(ts_2hours)
        idx_12_11 = len(ts_l5) * 11 // 12
        for ts in ts_l5[idx_12_11:]:
            LogSiteTimeReqNum(timestamp=ts, count=random.randint(-10, -1), site_id=site5.id).save(force_insert=True)

        for ts in ts_l5[0:idx_12_11]:
            LogSiteTimeReqNum(timestamp=ts, count=random.randint(0, 100), site_id=site5.id).save(force_insert=True)

    def test_update_invalid(self):
        async def get_site_req_num(site: LogSite, until_timestamp: int, minutes: int):
            return random.randint(0, 1000)

        cycle_minutes = 1
        log_counter = LogSiteReqCounter(minutes=cycle_minutes)
        log_counter.get_site_req_num = get_site_req_num
        now_ts = log_counter.get_now_timestamp()

        self.init_data(now_ts=now_ts, cycle_minutes=cycle_minutes)
        before_count = LogSiteTimeReqNum.objects.filter(count__lt=0).count()
        invalid_count, update_count, ok_count = log_counter.run_update_invalid(before_minutes=60, now_timestamp=now_ts)
        self.assertTrue(invalid_count > 0)
        self.assertTrue(update_count > 0)
        self.assertTrue(ok_count > 0)
        after_count = LogSiteTimeReqNum.objects.filter(count__lt=0).count()
        self.assertEqual(before_count - after_count, ok_count)

    def test_create_and_update_invalid(self):
        async def get_site_req_num(site: LogSite, until_timestamp: int, minutes: int):
            return random.randint(0, 1000)

        cycle_minutes = 1
        log_counter = LogSiteReqCounter(minutes=cycle_minutes)
        log_counter.get_site_req_num = get_site_req_num
        now_ts = log_counter.get_now_timestamp()

        self.init_data(now_ts=now_ts, cycle_minutes=cycle_minutes)
        before_count = LogSiteTimeReqNum.objects.filter(count__lt=0).count()
        ret = log_counter.run(update_before_invalid_cycles=5)
        self.assertTrue(ret['invalid_count'] > 0)
        self.assertTrue(ret['update_count'] > 0)
        self.assertTrue(ret['update_ok_count'] > 0)
        new_invalid_count = ret['sites_count'] - ret['new_ok_count']
        after_count = LogSiteTimeReqNum.objects.filter(count__lt=0).count()
        self.assertEqual(before_count - ret['update_ok_count'] + new_invalid_count, after_count)

    def test_is_series_invalid(self):
        now_ts = LogSiteReqCounter.get_now_timestamp()

        tss = list(range(now_ts - 60 * 10, now_ts, 60))
        ok = LogSiteReqCounter.is_series_invalid(tss=tss, cycle_minutes=1, now_ts=now_ts)
        self.assertTrue(ok)

        tss = list(range(now_ts - 60 * 10, now_ts, 60))
        tss.pop(5)
        ok = LogSiteReqCounter.is_series_invalid(tss=tss, cycle_minutes=1, now_ts=now_ts)
        self.assertFalse(ok)

        tss = list(range(now_ts - 60 * 1, now_ts, 60))
        ok = LogSiteReqCounter.is_series_invalid(tss=tss, cycle_minutes=1, now_ts=now_ts)
        self.assertFalse(ok)

        tss = list(range(now_ts - 60 * 3, now_ts, 60))
        ok = LogSiteReqCounter.is_series_invalid(tss=tss, cycle_minutes=1, now_ts=now_ts)
        self.assertTrue(ok)

        # 一个周期 + 允许误差1秒
        tss = list(range(now_ts - 1 - 60 * 3, now_ts - 1, 60))
        self.assertEqual(len(tss), 3)
        ok = LogSiteReqCounter.is_series_invalid(tss=tss, cycle_minutes=1, now_ts=now_ts)
        self.assertTrue(ok)

        tss = list(range(now_ts - 2 - 60 * 3, now_ts - 2, 60))
        self.assertEqual(len(tss), 3)
        ok = LogSiteReqCounter.is_series_invalid(tss=tss, cycle_minutes=1, now_ts=now_ts)
        self.assertFalse(ok)

        # 一个周期 + 允许误差1秒
        tss = list(range(now_ts - 1 - 60 * 2 * 3, now_ts - 1, 60 * 2))
        self.assertEqual(len(tss), 3)
        ok = LogSiteReqCounter.is_series_invalid(tss=tss, cycle_minutes=2, now_ts=now_ts)
        self.assertTrue(ok)

        tss = list(range(now_ts - 2 - 60 * 2 * 3, now_ts - 2, 60 * 2))
        self.assertEqual(len(tss), 3)
        ok = LogSiteReqCounter.is_series_invalid(tss=tss, cycle_minutes=2, now_ts=now_ts)
        self.assertFalse(ok)

        # -----  test is_site_service_down ----

        # 无效数少
        tss = list(range(now_ts - 60 * 3, now_ts, 60))
        ok = LogSiteReqCounter.is_site_service_down(tss=tss, ts_count=100, cycle_minutes=1, now_ts=now_ts)
        self.assertFalse(ok)

        # 无效占比10%
        tss = list(range(now_ts - 60 * 10, now_ts, 60))
        ok = LogSiteReqCounter.is_site_service_down(tss=tss, ts_count=100, cycle_minutes=1, now_ts=now_ts)
        self.assertTrue(ok)

        # 无效占比95%，最近几个周期不连续
        tss = list(range(now_ts - 120 - 60 * 95, now_ts - 120, 60))
        ok = LogSiteReqCounter.is_site_service_down(tss=tss, ts_count=100, cycle_minutes=1, now_ts=now_ts)
        self.assertTrue(ok)

        # 无效占比80%，最近几个周期不连续无效, not down
        tss = list(range(now_ts - 121 - 60 * 80, now_ts - 121, 60))
        ok = LogSiteReqCounter.is_site_service_down(tss=tss, ts_count=100, cycle_minutes=1, now_ts=now_ts)
        self.assertFalse(ok)

        # 无效占比80%，最近几个周期连续无效
        tss = list(range(now_ts - 60 * 80, now_ts, 60))
        tss.reverse()
        ok = LogSiteReqCounter.is_site_service_down(tss=tss, ts_count=100, cycle_minutes=1, now_ts=now_ts)
        self.assertTrue(ok)

        # 无效占比20%，最近几个周期连续无效
        tss = list(range(now_ts - 60 * 20, now_ts, 60))
        tss.reverse()
        ok = LogSiteReqCounter.is_site_service_down(tss=tss, ts_count=100, cycle_minutes=1, now_ts=now_ts)
        self.assertTrue(ok)

        # 无效占比20%，最近几个周期不连续无效，无效连续占比100
        tss = list(range(now_ts - 120 - 60 * 20, now_ts - 120, 60))
        tss.reverse()
        ok = LogSiteReqCounter.is_site_service_down(tss=tss, ts_count=100, cycle_minutes=1, now_ts=now_ts)
        self.assertFalse(ok)
