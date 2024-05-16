from apps.app_screenvis.models import HostNetflow
from apps.app_screenvis.workers import HostNetflowWorker
from . import MyAPITestCase, get_or_create_metric_host


class HostNetflowTests(MyAPITestCase):
    def setUp(self):
        pass

    def test_query(self):
        host_unit = get_or_create_metric_host()

        self.assertEqual(HostNetflow.objects.count(), 0)
        HostNetflowWorker(minutes=3).run()
        self.assertEqual(HostNetflow.objects.count(), 1)
        obj1: HostNetflow = HostNetflow.objects.first()
        self.assertEqual(obj1.unit_id, host_unit.id)
        self.assertTrue(obj1.flow_in > 0)
        self.assertTrue(obj1.flow_out > 0)

        # 改为无效数据
        obj1.flow_in = -1
        obj1.flow_out = -1
        obj1.save(update_fields=['flow_in', 'flow_out'])
        self.assertEqual(HostNetflow.objects.filter(flow_in__lt=0, flow_out__lt=0).count(), 1)
        HostNetflowWorker(minutes=3).run(update_before_invalid_cycles=5)
        self.assertEqual(HostNetflow.objects.count(), 2)   # 生产新数据
        self.assertEqual(HostNetflow.objects.filter(flow_in__lt=0).count(), 0)   # 更新无效数据
        self.assertEqual(HostNetflow.objects.filter(flow_out__lt=0).count(), 0)  # 更新无效数据
