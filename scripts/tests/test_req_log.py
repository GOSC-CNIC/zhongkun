from datetime import timedelta

from django.utils import timezone
from django.test.testcases import TransactionTestCase
from scripts.workers.req_logs import ServiceReqCounter
from monitor.models import TotalReqNum


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
