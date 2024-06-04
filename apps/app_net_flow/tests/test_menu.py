from django.conf import settings
from django.urls import reverse
from .test_administrator import GlobalAdministratorTests

from utils.test import get_or_create_user
from utils.test import get_or_create_user
from utils.test import MyAPITestCase
from utils.test import MyAPITransactionTestCase
from apps.app_net_flow.models import MenuModel
from apps.app_net_flow.models import ChartModel
from apps.app_net_flow.serializers import MenuModelSerializer


class NetflowMenuSerializerTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()

    def test_menu_serializer(self):
        self.assertFalse(MenuModelSerializer(data={}).is_valid())

        self.assertFalse(MenuModelSerializer(data={
            "name": 'name1',
            "sort_weight": '',
        }).is_valid())
        self.assertTrue(MenuModelSerializer(data={
            "name": 'name1',
            "sort_weight": -99,
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "name": 'name1',
            "sort_weight": -0.1,
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "name": 'name1',
            "sort_weight": True,
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "name": 100,
            "sort_weight": True,
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "name": -1,
            "sort_weight": True,
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "name": False,
            "sort_weight": True,
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "remark": True,
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "remark": -1,
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "remark": "备注1",
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "father": False,
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "father": -1,
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "father": "",
        }).is_valid())
        self.assertFalse(MenuModelSerializer(data={
            "father": None,
        }).is_valid())


class NetflowMenuListTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()

    def test_anonymous_user(self):
        """
        查询当前用户权限内的分组列表
        需要登陆
        """
        base_url = reverse('netflow-api:menu-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        查询当前用户权限内的分组列表
        普通用户无查看权限
        """
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "results"], response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_group_user(self):
        """
        查询当前用户权限内的分组列表
        组员 可查看所有所在的分组列表，且没有管理权限
        """
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.group_user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'results'], response.data)
        results = response.data['results']
        self.assertTrue(len(results) == 1)
        self.assertEqual(results[0].get('name'), '顶级分组1')
        self.assertEqual(results[0].get('father_id'), 'root')
        self.assertEqual(results[0].get('level'), 0)
        self.assertEqual(results[0].get('admin'), False)
        self.assertEqual(results[0].get('sub_categories')[0].get('name'), '一级分组1')
        self.assertEqual(results[0].get('sub_categories')[0].get('level'), 1)
        self.assertEqual(results[0].get('sub_categories')[0].get('admin'), False)
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('name'), '二级分组1')
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('level'), 2)
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('admin'), False)
        self.assertTrue(results[0].get('sub_categories')[0].get('sub_categories')[0].get('sub_categories') == [])

    def test_group_admin_user(self):
        """
        查询当前用户权限内的分组列表
        组管理员 可查看所有所在的分组列表，且有管理权限
        """
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.group_admin1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'results'], response.data)
        results = response.data['results']
        self.assertTrue(len(results) == 1)
        self.assertEqual(results[0].get('name'), '顶级分组1')
        self.assertEqual(results[0].get('father_id'), 'root')
        self.assertEqual(results[0].get('level'), 0)
        self.assertEqual(results[0].get('admin'), False)
        self.assertEqual(results[0].get('sub_categories')[0].get('name'), '一级分组1')
        self.assertEqual(results[0].get('sub_categories')[0].get('level'), 1)
        self.assertEqual(results[0].get('sub_categories')[0].get('admin'), False)
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('name'), '二级分组1')
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('level'), 2)
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('admin'), True)
        self.assertTrue(results[0].get('sub_categories')[0].get('sub_categories')[0].get('sub_categories') == [])

    def test_super_user(self):
        """
        查询当前用户权限内的分组列表
        超级管理员可查看
        """
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.super_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'results'], response.data)
        results = response.data['results']
        self.assertTrue(len(results) == 3)
        # 顶级分组
        self.assertEqual(results[0].get('name'), '顶级分组1')
        self.assertEqual(results[0].get('father_id'), 'root')
        self.assertEqual(results[0].get('level'), 0)
        self.assertEqual(results[0].get('admin'), True)
        self.assertTrue(results[0].get('sub_categories') is not None)
        self.assertEqual(results[1].get('name'), '顶级分组2')
        self.assertEqual(results[1].get('father_id'), 'root')
        self.assertEqual(results[1].get('level'), 0)
        self.assertEqual(results[1].get('admin'), True)
        self.assertEqual(results[1].get('sub_categories'), [])
        self.assertEqual(results[2].get('name'), '顶级分组3')
        self.assertEqual(results[2].get('father_id'), 'root')
        self.assertEqual(results[2].get('level'), 0)
        self.assertEqual(results[2].get('admin'), True)
        self.assertEqual(results[2].get('sub_categories'), [])
        # 一级分组
        self.assertEqual(results[0].get('sub_categories')[0].get('name'), '一级分组1')
        self.assertEqual(results[0].get('sub_categories')[0].get('level'), 1)
        self.assertEqual(results[0].get('sub_categories')[0].get('admin'), True)
        self.assertTrue(results[0].get('sub_categories')[0].get('sub_categories') is not None)

        self.assertEqual(results[0].get('sub_categories')[1].get('name'), '一级分组2')
        self.assertEqual(results[0].get('sub_categories')[1].get('level'), 1)
        self.assertEqual(results[0].get('sub_categories')[1].get('admin'), True)
        self.assertEqual(results[0].get('sub_categories')[1].get('sub_categories'), [])

        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('name'), '二级分组1')
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('level'), 2)
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('level'), 2)
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('admin'), True)
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('sub_categories'), [])

    def test_obs_user(self):
        """
        查询当前用户权限内的分组列表
        运维管理员可查看
        """
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.obs_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'results'], response.data)
        results = response.data['results']
        self.assertTrue(len(results) == 3)
        # 顶级分组
        self.assertEqual(results[0].get('name'), '顶级分组1')
        self.assertEqual(results[0].get('father_id'), 'root')
        self.assertEqual(results[0].get('level'), 0)
        self.assertEqual(results[0].get('admin'), False)
        self.assertTrue(results[0].get('sub_categories') is not None)
        self.assertEqual(results[1].get('name'), '顶级分组2')
        self.assertEqual(results[1].get('father_id'), 'root')
        self.assertEqual(results[1].get('level'), 0)
        self.assertEqual(results[1].get('admin'), False)
        self.assertEqual(results[1].get('sub_categories'), [])
        self.assertEqual(results[2].get('name'), '顶级分组3')
        self.assertEqual(results[2].get('father_id'), 'root')
        self.assertEqual(results[2].get('level'), 0)
        self.assertEqual(results[2].get('admin'), False)
        self.assertEqual(results[2].get('sub_categories'), [])
        # 一级分组
        self.assertEqual(results[0].get('sub_categories')[0].get('name'), '一级分组1')
        self.assertEqual(results[0].get('sub_categories')[0].get('level'), 1)
        self.assertEqual(results[0].get('sub_categories')[0].get('admin'), False)
        self.assertTrue(results[0].get('sub_categories')[0].get('sub_categories') is not None)

        self.assertEqual(results[0].get('sub_categories')[1].get('name'), '一级分组2')
        self.assertEqual(results[0].get('sub_categories')[1].get('level'), 1)
        self.assertEqual(results[0].get('sub_categories')[1].get('admin'), False)
        self.assertEqual(results[0].get('sub_categories')[1].get('sub_categories'), [])

        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('name'), '二级分组1')
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('level'), 2)
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('level'), 2)
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('admin'), False)
        self.assertEqual(results[0].get('sub_categories')[0].get('sub_categories')[0].get('sub_categories'), [])


class NetflowMenuCreateTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()

    def test_anonymous_user(self):
        """
        创建分组
        需要登陆
        """
        base_url = reverse('netflow-api:menu-list')
        response = self.client.post(base_url, data={'test': 'test'})

        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        创建分组
        普通用户无添加权限
        """
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={'test': 'test'})

        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        创建分组
        组员无添加权限
        """
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.group_user1)
        response = self.client.post(base_url, data={'test': 'test'})

        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        创建分组
        组管理员无添加权限
        """
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.group_admin1)
        response = self.client.post(base_url, data={'test': 'test'})

        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        创建分组
        运维管理员无添加权限
        """
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.obs_user)
        response = self.client.post(base_url, data={'test': 'test'})

        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        创建分组
        超级管理员 有添加权限
        """
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.super_user)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "invalid")
        response = self.client.post(base_url, data={'name': '测试分组'})
        self.assertEqual(response.status_code, 500)
        self.assertTrue('请选择上级分组' in response.data["message"])

        response = self.client.post(base_url, data={'name': '顶级分组1', 'father_id': 'root'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid")
        self.assertTrue('字段 father_id, name 必须能构成唯一集合。' in response.data["message"])

        response = self.client.post(base_url, data={'name': '顶级分组4', 'father_id': 'root'})
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "name", "sort_weight", "remark", "level"], response.data)
        response = self.client.post(base_url, data={'name': '一级分组4', 'father_id': response.data['id']})
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "name", "sort_weight", "remark", "level"], response.data)
        response = self.client.post(base_url, data={'name': '二级分组4', 'father_id': response.data['id']})
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "name", "sort_weight", "remark", "level"], response.data)
        response = self.client.post(base_url, data={'name': '三级分组4', 'father_id': response.data['id']})
        self.assertEqual(response.status_code, 500)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertTrue('仅支持三层组结构' in response.data["message"])


class NetflowMenuRetrieveTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.super_user)
        response = self.client.post(base_url, data={'name': '顶级分组4', 'father_id': 'root'})
        self.assertEqual(response.status_code, 201)
        self.test_group_id = response.data['id']
        self.client.logout()

    def test_anonymous_user(self):
        """
        查询指定分组
        需要登陆
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        查询指定分组
        普通用户 无权限查看
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        查询指定分组
        组员 无权限查看
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.group_user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        查询指定分组
        组管理员 无权限查看
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.group_admin1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        查询指定分组
        运维管理员 有权限查看
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.obs_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "name", "sort_weight", "remark"], response.data)

    def test_super_user(self):
        """
        查询指定分组
        超级管理员 有权限查看
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.super_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "name", "sort_weight", "remark"], response.data)


class NetflowMenuUpdateTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.super_user)
        response = self.client.post(base_url, data={'name': '顶级分组4', 'father_id': 'root'})
        self.assertEqual(response.status_code, 201)
        self.test_group_id = response.data['id']
        self.client.logout()

    def test_anonymous_user(self):
        """
        修改指定分组
        需要登陆
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        修改指定分组
        普通用户 无权限修改
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.user1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        修改指定分组
        组员 无权限修改
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.group_user1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        修改指定分组
        组管理员 无权限修改
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.group_admin1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        修改指定分组
        运维管理员 无权限修改
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.obs_user)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        修改指定分组
        超级管理员 有权限修改
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.super_user)
        response = self.client.put(base_url, data={'sort_weight': -99})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "name", "sort_weight", "remark"], response.data)
        self.assertTrue(response.data['sort_weight'] == -99)

        response = self.client.put(base_url, data={'remark': "备注信息"})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "name", "sort_weight", "remark"], response.data)
        self.assertTrue(response.data['remark'] == "备注信息")


class NetflowMenuDestroyTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()
        base_url = reverse('netflow-api:menu-list')
        self.client.force_login(self.super_user)
        response = self.client.post(base_url, data={'name': '顶级分组4', 'father_id': 'root'})
        self.assertEqual(response.status_code, 201)
        self.test_group_id = response.data['id']
        self.client.logout()

    def test_anonymous_user(self):
        """
        删除指定分组
        需要登陆
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        删除指定分组
        普通用户 无删除权限
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.user1)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        删除指定分组
        组员 无删除权限
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.group_user1)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        删除指定分组
        组管理员 无删除权限
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.group_admin1)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        删除指定分组
        运维管理员 无删除权限
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.obs_user)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        删除指定分组
        超级管理员 有删除权限
        """
        base_url = reverse('netflow-api:menu-detail', args=[self.test_group_id])
        self.client.force_login(self.super_user)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(response.data is None)
