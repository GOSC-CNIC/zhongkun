from django.conf import settings
from django.urls import reverse
from .test_administrator import GlobalAdministratorTests


class NetflowGroupChartListTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()

    def test_anonymous_user(self):
        """
        查询组内元素列表
        需要登陆
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:chart-list')
        url = f'{base_url}?menu={group_id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        查询组内元素列表
        普通用户无查看权限
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:chart-list')
        url = f'{base_url}?menu={group_id}'
        self.client.force_login(self.user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        self.assertEqual(response.data["results"], [])

    def test_group_user(self):
        """
        查询组内元素列表
        组员 可查看
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:chart-list')
        url = f'{base_url}?menu={group_id}'
        self.client.force_login(self.group_user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertFalse(item.get('remark') is None)
        self.assertTrue(item.get('admin_remark') is None)
        self.assertTrue(item.get('device_ip') is None)
        self.assertTrue(item.get('port_name') is None)

        url = f'{base_url}?menu={self.first_level_menu1.id}'
        self.client.force_login(self.group_user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertFalse(item.get('remark') is None)
        self.assertTrue(item.get('admin_remark') is None)
        self.assertTrue(item.get('device_ip') is None)
        self.assertTrue(item.get('port_name') is None)

        url = f'{base_url}?menu={self.top_level_menu1.id}'
        self.client.force_login(self.group_user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertFalse(item.get('remark') is None)
        self.assertTrue(item.get('admin_remark') is None)
        self.assertTrue(item.get('device_ip') is None)
        self.assertTrue(item.get('port_name') is None)

        url = f'{base_url}?menu={self.root.id}'
        self.client.force_login(self.group_user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertFalse(item.get('remark') is None)
        self.assertTrue(item.get('admin_remark') is None)
        self.assertTrue(item.get('device_ip') is None)
        self.assertTrue(item.get('port_name') is None)

        url = f'{base_url}?menu={self.top_level_menu2.id}'
        self.client.force_login(self.group_user1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 0)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(data.get('results') == [])

    def test_group_admin_user(self):
        """
        查询组内元素列表
        组管理员 可查看
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:chart-list')
        url = f'{base_url}?menu={group_id}'
        self.client.force_login(self.group_admin1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertTrue(item.get('remark') is not None)
        self.assertTrue(item.get('admin_remark') is not None)
        self.assertTrue(item.get('device_ip') is not None)
        self.assertTrue(item.get('port_name') is not None)

        url = f'{base_url}?menu={self.first_level_menu1.id}'
        self.client.force_login(self.group_admin1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertTrue(item.get('remark') is not None)
        self.assertTrue(item.get('admin_remark') is not None)
        self.assertTrue(item.get('device_ip') is not None)
        self.assertTrue(item.get('port_name') is not None)

        url = f'{base_url}?menu={self.top_level_menu1.id}'
        self.client.force_login(self.group_admin1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertTrue(item.get('remark') is not None)
        self.assertTrue(item.get('admin_remark') is not None)
        self.assertTrue(item.get('device_ip') is not None)
        self.assertTrue(item.get('port_name') is not None)

        url = f'{base_url}?menu={self.root.id}'
        self.client.force_login(self.group_admin1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertTrue(item.get('remark') is not None)
        self.assertTrue(item.get('admin_remark') is not None)
        self.assertTrue(item.get('device_ip') is not None)
        self.assertTrue(item.get('port_name') is not None)

        url = f'{base_url}?menu={self.top_level_menu2.id}'
        self.client.force_login(self.group_admin1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 0)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(data.get('results') == [])

    def test_obs_user(self):
        """
        查询组内元素列表
        运维管理员可查看
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:chart-list')
        url = f'{base_url}?menu={group_id}'
        self.client.force_login(self.obs_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertTrue(item.get('remark') is not None)
        self.assertTrue(item.get('admin_remark') is not None)
        self.assertTrue(item.get('device_ip') is not None)
        self.assertTrue(item.get('port_name') is not None)

        url = f'{base_url}?menu={self.first_level_menu1.id}'
        self.client.force_login(self.obs_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertTrue(item.get('remark') is not None)
        self.assertTrue(item.get('admin_remark') is not None)
        self.assertTrue(item.get('device_ip') is not None)
        self.assertTrue(item.get('port_name') is not None)

        url = f'{base_url}?menu={self.top_level_menu1.id}'
        self.client.force_login(self.obs_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 4)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertTrue(item.get('remark') is not None)
        self.assertTrue(item.get('admin_remark') is not None)
        self.assertTrue(item.get('device_ip') is not None)
        self.assertTrue(item.get('port_name') is not None)

        url = f'{base_url}?menu={self.root.id}'
        self.client.force_login(self.obs_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 4)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertTrue(item.get('remark') is not None)
        self.assertTrue(item.get('admin_remark') is not None)
        self.assertTrue(item.get('device_ip') is not None)
        self.assertTrue(item.get('port_name') is not None)

        url = f'{base_url}?menu={self.top_level_menu2.id}'
        self.client.force_login(self.obs_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 0)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(data.get('results') == [])

    def test_super_user(self):
        """
        查询组内元素列表
        超级管理员可查看
        """
        group_id = self.second_level_menu1.id
        base_url = reverse('netflow-api:chart-list')
        url = f'{base_url}?menu={group_id}'
        self.client.force_login(self.super_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertFalse(item.get('remark') is None)
        self.assertFalse(item.get('admin_remark') is None)
        self.assertFalse(item.get('device_ip') is None)
        self.assertFalse(item.get('port_name') is None)

        url = f'{base_url}?menu={self.first_level_menu1.id}'
        self.client.force_login(self.super_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 3)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertTrue(item.get('remark') is not None)
        self.assertTrue(item.get('admin_remark') is not None)
        self.assertTrue(item.get('device_ip') is not None)
        self.assertTrue(item.get('port_name') is not None)

        url = f'{base_url}?menu={self.top_level_menu1.id}'
        self.client.force_login(self.super_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 4)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertTrue(item.get('remark') is not None)
        self.assertTrue(item.get('admin_remark') is not None)
        self.assertTrue(item.get('device_ip') is not None)
        self.assertTrue(item.get('port_name') is not None)

        url = f'{base_url}?menu={self.root.id}'
        self.client.force_login(self.super_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 4)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(response.data['results'])
        results = data.get('results')
        self.assertKeysIn([
            'id', "instance_name", 'global_title', 'global_remark', 'remark', 'sort_weight', 'if_alias',
            'if_address', 'device_ip', 'port_name', 'class_uuid', 'band_width'
        ], results[0])
        item = results[0]
        self.assertTrue(item.get('remark') is not None)
        self.assertTrue(item.get('admin_remark') is not None)
        self.assertTrue(item.get('device_ip') is not None)
        self.assertTrue(item.get('port_name') is not None)

        url = f'{base_url}?menu={self.top_level_menu2.id}'
        self.client.force_login(self.super_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        data = response.data
        self.assertTrue(data.get('count') == 0)
        self.assertTrue(data.get('next') is None)
        self.assertTrue(data.get('previous') is None)
        self.assertTrue(data.get('results') == [])


class NetflowGroupChartCreateTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()

    def test_anonymous_user(self):
        """
        添加组内元素
        需要登陆
        """
        base_url = reverse('netflow-api:chart-list')
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        添加组内元素
        普通用户 无权限添加
        """
        base_url = reverse('netflow-api:chart-list')
        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        添加组内元素
        组员 无添加权限
        """
        base_url = reverse('netflow-api:chart-list')
        self.client.force_login(self.group_user1)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        添加组内元素
        组管理员 无添加权限
        """
        base_url = reverse('netflow-api:chart-list')
        self.client.force_login(self.group_admin1)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        添加组内元素
        运维管理员 无添加权限
        """
        base_url = reverse('netflow-api:chart-list')
        self.client.force_login(self.obs_user)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        新增组内元素
        超级管理员 有添加权限
        """
        base_url = reverse('netflow-api:chart-list')
        self.client.force_login(self.super_user)
        response = self.client.post(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 400)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "invalid")
        response = self.client.post(base_url, data={'menu': 'test'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["code"], "invalid")
        self.assertTrue('无效主键 “test” － 对象不存在。' in response.data["message"])
        response = self.client.post(base_url, data={'menu': 'test', 'chart': "testchart"})
        self.assertTrue('无效主键 “test” － 对象不存在。' in response.data["message"])
        self.assertTrue('无效主键 “testchart” － 对象不存在。' in response.data["message"])
        group_id = self.second_level_menu1.id
        chart_id = self.chart1.id

        response = self.client.post(base_url, data={'menu': group_id, 'chart': chart_id})
        self.assertEqual(response.data["code"], "Existed")
        self.assertTrue('元素已经存在，请勿重复添加' in response.data["message"])

        group_id = self.first_level_menu2.id
        chart_id = self.chart1.id

        response = self.client.post(base_url,
                                    data={'menu': group_id,
                                          'chart': chart_id,
                                          'remark': '备注',
                                          'admin_remark': "管理员备注"}
                                    )
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(
            ['id', "instance_name", "global_title", 'global_remark',
             "remark", "admin_remark", "sort_weight", "if_alias",
             "if_address", "device_ip", "port_name", "class_uuid", "band_width"], response.data)
        self.assertTrue(response.data['remark'] == '备注')
        self.assertTrue(response.data['admin_remark'] == '管理员备注')


class NetflowGroupChartRetrieveTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()
        base_url = reverse('netflow-api:chart-list')
        group_id = self.first_level_menu2.id
        chart_id = self.chart1.id
        self.client.force_login(self.super_user)
        response = self.client.post(base_url,
                                    data={
                                        'menu': group_id,
                                        'chart': chart_id,
                                        'remark': '备注',
                                        'admin_remark': '管理员备注',
                                    })
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "instance_name", "global_title", "global_remark",
                           'remark', 'admin_remark',
                           'sort_weight', 'if_alias', 'if_address', 'device_ip', 'port_name', 'class_uuid',
                           'band_width'], response.data)
        self.menu_chart_id = response.data.get('id')
        self.client.logout()

    def test_anonymous_user(self):
        """
        查看指定 组内元素
        需要登陆
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        查看指定 组内元素
        普通用户 无权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        查看指定 组内元素
        组员 无权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.group_user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        查看指定 组内元素
        组管理员 无权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.group_admin1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        查看指定 组内元素
        运维管理员 有权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.obs_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "remark", 'admin_remark', 'sort_weight'], response.data)

    def test_super_user(self):
        """
        查看指定 组内元素
        超级管理员 有权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.super_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', "remark", 'admin_remark', 'sort_weight'], response.data)
        self.assertTrue(response.data['remark'] == '备注')
        self.assertTrue(response.data['admin_remark'] == '管理员备注')


class NetflowGroupChartUpdateTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()
        base_url = reverse('netflow-api:chart-list')
        group_id = self.first_level_menu2.id
        chart_id = self.chart1.id
        self.client.force_login(self.super_user)
        response = self.client.post(base_url,
                                    data={
                                        'menu': group_id,
                                        'chart': chart_id,
                                        'remark': '备注',
                                        'admin_remark': '管理员备注',
                                        'band_width': -2,
                                    })
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "instance_name", "global_title", "global_remark",
                           'remark', 'sort_weight', 'if_alias', 'if_address', 'device_ip', 'port_name', 'class_uuid',
                           'band_width'], response.data)
        self.menu_chart_id = response.data.get('id')
        self.client.logout()

    def test_anonymous_user(self):
        """
        修改指定 组内元素
        需要登陆
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        修改指定 组内元素
        普通用户 无权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.user1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        修改指定 组内元素
        组管理员 无权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.group_admin1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        修改指定 组内元素
        组员 无权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.group_user1)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        修改指定 组内元素
        运维管理员 无权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.obs_user)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        修改指定 组内元素
        超级管理员 有权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.super_user)
        response = self.client.put(base_url, data={'test': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'remark', 'admin_remark', 'sort_weight'], response.data)
        self.assertTrue(response.data['remark'] == '备注')
        self.assertTrue(response.data['admin_remark'] == '管理员备注')
        self.assertTrue(response.data['sort_weight'] == -1)
        response = self.client.put(base_url, data={'remark': "123", 'sort_weight': -1})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'remark', 'admin_remark', 'sort_weight'], response.data)
        self.assertTrue(response.data['remark'] == '123')
        self.assertTrue(response.data['sort_weight'] == -1)

        response = self.client.put(base_url, data={'sort_weight': -99})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'remark', 'admin_remark', 'sort_weight'], response.data)
        self.assertTrue(response.data['remark'] == '123')
        self.assertTrue(response.data['sort_weight'] == -99)

        response = self.client.put(base_url, data={'remark': 456})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'remark', 'admin_remark', 'sort_weight'], response.data)
        self.assertTrue(response.data['remark'] == '456')
        self.assertTrue(response.data['sort_weight'] == -99)

        response = self.client.put(base_url, data={'admin_remark': -1})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'remark', 'admin_remark', 'sort_weight'], response.data)
        self.assertTrue(response.data['admin_remark'] == '-1')
        self.assertTrue(response.data['remark'] == '456')
        self.assertTrue(response.data['sort_weight'] == -99)

        response = self.client.put(base_url, data={'admin_remark': "管理员备注"})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'remark', 'admin_remark', 'sort_weight'], response.data)
        self.assertTrue(response.data['admin_remark'] == '管理员备注')
        self.assertTrue(response.data['remark'] == '456')
        self.assertTrue(response.data['sort_weight'] == -99)


