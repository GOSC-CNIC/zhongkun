from django.urls import reverse
from django.conf import settings
from utils.test import get_or_create_user
from utils.test import MyAPITestCase
from utils.test import MyAPITransactionTestCase
from apps.app_net_flow.models import MenuModel
from apps.app_net_flow.models import GlobalAdminModel
from apps.app_net_flow.models import ChartModel
from apps.app_net_flow.models import Menu2Chart
from apps.app_net_flow.models import Menu2Member
from apps.app_net_flow.permission import NetFlowAPIIPRestrictor


class GlobalAdministratorTests(MyAPITransactionTestCase):
    def setUp(self):
        self.super_user = get_or_create_user(username='superuser@cnic.com')  # 全局超级管理员
        self.obs_user = get_or_create_user(username='obsuser@cnic.cn')  # 全局运维管理员
        self.group_admin1 = get_or_create_user(username='groupadmin1@cnic.cn')  # 组管理员
        self.group_admin2 = get_or_create_user(username='groupadmin2@cnic.cn')  # 组管理员
        self.group_admin3 = get_or_create_user(username='groupadmin3@cnic.cn')  # 组管理员
        self.group_admin4 = get_or_create_user(username='groupadmin4@cnic.cn')  # 组管理员
        self.group_user1 = get_or_create_user(username='groupuser1@cnic.cn')  # 组员
        self.group_user2 = get_or_create_user(username='groupuser2@cnic.cn')  # 组员
        self.user1 = get_or_create_user(username='user1@cnic.cn')  # 普通用户
        self.user2 = get_or_create_user(username='user2@cnic.cn')  # 普通用户
        GlobalAdminModel.objects.create(
            member=self.super_user,
            role=GlobalAdminModel.Roles.SUPER_ADMIN.value
        )
        GlobalAdminModel.objects.create(
            member=self.obs_user,
            role=GlobalAdminModel.Roles.ADMIN.value
        )
        # 图表元素
        self.chart1 = ChartModel.objects.create(
            title='global_title1',
            instance_name='test1',
            if_alias='alias1',
            if_address='192.168.0.1',
            device_ip='192.168.0.1',
            port_name='Ethernet1/0/1',
        )
        self.chart2 = ChartModel.objects.create(
            title='global_title2',
            instance_name='test2',
            if_alias='alias2',
            if_address='192.168.0.1',
            device_ip='192.168.0.1',
            port_name='Ethernet1/0/2',
        )
        self.chart3 = ChartModel.objects.create(
            title='global_title3',
            instance_name='test3',
            if_alias='alias3',
            if_address='192.168.0.1',
            device_ip='192.168.0.1',
            port_name='Ethernet1/0/3',
        )
        self.chart4 = ChartModel.objects.create(
            title='global_title4',
            instance_name='test4',
            if_alias='alias4',
            if_address='192.168.0.1',
            device_ip='192.168.0.1',
            port_name='Ethernet1/0/4',
        )
        self.chart5 = ChartModel.objects.create(
            title='global_title5',
            instance_name='test5',
            if_alias='alias5',
            if_address='192.168.0.1',
            device_ip='192.168.0.1',
            port_name='Ethernet1/0/5',
        )
        self.chart6 = ChartModel.objects.create(
            title='global_title6',
            instance_name='test6',
            if_alias='alias6',
            if_address='192.168.1.1',
            device_ip='192.168.1.1',
            port_name='Ethernet1/0/5',
        )
        self.chart7 = ChartModel.objects.create(
            title='global_title7',
            instance_name='test7',
            if_alias='alias7',
            if_address='192.168.1.2',
            device_ip='192.168.1.2',
            port_name='Ethernet1/0/6',
        )
        # 组结构
        # 根节点
        """
        -root
            -toplevel1
                -firstlevel1  (group_admin3)
                    -secondlevel1  (member1)
                    -secondlevel2  (group_admin2)
                -firstlevel2   (group_admin4)
            -toplevel2
            -toplevel3
        """
        self.root = MenuModel.objects.create(
            name='全部'
        )
        self.top_level_menu1 = MenuModel.objects.create(
            name='顶级分组1',
            father=self.root
        )
        self.first_level_menu1 = MenuModel.objects.create(
            name='一级分组1',
            father=self.top_level_menu1
        )
        self.first_level_menu2 = MenuModel.objects.create(
            name='一级分组2',
            father=self.top_level_menu1
        )
        self.second_level_menu1 = MenuModel.objects.create(
            name='二级分组1',
            father=self.first_level_menu1
        )
        self.second_level_menu2 = MenuModel.objects.create(
            name='二级分组2',
            father=self.first_level_menu1
        )
        self.top_level_menu2 = MenuModel.objects.create(
            name='顶级分组2',
            father=self.root
        )
        self.top_level_menu3 = MenuModel.objects.create(
            name='顶级分组3',
            father=self.root
        )
        # 添加组元素
        Menu2Chart.objects.create(
            menu=self.second_level_menu1,
            chart=self.chart1,
            remark='备注1',
            admin_remark='管理员备注1',
            sort_weight=-999,

        )
        Menu2Chart.objects.create(
            menu=self.second_level_menu1,
            chart=self.chart2,
            remark='备注2',
            admin_remark='管理员备注2',
            sort_weight=-998,

        )
        Menu2Chart.objects.create(
            menu=self.second_level_menu1,
            chart=self.chart3,
            remark='备注3',
            admin_remark='管理员备注3',
            sort_weight=-1,

        )
        Menu2Chart.objects.create(
            menu=self.first_level_menu2,
            chart=self.chart4,
            remark='备注4',
            admin_remark='管理员备注4',
            sort_weight=-1,
        )
        # 添加组管理员
        Menu2Member.objects.create(
            menu=self.second_level_menu1,
            member=self.group_admin1,
            role=Menu2Member.Roles.GROUP_ADMIN.value,
            inviter="test@cnic.cn",
        )
        self.menu1_member1 = Menu2Member.objects.create(
            menu=self.first_level_menu1,
            member=self.group_admin3,
            role=Menu2Member.Roles.GROUP_ADMIN.value,
            inviter="test@cnic.cn",
        )
        self.menu2_admin_member1 = Menu2Member.objects.create(
            menu=self.first_level_menu2,
            member=self.group_admin4,
            role=Menu2Member.Roles.GROUP_ADMIN.value,
            inviter="test@cnic.cn",
        )
        self.menu2_member1 = Menu2Member.objects.create(
            menu=self.second_level_menu2,
            member=self.group_admin2,
            role=Menu2Member.Roles.GROUP_ADMIN.value,
            inviter="test@cnic.cn",
        )

        # 添加组员
        self.member1 = Menu2Member.objects.create(
            menu=self.second_level_menu1,
            member=self.group_user1,
            role=Menu2Member.Roles.ORDINARY.value,
            inviter="test@cnic.cn",
        )


        Menu2Member.objects.create(
            menu=self.second_level_menu2,
            member=self.group_user2,
            role=Menu2Member.Roles.ORDINARY.value,
            inviter="test@cnic.cn",
        )
        # 添加ip 白名单
        NetFlowAPIIPRestrictor.add_ip_rule(ip_value='127.0.0.1')
        NetFlowAPIIPRestrictor.clear_cache()    # 有缓存，需要清除缓存


