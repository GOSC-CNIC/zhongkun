from django.utils import timezone as dj_timezone
from django.urls import reverse

from apps.app_screenvis.models import (
    DataCenter, ServerService, ServerServiceTimedStats, ApiAllowIP, VPNTimedStats
)
from apps.app_screenvis.permissions import ScreenAPIIPRestrictor
from . import MyAPITestCase


class ServerServiceStatsTests(MyAPITestCase):
    def setUp(self):
        ScreenAPIIPRestrictor.clear_cache()

    def test_list(self):
        nt = dj_timezone.now()
        dc1 = DataCenter(name='dc1', name_en='dc1', creation_time=nt, update_time=nt)
        dc1.save(force_insert=True)
        dc2 = DataCenter(name='dc2', name_en='dc2', creation_time=nt, update_time=nt)
        dc2.save(force_insert=True)

        site1 = ServerService(
            name='site1', name_en='site1 en', data_center=dc1, status=ServerService.Status.ENABLE.value,
            endpoint_url='https://test.com', username='test', sort_weight=1)
        site1.set_password(raw_password='test_passwd')
        site1.save(force_insert=True)

        site2 = ServerService(
            name='site2', name_en='site2 en', data_center=dc1, status=ServerService.Status.DISABLE.value,
            endpoint_url='https://test2.com', username='test2', sort_weight=2)
        site2.set_password(raw_password='test_passwd2')
        site2.save(force_insert=True)

        site3 = ServerService(
            name='site3', name_en='site3 en', data_center=dc1, status=ServerService.Status.DELETED.value,
            endpoint_url='https://test3.com', username='test3', sort_weight=3)
        site3.set_password(raw_password='test_passwd')
        site3.save(force_insert=True)

        site4 = ServerService(
            name='site4', name_en='site4 en', data_center=dc2, status=ServerService.Status.ENABLE.value,
            endpoint_url='https://test4.com', username='test4', sort_weight=4
        )
        site4.set_password(raw_password='test_passwd')
        site4.save(force_insert=True)

        nt = dj_timezone.now()
        now_ts = int(nt.timestamp())
        site1_obj1 = ServerServiceTimedStats(
            service_id=site1.id, timestamp=now_ts,
            server_count=10, disk_count=8,
            ip_count=200, ip_used_count=88,
            mem_size=12345, mem_used_size=111,
            cpu_count=3000, cpu_used_count=234
        )
        site1_obj1.save(force_insert=True)
        site1_obj2 = ServerServiceTimedStats(
            service_id=site1.id, timestamp=now_ts - 60,
            server_count=2342, disk_count=824,
            ip_count=20240, ip_used_count=8228,
            mem_size=1245, mem_used_size=171,
            cpu_count=3200, cpu_used_count=34
        )
        site1_obj2.save(force_insert=True)
        site2_obj1 = ServerServiceTimedStats(
            service_id=site2.id, timestamp=now_ts - 120,
            server_count=2366, disk_count=57,
            ip_count=25252, ip_used_count=536,
            mem_size=4363, mem_used_size=436,
            cpu_count=25235, cpu_used_count=363
        )
        site2_obj1.save(force_insert=True)
        site3_obj1 = ServerServiceTimedStats(
            service_id=site3.id, timestamp=now_ts,
            server_count=46747, disk_count=3337,
            ip_count=37373, ip_used_count=575,
            mem_size=5855, mem_used_size=585,
            cpu_count=47448, cpu_used_count=4858
        )
        site3_obj1.save(force_insert=True)
        site4_obj1 = ServerServiceTimedStats(
            service_id=site4.id, timestamp=now_ts,
            server_count=3647, disk_count=363,
            ip_count=36375, ip_used_count=2362,
            mem_size=7573, mem_used_size=357,
            cpu_count=6786, cpu_used_count=877
        )
        site4_obj1.save(force_insert=True)

        url = reverse('screenvis-api:server-stats-dc', kwargs={'dc_id': 'fafa'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        ApiAllowIP(ip_value='127.0.0.1').save(force_insert=True)
        ScreenAPIIPRestrictor.clear_cache()

        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        url = reverse('screenvis-api:server-stats-dc', kwargs={'dc_id': 0})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        url = reverse('screenvis-api:server-stats-dc', kwargs={'dc_id': dc2.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['server_count'], site4_obj1.server_count)
        self.assertEqual(response.data['disk_count'], site4_obj1.disk_count)
        self.assertEqual(response.data['ip_count'], site4_obj1.ip_count)
        self.assertEqual(response.data['ip_used_count'], site4_obj1.ip_used_count)
        self.assertEqual(response.data['mem_size'], site4_obj1.mem_size)
        self.assertEqual(response.data['mem_used_size'], site4_obj1.mem_used_size)
        self.assertEqual(response.data['cpu_count'], site4_obj1.cpu_count)
        self.assertEqual(response.data['cpu_used_count'], site4_obj1.cpu_used_count)

        site4.status = site4.Status.DELETED.value
        site4.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['server_count'], 0)
        self.assertEqual(response.data['disk_count'], 0)
        self.assertEqual(response.data['ip_count'], 0)
        self.assertEqual(response.data['ip_used_count'], 0)
        self.assertEqual(response.data['mem_size'], 0)
        self.assertEqual(response.data['mem_used_size'], 0)
        self.assertEqual(response.data['cpu_count'], 0)
        self.assertEqual(response.data['cpu_used_count'], 0)

        # dc1
        url = reverse('screenvis-api:server-stats-dc', kwargs={'dc_id': dc1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['server_count'], site1_obj1.server_count + site2_obj1.server_count)
        self.assertEqual(response.data['disk_count'], site1_obj1.disk_count + site2_obj1.disk_count)
        self.assertEqual(response.data['ip_count'], site1_obj1.ip_count + site2_obj1.ip_count)
        self.assertEqual(response.data['ip_used_count'], site1_obj1.ip_used_count + site2_obj1.ip_used_count)
        self.assertEqual(response.data['mem_size'], site1_obj1.mem_size + site2_obj1.mem_size)
        self.assertEqual(response.data['mem_used_size'], site1_obj1.mem_used_size + site2_obj1.mem_used_size)
        self.assertEqual(response.data['cpu_count'], site1_obj1.cpu_count + site2_obj1.cpu_count)
        self.assertEqual(response.data['cpu_used_count'], site1_obj1.cpu_used_count + site2_obj1.cpu_used_count)


class VPNServiceStatsTests(MyAPITestCase):
    def setUp(self):
        ScreenAPIIPRestrictor.clear_cache()

    def test_list(self):
        nt = dj_timezone.now()
        dc1 = DataCenter(name='dc1', name_en='dc1', creation_time=nt, update_time=nt)
        dc1.save(force_insert=True)
        dc2 = DataCenter(name='dc2', name_en='dc2', creation_time=nt, update_time=nt)
        dc2.save(force_insert=True)

        site1 = ServerService(
            name='site1', name_en='site1 en', data_center=dc1, status=ServerService.Status.ENABLE.value,
            endpoint_url='https://test.com', username='test', sort_weight=1)
        site1.set_password(raw_password='test_passwd')
        site1.save(force_insert=True)

        site2 = ServerService(
            name='site2', name_en='site2 en', data_center=dc1, status=ServerService.Status.DISABLE.value,
            endpoint_url='https://test2.com', username='test2', sort_weight=2)
        site2.set_password(raw_password='test_passwd2')
        site2.save(force_insert=True)

        site3 = ServerService(
            name='site3', name_en='site3 en', data_center=dc1, status=ServerService.Status.DELETED.value,
            endpoint_url='https://test3.com', username='test3', sort_weight=3)
        site3.set_password(raw_password='test_passwd')
        site3.save(force_insert=True)

        site4 = ServerService(
            name='site4', name_en='site4 en', data_center=dc2, status=ServerService.Status.ENABLE.value,
            endpoint_url='https://test4.com', username='test4', sort_weight=4
        )
        site4.set_password(raw_password='test_passwd')
        site4.save(force_insert=True)

        nt = dj_timezone.now()
        now_ts = int(nt.timestamp())
        site1_obj1 = VPNTimedStats(
            service_id=site1.id, timestamp=now_ts,
            vpn_online_count=10, vpn_active_count=118, vpn_count=200
        )
        site1_obj1.save(force_insert=True)
        site1_obj2 = VPNTimedStats(
            service_id=site1.id, timestamp=now_ts - 60,
            vpn_online_count=66, vpn_active_count=464, vpn_count=532
        )
        site1_obj2.save(force_insert=True)
        site2_obj1 = VPNTimedStats(
            service_id=site2.id, timestamp=now_ts - 120,
            vpn_online_count=433, vpn_active_count=2222, vpn_count=2525
        )
        site2_obj1.save(force_insert=True)
        site3_obj1 = VPNTimedStats(
            service_id=site3.id, timestamp=now_ts,
            vpn_online_count=242, vpn_active_count=3525, vpn_count=3535
        )
        site3_obj1.save(force_insert=True)
        site4_obj1 = VPNTimedStats(
            service_id=site4.id, timestamp=now_ts,
            vpn_online_count=224, vpn_active_count=644, vpn_count=5654
        )
        site4_obj1.save(force_insert=True)

        url = reverse('screenvis-api:vpn-stats-dc', kwargs={'dc_id': 'fafa'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        ApiAllowIP(ip_value='127.0.0.1').save(force_insert=True)
        ScreenAPIIPRestrictor.clear_cache()

        response = self.client.get(url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        url = reverse('screenvis-api:vpn-stats-dc', kwargs={'dc_id': 0})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        url = reverse('screenvis-api:vpn-stats-dc', kwargs={'dc_id': dc2.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['vpn_online_count'], site4_obj1.vpn_online_count)
        self.assertEqual(response.data['vpn_active_count'], site4_obj1.vpn_active_count)
        self.assertEqual(response.data['vpn_count'], site4_obj1.vpn_count)

        site4.status = site4.Status.DELETED.value
        site4.save(update_fields=['status'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['vpn_online_count'], 0)
        self.assertEqual(response.data['vpn_active_count'], 0)
        self.assertEqual(response.data['vpn_count'], 0)

        # dc1
        url = reverse('screenvis-api:vpn-stats-dc', kwargs={'dc_id': dc1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['vpn_online_count'], site1_obj1.vpn_online_count + site2_obj1.vpn_online_count)
        self.assertEqual(response.data['vpn_active_count'], site1_obj1.vpn_active_count + site2_obj1.vpn_active_count)
        self.assertEqual(response.data['vpn_count'], site1_obj1.vpn_count + site2_obj1.vpn_count)