class NetflowGroupChartDestroyTests(GlobalAdministratorTests):
    def setUp(self):
        super().setUp()
        base_url = reverse('netflow-api:chart-list')
        group_id = self.first_level_menu2.id
        chart_id = self.chart1.id
        self.client.force_login(self.super_user)
        response = self.client.post(base_url,
                                    data={
                                        'menu': group_id,
                                        'chart': chart_id
                                    })
        self.assertEqual(response.status_code, 201)
        self.assertKeysIn(['id', "instance_name", "global_title", "global_remark",
                           'remark', 'sort_weight', 'if_alias', 'if_address', 'device_ip', 'port_name', 'class_uuid',
                           'band_width'], response.data)
        self.menu_chart_id = response.data.get('id')
        self.client.logout()

    def test_anonymous_user(self):
        """
        删除指定 组内元素
        需要登陆
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        删除指定 组内元素
        普通用户 无权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.user1)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_user(self):
        """
        删除指定 组内元素
        组员 无权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.group_user1)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        删除指定 组内元素
        组管理员 无权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.group_admin1)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        删除指定 组内元素
        运维管理员 无权限
        """
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
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
        base_url = reverse('netflow-api:chart-detail', args=[self.menu_chart_id])
        self.client.force_login(self.super_user)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        self.assertTrue(response.data is None)
