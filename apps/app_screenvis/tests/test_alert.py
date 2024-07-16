from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone

from apps.app_alert.models import AlertModel, ResolvedAlertModel
from apps.app_screenvis.models import MetricMonitorUnit
from apps.app_screenvis.permissions import ScreenAPIIPRestrictor
from . import MyAPITestCase


class AlertTests(MyAPITestCase):
    def setUp(self):
        ScreenAPIIPRestrictor.clear_cache()

    def query_response(self, querys: dict = None):
        url = reverse('screenvis-api:alert-list')
        if not querys:
            return self.client.get(url)

        query = parse.urlencode(query=querys)
        return self.client.get(f'{url}?{query}')

    def test_list(self):
        nt = dj_timezone.now()
        unit_ceph1 = MetricMonitorUnit(
            name='ceph1 name', name_en='ceph1 name en', job_tag='ceph1_metric',
            unit_type=MetricMonitorUnit.UnitType.CEPH.value,
            creation_time=nt, update_time=nt
        )
        unit_ceph1.save(force_insert=True)

        nt = dj_timezone.now()
        unit_host1 = MetricMonitorUnit(
            name='host1 name', name_en='host1 name en', job_tag='host1_metric',
            unit_type=MetricMonitorUnit.UnitType.HOST.value,
            creation_time=nt, update_time=nt
        )
        unit_host1.save(force_insert=True)

        nt = dj_timezone.now()
        nt_ts = nt.timestamp()
        alert1 = AlertModel(
            fingerprint='fingerprint1', name='name1', type=AlertModel.AlertType.METRIC.value,
            instance='instance1', port='1', cluster='ceph1_metric', summary='summary1', description='description1',
            start=int(nt_ts), end=int(nt_ts), recovery=int(nt_ts), status=AlertModel.AlertStatus.FIRING.value,
            count=1, creation=nt_ts, modification=int(nt_ts),
            first_notification=None, last_notification=None
        )
        alert1.save(force_insert=True)

        nt = dj_timezone.now()
        nt_ts = nt.timestamp()
        rl_alert2 = ResolvedAlertModel(
            fingerprint='fingerprint2', name='name2', type=ResolvedAlertModel.AlertType.METRIC.value,
            instance='instance2', port='2', cluster='ceph1_metric', summary='summary2', description='description2',
            start=int(nt_ts), end=int(nt_ts), recovery=int(nt_ts), status=ResolvedAlertModel.AlertStatus.RESOLVED.value,
            count=2, creation=nt_ts, modification=int(nt_ts),
            first_notification=None, last_notification=None
        )
        rl_alert2.save(force_insert=True)

        nt = dj_timezone.now()
        nt_ts = nt.timestamp()
        alert3 = AlertModel(
            fingerprint='fingerprint3', name='name3', type=AlertModel.AlertType.METRIC.value,
            instance='instance3', port='3', cluster='mail_log', summary='summary3', description='description3',
            start=int(nt_ts), end=int(nt_ts), recovery=int(nt_ts), status=AlertModel.AlertStatus.FIRING.value,
            count=3, creation=nt_ts, modification=int(nt_ts),
            first_notification=None, last_notification=None
        )
        alert3.save(force_insert=True)

        nt = dj_timezone.now()
        nt_ts = nt.timestamp()
        rl_alert4 = ResolvedAlertModel(
            fingerprint='fingerprint4', name='name4', type=ResolvedAlertModel.AlertType.METRIC.value,
            instance='instance4', port='4', cluster='host1_metric', summary='summary4', description='description4',
            start=int(nt_ts), end=int(nt_ts), recovery=int(nt_ts), status=ResolvedAlertModel.AlertStatus.RESOLVED.value,
            count=2, creation=nt_ts, modification=int(nt_ts),
            first_notification=None, last_notification=None
        )
        rl_alert4.save(force_insert=True)

        nt = dj_timezone.now()
        nt_ts = nt.timestamp()
        alert5 = AlertModel(
            fingerprint='fingerprint5', name='name5', type=AlertModel.AlertType.METRIC.value,
            instance='instance5', port='5', cluster='host1_metric', summary='summary5', description='description5',
            start=int(nt_ts), end=int(nt_ts), recovery=int(nt_ts), status=AlertModel.AlertStatus.FIRING.value,
            count=3, creation=nt_ts, modification=int(nt_ts),
            first_notification=None, last_notification=None
        )
        alert5.save(force_insert=True)

        response = self.query_response(querys=None)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        ScreenAPIIPRestrictor.add_ip_rule(ip_value='127.0.0.1')
        ScreenAPIIPRestrictor.clear_cache()

        response = self.query_response(querys={'status': 'test'})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.query_response(querys=None)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['has_next', 'next_marker', 'marker', 'page_size', 'results'], response.data)
        self.assertFalse(response.data['has_next'])
        self.assertIsNone(response.data['next_marker'])
        self.assertIsNone(response.data['marker'])
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 5)
        self.assertEqual(response.data['results'][0]['id'], alert5.id)
        self.assertEqual(response.data['results'][1]['id'], rl_alert4.id)
        self.assertEqual(response.data['results'][2]['id'], alert3.id)
        self.assertEqual(response.data['results'][3]['id'], rl_alert2.id)
        self.assertEqual(response.data['results'][4]['id'], alert1.id)

        # page_size
        response = self.query_response(querys={'page_size': 2})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['has_next', 'next_marker', 'marker', 'page_size', 'results'], response.data)
        self.assertTrue(response.data['has_next'])
        self.assertTrue(response.data['next_marker'])
        self.assertIsNone(response.data['marker'])
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], alert5.id)
        self.assertEqual(response.data['results'][1]['id'], rl_alert4.id)
        next_marker = response.data['next_marker']

        response = self.query_response(querys={'page_size': 2, 'marker': next_marker})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['has_next', 'next_marker', 'marker', 'page_size', 'results'], response.data)
        self.assertTrue(response.data['has_next'])
        self.assertTrue(response.data['next_marker'])
        self.assertEqual(response.data['marker'], next_marker)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], alert3.id)
        self.assertEqual(response.data['results'][1]['id'], rl_alert2.id)
        next_marker = response.data['next_marker']

        response = self.query_response(querys={'page_size': 2, 'marker': next_marker})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['has_next', 'next_marker', 'marker', 'page_size', 'results'], response.data)
        self.assertFalse(response.data['has_next'])
        self.assertIsNone(response.data['next_marker'])
        self.assertEqual(response.data['marker'], next_marker)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], alert1.id)

        # status
        response = self.query_response(querys={'status': 'firing'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['has_next', 'next_marker', 'marker', 'page_size', 'results'], response.data)
        self.assertFalse(response.data['has_next'])
        self.assertIsNone(response.data['next_marker'])
        self.assertIsNone(response.data['marker'])
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['results'][0]['id'], alert5.id)
        self.assertEqual(response.data['results'][1]['id'], alert3.id)
        self.assertEqual(response.data['results'][2]['id'], alert1.id)

        # 排序时间相同分页测试，下一页相同的会被跳过
        alert3.creation = rl_alert4.creation
        alert3.save(update_fields=['creation'])

        response = self.query_response(querys={'page_size': 2})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['has_next', 'next_marker', 'marker', 'page_size', 'results'], response.data)
        self.assertTrue(response.data['has_next'])
        self.assertTrue(response.data['next_marker'])
        self.assertIsNone(response.data['marker'])
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], alert5.id)
        # self.assertEqual(response.data['results'][1]['id'], rl_alert4.id)
        next_marker = response.data['next_marker']

        # 3和4时间相同，3或4被跳过，返回2、1
        response = self.query_response(querys={'page_size': 2, 'marker': next_marker})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['has_next', 'next_marker', 'marker', 'page_size', 'results'], response.data)
        self.assertFalse(response.data['has_next'])
        self.assertIsNone(response.data['next_marker'])
        self.assertEqual(response.data['marker'], next_marker)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], rl_alert2.id)
        self.assertEqual(response.data['results'][1]['id'], alert1.id)
