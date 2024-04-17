from urllib import parse
from datetime import datetime

from django.urls import reverse

from apps.vo.models import VirtualOrganization
from utils.test import get_or_create_service
from utils.time import utc
from . import MyAPITestCase, get_or_create_user


class UserTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='tom@cnic.cn')
        self.service = get_or_create_service()

    def test_account(self):
        base_url = reverse('api:user-account')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "username", "fullname", "role"], response.data)

        self.assertEqual(response.data['id'], self.user.id)
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['fullname'], self.user.get_full_name())
        self.assertEqual(response.data['role'], self.user.role)

    def test_permission_policy(self):
        base_url = reverse('api:user-permission-policy')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["vms", "role"], response.data)
        self.assertEqual(response.data['role'], self.user.Roles.ORDINARY)
        vms = response.data['vms']
        self.assertKeysIn(["service_ids", "role"], vms)
        self.assertEqual(vms['role'], 'admin')
        self.assertIsInstance(vms['service_ids'], list)
        self.assertEqual(len(vms['service_ids']), 0)

        self.user.set_federal_admin()
        self.service.users.add(self.user)

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["vms", "role"], response.data)
        self.assertEqual(response.data['role'], self.user.Roles.FEDERAL)
        vms = response.data['vms']
        self.assertKeysIn(["service_ids", "role"], vms)
        self.assertEqual(vms['role'], 'admin')
        self.assertIsInstance(vms['service_ids'], list)
        self.assertEqual(len(vms['service_ids']), 1)
        self.assertEqual(vms['service_ids'][0], self.service.id)

    def test_list_user(self):
        user_lilei = get_or_create_user(username='lilei@cnic.cn')
        get_or_create_user(username='zhangsan@cnic.cn')
        get_or_create_user(username='lisi@cnic.cn')

        base_url = reverse('api:user-list')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user.set_federal_admin()
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(len(response.data['results']), 4)

        # query "search"
        query = parse.urlencode(query={'search': 'li'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'search': 'lil'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], user_lilei.id)

        # query "federal_admin"
        query = parse.urlencode(query={'federal_admin': 'tru'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={'federal_admin': 'false'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'federal_admin': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(keys=['id', 'username', 'fullname', 'role'], container=response.data['results'][0])
        self.assertEqual(response.data['results'][0]['id'], self.user.id)


class AdminUserStatisticsTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='tom@cnic.cn')

    def test_statistics(self):
        base_url = reverse('api:admin-user-statistics-list')
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user.set_federal_admin()
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['user_count'], 1)
        self.assertEqual(r.data['vo_count'], 0)

        query = parse.urlencode(query={'time_start': '2023-05-01T00:00:00'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'time_end': '2023-05-01T00:00:00'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'time_start': '2023-05-02T00:00:00Z', 'time_end': '2023-05-01T00:00:00Z'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=r)

        query = parse.urlencode(query={'time_start': '2023-05-02T00:00:00Z', 'time_end': '2023-05-21T00:00:00Z'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)

        query = parse.urlencode(query={'time_start': '2023-05-02T00:00:00Z'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['user_count'], 1)
        self.assertEqual(r.data['vo_count'], 0)

        user2 = get_or_create_user(username='test2@cnic.cn')
        user2.date_joined = datetime(year=2023, month=4, day=1, tzinfo=utc)
        user2.save(update_fields=['date_joined'])

        user3 = get_or_create_user(username='test3@cnic.cn')
        user3.date_joined = datetime(year=2023, month=6, day=1, tzinfo=utc)
        user3.save(update_fields=['date_joined'])

        vo1 = VirtualOrganization(name='vo1', owner_id=self.user.id)
        vo1.save(force_insert=True)
        vo2 = VirtualOrganization(name='vo2', owner_id=self.user.id)
        vo2.save(force_insert=True)
        vo2.creation_time = datetime(year=2023, month=4, day=1, tzinfo=utc)
        vo2.save(update_fields=['creation_time'])

        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['user_count'], 3)
        self.assertEqual(r.data['vo_count'], 2)

        query = parse.urlencode(query={'time_start': '2023-05-01T00:00:00Z'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['user_count'], 2)
        self.assertEqual(r.data['vo_count'], 1)

        query = parse.urlencode(query={'time_end': '2023-05-01T00:00:00Z'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['user_count'], 1)
        self.assertEqual(r.data['vo_count'], 1)
