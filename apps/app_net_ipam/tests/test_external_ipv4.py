import ipaddress
from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_user, MyAPITransactionTestCase
from apps.app_net_ipam.managers.common import NetIPamUserRoleWrapper
from apps.app_net_ipam.managers.ipv4_mgrs import ExternalIPv4RangeManager
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

    def test_list(self):
        ip_range1 = ExternalIPv4RangeManager().create_external_ipv4_range(
            start_address=int(ipaddress.IPv4Address('127.0.0.1')),
            end_address=int(ipaddress.IPv4Address('127.0.0.255')), mask_len=24, asn=66,
            operator='zhangsan@cnic.cn', org_name='机构1', country='中国', city='北京', remark='remark1'
        )
        ip_range2 = ExternalIPv4RangeManager().create_external_ipv4_range(
            start_address=int(ipaddress.IPv4Address('159.0.1.1')),
            end_address=int(ipaddress.IPv4Address('159.0.2.255')), mask_len=22, asn=88,
            operator='zhangsan@cnic.cn', org_name='机构2', country='新加坡', city='新加坡', remark='remark2'
        )
        ip_range3 = ExternalIPv4RangeManager().create_external_ipv4_range(
            start_address=int(ipaddress.IPv4Address('10.0.1.1')),
            end_address=int(ipaddress.IPv4Address('10.0.1.255')), mask_len=24, asn=88,
            operator='tom@qq.com', org_name='机构3', country='中国', city='shanghai', remark='remark3'
        )
        ip_range4 = ExternalIPv4RangeManager().create_external_ipv4_range(
            start_address=int(ipaddress.IPv4Address('10.0.2.1')),
            end_address=int(ipaddress.IPv4Address('10.0.2.255')), mask_len=24, asn=88,
            operator='tom@qq.com', org_name='机构3', country='中国', city='台北', remark='remark4'
        )

        base_url = reverse('net_ipam-api:ipam-external-ipv4range-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_role()
        u1_role_wrapper.set_ipam_readonly(True)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 4)
        self.assertEqual(response.data['results'][0]['id'], ip_range3.id)
        self.assertEqual(response.data['results'][1]['id'], ip_range4.id)
        self.assertEqual(response.data['results'][2]['id'], ip_range1.id)
        self.assertEqual(response.data['results'][3]['id'], ip_range2.id)
        iprange = response.data['results'][0]
        self.assertKeysIn([
            'id', 'name', 'start_address', 'end_address', 'mask_len', 'asn', 'remark', 'creation_time', 'update_time',
            'operator', 'org_name', 'country', 'city'
        ], iprange)
        self.assertEqual(iprange['id'], ip_range3.id)
        self.assertEqual(iprange['start_address'], int(ipaddress.IPv4Address('10.0.1.1')))
        self.assertEqual(iprange['end_address'], int(ipaddress.IPv4Address('10.0.1.255')))
        self.assertEqual(iprange['mask_len'], 24)
        self.assertEqual(iprange['asn'], 88)
        self.assertEqual(iprange['remark'], ip_range3.remark)
        self.assertEqual(iprange['operator'], ip_range3.operator)
        self.assertEqual(iprange['org_name'], ip_range3.org_name)
        self.assertEqual(iprange['country'], ip_range3.country)
        self.assertEqual(iprange['city'], ip_range3.city)

        # query "asn"
        query = parse.urlencode(query={'asn': 'a'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'asn': '66'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], ip_range1.id)

        query = parse.urlencode(query={'asn': 88})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)

        # query "ip"
        query = parse.urlencode(query={'ip': '127.0.0.256'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'ip': '127.0.0.88'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], ip_range1.id)

        query = parse.urlencode(query={'ip': '127.0.1.0'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'ip': '159.0.1.188'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], ip_range2.id)

        # query "search"
        query = parse.urlencode(query={'search': 'remark4'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], ip_range4.id)

        query = parse.urlencode(query={'search': '中国'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['results'][0]['id'], ip_range3.id)
        self.assertEqual(response.data['results'][1]['id'], ip_range4.id)
        self.assertEqual(response.data['results'][2]['id'], ip_range1.id)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 3})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 3)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], ip_range2.id)

    def test_update(self):
        ip_range1 = ExternalIPv4RangeManager().create_external_ipv4_range(
            start_address=int(ipaddress.IPv4Address('127.0.0.1')),
            end_address=int(ipaddress.IPv4Address('127.0.0.255')), mask_len=24, asn=66,
            operator='zhangsan@cnic.cn', org_name='机构1', country='中国', city='北京', remark='remark1'
        )
        ip_range2 = ExternalIPv4RangeManager().create_external_ipv4_range(
            start_address=int(ipaddress.IPv4Address('0.0.2.1')),
            end_address=int(ipaddress.IPv4Address('0.0.2.255')), mask_len=24, asn=33,
            operator='tom@cnic.cn', org_name='机构2', country='新加坡', city='新加坡', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-external-ipv4range-detail', kwargs={'id': 'test'})
        response = self.client.put(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 23,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.put(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 23,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        base_url = reverse('net_ipam-api:ipam-external-ipv4range-detail', kwargs={'id': ip_range1.id})
        response = self.client.put(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 23,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # start_address
        response = self.client.put(base_url, data={
            'start_address': -1, 'end_address': 255, 'mask_len': 23,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # end_address
        response = self.client.put(base_url, data={
            'start_address': 1, 'end_address': 2**32, 'mask_len': 23,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # mask_len 0-32
        response = self.client.put(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 33,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # asn 0-4294967295
        response = self.client.put(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 23,
            'asn': 4294967295 + 1, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.put(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 23,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_role()
        u1_role_wrapper.set_ipam_readonly(True)
        response = self.client.put(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 23,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.set_ipam_readonly(False)
        u1_role_wrapper.set_ipam_admin(True)

        # start_address > end_address
        response = self.client.put(base_url, data={
            'start_address': 256, 'end_address': 255, 'mask_len': 23,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # start_address, end_address, mask_len, not in same network
        response = self.client.put(base_url, data={
            'start_address': 1, 'end_address': 256, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.put(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 25,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.put(base_url, data={
            'start_address': 1, 'end_address': 255, 'mask_len': 23,
            'asn': 88, 'remark': 'remark test',
            'org_name': 'org_name1', 'country': 'china', 'city': 'shanghai'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'operator', 'update_time',
                           'remark', 'start_address', 'end_address', 'mask_len', 'asn',
                           'org_name', 'country', 'city'], response.data)
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.start_address, int(ipaddress.IPv4Address('0.0.0.1')))
        self.assertEqual(ip_range1.end_address, int(ipaddress.IPv4Address('0.0.0.255')))
        self.assertEqual(ip_range1.mask_len, 23)
        self.assertEqual(ip_range1.asn, 88)
        self.assertEqual(ip_range1.name, '0.0.0.0/23')
        self.assertEqual(ip_range1.operator, self.user1.username)
        self.assertEqual(ip_range1.org_name, 'org_name1')
        self.assertEqual(ip_range1.country, 'china')
        self.assertEqual(ip_range1.city, 'shanghai')
        self.assertEqual(ip_range1.remark, 'remark test')

        # 存在重叠
        response = self.client.put(base_url, data={
            'start_address': 512, 'end_address': 600, 'mask_len': 24,
            'asn': 88, 'remark': 'remark test88',
            'org_name': 'org_name2', 'country': '中国', 'city': '上海'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.put(base_url, data={
            'start_address': 768, 'end_address': 1023, 'mask_len': 24,
            'asn': 4294967295, 'remark': 'remark test88',
            'org_name': 'org_name2', 'country': '中国', 'city': '上海'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'start_address', 'end_address', 'mask_len', 'asn', 'remark',
                           'creation_time', 'update_time', 'operator', 'org_name', 'country', 'city'
                           ], response.data)
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.start_address, int(ipaddress.IPv4Address('0.0.3.0')))
        self.assertEqual(ip_range1.end_address, int(ipaddress.IPv4Address('0.0.3.255')))
        self.assertEqual(ip_range1.mask_len, 24)
        self.assertEqual(ip_range1.remark, 'remark test88')
        self.assertEqual(ip_range1.asn, 4294967295)
        self.assertEqual(ip_range1.name, '0.0.3.0/24')
        self.assertEqual(ip_range1.operator, self.user1.username)
        self.assertEqual(ip_range1.org_name, 'org_name2')
        self.assertEqual(ip_range1.country, '中国')
        self.assertEqual(ip_range1.city, '上海')
