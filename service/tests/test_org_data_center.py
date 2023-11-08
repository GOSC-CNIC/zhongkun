from django.urls import reverse

from utils.test import MyAPITransactionTestCase, get_or_create_user, get_or_create_organization


class OrgDataCenterTests(MyAPITransactionTestCase):

    def setUp(self):
        self.user1 = get_or_create_user(username='test1@cnic.cn')
        self.user2 = get_or_create_user(username='test2@cnic.cn')
        self.dc = get_or_create_organization(name='dc')

    def test_create_org_data_center(self):
        url = reverse('api:org-dc-list')

        data = {
            'name': '',
            'name_en': '',
            'organization': '',
            'users': '',
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

        data['organization'] = self.dc.id
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='ValidationError', response=response)

        data['users'] = 'test333'
        response = self.client.post(url, data=data)

        self.assertErrorResponse(status_code=404, code='UserNotExist', response=response)

        data['organization'] = 'sdfweirfweoprwpo'
        response = self.client.post(url, data=data)

        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        data['organization'] = self.dc.id
        data['users'] = self.user1.username
        response = self.client.post(url, data=data)
        
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['users'] = f'{self.user1.username}, {self.user2.username}'
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['users'] = f'{self.user1.username}:       {self.user2.username}'  # 格式错误
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=404, code='UserNotExist', response=response)

        data['users'] = f'{self.user1.username},       {self.user2.username}'
        response = self.client.post(url, data=data)
        
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['thanos_endpoint_url'] = 'xxxx'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='ValidationError', response=response)

        data['thanos_endpoint_url'] = 'https://thanosxx.cn'
        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['thanos_username'] = 'thanos'
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['thanos_password'] = 'thanos'
        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['thanos_receive_url'] = 'thanos'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='ValidationError', response=response)

        data['thanos_receive_url'] = 'http://thanosrexx.cn'
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['thanos_remark'] = 'thanos'
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['loki_endpoint_url'] = 'thanos'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='ValidationError', response=response)

        data['loki_endpoint_url'] = 'http://lokixxxthanos.cnhttps://xxx'
        response = self.client.post(url, data=data)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['loki_username'] = 'thanos'
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['loki_password'] = 'thanos'
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['loki_receive_url'] = 'lokixx.cn'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='ValidationError', response=response)

        data['loki_receive_url'] = 'https://lokixx.cn'
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['loki_remark'] = 'thanos'
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['longitude'] = 'ssd'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['longitude'] = '12'
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['longitude'] = 10.2
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['latitude'] = 'ssd'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['latitude'] = 10.2
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['sort_weight'] = 'ssd'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['sort_weight'] = 10.2
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['sort_weight'] = 10
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['users'] = f'{self.user1.username},{self.user2.username}'
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
                           'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
                           'thanos_remark',
                           'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
                          response.data)

        data['users'] = f'{self.user1.username}，{self.user2.username}'
        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='ValidationError', response=response)

    def test_list_org_data_center(self):
        url = reverse('api:org-dc-list')

        data = {
            'name': '测试',
            'name_en': 'test',
            'organization': self.dc.id,
            'users': self.user1.username,
            'longitude': 0,
            'latitude': 0,
            'sort_weight': 0,
            'remark': '无',
            'thanos_endpoint_url': 'https://thanosxxxx.cn',
            'thanos_username': 'ss',
            'thanos_password': 'xxx',
            'thanos_receive_url': 'https://thanosrexxxx.cn',
            'thanos_remark': '',
            'loki_endpoint_url': 'https://lokixxxx.cn',
            'loki_username': 'xxx',
            'loki_password': 'xxx',
            'loki_receive_url': 'https://lokerexxxx.cn',
            'loki_remark': ''
        }

        self.client.force_login(self.user2)
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)

        self.client.logout()

        response = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user2)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data['results'][0])

        self.assertKeysIn(['id', 'name'], response.data['results'][0]['organization'])
        self.assertKeysIn(['id', 'username'], response.data['results'][0]['users'][0])

    def test_update_org_data_center(self):
        data = {
            'name': '测试',
            'name_en': 'test',
            'organization': self.dc.id,
            'users': self.user1.username,
            'longitude': 0,
            'latitude': 0,
            'sort_weight': 0,
            'remark': '无',
            'thanos_endpoint_url': 'https://thanosxxxx.cn',
            'thanos_username': 'ss',
            'thanos_password': 'xxx',
            'thanos_receive_url': 'https://thanosrexxxx.cn',
            'thanos_remark': '',
            'loki_endpoint_url': 'https://lokixxxx.cn',
            'loki_username': 'xxx',
            'loki_password': 'xxx',
            'loki_receive_url': 'https://lokerexxxx.cn',
            'loki_remark': ''
        }
        url = reverse('api:org-dc-list')

        response = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user2)
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        org_data_center_id = response.data["id"]

        self.client.logout()
        url = reverse('api:org-dc-detail', kwargs={'id': org_data_center_id})
        data['name'] = '测试2'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user2)
        url = reverse('api:org-dc-detail', kwargs={'id': org_data_center_id})
        data['name'] = '测试2'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['name'], '测试2')

        data['name_en'] = 'test2test2test2test2test2test2test2test2test2test2test2test' \
                          '2test2test2test2test2test2test2test2test2test2test2test2test2test2test2' \
                          'test2test2test2test2test2test2test2test2test2test2test2test2test2tes' \
                          't2test2test2test2test2test2test2test2test2test2test2test2test2test2test2'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['name_en'] = 'name_en'
        response = self.client.put(url, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['name_en'], 'name_en')

        data['organization'] = 'fsdfeterter'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        self.dc2 = get_or_create_organization(name='dc2')
        data['organization'] = self.dc2.id
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)

        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['organization']['name'], self.dc2.name)

        data['users'] = 'test3@cnic.cn'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=404, code='UserNotExist', response=response)

        self.user3 = get_or_create_user(username='test3@cnic.cn')
        data['users'] = self.user3.username
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['users'][1]['username'], self.user3.username)

        data['users'] = self.user2.username
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['users'][1]['username'], self.user2.username)

        data['users'] = f'{self.user1.username}, {self.user2.username}, {self.user3.username}'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)

        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['users'][0]['username'], self.user1.username)
        self.assertEqual(response.data['users'][1]['username'], self.user2.username)
        self.assertEqual(response.data['users'][2]['username'], self.user3.username)

        data['users'] = f'{self.user1.username},       {self.user3.username}'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)

        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['users'][0]['username'], self.user1.username)
        self.assertEqual(response.data['users'][1]['username'], self.user2.username)
        self.assertEqual(response.data['users'][2]['username'], self.user3.username)

        data['thanos_endpoint_url'] = 'thanos.cn'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='ValidationError', response=response)

        data['thanos_endpoint_url'] = 'https://thanos.cn'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['thanos_endpoint_url'], 'https://thanos.cn')

        data['thanos_receive_url'] = 'receivethanos.cn'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='ValidationError', response=response)

        data['thanos_receive_url'] = 'https://receivethanos.cn'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['thanos_receive_url'], 'https://receivethanos.cn')

        data['loki_endpoint_url'] = 'receiveloki.cn'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='ValidationError', response=response)

        data['loki_endpoint_url'] = 'https://receiveloki.cn'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['loki_endpoint_url'], 'https://receiveloki.cn')

        data['loki_receive_url'] = 'receiveloki.cn'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='ValidationError', response=response)

        data['loki_receive_url'] = 'https://receiveloki.cn'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['loki_receive_url'], 'https://receiveloki.cn')

        data['longitude'] = '12'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['longitude'], 12)

        data['longitude'] = '12tt'
        response = self.client.put(url, data=data)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        data['longitude'] = 12.0000002
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)

        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['longitude'], 12.0000002)

        data['latitude'] = '12tt'
        response = self.client.put(url, data=data)

        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        data['latitude'] = 12.0000002
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)

        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['latitude'], 12.0000002)

        data['sort_weight'] = -100
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['sort_weight'], -100)

        data['remark'] = 'remark123'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['remark'], 'remark123')

        data['thanos_username'] = 'thanos_username123'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['thanos_username'], 'thanos_username123')

        data['thanos_username'] = 123454
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['thanos_username'], '123454')

        data['thanos_password'] = '123454'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['thanos_password'], '123454')

        data['thanos_remark'] = '123454'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['thanos_remark'], '123454')

        data['loki_username'] = '123454'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['loki_username'], '123454')

        data['loki_password'] = '123454'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['loki_password'], '123454')

        data['loki_remark'] = '123454'
        response = self.client.put(url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'name', 'name_en', 'organization', 'users', 'longitude', 'latitude', 'sort_weight', 'remark',
             'thanos_endpoint_url', 'thanos_username', 'thanos_password', 'thanos_receive_url',
             'thanos_remark',
             'loki_endpoint_url', 'loki_username', 'loki_password', 'loki_receive_url', 'loki_remark'],
            response.data)
        self.assertEqual(response.data['loki_remark'], '123454')
