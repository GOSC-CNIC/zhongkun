import ipaddress

from django.urls import reverse

from utils.test import get_or_create_user, MyAPITransactionTestCase
from apps.app_net_ipam.managers.common import NetIPamUserRoleWrapper
from apps.app_net_ipam.models import ExternalIPv4Range
from apps.app_net_ipam.permissions import IPamIPRestrictor


class ExternalIPv4RangeTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

        IPamIPRestrictor.add_ip_rule('127.0.0.1')
        IPamIPRestrictor.clear_cache()

    def test_create(self):
        base_url = reverse('net_ipam-api:ipam-external-ipv4range-list')
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # start_address
        response = self.client.post(base_url, data={
            'start_address': -1, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # end_address
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 2**32, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # mask_len 0-32
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 33,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # asn 0-4294967295
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 24,
            'asn': 4294967295 + 1, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_role()
        u1_role_wrapper.set_ipam_readonly(True)
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.set_ipam_readonly(False)
        u1_role_wrapper.set_ipam_admin(True)

        # start_address > end_address
        response = self.client.post(base_url, data={
            'start_address': 256, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # start_address, end_address, mask_len, not in same network
        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 256, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 25,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.post(base_url, data={
            'start_address': 0, 'end_address': 255, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test1',
            'org_name': 'org_name1', 'country': '中国', 'city': '北京'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'operator', 'update_time',
                           'remark', 'start_address', 'end_address', 'mask_len', 'asn',
                           'org_name', 'country', 'city'], response.data)
        subnet1 = ExternalIPv4Range.objects.get(id=response.data['id'])
        self.assertEqual(subnet1.start_address, int(ipaddress.IPv4Address('0.0.0.0')))
        self.assertEqual(subnet1.end_address, int(ipaddress.IPv4Address('0.0.0.255')))
        self.assertEqual(subnet1.mask_len, 24)
        self.assertEqual(subnet1.asn, 88)
        self.assertEqual(subnet1.name, '0.0.0.0/24')
        self.assertEqual(subnet1.operator, self.user1.username)
        self.assertEqual(subnet1.org_name, 'org_name1')
        self.assertEqual(subnet1.country, '中国')
        self.assertEqual(subnet1.city, '北京')
        self.assertEqual(subnet1.remark, 'remark test1')

        # 存在重叠
        response = self.client.post(base_url, data={
            'start_address': 0, 'end_address': 200, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name2', 'country': '中国', 'city': '上海'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'start_address': 100, 'end_address': 256, 'mask_len': 23,
            'asn': 88, 'remark': 'remark test2',
            'org_name': 'org_name2', 'country': '中国', 'city': '上海'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'start_address': 255, 'end_address': 512, 'mask_len': 23,
            'asn': 88, 'remark': 'remark test2',
            'org_name': 'org_name2', 'country': '中国', 'city': '上海'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.post(base_url, data={
            'start_address': 256, 'end_address': 511, 'mask_len': 24,
            'asn': 4294967295, 'remark': '',
            'org_name': 'org_name2', 'country': '中国', 'city': '上海'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'start_address', 'end_address', 'mask_len', 'asn', 'remark',
                           'creation_time', 'update_time', 'operator', 'org_name', 'country', 'city'
                           ], response.data)
        subnet2 = ExternalIPv4Range.objects.get(id=response.data['id'])
        self.assertEqual(subnet2.start_address, int(ipaddress.IPv4Address('0.0.1.0')))
        self.assertEqual(subnet2.end_address, int(ipaddress.IPv4Address('0.0.1.255')))
        self.assertEqual(subnet2.mask_len, 24)
        self.assertEqual(subnet2.remark, '')
        self.assertEqual(subnet2.asn, 4294967295)
        self.assertEqual(subnet2.name, '0.0.1.0/24')
        self.assertEqual(subnet2.operator, self.user1.username)
        self.assertEqual(subnet2.country, '中国')
        self.assertEqual(subnet2.city, '上海')
