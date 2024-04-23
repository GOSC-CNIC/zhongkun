import random

from django.test.testcases import TransactionTestCase
from apps.app_screenvis.workers import ServerServiceStatsWorker
from apps.app_screenvis.models import ServerService, ServerServiceTimedStats, VPNTimedStats


class ServerServiceStatsWorkerTests(TransactionTestCase):
    @staticmethod
    def init_data():
        site1 = ServerService(
            name='site1', name_en='site1 en', endpoint_url='https://test.com', username='test', sort_weight=1)
        site1.set_password(raw_password='test_passwd')
        site1.save(force_insert=True)
        site2 = ServerService(
            name='site2', name_en='site2 en', endpoint_url='https://test2.com', username='test2', sort_weight=2)
        site2.set_password(raw_password='test_passwd2')
        site2.save(force_insert=True)
        site3 = ServerService(
            name='site3', name_en='site3 en', endpoint_url='https://test3.com', username='test3', sort_weight=3)
        site3.set_password(raw_password='test_passwd')
        site3.save(force_insert=True)
        site4 = ServerService(
            name='site4', name_en='site4 en', endpoint_url='https://test4.com', username='test4', sort_weight=4,
            status=ServerService.Status.DISABLE.value
        )
        site4.set_password(raw_password='test_passwd')
        site4.save(force_insert=True)

    def test_create(self):
        async def async_request(api_url: str, username: str, password: str):
            mem_total = random.randint(100, 10000)
            vcpu_total = random.randint(200, 5000)
            ips_total = random.randint(20, 600)
            vpn_total = random.randint(100, 3000)
            vpn_invalid = random.randint(0, 100)
            return {
                "quota": {
                    "mem_total": mem_total,
                    "mem_allocated": random.randint(1, mem_total),
                    "vcpu_total": vcpu_total,
                    "vcpu_allocated": random.randint(1, vcpu_total),
                    "vm_created": random.randint(1, 100),
                    "ips_total": ips_total,
                    "ips_used": random.randint(1, ips_total),
                    "vdisk_num": random.randint(1, 200),
                    "vpn_total": vpn_total,
                    "vpn_active": random.randint(0, vpn_total - vpn_invalid),
                    "vpn_invalid": vpn_invalid,
                    "mem_unit": "GB"
                }
            }

        cycle_minutes = 3
        log_counter = ServerServiceStatsWorker(minutes=cycle_minutes)
        log_counter.async_request = async_request

        self.init_data()
        self.assertEqual(ServerServiceTimedStats.objects.count(), 0)
        self.assertEqual(VPNTimedStats.objects.count(), 0)
        ret = log_counter.run()
        self.assertEqual(ret['unit_count'], 3)
        self.assertEqual(ret['new_ok_count'], 3)
        self.assertEqual(ret['compute_count'], 3)
        self.assertEqual(ret['vpn_count'], 3)
        self.assertEqual(ServerServiceTimedStats.objects.count(), 3)
        self.assertEqual(VPNTimedStats.objects.count(), 3)
