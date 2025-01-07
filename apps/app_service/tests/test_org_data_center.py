from urllib import parse

from django.urls import reverse

from utils.test import MyAPITransactionTestCase, get_or_create_user, get_or_create_organization
from apps.app_storage.models import ObjectsService
from apps.app_monitor.models import MonitorJobCeph, MonitorJobServer, MonitorJobTiDB, LogSite, LogSiteType
from apps.app_wallet.models import PayAppService
from apps.app_wallet.tests import register_and_set_app_id_for_test
from apps.app_servers.models import ServiceConfig
from apps.app_service.models import OrgDataCenter
from ..odc_manager import OrgDataCenterManager


class AdminODCTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='test1@cnic.cn')
        self.org = get_or_create_organization(name='test org')

    def test_create_odc(self):
        url = reverse('service-api:admin-odc-list')

        data = {
            'name': '',
            'name_en': '',
            'organization': '',
            'longitude': 0,
            'latitude': 0,
            'sort_weight': 0,
            'remark': '',
            'thanos_endpoint_url': '',
            'thanos_username': '',
            'thanos_password': '',
            'thanos_receive_url': '',
            'thanos_remark': '',
            'loki_endpoint_url': '',
            'loki_username': '',
            'loki_password': '',
            'loki_receive_url': '',
            'loki_remark': ''
        }

        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user1)
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        # 字段为空的判断
        data['name'] = '测试'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['name_en'] = 'test'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['organization_id'] = 'testnot'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user1.set_federal_admin()
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        data['organization_id'] = self.org.id
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        # longitude, latitude
        data['longitude'] = 121
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['longitude'] = 20
        data['latitude'] = -91
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        data['latitude'] = -90

        # url
        data['thanos_endpoint_url'] = 'xxxx'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['thanos_endpoint_url'] = 'https://thanosxx.cn'
        data['loki_endpoint_url'] = 'http:/sss'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['loki_endpoint_url'] = 'https://lokixx.cn'

        # ok
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data = {
            'name': 'test 1',
            'name_en': 'test1 en',
            'organization_id': self.org.id,
            'longitude': 10,
            'latitude': -20.1,
            'sort_weight': 6,
            'remark': 'remark6',
            'thanos_endpoint_url': 'http://10.0.50.1:8888',
            'thanos_username': 'tom@cnic.cn',
            'thanos_password': 'test',
            'thanos_receive_url': 'http://10.0.0.100:1111',
            'thanos_remark': 'thanos_remark',
            'loki_endpoint_url': 'http://test.cn:9999',
            'loki_username': 'loki username',
            'loki_password': 'loki_password',
            'loki_receive_url': 'http://100.10.50.100',
            'loki_remark': 'loki_remark'
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)
        odc: OrgDataCenter = OrgDataCenterManager.get_odc(odc_id=response.data['id'])
        self.assertEqual(odc.name, data['name'])
        self.assertEqual(odc.name_en, data['name_en'])
        self.assertEqual(odc.organization_id, data['organization_id'])
        self.assertEqual(odc.longitude, data['longitude'])
        self.assertEqual(odc.latitude, data['latitude'])
        self.assertEqual(odc.sort_weight, data['sort_weight'])
        self.assertEqual(odc.remark, data['remark'])
        self.assertEqual(odc.thanos_endpoint_url, data['thanos_endpoint_url'])
        self.assertEqual(odc.thanos_receive_url, data['thanos_receive_url'])
        self.assertEqual(odc.thanos_username, data['thanos_username'])
        self.assertEqual(odc.raw_thanos_password, data['thanos_password'])
        self.assertEqual(odc.thanos_remark, data['thanos_remark'])
        self.assertEqual(odc.loki_endpoint_url, data['loki_endpoint_url'])
        self.assertEqual(odc.loki_receive_url, data['loki_receive_url'])
        self.assertEqual(odc.loki_username, data['loki_username'])
        self.assertEqual(odc.raw_loki_password, data['loki_password'])
        self.assertEqual(odc.loki_remark, data['loki_remark'])

    def test_list_odc(self):
        odc1 = OrgDataCenterManager.create_org_dc(
            name='测试', name_en='test11', organization_id=self.org.id,
            longitude=-10, latitude=80, sort_weight=0, remark='Test Remark66',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )
        org2 = get_or_create_organization(name='test org2')
        odc2 = OrgDataCenterManager.create_org_dc(
            name='测试2', name_en='test22', organization_id=org2.id,
            longitude=-10, latitude=80, sort_weight=0, remark='test remark88',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )

        url = reverse('service-api:admin-odc-list')
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

        # test dc admin
        odc1.add_admin_user(user=self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark', 'map_display'],
            response.data['results'][0])
        self.assertKeysIn(['id', 'name', 'name_en', 'sort_weight'], response.data['results'][0]['organization'])

        # test federal admin
        odc1.remove_admin_user(user=self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        self.user1.set_federal_admin()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data['results'][0])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['results'][0]['organization'])

        # query "org_id"
        query = parse.urlencode(query={'org_id': org2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], odc2.id)

        # query "search"
        query = parse.urlencode(query={'search': 'test1'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], odc1.id)

        query = parse.urlencode(query={'search': 'Test Remark6'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

        query = parse.urlencode(query={'search': 'ddTestRemark'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # query "org_id", "search"
        query = parse.urlencode(query={'search': 'test1', 'org_id': org2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'search': 'test1', 'org_id': odc1.organization_id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], odc1.id)

    def test_update_odc(self):
        data = {
            'name': '测试',
            'name_en': 'test',
            'organization_id': self.org.id,
            'longitude': -10,
            'latitude': 80,
            'sort_weight': 0,
            'remark': 'test remark',
            'thanos_endpoint_url': 'https://thanosxxxx.cn',
            'thanos_username': 'tom@cnic.cn',
            'thanos_password': 'test123456',
            'thanos_receive_url': 'https://thanosrexxxx.cn',
            'thanos_remark': 'thanos remark',
            'loki_endpoint_url': 'https://lokixxxx.cn',
            'loki_username': 'jerry@qq.com',
            'loki_password': 'loki123456',
            'loki_receive_url': 'https://lokerexxxx.cn',
            'loki_remark': 'loki remark'
        }
        org2 = get_or_create_organization(name='org2')
        odc1 = OrgDataCenterManager.create_org_dc(
            name=data['name'], name_en=data['name_en'], organization_id=data['organization_id'],
            longitude=data['longitude'], latitude=data['latitude'],
            sort_weight=data['sort_weight'], remark=data['remark'],
            thanos_endpoint_url=data['thanos_endpoint_url'], thanos_receive_url=data['thanos_receive_url'],
            thanos_username=data['thanos_username'], thanos_password=data['thanos_password'],
            thanos_remark=data['thanos_remark'],
            loki_endpoint_url=data['loki_endpoint_url'], loki_receive_url=data['loki_receive_url'],
            loki_username=data['loki_username'], loki_password=data['loki_password'], loki_remark=data['loki_remark']
        )

        url = reverse('service-api:admin-odc-detail', kwargs={'id': 'notfound'})
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user1)
        url = reverse('service-api:admin-odc-detail', kwargs={'id': 'notfound'})

        # invalid organization_id
        data['organization_id'] = 'invalid'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        data['organization_id'] = odc1.organization.id

        # odc TargetNotExist
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # AccessDenied
        url = reverse('service-api:admin-odc-detail', kwargs={'id': odc1.id})
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # ok, no change
        self.user1.set_federal_admin()
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        subdict = data.copy()
        subdict.pop('organization_id')
        self.assert_is_subdict_of(subdict, response.data)

        # name
        data['name'] = '测试2'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], '测试2')
        odc1.refresh_from_db()
        self.assertEqual(odc1.name, '测试2')

        # name_en
        data['name_en'] = 't' * 256
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['name_en'] = 'name_en'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name_en'], 'name_en')
        subdict = data.copy()
        subdict.pop('organization_id')
        self.assert_is_subdict_of(subdict, response.data)

        # organization_id
        data['organization_id'] = 'fsdfeterter'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        data['organization_id'] = org2.id
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['organization']['id'], org2.id)
        self.assertEqual(response.data['organization']['name'], org2.name)
        odc1.refresh_from_db()
        self.assertEqual(odc1.organization_id, org2.id)
        subdict = data.copy()
        subdict.pop('organization_id')
        self.assert_is_subdict_of(subdict, response.data)

        # url
        data['thanos_endpoint_url'] = 'thanos.cn'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        data['thanos_endpoint_url'] = 'https://thanos.cn'
        response = self.client.put(url, data=data)
        self.assertEqual(response.data['thanos_endpoint_url'], 'https://thanos.cn')
        odc1.refresh_from_db()
        self.assertEqual(odc1.thanos_endpoint_url, 'https://thanos.cn')

        data['thanos_receive_url'] = 'receivethanos.cn'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['thanos_receive_url'] = 'https://receivethanos.cn'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['thanos_receive_url'], 'https://receivethanos.cn')
        odc1.refresh_from_db()
        self.assertEqual(odc1.thanos_receive_url, 'https://receivethanos.cn')

        data['loki_endpoint_url'] = 'queryloki.cn'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['loki_endpoint_url'] = 'https://queryloki.cn'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['loki_endpoint_url'], 'https://queryloki.cn')
        odc1.refresh_from_db()
        self.assertEqual(odc1.loki_endpoint_url, 'https://queryloki.cn')

        data['loki_receive_url'] = 'receiveloki.cn'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['loki_receive_url'] = 'https://receiveloki.cn'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['loki_receive_url'], 'https://receiveloki.cn')
        odc1.refresh_from_db()
        self.assertEqual(odc1.loki_receive_url, 'https://receiveloki.cn')

        # longitude -120 ~ 120
        data['longitude'] = 120.1
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['longitude'] = -120.1
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['longitude'] = '12ss'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['longitude'] = -120
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['longitude'], -120)
        odc1.refresh_from_db()
        self.assertEqual(odc1.longitude, -120)

        # latitude -90 ~ 90
        data['latitude'] = 90.1
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['latitude'] = -90.1
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['latitude'] = '12ss'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['latitude'] = 89.9
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['latitude'], 89.9)
        odc1.refresh_from_db()
        self.assertEqual(odc1.latitude, 89.9)

        data = {
            'name': '测试66',
            'name_en': 'test66',
            'organization_id': org2.id,
            'longitude': -110,
            'latitude': 88,
            'sort_weight': -1000,
            'remark': 'test remark666',
            'thanos_endpoint_url': 'https://10.88.0.88',
            'thanos_username': 'tom66@cnic.cn',
            'thanos_password': 'adatest123456',
            'thanos_receive_url': 'https://10.188.0.88:6666',
            'thanos_remark': 'thanos remark543',
            'loki_endpoint_url': 'https://lokixxxx.com',
            'loki_username': 'jerrydaa@qq.com',
            'loki_password': 'lokiada123456',
            'loki_receive_url': 'https://lokerexxxx.com',
            'loki_remark': 'loki remarkqqq'
        }
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        subdict = data.copy()
        subdict.pop('organization_id')
        self.assert_is_subdict_of(subdict, response.data)
        odc1.refresh_from_db()
        self.assertEqual(odc1.name, data['name'])
        self.assertEqual(odc1.name_en, data['name_en'])
        self.assertEqual(odc1.organization_id, data['organization_id'])
        self.assertEqual(odc1.longitude, data['longitude'])
        self.assertEqual(odc1.latitude, data['latitude'])
        self.assertEqual(odc1.sort_weight, data['sort_weight'])
        self.assertEqual(odc1.remark, data['remark'])
        self.assertEqual(odc1.thanos_endpoint_url, data['thanos_endpoint_url'])
        self.assertEqual(odc1.thanos_receive_url, data['thanos_receive_url'])
        self.assertEqual(odc1.thanos_username, data['thanos_username'])
        self.assertEqual(odc1.raw_thanos_password, data['thanos_password'])
        self.assertEqual(odc1.thanos_remark, data['thanos_remark'])
        self.assertEqual(odc1.loki_endpoint_url, data['loki_endpoint_url'])
        self.assertEqual(odc1.loki_receive_url, data['loki_receive_url'])
        self.assertEqual(odc1.loki_username, data['loki_username'])
        self.assertEqual(odc1.raw_loki_password, data['loki_password'])
        self.assertEqual(odc1.loki_remark, data['loki_remark'])

    def test_detail_odc(self):
        user2 = get_or_create_user(username='test2@cnic.cn')
        odc1 = OrgDataCenterManager.create_org_dc(
            name='测试', name_en='test', organization_id=self.org.id,
            longitude=-10, latitude=80, sort_weight=0, remark='test remark',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )

        url = reverse('service-api:admin-odc-detail', kwargs={'id': 'test'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user1)
        url = reverse('service-api:admin-odc-detail', kwargs={'id': 'test'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        url = reverse('service-api:admin-odc-detail', kwargs={'id': odc1.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # odc admin
        odc1.add_admin_user(user=self.user1.id)
        url = reverse('service-api:admin-odc-detail', kwargs={'id': odc1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark', 'users'],
            response.data)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['organization'])
        self.assertEqual(len(response.data['users']), 1)
        self.assertEqual(response.data['users'][0]['id'], self.user1.id)
        self.assertEqual(response.data['users'][0]['username'], self.user1.username)

        odc1.add_admin_user(user=user2.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['users']), 2)

        # test federal admin
        odc1.remove_admin_user(user=self.user1)
        url = reverse('service-api:admin-odc-detail', kwargs={'id': odc1.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user1.set_federal_admin()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark', 'users'],
            response.data)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['organization'])
        self.assertEqual(len(response.data['users']), 1)
        self.assertEqual(response.data['users'][0]['id'], user2.id)

    def test_add_admin(self):
        app = register_and_set_app_id_for_test()

        user2 = get_or_create_user(username='test2@163.com')
        user3 = get_or_create_user(username='test3@qq.com')
        odc1 = OrgDataCenterManager.create_org_dc(
            name='测试', name_en='test11', organization_id=self.org.id,
            longitude=-10, latitude=80, sort_weight=0, remark='Test Remark66',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )

        # 云主机、对象存储服务单元
        server_unit1 = ServiceConfig(name='service1', name_en='service1 en', org_data_center=odc1)
        server_unit1.save(force_insert=True)
        pay1_server = server_unit1.check_or_register_pay_app_service()
        server_unit2 = ServiceConfig(name='service2', name_en='service2 en', org_data_center=odc1)
        server_unit2.save(force_insert=True)
        pay2_server = server_unit2.check_or_register_pay_app_service()

        obj_unit1 = ObjectsService(name='test1', name_en='test1_en', org_data_center=odc1)
        obj_unit1.save(force_insert=True)
        pay1_obj = obj_unit1.check_or_register_pay_app_service()
        obj_unit2 = ObjectsService(name='test2', name_en='test2_en', org_data_center=None)
        obj_unit2.save(force_insert=True)
        pay2_obj = obj_unit2.check_or_register_pay_app_service()
        self.assertEqual(PayAppService.objects.count(), 4)

        url = reverse('service-api:admin-odc-add-admin', kwargs={'id': 'test'})
        response = self.client.post(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user1)
        response = self.client.post(url, data={'test': 'dd'})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        response = self.client.post(url, data={'usernames': []})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        response = self.client.post(url, data={'usernames': ['test']})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # odc not exist
        self.user1.set_federal_admin()
        response = self.client.post(url, data={'usernames': ['test']})
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # user not exist
        url = reverse('service-api:admin-odc-add-admin', kwargs={'id': odc1.id})
        response = self.client.post(url, data={'usernames': ['test']})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # username 重复
        response = self.client.post(url, data={'usernames': ['test', 'test']})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # 有user not exist
        response = self.client.post(url, data={'usernames': [self.user1.username, 'test']})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        # 数据中心管理员同步到钱包结算单元管理员验证
        self.assertEqual(pay1_server.users.count(), 0)
        self.assertEqual(pay2_server.users.count(), 0)
        self.assertEqual(pay1_obj.users.count(), 0)
        self.assertEqual(pay2_obj.users.count(), 0)

        self.assertEqual(len(odc1.users.all()), 0)
        response = self.client.post(url, data={'usernames': [self.user1.username]})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark', 'users'],
            response.data)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['organization'])
        self.assertEqual(len(response.data['users']), 1)
        self.assertEqual(response.data['users'][0]['id'], self.user1.id)
        self.assertEqual(response.data['users'][0]['username'], self.user1.username)
        self.assertEqual(len(odc1.users.all()), 1)

        # 数据中心管理员同步到钱包结算单元管理员验证
        self.assertEqual(pay1_server.users.count(), 1)
        self.assertEqual(pay2_server.users.count(), 1)
        self.assertEqual(pay1_obj.users.count(), 1)
        self.assertEqual(pay2_obj.users.count(), 0)
        self.assertEqual(pay1_server.users.first().username, self.user1.username)
        self.assertEqual(pay2_server.users.first().username, self.user1.username)
        self.assertEqual(pay1_obj.users.first().username, self.user1.username)

        # 重复添加管理员
        response = self.client.post(url, data={'usernames': [self.user1.username]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['users']), 1)
        self.assertEqual(response.data['users'][0]['id'], self.user1.id)
        self.assertEqual(response.data['users'][0]['username'], self.user1.username)
        self.assertEqual(len(odc1.users.all()), 1)
        # 数据中心管理员同步到钱包结算单元管理员验证
        self.assertEqual(pay1_server.users.count(), 1)
        self.assertEqual(pay2_server.users.count(), 1)
        self.assertEqual(pay1_obj.users.count(), 1)
        self.assertEqual(pay2_obj.users.count(), 0)

        # 添加用户中有些已是管理员
        response = self.client.post(url, data={'usernames': [self.user1.username, user2.username]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['users']), 2)
        self.assertEqual([u['id'] for u in response.data['users']].sort(), [self.user1.id, user2.id].sort())
        self.assertEqual(len(odc1.users.all()), 2)
        # 数据中心管理员同步到钱包结算单元管理员验证
        self.assertEqual(pay1_server.users.count(), 2)
        self.assertEqual(pay2_server.users.count(), 2)
        self.assertEqual(pay1_obj.users.count(), 2)
        self.assertEqual(pay2_obj.users.count(), 0)
        self.assertTrue(pay1_server.users.filter(username=user2.username).exists())
        self.assertTrue(pay2_server.users.filter(username=user2.username).exists())
        self.assertTrue(pay1_obj.users.filter(username=user2.username).exists())

        response = self.client.post(url, data={'usernames': [self.user1.username, user2.username, user3.username]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['users']), 3)
        self.assertEqual([u['id'] for u in response.data['users']].sort(), [self.user1.id, user2.id, user3.id].sort())
        self.assertEqual(len(odc1.users.all()), 3)

        # 数据中心管理员同步到钱包结算单元管理员验证
        self.assertEqual(pay1_server.users.count(), 3)
        self.assertEqual(pay2_server.users.count(), 3)
        self.assertEqual(pay1_obj.users.count(), 3)
        self.assertEqual(pay2_obj.users.count(), 0)
        self.assertTrue(pay1_server.users.filter(username=user3.username).exists())
        self.assertTrue(pay2_server.users.filter(username=user3.username).exists())
        self.assertTrue(pay1_obj.users.filter(username=user3.username).exists())

    def test_remove_admin(self):
        app = register_and_set_app_id_for_test()

        user2 = get_or_create_user(username='test2@163.com')
        user3 = get_or_create_user(username='test3@qq.com')
        odc1 = OrgDataCenterManager.create_org_dc(
            name='测试', name_en='test11', organization_id=self.org.id,
            longitude=-10, latitude=80, sort_weight=0, remark='Test Remark66',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )
        odc1.add_admin_user(user=self.user1)
        odc1.add_admin_user(user=user2)
        odc1.add_admin_user(user=user3)

        # 云主机、对象存储服务单元
        server_unit1 = ServiceConfig(name='service1', name_en='service1 en', org_data_center=odc1)
        server_unit1.save(force_insert=True)
        pay1_server = server_unit1.check_or_register_pay_app_service()
        pay1_server.users.add(self.user1, user2, user3)
        server_unit2 = ServiceConfig(name='service2', name_en='service2 en', org_data_center=odc1)
        server_unit2.save(force_insert=True)
        pay2_server = server_unit2.check_or_register_pay_app_service()
        pay2_server.users.add(self.user1, user2)

        obj_unit1 = ObjectsService(name='test1', name_en='test1_en', org_data_center=odc1)
        obj_unit1.save(force_insert=True)
        pay1_obj = obj_unit1.check_or_register_pay_app_service()
        pay1_obj.users.add(user2, user3)
        obj_unit2 = ObjectsService(name='test2', name_en='test2_en', org_data_center=None)
        obj_unit2.save(force_insert=True)
        pay2_obj = obj_unit2.check_or_register_pay_app_service()
        pay2_obj.users.add(user3)
        self.assertEqual(PayAppService.objects.count(), 4)

        url = reverse('service-api:admin-odc-remove-admin', kwargs={'id': 'test'})
        response = self.client.post(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user1)
        response = self.client.post(url, data={'usernames': []})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        response = self.client.post(url, data={'test': 'dd'})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        response = self.client.post(url, data={'usernames': ['test']})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # odc not exist
        self.user1.set_federal_admin()
        response = self.client.post(url, data={'usernames': ['test']})
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # user not exist
        url = reverse('service-api:admin-odc-remove-admin', kwargs={'id': odc1.id})
        response = self.client.post(url, data={'usernames': ['test']})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # username 重复
        response = self.client.post(url, data={'usernames': ['test', 'test']})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # 有user not exist
        response = self.client.post(url, data={'usernames': [self.user1.username, 'test']})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        # 数据中心管理员同步到钱包结算单元管理员验证
        self.assertEqual(pay1_server.users.count(), 3)
        self.assertEqual(pay2_server.users.count(), 2)
        self.assertEqual(pay1_obj.users.count(), 2)
        self.assertEqual(pay2_obj.users.count(), 1)

        self.assertEqual(len(odc1.users.all()), 3)
        response = self.client.post(url, data={'usernames': [self.user1.username]})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark', 'users'],
            response.data)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['organization'])
        self.assertEqual(len(response.data['users']), 2)
        self.assertEqual([u['id'] for u in response.data['users']].sort(), [user3.id, user2.id].sort())
        self.assertEqual(len(odc1.users.all()), 2)

        # 数据中心管理员同步到钱包结算单元管理员验证
        self.assertEqual(pay1_server.users.count(), 2)
        self.assertEqual(pay2_server.users.count(), 1)
        self.assertEqual(pay1_obj.users.count(), 2)
        self.assertEqual(pay2_obj.users.count(), 1)
        self.assertEqual(pay2_server.users.first().username, user2.username)
        self.assertEqual(pay2_obj.users.first().username, user3.username)

        # 重复remove管理员
        response = self.client.post(url, data={'usernames': [self.user1.username]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['users']), 2)
        self.assertEqual([u['id'] for u in response.data['users']].sort(), [user3.id, user2.id].sort())
        self.assertEqual(len(odc1.users.all()), 2)
        # 数据中心管理员同步到钱包结算单元管理员验证
        self.assertEqual(pay1_server.users.count(), 2)
        self.assertEqual(pay2_server.users.count(), 1)
        self.assertEqual(pay1_obj.users.count(), 2)
        self.assertEqual(pay2_obj.users.count(), 1)
        self.assertEqual(pay2_server.users.first().username, user2.username)
        self.assertEqual(pay2_obj.users.first().username, user3.username)

        # remove用户中有些已是管理员
        response = self.client.post(url, data={'usernames': [self.user1.username, user2.username]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['users']), 1)
        self.assertEqual(response.data['users'][0]['id'], user3.id)
        self.assertEqual(response.data['users'][0]['username'], user3.username)
        self.assertEqual(len(odc1.users.all()), 1)
        # 数据中心管理员同步到钱包结算单元管理员验证
        self.assertEqual(pay1_server.users.count(), 1)
        self.assertEqual(pay2_server.users.count(), 0)
        self.assertEqual(pay1_obj.users.count(), 1)
        self.assertEqual(pay2_obj.users.count(), 1)
        self.assertEqual(pay1_obj.users.first().username, user3.username)
        self.assertEqual(pay1_server.users.first().username, user3.username)

        response = self.client.post(url, data={'usernames': [self.user1.username, user2.username, user3.username]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['users']), 0)
        self.assertEqual(len(odc1.users.all()), 0)
        # 数据中心管理员同步到钱包结算单元管理员验证
        self.assertEqual(pay1_server.users.count(), 0)
        self.assertEqual(pay2_server.users.count(), 0)
        self.assertEqual(pay1_obj.users.count(), 0)
        self.assertEqual(pay2_obj.users.count(), 1)

    def test_units(self):
        odc1 = OrgDataCenterManager.create_org_dc(
            name='测试', name_en='test', organization_id=self.org.id,
            longitude=-10, latitude=80, sort_weight=0, remark='test remark',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )
        odc2 = OrgDataCenterManager.create_org_dc(
            name='测试2', name_en='test2', organization_id=self.org.id,
            longitude=-10, latitude=80, sort_weight=0, remark='test remark2',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark2',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark2'
        )

        url = reverse('service-api:admin-odc-units', kwargs={'id': 'test'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user1)
        url = reverse('service-api:admin-odc-units', kwargs={'id': 'test'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user1.set_federal_admin()
        response = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # ok
        url = reverse('service-api:admin-odc-units', kwargs={'id': odc1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['org_data_center', 'server_units', 'object_units', 'monitor_server_units',
                           'monitor_ceph_units', 'monitor_tidb_units', 'site_log_units'], response.data)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data['org_data_center'])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['org_data_center']['organization'])
        self.assertIsInstance(response.data['server_units'], list)
        self.assertIsInstance(response.data['object_units'], list)
        self.assertIsInstance(response.data['monitor_server_units'], list)
        self.assertIsInstance(response.data['monitor_ceph_units'], list)
        self.assertIsInstance(response.data['monitor_tidb_units'], list)
        self.assertIsInstance(response.data['site_log_units'], list)

        # 云主机、对象存储服务单元
        server_unit1 = ServiceConfig(name='service1', name_en='service1 en', org_data_center=odc1)
        server_unit1.save(force_insert=True)
        server_unit2 = ServiceConfig(name='service2', name_en='service2 en', org_data_center=odc2)
        server_unit2.save(force_insert=True)

        obj_unit1 = ObjectsService(name='test1', name_en='test1_en', org_data_center=odc1)
        obj_unit1.save(force_insert=True)
        obj_unit2 = ObjectsService(name='test2', name_en='test2_en', org_data_center=odc2)
        obj_unit2.save(force_insert=True)

        url = reverse('service-api:admin-odc-units', kwargs={'id': odc1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data['org_data_center'])
        self.assertEqual(len(response.data['server_units']), 1)
        self.assertEqual(response.data['server_units'][0]['id'], server_unit1.id)
        self.assertKeysIn([
            "id", "name", "name_en", "service_type", "cloud_type", "add_time", "sort_weight",
            "need_vpn", "status", "org_data_center", 'longitude', 'latitude', 'pay_app_service_id',
            'disk_available', 'region_id', 'endpoint_url', 'api_version', 'username', 'extra', 'remarks'
        ], response.data["server_units"][0])

        self.assertEqual(len(response.data['object_units']), 1)
        self.assertEqual(response.data['object_units'][0]['id'], obj_unit1.id)
        self.assertKeysIn([
            'id', 'name', 'name_en', 'service_type', 'endpoint_url', 'add_time', 'status', 'remarks', 'provide_ftp',
            'ftp_domains', 'longitude', 'latitude', 'pay_app_service_id', 'org_data_center', 'sort_weight', 'version',
            'username'], response.data["object_units"][0])
        self.assertKeysIn(['id', "name", "name_en", 'sort_weight', 'organization'
                           ], response.data["object_units"][0]['org_data_center'])
        self.assertKeysIn(['id', "name", "name_en", 'sort_weight'
                           ], response.data["object_units"][0]['org_data_center']['organization'])
        self.assertEqual(len(response.data['monitor_server_units']), 0)
        self.assertEqual(len(response.data['monitor_ceph_units']), 0)
        self.assertEqual(len(response.data['monitor_tidb_units']), 0)
        self.assertEqual(len(response.data['site_log_units']), 0)

        # 各监控单元
        mntr_ceph1 = MonitorJobCeph(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10, org_data_center=odc1
        )
        mntr_ceph1.save(force_insert=True)
        mntr_ceph2 = MonitorJobCeph(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=10, org_data_center=odc2
        )
        mntr_ceph2.save(force_insert=True)

        mntr_server1 = MonitorJobServer(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10, org_data_center=odc1
        )
        mntr_server1.save(force_insert=True)
        mntr_server2 = MonitorJobServer(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=10, org_data_center=odc2
        )
        mntr_server2.save(force_insert=True)

        mntr_tidb1 = MonitorJobTiDB(
            name='name1', name_en='name_en1', job_tag='job_tag1', sort_weight=10, org_data_center=odc1
        )
        mntr_tidb1.save(force_insert=True)
        mntr_tidb2 = MonitorJobTiDB(
            name='name2', name_en='name_en2', job_tag='job_tag2', sort_weight=20, org_data_center=odc2
        )
        mntr_tidb2.save(force_insert=True)

        site_type1 = LogSiteType(name='obj', name_en='obj en', sort_weight=6)
        site_type1.save(force_insert=True)
        log_site1 = LogSite(
            name='name1', name_en='name_en1', log_type=LogSite.LogType.HTTP.value,
            site_type=site_type1, job_tag='job_tag1', sort_weight=10, org_data_center=odc1
        )
        log_site1.save(force_insert=True)
        log_site2 = LogSite(
            name='name2', name_en='name_en2', log_type=LogSite.LogType.HTTP.value,
            site_type_id=site_type1, job_tag='job_tag2', sort_weight=10, org_data_center=odc2
        )
        log_site2.save(force_insert=True)

        url = reverse('service-api:admin-odc-units', kwargs={'id': odc2.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['server_units']), 1)
        self.assertEqual(response.data['server_units'][0]['id'], server_unit2.id)
        self.assertEqual(len(response.data['object_units']), 1)
        self.assertEqual(response.data['object_units'][0]['id'], obj_unit2.id)

        self.assertEqual(len(response.data['monitor_ceph_units']), 1)
        self.assertEqual(response.data['monitor_ceph_units'][0]['id'], mntr_ceph2.id)
        self.assertKeysIn([
            'id', "name", "name_en", "job_tag", 'creation', 'remark',
            'sort_weight', 'grafana_url', 'dashboard_url', 'org_data_center'
        ], response.data['monitor_ceph_units'][0])
        self.assertKeysIn(['id', "name", "name_en", 'sort_weight', 'organization'
                           ], response.data["monitor_ceph_units"][0]['org_data_center'])
        self.assertKeysIn(['id', "name", "name_en", 'sort_weight'
                           ], response.data["monitor_ceph_units"][0]['org_data_center']['organization'])

        self.assertEqual(len(response.data['monitor_server_units']), 1)
        self.assertEqual(response.data['monitor_server_units'][0]['id'], mntr_server2.id)
        self.assertKeysIn([
            'id', "name", "name_en", "job_tag", 'creation', 'remark',
            'sort_weight', 'grafana_url', 'dashboard_url', 'org_data_center'
        ], response.data['monitor_server_units'][0])

        self.assertEqual(len(response.data['monitor_tidb_units']), 1)
        self.assertEqual(response.data['monitor_tidb_units'][0]['id'], mntr_tidb2.id)
        self.assertKeysIn([
            'id', "name", "name_en", "job_tag", 'creation', 'remark', 'version',
            'sort_weight', 'grafana_url', 'dashboard_url', 'org_data_center'
        ], response.data['monitor_tidb_units'][0])

        self.assertEqual(len(response.data['site_log_units']), 1)
        self.assertEqual(response.data['site_log_units'][0]['id'], log_site2.id)
        self.assertKeysIn([
            'id', "name", "name_en", "job_tag", 'creation', 'desc', 'log_type',
            'sort_weight', 'org_data_center'], response.data['site_log_units'][0])


class ODCTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='test1@cnic.cn')
        self.org = get_or_create_organization(name='test org')

    def test_list_odc(self):
        org2 = get_or_create_organization(name='test org2')
        odc1 = OrgDataCenterManager.create_org_dc(
            name='测试', name_en='test11', organization_id=self.org.id,
            longitude=-10, latitude=80, sort_weight=0, remark='test remark66',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )
        odc2 = OrgDataCenterManager.create_org_dc(
            name='测试2', name_en='test22', organization_id=org2.id,
            longitude=-10, latitude=80, sort_weight=0, remark='test remark88',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )

        url = reverse('service-api:odc-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark', 'map_display'],
            response.data['results'][0])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['results'][0]['organization'])

        # page page_size
        query = parse.urlencode(query={'page': 1, 'page_size': 1})
        response = self.client.get(f'{url}?{query}')
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], odc1.id)

        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{url}?{query}')
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], odc2.id)

        # query "org_id"
        query = parse.urlencode(query={'org_id': org2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], odc2.id)

        # query "search"
        query = parse.urlencode(query={'search': 'test1'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], odc1.id)

        query = parse.urlencode(query={'search': 'test remark'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'search': 'ddTestRemark'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # query "org_id", "search"
        query = parse.urlencode(query={'search': 'test1', 'org_id': org2.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'search': 'test1', 'org_id': odc1.organization_id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], odc1.id)
