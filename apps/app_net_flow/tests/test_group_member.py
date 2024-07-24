from django.conf import settings
from django.urls import reverse
from .test_administrator import GlobalAdministratorTests


class NetflowGroupMemberListTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()

    def test_anonymous_user(self):
        """
        查询组内成员列表
        需要登陆
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:member-list')
        url = f'{base_url}?menu={group_id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        查询组内成员列表
        普通用户无查看权限
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:member-list')
        url = f'{base_url}?menu={group_id}'
        self.client.force_login(self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        查询组内成员列表
        组员 无查看权限
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:member-list')
        url = f'{base_url}?menu={group_id}'
        self.client.force_login(self.group_user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        查询组内成员列表
        组管理员 可查看
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:member-list')
        url = f'{base_url}?menu={group_id}'
        self.client.force_login(self.group_admin1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 2)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn(['id', "role", 'inviter', 'creation', 'username', ], results[0])

    def test_obs_user(self):
        """
        查询组内成员列表
        运维管理员可查看
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:member-list')
        url = f'{base_url}?menu={group_id}'
        self.client.force_login(self.obs_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 2)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn(['id', "role", 'inviter', 'creation', 'username', ], results[0])

    def test_super_user(self):
        """
        查询组内成员列表
        超级管理员可查看
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:member-list')
        url = f'{base_url}?menu={group_id}'
        self.client.force_login(self.super_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 2)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn(['id', "role", 'inviter', 'creation', 'username', ], results[0])


class NetflowGroupMemberCreateTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()

    def test_anonymous_user(self):
        """
        添加组内成员
        需要登陆
        """
        base_url = reverse('netflow-api:member-list')
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        添加组内成员
        普通用户 无权限添加
        """
        base_url = reverse('netflow-api:member-list')
        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        添加组内成员
        组员 无添加权限
        """
        base_url = reverse('netflow-api:member-list')
        self.client.force_login(self.group_user1)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        添加组内成员
        组管理员 有添加权限
        """
        base_url = reverse('netflow-api:member-list')
        self.client.force_login(self.group_admin1)
        group_id = self.second_level_menu1.id
        user_email = self.user1.username
        response = self.client.post(base_url, data={'menu': group_id, 'member': user_email})
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['menu', "member"], response.data)
        # 重复添加
        response = self.client.post(base_url, data={'menu': group_id, 'member': user_email})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertTrue(response.data['message'] == '用户已经存在，请勿重复添加')
        self.assertTrue(response.data['code'] == 'Existed')

        response = self.client.post(base_url, data={'menu': group_id, 'member': "unknown@cnic.cn"})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "invalid")
        self.assertTrue('无效的用户邮箱' in response.data['message'])

        response = self.client.post(base_url, data={'menu': "unknown group id", 'member': "unknown@cnic.cn"})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        添加组内成员
        运维管理员 无权限
        """
        base_url = reverse('netflow-api:member-list')
        self.client.force_login(self.obs_user)
        group_id = self.second_level_menu1.id
        user_email = self.user1.username
        response = self.client.post(base_url, data={'menu': group_id, 'member': user_email})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        添加组内成员
        超级管理员 有添加权限
        """
        base_url = reverse('netflow-api:member-list')
        self.client.force_login(self.super_user)
        group_id = self.second_level_menu1.id
        user_email = self.user1.username
        response = self.client.post(base_url, data={'menu': group_id, 'member': user_email})
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['menu', "member"], response.data)
        response = self.client.post(base_url, data={'menu': group_id, 'member': user_email})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertTrue(response.data['message'] == '用户已经存在，请勿重复添加')
        self.assertTrue(response.data['code'] == 'Existed')

        response = self.client.post(base_url, data={'menu': group_id, 'member': "unknown@cnic.cn"})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "invalid")
        self.assertTrue('无效的用户邮箱' in response.data['message'])
        response = self.client.post(base_url, data={'menu': "unknown group id", 'member': "unknown@cnic.cn"})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)


class NetflowGroupMemberRetrieveTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()

    def test_anonymous_user(self):
        """
        查看指定 组内成员
        需要登陆
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        查看指定 组内成员
        普通用户 无权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        查看指定 组内成员
        组员 无权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        查看指定 组内成员
        组管理员 有权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_admin1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertEqual(response.data["role"], "ordinary")

    def test_obs_user(self):
        """
        查看指定 组内成员
        运维管理员 有权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.obs_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertEqual(response.data["role"], "ordinary")

    def test_super_user(self):
        """
        查看指定 组内成员
        超级管理员 有权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.super_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertEqual(response.data["role"], "ordinary")


class NetflowGroupMemberUpdateTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()

    def test_anonymous_user(self):
        """
        修改指定 组内成员
        需要登陆
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        修改指定 组内成员
        普通用户 无权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.user1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        修改指定 组内成员
        组员 无权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_user1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        修改指定 组内成员
        组管理员 有对应组内的权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_admin2)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")
        self.client.logout()
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_admin1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertEqual(response.data["role"], "ordinary")
        response = self.client.put(base_url, data={'role': 'group-admin'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertEqual(response.data["role"], "group-admin")

        response = self.client.put(base_url, data={'role': 'test-admin'})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertTrue('invalid_choice' in response.data['message'])

    def test_father_group(self):
        """
        上级分组的管理员 有权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_admin3)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertEqual(response.data["role"], "ordinary")
        response = self.client.put(base_url, data={'role': 'test-admin'})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertTrue('invalid_choice' in response.data['message'])
        response = self.client.put(base_url, data={'role': 'group-admin'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertEqual(response.data["role"], "group-admin")

    def test_not_father_group(self):
        """
        非上级分组的管理员 无权限
        """
        self.client.logout()
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_admin4)
        response = self.client.put(base_url, data={'role': 'group-admin'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        修改指定 组内成员
        运维管理员 无权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.obs_user)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        修改指定 组内成员
        超级管理员 有权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.super_user)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertEqual(response.data["role"], "ordinary")
        response = self.client.put(base_url, data={'role': 'group-admin'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertEqual(response.data["role"], "group-admin")

        response = self.client.put(base_url, data={'role': 'test-admin'})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertTrue('invalid_choice' in response.data['message'])


class NetflowGroupMemberDestroyTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()

    def test_anonymous_user(self):
        """
        删除指定 组内成员
        需要登陆
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        response = self.client.delete(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        删除指定 组内成员
        普通用户 无权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.user1)
        response = self.client.delete(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        删除指定 组内成员
        组员 无权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_user1)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        删除指定 组内成员
        组管理员 有当前组权限
        """
        # 不存在的组员
        base_url = reverse('netflow-api:member-detail', args=["test"])
        self.client.force_login(self.group_admin2)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")
        self.client.logout()
        # 非当前组管理员，无权限
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_admin2)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")
        self.client.logout()

        # 当前组管理员，有权限
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_admin1)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(response.data is None)
        self.client.logout()

    def test_father_group(self):
        """
        上级分组的管理员 有权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_admin3)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(response.data is None)
        self.client.logout()

    def test_not_father_group(self):
        """
        非上级分组的管理员 无权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.group_admin4)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        删除指定 组内成员
        运维管理员 无权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.obs_user)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        删除指定 组内元素
        超级管理员 有权限
        """
        base_url = reverse('netflow-api:member-detail', args=[self.member1.id])
        self.client.force_login(self.super_user)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(response.data is None)

        base_url = reverse('netflow-api:member-detail', args=[self.menu2_member1.id])
        self.client.force_login(self.super_user)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(response.data is None)
        base_url = reverse('netflow-api:member-detail', args=['test'])
        self.client.force_login(self.super_user)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 404)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotFound")
