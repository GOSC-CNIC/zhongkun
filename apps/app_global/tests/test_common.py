from django.shortcuts import reverse

from utils.test import get_or_create_user, MyAPITestCase
from apps.app_global.models import GlobalConfig
from apps.app_global.configs_manager import global_configs


class CommonTests(MyAPITestCase):
    def setUp(self):
        pass

    def test_sales_customer(self):
        user1 = get_or_create_user(username='lisi@cnic.cn')

        base_url = reverse('app-global-api:sales-info-list')

        # 未认证
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 401)
        self.client.force_login(user1)

        # 不存在自动创建
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['info'], '')

        obj = GlobalConfig.objects.get(name=GlobalConfig.ConfigName.SALES_CUSTOMER_SERVICE_INFO.value)
        obj.value = 'test测试'
        obj.save(update_fields=['value'])
        global_configs.clear_cache()

        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['info'], 'test测试')
