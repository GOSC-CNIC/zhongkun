from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone

from utils.test import MyAPITransactionTestCase, get_or_create_user, get_or_create_organization
from apps.service.models import KunYuanService
from ..odc_manager import OrgDataCenterManager


class KunYuanServiceTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='test1@cnic.cn')

    def test_list(self):
        org = get_or_create_organization(name='test org')
        odc1 = OrgDataCenterManager.create_org_dc(
            name='测试', name_en='test11', organization_id=org.id,
            longitude=-10, latitude=80, sort_weight=0, remark='Test Remark66',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )

        url = reverse('service-api:kunyuan-service-list')
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 0)

        kunyuan1 = KunYuanService(
            name='name1', name_en='name en 1', endpoint_url='https://test1.com', username='user1',
            status=KunYuanService.Status.ENABLE.value, remarks='test1', longitude=0, latitude=0,
            sort_weight=-1, version='v1.1.1', version_update_time=dj_timezone.now(), org_data_center=odc1
        )
        kunyuan1.set_password('pd1')
        kunyuan1.save(force_insert=True)
        kunyuan2 = KunYuanService(
            name='name2', name_en='name en 2', endpoint_url='https://test2.com', username='user2',
            status=KunYuanService.Status.DISABLE.value, remarks='test2', longitude=0, latitude=0,
            sort_weight=6, version='v2.1.1', version_update_time=dj_timezone.now(), org_data_center=odc1
        )
        kunyuan2.set_password('pd2')
        kunyuan2.save(force_insert=True)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'endpoint_url', 'username', 'creation_time', 'status', 'remarks',
             'longitude', 'latitude', 'sort_weight', 'version', 'version_update_time', 'org_data_center'],
            response.data['results'][0])
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'longitude', 'latitude', 'sort_weight', 'organization'],
            response.data['results'][0]['org_data_center'])
        self.assertKeysIn(['id', 'name', 'name_en', 'sort_weight'],
                          response.data['results'][0]['org_data_center']['organization'])
        self.assertEqual(response.data['results'][0]['id'], kunyuan1.id)
        self.assertEqual(response.data['results'][1]['id'], kunyuan2.id)

        # query "status"
        query = parse.urlencode(query={'status': 'tes'})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'status': KunYuanService.Status.ENABLE.value})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], kunyuan1.id)

    def test_version(self):
        kunyuan1 = KunYuanService(
            name='name1', name_en='name en 1', endpoint_url='https://test1.com', username='user1',
            status=KunYuanService.Status.ENABLE.value, remarks='test1', longitude=0, latitude=0,
            sort_weight=-1, version='v1.1.1', version_update_time=None, org_data_center=None
        )
        kunyuan1.set_password('pd1')
        kunyuan1.save(force_insert=True)

        url = reverse('service-api:kunyuan-service-version', kwargs={'id': kunyuan1.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user1)

        url = reverse('service-api:kunyuan-service-version', kwargs={'id': 'test'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # 请求坤元服务失败
        url = reverse('service-api:kunyuan-service-version', kwargs={'id': kunyuan1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 500)

        # 更新时间在1分钟内，直接返回
        kunyuan1.version_update_time = dj_timezone.now()
        kunyuan1.save(update_fields=['version_update_time'])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["version", "version_update_time"], response.data)
