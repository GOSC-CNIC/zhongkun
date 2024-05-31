from django.urls import reverse

from utils.test import get_or_create_user, MyAPITransactionTestCase
from apps.app_net_link.managers.common import NetLinkUserRoleWrapper
from apps.app_net_link.permissions import LinkIPRestrictor


class NetLinkUserRoleTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

        LinkIPRestrictor.add_ip_rule(ip_value='0.0.0.0/0')
        LinkIPRestrictor.clear_cache()

    def test_list_user_role(self):
        base_url = reverse('net_link-api:link-userrole-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'user', 'is_link_admin', 'is_link_readonly', 'creation_time', 'update_time'], response.data)
        self.assertKeysIn(['id', 'username'], response.data['user'])
        self.assertEqual(response.data['user']['id'], self.user1.id)
        self.assertFalse(response.data['is_link_admin'])
        self.assertFalse(response.data['is_link_readonly'])

        u1_role_wrapper = NetLinkUserRoleWrapper(self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_role()
        u1_role_wrapper.set_link_admin(True)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_link_admin'])
        self.assertFalse(response.data['is_link_readonly'])

        u1_role_wrapper.set_link_admin(False)
        u1_role_wrapper.set_link_readonly(True)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_link_admin'])
        self.assertTrue(response.data['is_link_readonly'])

        # user2
        self.client.logout()
        self.client.force_login(self.user2)
        u2_role_wrapper = NetLinkUserRoleWrapper(user=self.user2)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['is_link_admin'])
        self.assertFalse(response.data['is_link_readonly'])

        u2_role_wrapper.user_role = u2_role_wrapper.get_or_create_user_role()
        u2_role_wrapper.set_link_readonly(True)
        u2_role_wrapper.set_link_admin(True)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['is_link_admin'])
        self.assertTrue(response.data['is_link_readonly'])
