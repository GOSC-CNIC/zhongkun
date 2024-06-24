from django.urls import reverse
from django.utils import timezone as dj_timezone

from apps.app_screenvis.models import MetricMonitorUnit, LogMonitorUnit, ScreenConfig
from apps.app_screenvis.permissions import ScreenAPIIPRestrictor
from apps.app_screenvis.configs_manager import screen_configs
from . import MyAPITestCase


class DataCenterTests(MyAPITestCase):
    def setUp(self):
        ScreenAPIIPRestrictor.clear_cache()

    def test_odc_units(self):

        nt = dj_timezone.now()
        ceph1 = MetricMonitorUnit(
            name='ceph1 name', name_en='ceph1 name en', job_tag='ceph1_metric',
            unit_type=MetricMonitorUnit.UnitType.CEPH.value,
            creation_time=nt, update_time=nt
        )
        ceph1.save(force_insert=True)

        nt = dj_timezone.now()
        ceph2 = MetricMonitorUnit(
            name='ceph2 name', name_en='ceph2 name en', job_tag='ceph2_metric',
            unit_type=MetricMonitorUnit.UnitType.CEPH.value,
            creation_time=nt, update_time=nt
        )
        ceph2.save(force_insert=True)

        nt = dj_timezone.now()
        host1 = MetricMonitorUnit(
            name='host1 name', name_en='host1 name en', job_tag='host1_metric',
            unit_type=MetricMonitorUnit.UnitType.HOST.value,
            creation_time=nt, update_time=nt
        )
        host1.save(force_insert=True)

        nt = dj_timezone.now()
        tidb1 = MetricMonitorUnit(
            name='tidb1 name', name_en='tidb1 name en', job_tag='tidb1_metric',
            unit_type=MetricMonitorUnit.UnitType.TIDB.value,
            creation_time=nt, update_time=nt
        )
        tidb1.save(force_insert=True)

        nt = dj_timezone.now()
        log1 = LogMonitorUnit(
            name='log1 name', name_en='log1 name en', job_tag='log1_metric',
            log_type=LogMonitorUnit.LogType.NAT.value,
            creation_time=nt, update_time=nt
        )
        log1.save(force_insert=True)

        nt = dj_timezone.now()
        log2 = LogMonitorUnit(
            name='log2 name', name_en='log2 name en', job_tag='log2_metric',
            log_type=LogMonitorUnit.LogType.HTTP.value,
            creation_time=nt, update_time=nt
        )
        log2.save(force_insert=True)

        base_url = reverse('screenvis-api:datacenter-units')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        ScreenAPIIPRestrictor.add_ip_rule(ip_value='127.0.0.1')
        ScreenAPIIPRestrictor.clear_cache()

        base_url = reverse('screenvis-api:datacenter-units')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['metric_units', 'log_units'], response.data)

        self.assertEqual(len(response.data['metric_units']), 4)
        self.assertKeysIn([
            'id', 'name', 'name_en', 'creation_time', 'unit_type', 'job_tag', 'sort_weight', 'remark'
        ], response.data['metric_units'][0])
        self.assertEqual(len(response.data['log_units']), 0)


class ConfigTests(MyAPITestCase):
    def setUp(self):
        ScreenAPIIPRestrictor.clear_cache()

    def test_list(self):
        base_url = reverse('screenvis-api:configs-list')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        ScreenAPIIPRestrictor.add_ip_rule(ip_value='127.0.0.1')
        ScreenAPIIPRestrictor.clear_cache()

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['org_name', 'org_name_en'], response.data)
        self.assertEqual(response.data['org_name'], 'ZhongKun')
        self.assertEqual(response.data['org_name_en'], 'ZhongKun')

        ScreenConfig.objects.filter(name=ScreenConfig.ConfigName.ORG_NAME.value).update(value='org 名称')
        screen_configs.clear_cache()
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['org_name', 'org_name_en'], response.data)
        self.assertEqual(response.data['org_name'], 'org 名称')
        self.assertEqual(response.data['org_name_en'], 'ZhongKun')

        ScreenConfig.objects.filter(name=ScreenConfig.ConfigName.ORG_NAME_EN.value).update(value='org name')
        screen_configs.clear_cache()
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['org_name', 'org_name_en'], response.data)
        self.assertEqual(response.data['org_name'], 'org 名称')
        self.assertEqual(response.data['org_name_en'], 'org name')
