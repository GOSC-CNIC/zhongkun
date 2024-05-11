from django.urls import reverse
from django.conf import settings

from utils.test import get_or_create_user
from utils.test import get_or_create_user
from utils.test import MyAPITestCase
from utils.test import MyAPITransactionTestCase
from apps.app_netflow.models import MenuModel
from apps.app_netflow.models import ChartModel
from apps.app_netflow.serializers import MenuModelSerializer


class NetflowMenuTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='user1@cnic.com')
        self.user2 = get_or_create_user(username='user2@cnic.cn')
        self.user3 = get_or_create_user(username='user3@cnic.cn')
        self.user4 = get_or_create_user(username='user4@cnic.cn')
        ChartModel.objects.create(
            title='global_title1',
            instance_name='test1',
            if_alias='alias1',
            if_address='192.168.0.1',
            device_ip='192.168.0.1',
            port_name='Ethernet1/0/1',
        )
        ChartModel.objects.create(
            title='global_title2',
            instance_name='test2',
            if_alias='alias2',
            if_address='192.168.0.1',
            device_ip='192.168.0.1',
            port_name='Ethernet1/0/2',
        )
        ChartModel.objects.create(
            title='global_title3',
            instance_name='test3',
            if_alias='alias3',
            if_address='192.168.0.1',
            device_ip='192.168.0.1',
            port_name='Ethernet1/0/3',
        )
        ChartModel.objects.create(
            title='global_title4',
            instance_name='test4',
            if_alias='alias4',
            if_address='192.168.0.1',
            device_ip='192.168.0.1',
            port_name='Ethernet1/0/4',
        )
        ChartModel.objects.create(
            title='global_title5',
            instance_name='test5',
            if_alias='alias5',
            if_address='192.168.0.1',
            device_ip='192.168.0.1',
            port_name='Ethernet1/0/5',
        )
        ChartModel.objects.create(
            title='global_title6',
            instance_name='test6',
            if_alias='alias6',
            if_address='192.168.1.1',
            device_ip='192.168.1.1',
            port_name='Ethernet1/0/5',
        )
        ChartModel.objects.create(
            title='global_title7',
            instance_name='test7',
            if_alias='alias7',
            if_address='192.168.1.2',
            device_ip='192.168.1.2',
            port_name='Ethernet1/0/6',
        )

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

    def test_menu_list_api(self):
        base_url = reverse('netflow-api:menu-list')
        response = self.client.get(base_url)
        # self.assertEqual(response.status_code, 401)
        # self.client.force_login(self.user1)
        # response = self.client.get(base_url)
        # self.assertEqual(response.status_code, 200)
        # self.assertKeysIn(['count', "results"], response.data)
        # self.client.logout()