class GlobalAdministratorListTests(GlobalAdministratorTests):
    """
    查询管理员列表
    """

    def test_anonymous_user(self):
        """
        全局管理员列表
        需要登陆
        """
        base_url = reverse('netflow-api:administrator-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        全局管理员列表
        普通用户不可查看
        """
        base_url = reverse('netflow-api:administrator-list')
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        全局管理员列表
        组管理员 不可查看
        """
        base_url = reverse('netflow-api:administrator-list')
        self.client.force_login(self.group_admin1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        全局管理员列表
        组员 不可查看
        """
        base_url = reverse('netflow-api:administrator-list')
        self.client.force_login(self.group_user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        全局管理员列表
        运维管理员可查看
        """
        base_url = reverse('netflow-api:administrator-list')
        self.client.force_login(self.obs_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        self.assertTrue(response.data['results'])

    def test_super_user(self):
        """
        全局管理员列表
        超级管理员可查看
        """
        base_url = reverse('netflow-api:administrator-list')
        self.client.force_login(self.super_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        self.assertTrue(response.data['results'])


class GlobalAdministratorCreateTests(GlobalAdministratorTests):
    def test_anonymous_user(self):
        """
        新增全局管理员
        需要登陆
        """
        base_url = reverse('netflow-api:administrator-list')
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        新增全局管理员
        普通用户无添加权限
        """
        base_url = reverse('netflow-api:administrator-list')
        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        新增全局管理员
        组管理员 无添加权限
        """
        base_url = reverse('netflow-api:administrator-list')
        self.client.force_login(self.group_admin1)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        新增全局管理员
        组员 无添加权限
        """
        base_url = reverse('netflow-api:administrator-list')
        self.client.force_login(self.group_user1)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        新增全局管理员
        运维管理员 无添加权限
        """
        base_url = reverse('netflow-api:administrator-list')
        self.client.force_login(self.obs_user)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        新增全局管理员
        超级管理员 有添加权限
        """
        base_url = reverse('netflow-api:administrator-list')
        self.client.force_login(self.super_user)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "invalid")
        response = self.client.post(base_url, data={'member': 'test'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid")
        self.assertTrue('请输入合法的邮件地址' in response.data["message"])

        response = self.client.post(base_url, data={'member': 'A@test.cn'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid")
        # 添加人员  默认角色为运维管理员
        get_or_create_user(username='test1@cnic.com')
        get_or_create_user(username='test2@cnic.com')
        get_or_create_user(username='test3@cnic.com')
        response = self.client.post(base_url, data={'member': 'test1@cnic.com'})
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "username", "role", "inviter"], response.data)
        self.assertTrue(response.data['username'] == 'test1@cnic.com')
        self.assertTrue(response.data['inviter'] == 'superuser@cnic.com')
        self.assertTrue(response.data['role'] == GlobalAdminModel.Roles.ADMIN.value)
        # 添加 运维管理员
        response = self.client.post(base_url,
                                    data={
                                        'member': 'test2@cnic.com',
                                        'role': GlobalAdminModel.Roles.ADMIN.value
                                    })
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "username", "role", "inviter"], response.data)
        self.assertTrue(response.data['username'] == 'test2@cnic.com')
        self.assertTrue(response.data['inviter'] == 'superuser@cnic.com')
        self.assertTrue(response.data['role'] == GlobalAdminModel.Roles.ADMIN.value)
        # 添加 超级管理员
        response = self.client.post(base_url,
                                    data={
                                        'member': 'test3@cnic.com',
                                        'role': GlobalAdminModel.Roles.SUPER_ADMIN.value
                                    })
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "username", "role", "inviter"], response.data)
        self.assertTrue(response.data['username'] == 'test3@cnic.com')
        self.assertTrue(response.data['inviter'] == 'superuser@cnic.com')
        self.assertTrue(response.data['role'] == GlobalAdminModel.Roles.SUPER_ADMIN.value)


class GlobalAdministratorRetrieveTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()
        # 添加 运维管理员
        base_url = reverse('netflow-api:administrator-list')

        get_or_create_user(username='test4@cnic.cn')
        self.client.force_login(self.super_user)
        response = self.client.post(base_url,
                                    data={
                                        'member': 'test4@cnic.cn',
                                        'role': GlobalAdminModel.Roles.SUPER_ADMIN.value
                                    })
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "username", "role", "inviter"], response.data)
        self.assertTrue(response.data['username'] == 'test4@cnic.cn')
        self.assertTrue(response.data['inviter'] == 'superuser@cnic.com')
        self.assertTrue(response.data['role'] == GlobalAdminModel.Roles.SUPER_ADMIN.value)
        self.global_admin_id = response.data['id']
        self.client.logout()

    def test_anonymous_user(self):
        """
        查看指定 全局管理员
        需要登陆
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        查看指定 全局管理员
        普通用户 无权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        查看指定  全局管理员
        组管理员 无权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.group_admin1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        查看指定 全局管理员
        组员 无权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.group_user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        查看指定 全局管理员
        运维管理员 有权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.obs_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertTrue(response.data['role'] == GlobalAdminModel.Roles.SUPER_ADMIN.value)

    def test_super_user(self):
        """
        查看指定全局管理员
        超级管理员 有权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.super_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertTrue(response.data['role'] == GlobalAdminModel.Roles.SUPER_ADMIN.value)


class GlobalAdministratorUpdateTests(GlobalAdministratorTests):

    def setUp(self):
        super().setUp()
        # 添加 运维管理员
        base_url = reverse('netflow-api:administrator-list')

        get_or_create_user(username='test4@cnic.cn')
        self.client.force_login(self.super_user)
        response = self.client.post(base_url,
                                    data={
                                        'member': 'test4@cnic.cn',
                                        'role': GlobalAdminModel.Roles.SUPER_ADMIN.value
                                    })
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "username", "role", "inviter"], response.data)
        self.assertTrue(response.data['username'] == 'test4@cnic.cn')
        self.assertTrue(response.data['inviter'] == 'superuser@cnic.com')
        self.assertTrue(response.data['role'] == GlobalAdminModel.Roles.SUPER_ADMIN.value)
        self.global_admin_id = response.data['id']
        self.client.logout()

    def test_anonymous_user(self):
        """
        修改 全局管理员
        需要登陆
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    #
    def test_user(self):
        """
        修改 全局管理员
        普通用户 无权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.user1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        修改 全局管理员
        组管理员 无权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.group_admin1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        修改全局管理员
        组员 无权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.group_user1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        修改全局管理员
        运维管理员 无权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.obs_user)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        修改全局管理员
        超级管理员 有权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.super_user)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertTrue(response.data['role'] == GlobalAdminModel.Roles.SUPER_ADMIN.value)
        response = self.client.put(base_url, data={'role': "asdasdsad"})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertTrue('“asdasdsad” 不是合法选项。' in response.data['message'])
        response = self.client.put(base_url,
                                   data={'role': GlobalAdminModel.Roles.ADMIN.value})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "role"], response.data)
        self.assertTrue(response.data['role'] == GlobalAdminModel.Roles.ADMIN.value)


class GlobalAdministratorDestroyTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()
        # 添加 运维管理员
        base_url = reverse('netflow-api:administrator-list')

        get_or_create_user(username='test4@cnic.cn')
        self.client.force_login(self.super_user)
        response = self.client.post(base_url,
                                    data={
                                        'member': 'test4@cnic.cn',
                                        'role': GlobalAdminModel.Roles.SUPER_ADMIN.value
                                    })
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "username", "role", "inviter"], response.data)
        self.assertTrue(response.data['username'] == 'test4@cnic.cn')
        self.assertTrue(response.data['inviter'] == 'superuser@cnic.com')
        self.assertTrue(response.data['role'] == GlobalAdminModel.Roles.SUPER_ADMIN.value)
        self.global_admin_id = response.data['id']
        self.client.logout()

    def test_anonymous_user(self):
        """
        删除指定 全局管理员
        需要登陆
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        删除指定 全局管理员
        普通用户 无权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.user1)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        删除指定  全局管理员
        组管理员 无权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.group_admin1)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        删除指定 全局管理员
        组员 无权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.group_user1)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        删除指定 全局管理员
        运维管理员 无权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.obs_user)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        删除指定全局管理员
        超级管理员 有权限
        """
        base_url = reverse('netflow-api:administrator-detail',args=[self.global_admin_id])
        self.client.force_login(self.super_user)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(response.data is None)
