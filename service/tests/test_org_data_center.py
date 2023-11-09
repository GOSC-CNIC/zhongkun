from urllib import parse

from django.urls import reverse

from utils.test import MyAPITransactionTestCase, get_or_create_user, get_or_create_organization

from ..models import OrgDataCenter
from ..odc_manager import OrgDataCenterManager


class AdminODCTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='test1@cnic.cn')
        self.org = get_or_create_organization(name='test org')

    def test_create_odc(self):
        url = reverse('api:admin-odc-list')

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
            name='测试', name_en='test', organization_id=self.org.id,
            longitude=-10, latitude=80, sort_weight=0, remark='test remark',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )

        url = reverse('api:admin-odc-list')
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
        odc1.users.add(self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data['results'][0])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['results'][0]['organization'])

        # test federal admin
        odc1.users.remove(self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        self.user1.set_federal_admin()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url', 'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data['results'][0])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['results'][0]['organization'])

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

        url = reverse('api:admin-odc-detail', kwargs={'id': 'notfound'})
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user1)
        url = reverse('api:admin-odc-detail', kwargs={'id': 'notfound'})

        # invalid organization_id
        data['organization_id'] = 'invalid'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        data['organization_id'] = odc1.organization.id

        # odc TargetNotExist
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # AccessDenied
        url = reverse('api:admin-odc-detail', kwargs={'id': odc1.id})
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

        url = reverse('api:admin-odc-detail', kwargs={'id': 'test'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user1)
        url = reverse('api:admin-odc-detail', kwargs={'id': 'test'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        url = reverse('api:admin-odc-detail', kwargs={'id': odc1.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # odc admin
        odc1.users.add(self.user1)
        url = reverse('api:admin-odc-detail', kwargs={'id': odc1.id})
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

        odc1.users.add(user2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['users']), 2)

        # test federal admin
        odc1.users.remove(self.user1)
        url = reverse('api:admin-odc-detail', kwargs={'id': odc1.id})
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


class ODCTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='test1@cnic.cn')
        self.org = get_or_create_organization(name='test org')

    def test_list_odc(self):
        org2 = get_or_create_organization(name='test org2')
        odc1 = OrgDataCenterManager.create_org_dc(
            name='测试', name_en='test', organization_id=self.org.id,
            longitude=-10, latitude=80, sort_weight=0, remark='test remark',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )
        odc2 = OrgDataCenterManager.create_org_dc(
            name='测试2', name_en='test2', organization_id=org2.id,
            longitude=-10, latitude=80, sort_weight=0, remark='test remark',
            thanos_endpoint_url='https://thanosxxxx.cn', thanos_receive_url='https://thanosrexxxx.cn',
            thanos_username='tom@cnic.cn', thanos_password='test123456', thanos_remark='thanos remark',
            loki_endpoint_url='https://lokixxxx.cn', loki_receive_url='https://lokerexxxx.cn',
            loki_username='jerry@qq.com', loki_password='loki123456', loki_remark='loki remark'
        )

        url = reverse('api:odc-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'longitude', 'latitude', 'sort_weight', 'remark'],
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
