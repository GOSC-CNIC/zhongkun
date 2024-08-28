import random
from datetime import datetime, timedelta

from django.test.testcases import TransactionTestCase

from apps.app_screenvis.workers import ServerServiceStatsWorker, ObjectServiceStatsWorker
from apps.app_screenvis.models import (
    ServerService, ServerServiceTimedStats, VPNTimedStats,
    ObjectService, ObjectServiceTimedStats
)


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
        return site1, site2, site3, site4

    def test_create(self):
        async def async_request(api_url: str, username: str, password: str):
            mem_total = random.randint(100, 10000)
            vcpu_total = random.randint(200, 5000)
            ips_total = random.randint(20, 600)
            vpn_total = random.randint(100, 3000)
            vpn_invalid = random.randint(0, 100)
            ips_public = random.randint(1, ips_total - 2)
            ips_private = ips_total - ips_public
            return {
                "quota": {
                    "mem_total": mem_total,
                    "mem_allocated": random.randint(1, mem_total),
                    "vcpu_total": vcpu_total,
                    "vcpu_allocated": random.randint(1, vcpu_total),
                    "vm_created": random.randint(1, 100),
                    "ips_total": ips_total,
                    "ips_used": random.randint(1, ips_total),
                    "ips_public": ips_public,
                    "ips_public_used": random.randint(1, ips_public),
                    "ips_private": ips_private,
                    "ips_private_used": random.randint(1, ips_private),
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

        s1, s2, s3, s4 = self.init_data()
        self.assertEqual(ServerServiceTimedStats.objects.count(), 0)
        self.assertEqual(VPNTimedStats.objects.count(), 0)
        ret = log_counter.run()
        self.assertEqual(ret['unit_count'], 3)
        self.assertEqual(ret['new_ok_count'], 3)
        self.assertEqual(ret['compute_count'], 3)
        self.assertEqual(ret['vpn_count'], 3)
        self.assertEqual(ServerServiceTimedStats.objects.count(), 3)
        self.assertEqual(VPNTimedStats.objects.count(), 3)

        # 删除N天前的数据测试
        ago_days = 200
        nt = datetime.utcnow()
        dt_ago_days = nt - timedelta(days=ago_days)
        ts_ago_days = int(dt_ago_days.timestamp())
        obj1 = ServerServiceTimedStats(
            service_id=s1.id, timestamp=ts_ago_days - 20,
            server_count=1, disk_count=111,
            ip_count=11, ip_used_count=1,
            pub_ip_count=1, pub_ip_used_count=1,
            pri_ip_count=1, pri_ip_used_count=1,
            mem_size=1111, mem_used_size=111,
            cpu_count=1111, cpu_used_count=11
        )
        obj1.save(force_insert=True)
        obj2 = ServerServiceTimedStats(
            service_id=s2.id, timestamp=ts_ago_days - 10,
            server_count=2, disk_count=222,
            ip_count=22, ip_used_count=2,
            pub_ip_count=2, pub_ip_used_count=2,
            pri_ip_count=2, pri_ip_used_count=2,
            mem_size=2222, mem_used_size=222,
            cpu_count=2222, cpu_used_count=22
        )
        obj2.save(force_insert=True)
        obj3 = ServerServiceTimedStats(
            service_id=s3.id, timestamp=ts_ago_days + 10,
            server_count=3, disk_count=333,
            ip_count=33, ip_used_count=3,
            pub_ip_count=3, pub_ip_used_count=3,
            pri_ip_count=3, pri_ip_used_count=3,
            mem_size=3333, mem_used_size=333,
            cpu_count=3333, cpu_used_count=33
        )
        obj3.save(force_insert=True)

        vpn1 = VPNTimedStats(
            service_id=s4.id, timestamp=ts_ago_days - 8,
            vpn_online_count=111, vpn_active_count=21, vpn_count=3131
        )
        vpn1.save(force_insert=True)
        vpn2 = VPNTimedStats(
            service_id=s4.id, timestamp=ts_ago_days + 5,
            vpn_online_count=22, vpn_active_count=313, vpn_count=1133
        )
        vpn2.save(force_insert=True)

        self.assertEqual(ServerServiceTimedStats.objects.count(), 3 + 3)
        self.assertEqual(VPNTimedStats.objects.count(), 3 + 2)
        ret = log_counter.run()
        self.assertEqual(ret['unit_count'], 3)
        self.assertEqual(ret['new_ok_count'], 3)
        self.assertEqual(ret['compute_count'], 3)
        self.assertEqual(ret['vpn_count'], 3)
        self.assertEqual(ret['compute_deleted_count'], 2)
        self.assertEqual(ret['vpn_deleted_count'], 1)
        self.assertEqual(ServerServiceTimedStats.objects.count(), 6 + 3 - 2)
        self.assertEqual(VPNTimedStats.objects.count(), 5 + 3 - 1)


class ObjectServiceStatsWorkerTests(TransactionTestCase):
    @staticmethod
    def init_data():
        site1 = ObjectService(
            name='site1', name_en='site1 en', endpoint_url='https://test.com', username='test', sort_weight=1)
        site1.set_password(raw_password='test_passwd')
        site1.save(force_insert=True)
        site2 = ObjectService(
            name='site2', name_en='site2 en', endpoint_url='https://test2.com', username='test2', sort_weight=2)
        site2.set_password(raw_password='test_passwd2')
        site2.save(force_insert=True)
        site3 = ObjectService(
            name='site3', name_en='site3 en', endpoint_url='https://test3.com', username='test3', sort_weight=3)
        site3.set_password(raw_password='test_passwd')
        site3.save(force_insert=True)
        site4 = ObjectService(
            name='site4', name_en='site4 en', endpoint_url='https://test4.com', username='test4', sort_weight=4,
            status=ObjectService.Status.DISABLE.value
        )
        site4.set_password(raw_password='test_passwd')
        site4.save(force_insert=True)
        return site1, site2, site3, site4

    def test_create(self):
        async def async_request(api_url: str, username: str, password: str):
            bucket_count = random.randint(100, 1000)
            bucket_all_size = random.randint(2000, 5000)
            ceph_total = random.randint(5000, 30000)
            return {
                "stats": {
                    "bucket_count": bucket_count,
                    "bucket_all_size": bucket_all_size,
                    "ceph_use": random.randint(bucket_all_size, ceph_total),
                    "ceph_total": ceph_total,
                }
            }

        cycle_minutes = 3
        log_counter = ObjectServiceStatsWorker(minutes=cycle_minutes)
        log_counter.async_request = async_request

        s1, s2, s3, s4 = self.init_data()
        self.assertEqual(ObjectServiceTimedStats.objects.count(), 0)
        ret = log_counter.run()
        self.assertEqual(ret['unit_count'], 3)
        self.assertEqual(ret['new_ok_count'], 3)
        self.assertEqual(ObjectServiceTimedStats.objects.count(), 3)

        # 删除N天前的数据测试
        ago_days = 200
        nt = datetime.utcnow()
        dt_ago_days = nt - timedelta(days=ago_days)
        ts_ago_days = int(dt_ago_days.timestamp())
        obj1 = ObjectServiceTimedStats(
            service_id=s1.id, timestamp=ts_ago_days - 20,
            bucket_count=111, bucket_storage=11,
            storage_used=12, storage_capacity=123, user_count=121
        )
        obj1.save(force_insert=True)
        obj2 = ObjectServiceTimedStats(
            service_id=s2.id, timestamp=ts_ago_days - 10,
            bucket_count=232, bucket_storage=23,
            storage_used=131, storage_capacity=123, user_count=121
        )
        obj2.save(force_insert=True)
        obj3 = ObjectServiceTimedStats(
            service_id=s3.id, timestamp=ts_ago_days + 10,
            bucket_count=131, bucket_storage=11,
            storage_used=31, storage_capacity=123, user_count=121
        )
        obj3.save(force_insert=True)

        self.assertEqual(ObjectServiceTimedStats.objects.count(), 3 + 3)
        ret = log_counter.run()
        self.assertEqual(ret['unit_count'], 3)
        self.assertEqual(ret['new_ok_count'], 3)
        self.assertEqual(ret['deleted_count'], 2)
        self.assertEqual(ObjectServiceTimedStats.objects.count(), 6 + 3 -2)
