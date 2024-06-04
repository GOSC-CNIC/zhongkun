from django.urls import reverse
from .test_administrator import GlobalAdministratorTests


class NetflowRoleAPITests(GlobalAdministratorTests):
    """
    查询当前用户的角色
    """

    def setUp(self):
        super().setUp()

    def test_anonymous_user(self):
        """
        查询当前用户的角色
        需要登陆
        """
        base_url = reverse('netflow-api:user-role')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        查询当前用户的角色
        普通用户返回null
        """
        base_url = reverse('netflow-api:user-role')
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['role'], response.data)
        self.assertEqual(response.data["role"], None)

    def test_group_admin_user(self):
        """
        查询当前用户的角色
        组管理员 group-admin
        """
        base_url = reverse('netflow-api:user-role')
        self.client.force_login(self.group_admin1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['role'], response.data)
        self.assertEqual(response.data["role"], 'group-admin')

    def test_group_user(self):
        """
        查询当前用户的角色
        组员 ordinary
        """
        base_url = reverse('netflow-api:user-role')
        self.client.force_login(self.group_user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['role'], response.data)
        self.assertEqual(response.data["role"], 'ordinary')

    def test_obs_user(self):
        """
        查询当前用户的角色
        运维管理员 admin
        """
        base_url = reverse('netflow-api:user-role')
        self.client.force_login(self.obs_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['role'], response.data)
        self.assertEqual(response.data["role"], 'admin')

    def test_super_user(self):
        """
        查询当前用户的角色
        超级管理员 super-admin
        """
        base_url = reverse('netflow-api:user-role')
        self.client.force_login(self.super_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['role'], response.data)
        self.assertEqual(response.data["role"], 'super-admin')
