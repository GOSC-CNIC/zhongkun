from utils.test import get_or_create_user, MyAPITransactionTestCase
from django.urls import reverse
from link.models import LinkUserRole
from link.managers.userrole_manager import UserRoleWrapper
from urllib import parse


class TaskTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        self.user4 = get_or_create_user(username='wangwu@cnic.cn')
        urole = LinkUserRole(user=self.user2, is_admin=False, is_readonly=False)
        urole.save(force_insert=True)
        urole = LinkUserRole(user=self.user3, is_admin=False, is_readonly=True)
        urole.save(force_insert=True)
        urole = LinkUserRole(user=self.user4, is_admin=True, is_readonly=False)
        urole.save(force_insert=True)

    def test_list_userrole(self):
        # user role 
        base_url = reverse('api:link-userrole-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)

        # link user role is None
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertKeysIn([
            'id', 'is_admin', 'is_readonly', 'create_time', 'update_time', 'user'
        ], data)
        self.assertKeysIn([
            'id', 'username'
        ], data['user'])
        self.assertEqual(data['is_admin'], False)
        self.assertEqual(data['is_readonly'], False)
        self.assertEqual(data['user']['username'], 'tom@qq.com')

        # link user role without permission
        self.client.force_login(self.user2)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data['is_admin'], False)
        self.assertEqual(data['is_readonly'], False)
        self.assertEqual(data['user']['username'], 'lisi@cnic.cn')

        # link user role with read permission
        self.client.force_login(self.user3)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data['is_admin'], False)
        self.assertEqual(data['is_readonly'], True)
        self.assertEqual(data['user']['username'], 'zhangs@cnic.cn')

        # link user role without permission
        self.client.force_login(self.user4)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data['is_admin'], True)
        self.assertEqual(data['is_readonly'], False)
        self.assertEqual(data['user']['username'], 'wangwu@cnic.cn')