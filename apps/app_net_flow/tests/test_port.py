from django.urls import reverse
from django.conf import settings
from django.core.exceptions import ValidationError
from utils.test import get_or_create_user
from utils.test import MyAPITestCase
from utils.test import MyAPITransactionTestCase
from .test_administrator import GlobalAdministratorTests
from apps.app_net_flow.models import Menu2Chart


class NetflowPortListTests(GlobalAdministratorTests):
    """
    查询端口列表
    """

    def setUp(self):
        super().setUp()

    def test_anonymous_user(self):
        """
        查询端口列表
        需要登陆
        """
        base_url = reverse('netflow-api:port-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "NotAuthenticated")
        self.assertEqual(response.data["message"], "身份认证信息未提供。")

    def test_user(self):
        """
        查询端口列表
        普通用户不可查看
        """
        base_url = reverse('netflow-api:port-list')
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_group_admin_user(self):
        """
        查询端口列表
        组管理员 不可查看
        """
        base_url = reverse('netflow-api:port-list')
        self.client.force_login(self.group_admin1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_obs_user(self):
        """
        查询端口列表
        运维管理员 无权限
        """
        base_url = reverse('netflow-api:port-list')
        self.client.force_login(self.obs_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 403)
        self.assertKeysIn(['code', "message"], response.data)
        self.assertEqual(response.data["code"], "permission_denied")

    def test_super_user(self):
        """
        查询端口列表
        超级管理员可查看
        """
        base_url = reverse('netflow-api:port-list')
        self.client.force_login(self.super_user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        self.assertTrue(response.data['results'])

    def test_group_filter(self):
        """
        查询端口列表
        如果是查询指定分组，会过滤掉已经在当前组的元素
        """
        base_url = reverse('netflow-api:port-list')
        url = f'{base_url}?group={self.second_level_menu1.id}'
        self.client.force_login(self.super_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        self.assertTrue(response.data['results'])
        count1 = response.data['count']
        results1 = response.data['results']
        chart_id_list = [_["id"] for _ in results1]
        self.assertTrue(self.chart4.id in chart_id_list)
        self.assertFalse(self.chart1.id in chart_id_list)
        # 二级分组2 添加图表4

        Menu2Chart.objects.create(
            menu=self.second_level_menu1,
            chart=self.chart4,
            remark='组内备注文本',
            sort_weight=-998,
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', "next", 'previous', 'results'], response.data)
        self.assertTrue(response.data['results'])

        count2 = response.data['count']
        results2 = response.data['results']
        chart_id_list = [_["id"] for _ in results2]
        self.assertFalse(self.chart4.id in chart_id_list)
        self.assertTrue(count1 - count2 == 1)
