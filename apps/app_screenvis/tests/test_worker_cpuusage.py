from apps.app_screenvis.models import HostCpuUsage
from apps.app_screenvis.workers import HostCpuUsageWorker
from . import MyAPITestCase, get_or_create_metric_host


class HostCpuUsageTests(MyAPITestCase):
    def setUp(self):
        pass

    def test_query(self):
        host_unit = get_or_create_metric_host()

        self.assertEqual(HostCpuUsage.objects.count(), 0)
        HostCpuUsageWorker(minutes=10).run()
        self.assertEqual(HostCpuUsage.objects.count(), 1)
        obj1: HostCpuUsage = HostCpuUsage.objects.first()
        self.assertEqual(obj1.unit_id, host_unit.id)
        self.assertTrue(obj1.value > 0)

        # 改为无效数据
        obj1.value = -1
        obj1.save(update_fields=['value'])
        self.assertEqual(HostCpuUsage.objects.filter(value__lt=0).count(), 1)
        HostCpuUsageWorker(minutes=10).run(update_before_invalid_cycles=5)
        self.assertEqual(HostCpuUsage.objects.count(), 2)   # 生产新数据
        self.assertEqual(HostCpuUsage.objects.filter(value__lt=0).count(), 0)   # 更新无效数据
