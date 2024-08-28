from datetime import timedelta

from django.utils import timezone as dj_timezone

from apps.app_screenvis.models import HostNetflow
from apps.app_screenvis.workers import HostNetflowWorker
from apps.app_screenvis.workers.netflow import NetFlowValue
from . import MyAPITestCase, get_or_create_metric_host


class HostNetflowTests(MyAPITestCase):
    def setUp(self):
        pass

    def test_query(self):
        host_unit = get_or_create_metric_host()

        self.assertEqual(HostNetflow.objects.count(), 0)
        # 产生当前时间戳数据，会补全前24h数据
        HostNetflowWorker(minutes=6).run()
        self.assertEqual(HostNetflow.objects.count(), 241)
        obj1: HostNetflow = HostNetflow.objects.first()
        self.assertEqual(obj1.unit_id, host_unit.id)
        self.assertTrue(obj1.flow_in > 0)
        self.assertTrue(obj1.flow_out > 0)

        # 产生当前时间戳数据
        HostNetflowWorker(minutes=6).run()
        self.assertEqual(HostNetflow.objects.count(), 242)   # 生产新数据

        # 删除N天前的数据测试
        ago_days = 200
        nt = dj_timezone.now()
        dt_ago_days = nt - timedelta(days=ago_days)
        ts_ago_days = int(dt_ago_days.timestamp())
        obj1 = HostNetflow(timestamp=ts_ago_days - 20, unit_id=host_unit.id, flow_in=1, flow_out=11)
        obj1.save(force_insert=True)
        obj2 = HostNetflow(timestamp=ts_ago_days - 10, unit_id=host_unit.id, flow_in=2, flow_out=22)
        obj2.save(force_insert=True)
        obj3 = HostNetflow(timestamp=ts_ago_days + 10, unit_id=host_unit.id, flow_in=3, flow_out=33)
        obj3.save(force_insert=True)

        self.assertEqual(HostNetflow.objects.count(), 242 + 3)
        # 产生当前时间戳数据
        HostNetflowWorker(minutes=6).run()
        self.assertEqual(HostNetflow.objects.count(), 245 + 1 - 2)

    def test_piece_values(self):
        in_values = [
            NetFlowValue(ts=1, in_val=1.1, out_val=0),
            NetFlowValue(ts=3, in_val=3.3, out_val=0),
            NetFlowValue(ts=2, in_val=2.2, out_val=0),
        ]
        out_values = [
            NetFlowValue(ts=3, in_val=0, out_val=2.22),
            NetFlowValue(ts=4, in_val=0, out_val=3.32),
            NetFlowValue(ts=2, in_val=0, out_val=1.12),
        ]
        r = HostNetflowWorker.piece_together_in_out_values(
            flow_in_values=in_values, flow_out_values=out_values)
        self.assertEqual(r[0].ts, 1)
        self.assertEqual(r[0].in_val, 1.1)
        self.assertEqual(r[0].out_val, 1.12)
        self.assertEqual(r[1].ts, 2)
        self.assertEqual(r[1].in_val, 2.2)
        self.assertEqual(r[1].out_val, 2.22)
        self.assertEqual(r[2].ts, 3)
        self.assertEqual(r[2].in_val, 3.3)
        self.assertEqual(r[2].out_val, 3.32)

        in_values = [
            NetFlowValue(ts=1, in_val=1.1, out_val=0),
            NetFlowValue(ts=3, in_val=3.3, out_val=0),
        ]
        out_values = [
            NetFlowValue(ts=3, in_val=0, out_val=2.22),
            NetFlowValue(ts=2, in_val=0, out_val=1.12),
            NetFlowValue(ts=4, in_val=0, out_val=3.32),
        ]
        r = HostNetflowWorker.piece_together_in_out_values(
            flow_in_values=in_values, flow_out_values=out_values)
        self.assertEqual(r[0].ts, 1)
        self.assertEqual(r[0].in_val, 1.1)
        self.assertEqual(r[0].out_val, 1.12)
        self.assertEqual(r[1].ts, 3)
        self.assertEqual(r[1].in_val, 3.3)
        self.assertEqual(r[1].out_val, 2.22)
        self.assertEqual(r[2].ts, 4)
        self.assertEqual(r[2].in_val, 0)
        self.assertEqual(r[2].out_val, 3.32)

        in_values = [
            NetFlowValue(ts=1, in_val=1.1, out_val=0),
            NetFlowValue(ts=3, in_val=3.3, out_val=0),
            NetFlowValue(ts=2, in_val=2.2, out_val=0),
        ]
        out_values = [
            NetFlowValue(ts=3, in_val=0, out_val=2.22),
            NetFlowValue(ts=2, in_val=0, out_val=1.12),
        ]
        r = HostNetflowWorker.piece_together_in_out_values(
            flow_in_values=in_values, flow_out_values=out_values)
        self.assertEqual(r[0].ts, 1)
        self.assertEqual(r[0].in_val, 1.1)
        self.assertEqual(r[0].out_val, 1.12)
        self.assertEqual(r[1].ts, 2)
        self.assertEqual(r[1].in_val, 2.2)
        self.assertEqual(r[1].out_val, 2.22)
        self.assertEqual(r[2].ts, 3)
        self.assertEqual(r[2].in_val, 3.3)
        self.assertEqual(r[2].out_val, 0)
