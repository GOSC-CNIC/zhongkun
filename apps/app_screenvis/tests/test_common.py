from django.urls import reverse
from django.utils import timezone as dj_timezone

from apps.app_screenvis.models import DataCenter, MetricMonitorUnit, LogMonitorUnit, ScreenConfig
from . import MyAPITestCase


class DataCenterTests(MyAPITestCase):
    def setUp(self):
        pass

    def test_list(self):
        nt = dj_timezone.now()
        odc1 = DataCenter(
            name='name1', name_en='name1_en', creation_time=nt, update_time=nt, loki_endpoint_url=''
        )
        odc1.save(force_insert=True)
        odc2 = DataCenter(
            name='name2', name_en='name2_en', creation_time=nt, update_time=nt, loki_endpoint_url=''
        )
        odc2.save(force_insert=True)

        base_url = reverse('screenvis-api:datacenter-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 2)
        self.assertKeysIn([
            'id', 'name', 'name_en', 'creation_time', 'update_time', 'longitude', 'latitude', 'sort_weight', 'remark'
        ], response.data['results'][0])

    def test_odc_units(self):
        nt = dj_timezone.now()
        odc1 = DataCenter(
            name='name1', name_en='name1_en', creation_time=nt, update_time=nt, loki_endpoint_url=''
        )
        odc1.save(force_insert=True)

        nt = dj_timezone.now()
        ceph1 = MetricMonitorUnit(
            name='ceph1 name', name_en='ceph1 name en', job_tag='ceph1_metric', data_center=odc1,
            unit_type=MetricMonitorUnit.UnitType.CEPH.value,
            creation_time=nt, update_time=nt
        )
        ceph1.save(force_insert=True)

        nt = dj_timezone.now()
        ceph2 = MetricMonitorUnit(
            name='ceph2 name', name_en='ceph2 name en', job_tag='ceph2_metric', data_center=odc1,
            unit_type=MetricMonitorUnit.UnitType.CEPH.value,
            creation_time=nt, update_time=nt
        )
        ceph2.save(force_insert=True)

        nt = dj_timezone.now()
        host1 = MetricMonitorUnit(
            name='host1 name', name_en='host1 name en', job_tag='host1_metric', data_center=odc1,
            unit_type=MetricMonitorUnit.UnitType.HOST.value,
            creation_time=nt, update_time=nt
        )
        host1.save(force_insert=True)

        nt = dj_timezone.now()
        tidb1 = MetricMonitorUnit(
            name='tidb1 name', name_en='tidb1 name en', job_tag='tidb1_metric', data_center=odc1,
            unit_type=MetricMonitorUnit.UnitType.TIDB.value,
            creation_time=nt, update_time=nt
        )
        tidb1.save(force_insert=True)

        nt = dj_timezone.now()
        log1 = LogMonitorUnit(
            name='log1 name', name_en='log1 name en', job_tag='log1_metric', data_center=odc1,
            log_type=LogMonitorUnit.LogType.NAT.value,
            creation_time=nt, update_time=nt
        )
        log1.save(force_insert=True)

        nt = dj_timezone.now()
        log2 = LogMonitorUnit(
            name='log2 name', name_en='log2 name en', job_tag='log2_metric', data_center=odc1,
            log_type=LogMonitorUnit.LogType.HTTP.value,
            creation_time=nt, update_time=nt
        )
        log2.save(force_insert=True)

        base_url = reverse('screenvis-api:datacenter-units', kwargs={'id': 666})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        base_url = reverse('screenvis-api:datacenter-units', kwargs={'id': odc1.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['data_center', 'metric_units', 'log_units'], response.data)

        self.assertKeysIn([
            'id', 'name', 'name_en', 'creation_time', 'update_time', 'longitude', 'latitude', 'sort_weight', 'remark'
        ], response.data['data_center'])
        self.assertEqual(len(response.data['metric_units']), 4)
        self.assertKeysIn([
            'id', 'name', 'name_en', 'creation_time', 'unit_type', 'job_tag', 'data_center', 'sort_weight', 'remark'
        ], response.data['metric_units'][0])
        self.assertKeysIn(['id', 'name', 'name_en', 'sort_weight'], response.data['metric_units'][0]['data_center'])
        self.assertEqual(len(response.data['log_units']), 2)
        self.assertKeysIn([
            'id', 'name', 'name_en', 'creation_time', 'log_type', 'job_tag', 'data_center', 'sort_weight', 'remark'
        ], response.data['log_units'][0])


class ConfigTests(MyAPITestCase):
    def setUp(self):
        pass

    def test_list(self):
        base_url = reverse('screenvis-api:configs-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['org_name', 'org_name_en'], response.data)
        self.assertEqual(response.data['org_name'], '')
        self.assertEqual(response.data['org_name_en'], '')

        org_name = ScreenConfig(name=ScreenConfig.ConfigName.ORG_NAME.value, value='org 名称')
        org_name.save(force_insert=True)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['org_name', 'org_name_en'], response.data)
        self.assertEqual(response.data['org_name'], 'org 名称')
        self.assertEqual(response.data['org_name_en'], '')

        org_name_en = ScreenConfig(name=ScreenConfig.ConfigName.ORG_NAME_EN.value, value='org name')
        org_name_en.save(force_insert=True)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['org_name', 'org_name_en'], response.data)
        self.assertEqual(response.data['org_name'], 'org 名称')
        self.assertEqual(response.data['org_name_en'], 'org name')
