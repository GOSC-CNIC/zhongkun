import ipaddress
from datetime import datetime
from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone

from utils.test import get_or_create_user, MyAPITransactionTestCase, get_or_create_organization
from apps.app_net_ipam.managers.common import NetIPamUserRoleWrapper
from apps.app_net_ipam.managers.ipv6_mgrs import IPv6RangeManager
from apps.app_net_ipam.models import ASN, OrgVirtualObject, IPv6Range, IPv6RangeRecord
from apps.app_net_ipam.permissions import IPamIPRestrictor


class IPv6RangeTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

        IPamIPRestrictor.add_ip_rule('127.0.0.1')
        IPamIPRestrictor.clear_cache()

    def test_list_ipv6_ranges(self):
        org1 = get_or_create_organization(name='org1')
        org2 = get_or_create_organization(name='org2')

        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)
        virt_obj2 = OrgVirtualObject(name='org virt obj2', organization=org2, creation_time=dj_timezone.now())
        virt_obj2.save(force_insert=True)
        virt_obj3 = OrgVirtualObject(name='org virt obj3', organization=None, creation_time=dj_timezone.now())
        virt_obj3.save(force_insert=True)

        asn66 = ASN(name='asn 66', number=66, creation_time=dj_timezone.now())
        asn66.save(force_insert=True)
        asn88 = ASN(name='asn 88', number=88, creation_time=dj_timezone.now())
        asn88.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv6RangeManager.create_ipv6_range(
            name='已分配1', start_ip='2400:dd01:1010:30::', end_ip='2400:dd01:1010:30:ffff:ffff:ffff:ffff',
            prefixlen=64, asn=asn66,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv6RangeManager.create_ipv6_range(
            name='预留2', start_ip='2400:dd01:1010:34::', end_ip='2400:dd01:1010:35:ffff:ffff:ffff:fff',
            prefixlen=63, asn=asn88,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=virt_obj2, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )
        ip_range3 = IPv6RangeManager.create_ipv6_range(
            name='预留3', start_ip='2400:dd01::', end_ip='2400:dd01:fff:ffff:ffff:ffff:ffff:ffff',
            prefixlen=36, asn=asn88,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark3', remark='remark3'
        )
        ip_range4 = IPv6RangeManager.create_ipv6_range(
            name='待分配4', start_ip='2400:dd01:103c::', end_ip='2400:dd01:103f:ffff:ffff:ffff:ffff:ffff',
            prefixlen=46, asn=asn88,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.WAIT.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark4', remark='remark4'
        )

        base_url = reverse('net_ipam-api:ipam-ipv6range-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 0)

        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_role()
        u1_role_wrapper.user_role.organizations.add(org1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        iprange = response.data['results'][0]
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'
        ], iprange)
        self.assertKeysIn(['id', 'number'], iprange['asn'])
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization'], iprange['org_virt_obj'])
        self.assertKeysIn(['id', 'name', 'name_en'], iprange['org_virt_obj']['organization'])
        self.assertEqual(iprange['id'], ip_range1.id)
        self.assertEqual(iprange['start_address'], '2400:dd01:1010:30::')
        self.assertEqual(iprange['end_address'], '2400:dd01:1010:30:ffff:ffff:ffff:ffff')
        self.assertEqual(iprange['prefixlen'], 64)
        self.assertEqual(iprange['asn']['number'], 66)

        # query "org_id"
        query = parse.urlencode(query={'org_id': org1.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

        query = parse.urlencode(query={'org_id': org2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

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

        query = parse.urlencode(query={'asn': 88})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # query "ip"
        query = parse.urlencode(query={'ip': '127.0.0.255'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'ip': '2400:dd01:1010:30::ff'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

        query = parse.urlencode(query={'ip': '2400:dd01:1010:31::'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        # query "search"
        query = parse.urlencode(query={'search': 'admin1'})     # 不能搜索管理员备注
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'search': 'remark'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 1, 'page_size': 8})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 8)
        self.assertEqual(len(response.data['results']), 1)

        # query "status", admin param
        query = parse.urlencode(query={'status': IPv6Range.Status.ASSIGNED.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ---- admin ----
        # user1 as-admin
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 只读管理权限
        u1_role_wrapper.set_ipam_readonly(True)
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 4)

        # order by 'start_address'
        self.assertEqual(response.data['results'][0]['id'], ip_range3.id)
        self.assertEqual(response.data['results'][1]['id'], ip_range1.id)
        self.assertEqual(response.data['results'][2]['id'], ip_range2.id)
        self.assertEqual(response.data['results'][3]['id'], ip_range4.id)

        # query "org_id"
        query = parse.urlencode(query={'as-admin': '', 'org_id': org1.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'as-admin': '', 'org_id': org2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

        # user2
        self.client.logout()
        self.client.force_login(self.user2)

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u2_role_wrapper = NetIPamUserRoleWrapper(user=self.user2)
        u2_role_wrapper.user_role = u2_role_wrapper.get_or_create_user_role()
        u2_role_wrapper.set_ipam_admin(True)

        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 4)

        # query "search"
        query = parse.urlencode(query={'as-admin': '', 'search': 'admin remark'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)

        # query "page"、"page_size"
        query = parse.urlencode(query={'as-admin': '', 'page': 2, 'page_size': 3})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 3)
        self.assertEqual(len(response.data['results']), 1)

        # query "status", admin param
        query = parse.urlencode(query={'as-admin': '', 'status': 'test'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'as-admin': '', 'status': IPv6Range.Status.RESERVED.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_create_ipv6_range(self):
        base_url = reverse('net_ipam-api:ipam-ipv6range-list')
        response = self.client.post(base_url, data={
            'name': '', 'start_address': '', 'end_address': '', 'prefixlen': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # start_address
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::fffg',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # end_address
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:3000:ffff:ffff:ffff:fffg', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # prefixlen 0-128
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 129,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # asn 0-4294967295
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 4294967295 + 1, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_role()
        u1_role_wrapper.set_ipam_readonly(True)
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.set_ipam_readonly(False)
        u1_role_wrapper.set_ipam_admin(True)

        # start_address > end_address
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:31::',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # start_address, end_address, prefixlen, not in same network
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:31:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 65,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        self.assertEqual(IPv6RangeRecord.objects.count(), 0)
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 4294967295, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
                           'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'], response.data)
        self.assertEqual(response.data['start_address'], '2400:dd01:1010:30::')
        self.assertEqual(response.data['end_address'], '2400:dd01:1010:30:ffff:ffff:ffff:ffff')
        iprange = IPv6Range.objects.get(id=response.data['id'])
        self.assertEqual(iprange.start_address, ipaddress.IPv6Address('2400:dd01:1010:30::').packed)
        self.assertEqual(iprange.end_address, ipaddress.IPv6Address('2400:dd01:1010:30:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(iprange.prefixlen, 64)
        self.assertEqual(iprange.status, IPv6Range.Status.WAIT.value)
        self.assertEqual(iprange.asn.number, 4294967295)
        self.assertEqual(iprange.name, 'test')

        self.assertEqual(IPv6RangeRecord.objects.count(), 1)
        record: IPv6RangeRecord = IPv6RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv6RangeRecord.RecordType.ADD.value)
        self.assertEqual(record.start_address, ipaddress.IPv6Address('2400:dd01:1010:30::').packed)
        self.assertEqual(record.end_address, ipaddress.IPv6Address('2400:dd01:1010:30:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(record.prefixlen, 64)

        # 存在重叠
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:30:0:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30:1::',
            'end_address': '2400:dd01:1010:30:1:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff',
            'end_address': '2400:dd01:1010:31:ffff:ffff:ffff:ffff', 'prefixlen': 63,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:31::ffff',
            'end_address': '2400:dd01:1010:31:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IPv6RangeRecord.objects.count(), 2)

    def test_update_ipv6_range(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv6RangeManager.create_ipv6_range(
            name='已分配1', start_ip='2400:dd01:1010:30::', end_ip='2400:dd01:1010:30:ffff:ffff:ffff:ffff',
            prefixlen=64, asn=66,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.ASSIGNED.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv6RangeManager.create_ipv6_range(
            name='预留2', start_ip='2400:dd01:1010:34::', end_ip='2400:dd01:1010:35:ffff:ffff:ffff:fff',
            prefixlen=63, asn=88,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-ipv6range-detail', kwargs={'id': 'test'})
        response = self.client.put(base_url, data={
            'name': 'test', 'prefixlen': 64,
            'start_address': '2400:dd01:1010:31::', 'end_address': '2400:dd01:1010:31:ffff:ffff:ffff:0',
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.put(base_url, data={
            'name': 'test', 'prefixlen': 64,
            'start_address': '2400:dd01:1010:31::', 'end_address': '2400:dd01:1010:31:ffff:ffff:ffff:0',
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        base_url = reverse('net_ipam-api:ipam-ipv6range-detail', kwargs={'id': ip_range1.id})
        response = self.client.put(base_url, data={
            'name': 'test', 'prefixlen': 64,
            'start_address': '2400:dd01:1010:31::', 'end_address': '2400:dd01:1010:31:ffff:ffff:ffff:0',
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.put(base_url, data={
            'name': 'test', 'prefixlen': 64,
            'start_address': '2400:dd01:1010:31::', 'end_address': '2400:dd01:1010:31:ffff:ffff:ffff:0',
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)
        # status 'assigned'
        response = self.client.put(base_url, data={
            'name': 'test', 'prefixlen': 64,
            'start_address': '2400:dd01:1010:31::', 'end_address': '2400:dd01:1010:31:ffff:ffff:ffff:0',
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok
        ip_range1.status = IPv6Range.Status.WAIT.value
        ip_range1.save(update_fields=['status'])
        response = self.client.put(base_url, data={
            'name': 'test', 'prefixlen': 64,
            'start_address': '2400:dd01:1010:31::ffff', 'end_address': '2400:dd01:1010:31:ffff:ffff:ffff:1',
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
                           'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'], response.data)
        self.assertEqual(response.data['start_address'], '2400:dd01:1010:31::ffff')
        self.assertEqual(response.data['end_address'], '2400:dd01:1010:31:ffff:ffff:ffff:1')
        self.assertEqual(response.data['prefixlen'], 64)
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.start_address, ipaddress.IPv6Address('2400:dd01:1010:31::ffff').packed)
        self.assertEqual(ip_range1.end_address, ipaddress.IPv6Address('2400:dd01:1010:31:ffff:ffff:ffff:1').packed)

        self.assertEqual(IPv6RangeRecord.objects.count(), 1)
        record: IPv6RangeRecord = IPv6RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv6RangeRecord.RecordType.CHANGE.value)
        self.assertEqual(record.start_address, ipaddress.IPv6Address('2400:dd01:1010:30::').packed)
        self.assertEqual(record.end_address, ipaddress.IPv6Address('2400:dd01:1010:30:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(record.prefixlen, 64)
        self.assertEqual(record.ip_ranges[0]['start'], '2400:dd01:1010:31::ffff')
        self.assertEqual(record.ip_ranges[0]['end'], '2400:dd01:1010:31:ffff:ffff:ffff:1')
        self.assertEqual(record.ip_ranges[0]['prefix'], 64)

        # start和end 子网不同
        response = self.client.put(base_url, data={
            'name': 'test', 'prefixlen': 64,
            'start_address': '2400:dd01:1010:32::ffff', 'end_address': '2400:dd01:1010:33:ffff:ffff:ffff:1',
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.put(base_url, data={
            'name': 'test', 'prefixlen': 63,
            'start_address': '2400:dd01:1010:32::ffff', 'end_address': '2400:dd01:1010:33:ffff:ffff:ffff:1',
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IPv6RangeRecord.objects.count(), 2)

        # ip mask不变不产生记录
        response = self.client.put(base_url, data={
            'name': '66test88', 'prefixlen': 63,
            'start_address': '2400:dd01:1010:32::ffff', 'end_address': '2400:dd01:1010:33:ffff:ffff:ffff:1',
            'asn': 99, 'admin_remark': '88remark test 66'
        })
        self.assertEqual(response.status_code, 200)
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.name, '66test88')
        self.assertEqual(ip_range1.admin_remark, '88remark test 66')
        self.assertEqual(ip_range1.asn.number, 99)
        self.assertEqual(IPv6RangeRecord.objects.count(), 2)

        # ok
        base_url = reverse('net_ipam-api:ipam-ipv6range-detail', kwargs={'id': ip_range2.id})
        response = self.client.put(base_url, data={
            'name': 'test', 'prefixlen': 63,
            'start_address': '2400:dd01:1010:34::ffff', 'end_address': '2400:dd01:1010:34:ffff:ffff:ffff:1',
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
                           'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'], response.data)
        self.assertEqual('2400:dd01:1010:34::ffff', response.data['start_address'])
        self.assertEqual('2400:dd01:1010:34:ffff:ffff:ffff:1', response.data['end_address'])
        self.assertEqual(63, response.data['prefixlen'])
        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.start_address, ipaddress.IPv6Address('2400:dd01:1010:34::ffff').packed)
        self.assertEqual(ip_range2.end_address, ipaddress.IPv6Address('2400:dd01:1010:34:ffff:ffff:ffff:1').packed)
        self.assertEqual(ip_range2.prefixlen, 63)
        self.assertEqual(ip_range2.org_virt_obj_id, virt_obj1.id)

        self.assertEqual(IPv6RangeRecord.objects.count(), 3)

    def test_delete_ipv6_range(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        nt = dj_timezone.now()
        ip_range1 = IPv6RangeManager.create_ipv6_range(
            name='已分配1', start_ip='2400:dd01:1010:30::', end_ip='2400:dd01:1010:30:ffff:ffff:ffff:ffff',
            prefixlen=64, asn=66,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.ASSIGNED.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv6RangeManager.create_ipv6_range(
            name='预留2', start_ip='2400:dd01:1010:34::', end_ip='2400:dd01:1010:35:ffff:ffff:ffff:fff',
            prefixlen=63, asn=88,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-ipv6range-detail', kwargs={'id': 'test'})
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        base_url = reverse('net_ipam-api:ipam-ipv6range-detail', kwargs={'id': ip_range1.id})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok
        ip_range1.status = IPv6Range.Status.WAIT.value
        ip_range1.save(update_fields=['status'])
        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.count(), 0)
        base_url = reverse('net_ipam-api:ipam-ipv6range-detail', kwargs={'id': ip_range1.id})
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(IPv6Range.objects.count(), 1)
        self.assertEqual(IPv6RangeRecord.objects.count(), 1)
        record: IPv6RangeRecord = IPv6RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv6RangeRecord.RecordType.DELETE.value)
        self.assertEqual(record.start_address, ipaddress.IPv6Address('2400:dd01:1010:30::').packed)
        self.assertEqual(record.end_address, ipaddress.IPv6Address('2400:dd01:1010:30:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(record.prefixlen, 64)
        self.assertEqual(record.ip_ranges, [])

        # ok
        base_url = reverse('net_ipam-api:ipam-ipv6range-detail', kwargs={'id': ip_range2.id})
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(IPv6Range.objects.count(), 0)
        self.assertEqual(IPv6RangeRecord.objects.count(), 2)

    def test_recover_ipv6_range(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv6RangeManager.create_ipv6_range(
            name='已分配1', prefixlen=64, asn=66,
            start_ip='2400:dd01:1010:30::', end_ip='2400:dd01:1010:30:ffff:ffff:ffff:ffff',
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv6RangeManager.create_ipv6_range(
            name='预留2', prefixlen=62, asn=88,
            start_ip='2400:dd01:1010:34::', end_ip='2400:dd01:1010:37:ffff:ffff:ffff:ffff',
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-ipv6range-recover', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # ok
        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.count(), 0)
        base_url = reverse('net_ipam-api:ipam-ipv6range-recover', kwargs={'id': ip_range1.id})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'
        ], response.data)

        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.start_address, ipaddress.IPv6Address('2400:dd01:1010:30::').packed)
        self.assertEqual(ip_range1.end_address, ipaddress.IPv6Address('2400:dd01:1010:30:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ip_range1.prefixlen, 64)
        self.assertIsNone(ip_range1.org_virt_obj)
        self.assertIsNone(ip_range1.assigned_time)
        self.assertEqual(ip_range1.remark, '')
        self.assertEqual(ip_range1.status, IPv6Range.Status.WAIT.value)

        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.count(), 1)

        record: IPv6RangeRecord = IPv6RangeRecord.objects.first()
        self.assertEqual(record.start_address, ip_range1.start_address)
        self.assertEqual(record.end_address, ip_range1.end_address)
        self.assertEqual(record.prefixlen, 64)
        self.assertEqual(record.ip_ranges, [])
        self.assertEqual(record.org_virt_obj_id, virt_obj1.id)
        self.assertEqual(record.record_type, IPv6RangeRecord.RecordType.RECOVER.value)

        # ok
        base_url = reverse('net_ipam-api:ipam-ipv6range-recover', kwargs={'id': ip_range2.id})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'
        ], response.data)

        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.start_address, ipaddress.IPv6Address('2400:dd01:1010:34::').packed)
        self.assertEqual(ip_range2.end_address, ipaddress.IPv6Address('2400:dd01:1010:37:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ip_range2.prefixlen, 62)
        self.assertIsNone(ip_range2.org_virt_obj)
        self.assertIsNone(ip_range2.assigned_time)
        self.assertEqual(ip_range2.remark, '')
        self.assertEqual(ip_range2.status, IPv6Range.Status.WAIT.value)

        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.count(), 2)

    def test_reserve_ipv6_range(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv6RangeManager.create_ipv6_range(
            name='已分配1', prefixlen=64, asn=66,
            start_ip='2400:dd01:1010:30::', end_ip='2400:dd01:1010:30:ffff:ffff:ffff:ffff',
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv6RangeManager.create_ipv6_range(
            name='预留2', prefixlen=62, asn=88,
            start_ip='2400:dd01:1010:34::', end_ip='2400:dd01:1010:37:ffff:ffff:ffff:ffff',
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-ipv6range-reserve', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'org_virt_obj_id': 'notfound'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        query = parse.urlencode(query={'org_virt_obj_id': virt_obj1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # status
        base_url = reverse('net_ipam-api:ipam-ipv6range-reserve', kwargs={'id': ip_range1.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok
        ip_range1.org_virt_obj = None
        ip_range1.status = IPv6Range.Status.WAIT.value
        ip_range1.save(update_fields=['status', 'org_virt_obj'])
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.status, IPv6Range.Status.WAIT.value)
        self.assertIsNone(ip_range1.org_virt_obj)
        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.count(), 0)

        base_url = reverse('net_ipam-api:ipam-ipv6range-reserve', kwargs={'id': ip_range1.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'
        ], response.data)

        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.start_address, ipaddress.IPv6Address('2400:dd01:1010:30::').packed)
        self.assertEqual(ip_range1.end_address, ipaddress.IPv6Address('2400:dd01:1010:30:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ip_range1.prefixlen, 64)
        self.assertEqual(ip_range1.org_virt_obj_id, virt_obj1.id)
        self.assertIsNone(ip_range1.assigned_time)
        self.assertEqual(ip_range1.remark, '')
        self.assertEqual(ip_range1.status, IPv6Range.Status.RESERVED.value)

        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.count(), 1)

        record: IPv6RangeRecord = IPv6RangeRecord.objects.first()
        self.assertEqual(record.start_address, ip_range1.start_address)
        self.assertEqual(record.end_address, ip_range1.end_address)
        self.assertEqual(record.prefixlen, 64)
        self.assertEqual(record.ip_ranges, [])
        self.assertEqual(record.org_virt_obj_id, virt_obj1.id)
        self.assertEqual(record.record_type, IPv6RangeRecord.RecordType.RESERVE.value)

        # ok
        base_url = reverse('net_ipam-api:ipam-ipv6range-reserve', kwargs={'id': ip_range2.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        ip_range2.status = IPv6Range.Status.WAIT.value
        ip_range2.org_virt_obj = None
        ip_range2.save(update_fields=['status', 'org_virt_obj'])
        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.status, IPv6Range.Status.WAIT.value)
        self.assertIsNone(ip_range2.org_virt_obj)
        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.count(), 1)

        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'
        ], response.data)

        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.start_address, ipaddress.IPv6Address('2400:dd01:1010:34::').packed)
        self.assertEqual(ip_range2.end_address, ipaddress.IPv6Address('2400:dd01:1010:37:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ip_range2.prefixlen, 62)
        self.assertEqual(ip_range2.org_virt_obj_id, virt_obj1.id)
        self.assertIsNone(ip_range2.assigned_time)
        self.assertEqual(ip_range2.remark, '')
        self.assertEqual(ip_range2.status, IPv6Range.Status.RESERVED.value)

        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.filter(
            record_type=IPv6RangeRecord.RecordType.RESERVE.value).count(), 2)

    def test_assign_ipv6_range(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)
        virt_obj2 = OrgVirtualObject(name='org virt obj2', organization=org1, creation_time=dj_timezone.now())
        virt_obj2.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv6RangeManager.create_ipv6_range(
            name='已分配1', start_ip='2400:dd01:1010:30::', end_ip='2400:dd01:1010:30:ffff:ffff:ffff:ffff', prefixlen=64,
            asn=66, create_time=nt, update_time=nt, status_code=IPv6Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv6RangeManager.create_ipv6_range(
            name='预留2', start_ip='8400:dd01:1010:30::', end_ip='8400:dd01:1010:30:ffff:ffff:ffff:ffff', prefixlen=64,
            asn=88, create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-ipv6range-assign', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'org_virt_obj_id': 'notfound'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        query = parse.urlencode(query={'org_virt_obj_id': virt_obj1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # 只能分配给预留机构二级对象
        base_url = reverse('net_ipam-api:ipam-ipv6range-assign', kwargs={'id': ip_range2.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj2.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok
        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.count(), 0)
        base_url = reverse('net_ipam-api:ipam-ipv6range-assign', kwargs={'id': ip_range2.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'
        ], response.data)

        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.start_address, ipaddress.IPv6Address('8400:dd01:1010:30::').packed)
        self.assertEqual(ip_range2.end_address, ipaddress.IPv6Address('8400:dd01:1010:30:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ip_range2.prefixlen, 64)
        self.assertEqual(ip_range2.org_virt_obj_id, virt_obj1.id)
        self.assertIsNotNone(ip_range2.assigned_time)
        self.assertEqual(ip_range2.remark, '')
        self.assertEqual(ip_range2.status, IPv6Range.Status.ASSIGNED.value)

        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.count(), 1)

        record: IPv6RangeRecord = IPv6RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv6RangeRecord.RecordType.ASSIGN.value)
        self.assertEqual(record.start_address, ip_range2.start_address)
        self.assertEqual(record.end_address, ip_range2.end_address)
        self.assertEqual(record.prefixlen, 64)
        self.assertEqual(record.ip_ranges, [])
        self.assertEqual(record.org_virt_obj_id, virt_obj1.id)

        # ip_range1
        # status
        base_url = reverse('net_ipam-api:ipam-ipv6range-assign', kwargs={'id': ip_range1.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj2.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        ip_range1.status = IPv6Range.Status.WAIT.value
        ip_range1.org_virt_obj = None
        ip_range1.save(update_fields=['status', 'org_virt_obj'])
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.status, IPv6Range.Status.WAIT.value)
        self.assertIsNone(ip_range1.org_virt_obj)
        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.count(), 1)

        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'
        ], response.data)
        self.assertKeysIn([
            'id', 'name', 'remark', 'creation_time', 'organization'
        ], response.data['org_virt_obj'])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['org_virt_obj']['organization'])

        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.start_address, ipaddress.IPv6Address('2400:dd01:1010:30::').packed)
        self.assertEqual(ip_range1.end_address, ipaddress.IPv6Address('2400:dd01:1010:30:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ip_range1.prefixlen, 64)
        self.assertEqual(ip_range1.org_virt_obj_id, virt_obj2.id)
        self.assertIsInstance(ip_range1.assigned_time, datetime)
        self.assertEqual(ip_range1.remark, '')
        self.assertEqual(ip_range1.status, IPv6Range.Status.ASSIGNED.value)

        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.filter(
            record_type=IPv6RangeRecord.RecordType.ASSIGN.value).count(), 2)

    def test_remark(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv6RangeManager.create_ipv6_range(
            name='已分配1', start_ip='1234:cd11:24bb::', end_ip='1234:cd11:24bb:ffff:ffff:ffff:ffff:ffff', prefixlen=48,
            asn=66, create_time=nt, update_time=nt, status_code=IPv6Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv6RangeManager.create_ipv6_range(
            name='预留2', start_ip='df23:3432:bc33:1001::', end_ip='df23:3432:bc33:1001:ffff:ffff:ffff:ffff',
            prefixlen=64, asn=88, create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-ipv6range-remark', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'remark': 'notfound'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        query = parse.urlencode(query={'admin_remark': 'notfound66'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # not org admin
        base_url = reverse('net_ipam-api:ipam-ipv6range-remark', kwargs={'id': ip_range1.id})
        query = parse.urlencode(query={'remark': 'notfound'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.user_role.organizations.add(org1)
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.remark, 'notfound')
        self.assertEqual(ip_range1.admin_remark, 'admin1')

        # no org
        ip_range1.org_virt_obj = None
        ip_range1.save(update_fields=['org_virt_obj'])
        query = parse.urlencode(query={'remark': 'test66'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # status not assigned
        base_url = reverse('net_ipam-api:ipam-ipv6range-remark', kwargs={'id': ip_range2.id})
        query = parse.urlencode(query={'remark': 'notfound'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # ---- test as-admin ----
        uirw.user_role.organizations.remove(org1)

        base_url = reverse('net_ipam-api:ipam-ipv6range-remark', kwargs={'id': ip_range1.id})
        query = parse.urlencode(query={'remark': 'test88', 'admin_remark': 'admin remark88', 'as-admin': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_readonly(True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.remark, 'test88')
        self.assertEqual(ip_range1.admin_remark, 'admin remark88')

        base_url = reverse('net_ipam-api:ipam-ipv6range-remark', kwargs={'id': ip_range2.id})
        query = parse.urlencode(query={'remark': 'test66', 'admin_remark': 'admin remark66', 'as-admin': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.remark, 'test66')
        self.assertEqual(ip_range2.admin_remark, 'admin remark66')
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'
        ], response.data)
        self.assertEqual(response.data['admin_remark'], 'admin remark66')
        self.assertEqual(response.data['remark'], 'test66')

    def test_plan(self):
        base_url = reverse('net_ipam-api:ipam-ipv6range-plan')
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # 前缀长度跨度小于3，会平拆
        response = self.client.post(base_url, data={
            'start': 'cb00::', 'end': 'cb00:ffff:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 16,
            'new_prefix': 18
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ip_ranges']), 4)
        ip_ranges1 = response.data['ip_ranges']
        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[0]['start']), ipaddress.IPv6Address('cb00::'))
        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[0]['end']),
                         ipaddress.IPv6Address('cb00:3fff:ffff:ffff:ffff:ffff:ffff:ffff'))
        self.assertEqual(ip_ranges1[0]['prefix'], 18)

        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[1]['start']), ipaddress.IPv6Address('cb00:4000::'))
        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[1]['end']),
                         ipaddress.IPv6Address('cb00:7fff:ffff:ffff:ffff:ffff:ffff:ffff'))
        self.assertEqual(ip_ranges1[1]['prefix'], 18)

        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[2]['start']), ipaddress.IPv6Address('cb00:8000::'))
        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[2]['end']),
                         ipaddress.IPv6Address('cb00:bfff:ffff:ffff:ffff:ffff:ffff:ffff'))
        self.assertEqual(ip_ranges1[2]['prefix'], 18)

        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[3]['start']), ipaddress.IPv6Address('cb00:c000::'))
        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[3]['end']),
                         ipaddress.IPv6Address('cb00:ffff:ffff:ffff:ffff:ffff:ffff:ffff'))
        self.assertEqual(ip_ranges1[3]['prefix'], 18)

        # 会平拆一个124为8个127，其他拆分为前缀长度为17-124的108个子网段
        response = self.client.post(base_url, data={
            'start': 'cb00::', 'end': 'cb00:ffff:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 16,
            'new_prefix': 127
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['ip_ranges']), 116)
        ip_ranges1 = response.data['ip_ranges']
        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[0]['start']), ipaddress.IPv6Address('cb00::'))
        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[0]['end']),
                         ipaddress.IPv6Address('cb00::1'))
        self.assertEqual(ip_ranges1[0]['prefix'], 127)

        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[1]['start']), ipaddress.IPv6Address('cb00::2'))
        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[1]['end']),
                         ipaddress.IPv6Address('cb00::3'))
        self.assertEqual(ip_ranges1[1]['prefix'], 127)

        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[8]['start']), ipaddress.IPv6Address('cb00::10'))
        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[8]['end']),
                         ipaddress.IPv6Address('cb00::1f'))
        self.assertEqual(ip_ranges1[8]['prefix'], 124)

        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[-2]['start']), ipaddress.IPv6Address('cb00:4000::'))
        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[-2]['end']),
                         ipaddress.IPv6Address('cb00:7fff:ffff:ffff:ffff:ffff:ffff:ffff'))
        self.assertEqual(ip_ranges1[-2]['prefix'], 18)

        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[-1]['start']), ipaddress.IPv6Address('cb00:8000::'))
        self.assertEqual(ipaddress.IPv6Address(ip_ranges1[-1]['end']),
                         ipaddress.IPv6Address('cb00:ffff:ffff:ffff:ffff:ffff:ffff:ffff'))
        self.assertEqual(ip_ranges1[-1]['prefix'], 17)

    def test_split_to_plan(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv6RangeManager.create_ipv6_range(
            name='已分配1', start_ip='bc00:1000::', end_ip='bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff', prefixlen=32, asn=66,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.ASSIGNED.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv6RangeManager.create_ipv6_range(
            name='预留2', start_ip='d000:0:1fff::', end_ip='d000:0:1fff:ffff:ffff:ffff:ffff:ffff', prefixlen=48, asn=88,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-ipv6range-plan-split', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'sub_ranges': []
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'bc00:1000::',
                 'end_address': 'bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 33},
                {'start_address': 'bc00:1000:8000::',
                 'end_address': 'bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 33}
            ]
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'bc00:1000::',
                 'end_address': 'bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 33},
                {'start_address': 'bc00:1000:8000::',
                 'end_address': 'bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 33}
            ]
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        # sub_ranges
        # response = self.client.post(base_url, data={
        #     'sub_ranges': [
        #         {'start_address': 32, 'end_address': 'bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 33},
        #         {'start_address': 'bc00:1000:8000::',
        #          'end_address': 'bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 33}
        #     ]
        # })
        # self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'bc00:1000::',
                 'end_address': 'bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 129},
                {'start_address': 'bc00:1000:8000::',
                 'end_address': 'bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 33}
            ]
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'bc00:1000::',
                 'end_address': 'bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 33},
                {'start_address': 'bc00:1000:8000::',
                 'end_address': 'bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 33}
            ]
        })
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        base_url = reverse('net_ipam-api:ipam-ipv6range-plan-split', kwargs={'id': ip_range1.id})
        # assigned
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'bc00:1000::',
                 'end_address': 'bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 33},
                {'start_address': 'bc00:1000:8000::',
                 'end_address': 'bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 33}
            ]
        })
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        ip_range1.status = IPv6Range.Status.WAIT.value
        ip_range1.save(update_fields=['status'])

        # 子网和超网ip范围不一致
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'bc00:1000:1::',
                 'end_address': 'bc00:1000:3fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34},
                {'start_address': 'bc00:1000:4000::',
                 'end_address': 'bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34},
                {'start_address': 'bc00:1000:8000::',
                 'end_address': 'bc00:1000:bfff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34},
                {'start_address': 'bc00:1000:c000::',
                 'end_address': 'bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34}
            ]
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # 不连续
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'bc00:1000::',
                 'end_address': 'bc00:1000:3fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34},
                {'start_address': 'bc00:1000:4000::1',
                 'end_address': 'bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34},
                {'start_address': 'bc00:1000:8000::',
                 'end_address': 'bc00:1000:bfff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34},
                {'start_address': 'bc00:1000:c000::',
                 'end_address': 'bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34}
            ]
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # 掩码长度
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'bc00:1000::',
                 'end_address': 'bc00:1000:3fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34},
                {'start_address': 'bc00:1000:4000::',
                 'end_address': 'bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 31},
                {'start_address': 'bc00:1000:8000::',
                 'end_address': 'bc00:1000:bfff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34},
                {'start_address': 'bc00:1000:c000::',
                 'end_address': 'bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34}
            ]
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok, bc00:1000:: - bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff
        self.assertEqual(IPv6RangeRecord.objects.count(), 0)
        self.assertEqual(IPv6Range.objects.count(), 2)

        base_url = reverse('net_ipam-api:ipam-ipv6range-plan-split', kwargs={'id': ip_range1.id})
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'bc00:1000::',
                 'end_address': 'bc00:1000:3fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34},
                {'start_address': 'bc00:1000:4000::',
                 'end_address': 'bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34},
                {'start_address': 'bc00:1000:8000::',
                 'end_address': 'bc00:1000:bfff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34},
                {'start_address': 'bc00:1000:c000::',
                 'end_address': 'bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff', 'prefix': 34}
            ]
        })
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 4)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv6RangeRecord.objects.count(), 1)
        self.assertEqual(IPv6Range.objects.count(), 5)

        ir1, ir2, ir3, ir4 = IPv6Range.objects.order_by('start_address')[0:4]
        self.assertEqual(ir1.start_address, ipaddress.IPv6Address('bc00:1000::').packed)
        self.assertEqual(ir1.end_address, ipaddress.IPv6Address('bc00:1000:3fff:ffff:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ir1.prefixlen, 34)
        self.assertEqual(ir2.start_address, ipaddress.IPv6Address('bc00:1000:4000::').packed)
        self.assertEqual(ir2.end_address, ipaddress.IPv6Address('bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ir2.prefixlen, 34)
        self.assertEqual(ir3.start_address, ipaddress.IPv6Address('bc00:1000:8000::').packed)
        self.assertEqual(ir3.end_address, ipaddress.IPv6Address('bc00:1000:bfff:ffff:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ir3.prefixlen, 34)
        self.assertEqual(ir4.start_address, ipaddress.IPv6Address('bc00:1000:c000::').packed)
        self.assertEqual(ir4.end_address, ipaddress.IPv6Address('bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ir4.prefixlen, 34)

        # 拆分记录
        record = IPv6RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv6RangeRecord.RecordType.SPLIT.value)
        self.assertEqual(record.start_address, ipaddress.IPv6Address('bc00:1000::').packed)
        self.assertEqual(record.end_address, ipaddress.IPv6Address('bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(record.prefixlen, 32)
        ir1, ir2, ir3, ir4 = record.ip_ranges
        self.assertEqual(ipaddress.IPv6Address(ir1['start']), ipaddress.IPv6Address('bc00:1000::'))
        self.assertEqual(ipaddress.IPv6Address(ir1['end']),
                         ipaddress.IPv6Address('bc00:1000:3fff:ffff:ffff:ffff:ffff:ffff'))
        self.assertEqual(ir1['prefix'], 34)
        self.assertEqual(ipaddress.IPv6Address(ir2['start']), ipaddress.IPv6Address('bc00:1000:4000::'))
        self.assertEqual(ipaddress.IPv6Address(ir2['end']),
                         ipaddress.IPv6Address('bc00:1000:7fff:ffff:ffff:ffff:ffff:ffff'))
        self.assertEqual(ir2['prefix'], 34)
        self.assertEqual(ipaddress.IPv6Address(ir3['start']), ipaddress.IPv6Address('bc00:1000:8000::'))
        self.assertEqual(ipaddress.IPv6Address(ir3['end']),
                         ipaddress.IPv6Address('bc00:1000:bfff:ffff:ffff:ffff:ffff:ffff'))
        self.assertEqual(ir3['prefix'], 34)
        self.assertEqual(ipaddress.IPv6Address(ir4['start']), ipaddress.IPv6Address('bc00:1000:c000::'))
        self.assertEqual(ipaddress.IPv6Address(ir4['end']),
                         ipaddress.IPv6Address('bc00:1000:ffff:ffff:ffff:ffff:ffff:ffff'))
        self.assertEqual(ir4['prefix'], 34)

        # ok, range2
        self.assertEqual(IPv6RangeRecord.objects.count(), 1)
        self.assertEqual(IPv6Range.objects.count(), 5)
        base_url = reverse('net_ipam-api:ipam-ipv6range-plan-split', kwargs={'id': ip_range2.id})
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'd000:0:1fff::',
                 'end_address': 'd000:0:1fff:1fff:ffff:ffff:ffff:ffff', 'prefix': 51},
                {'start_address': 'd000:0:1fff:2000::',
                 'end_address': 'd000:0:1fff:3fff:ffff:ffff:ffff:ffff', 'prefix': 51},
                {'start_address': 'd000:0:1fff:4000::',
                 'end_address': 'd000:0:1fff:7fff:ffff:ffff:ffff:ffff', 'prefix': 50},
                {'start_address': 'd000:0:1fff:8000::',
                 'end_address': 'd000:0:1fff:ffff:ffff:ffff:ffff:ffff', 'prefix': 49}
            ]
        })
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 4)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv6RangeRecord.objects.count(), 2)
        self.assertEqual(IPv6Range.objects.count(), 8)

        ir1, ir2, ir3, ir4 = IPv6Range.objects.order_by('start_address')[4:8]
        self.assertEqual(ir1.start_address, ipaddress.IPv6Address('d000:0:1fff::').packed)
        self.assertEqual(ir1.end_address, ipaddress.IPv6Address('d000:0:1fff:1fff:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ir1.prefixlen, 51)
        self.assertEqual(ir2.start_address, ipaddress.IPv6Address('d000:0:1fff:2000::').packed)
        self.assertEqual(ir2.end_address, ipaddress.IPv6Address('d000:0:1fff:3fff:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ir2.prefixlen, 51)
        self.assertEqual(ir3.start_address, ipaddress.IPv6Address('d000:0:1fff:4000::').packed)
        self.assertEqual(ir3.end_address, ipaddress.IPv6Address('d000:0:1fff:7fff:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ir3.prefixlen, 50)
        self.assertEqual(ir4.start_address, ipaddress.IPv6Address('d000:0:1fff:8000::').packed)
        self.assertEqual(ir4.end_address, ipaddress.IPv6Address('d000:0:1fff:ffff:ffff:ffff:ffff:ffff').packed)
        self.assertEqual(ir4.prefixlen, 49)

        # prefixlen 127 test
        nt = dj_timezone.now()
        ip_range3 = IPv6RangeManager.create_ipv6_range(
            name='预留2', start_ip='dd66::1:0', end_ip='dd66::1:3', prefixlen=126, asn=88,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )
        self.assertEqual(IPv6RangeRecord.objects.count(), 2)
        self.assertEqual(IPv6Range.objects.count(), 9)

        base_url = reverse('net_ipam-api:ipam-ipv6range-plan-split', kwargs={'id': ip_range3.id})
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'dd66::1:0', 'end_address': 'dd66::1:0', 'prefix': 128},
                {'start_address': 'dd66::1:1', 'end_address': 'dd66::1:1', 'prefix': 128},
                {'start_address': 'dd66::1:2', 'end_address': 'dd66::1:3', 'prefix': 127},
            ]
        })
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 3)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv6RangeRecord.objects.count(), 3)
        self.assertEqual(IPv6Range.objects.count(), 11)
        ir1, ir2, ir3 = IPv6Range.objects.order_by('start_address')[8:11]
        self.assertEqual(ir1.start_address, ipaddress.IPv6Address('dd66::1:0').packed)
        self.assertEqual(ir1.end_address, ipaddress.IPv6Address('dd66::1:0').packed)
        self.assertEqual(ir1.prefixlen, 128)
        self.assertEqual(ir2.start_address, ipaddress.IPv6Address('dd66::1:1').packed)
        self.assertEqual(ir2.end_address, ipaddress.IPv6Address('dd66::1:1').packed)
        self.assertEqual(ir2.prefixlen, 128)
        self.assertEqual(ir3.start_address, ipaddress.IPv6Address('dd66::1:2').packed)
        self.assertEqual(ir3.end_address, ipaddress.IPv6Address('dd66::1:3').packed)
        self.assertEqual(ir3.prefixlen, 127)

        # 不完成网段
        nt = dj_timezone.now()
        ip_range4 = IPv6RangeManager.create_ipv6_range(
            name='预留4', start_ip='dd66::23:03', end_ip='dd66::23:0d', prefixlen=124, asn=88,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark4', remark='remark4'
        )
        base_url = reverse('net_ipam-api:ipam-ipv6range-plan-split', kwargs={'id': ip_range4.id})
        self.assertEqual(IPv6RangeRecord.objects.count(), 3)
        self.assertEqual(IPv6Range.objects.count(), 12)
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 'dd66::23:3', 'end_address': 'dd66::23:7', 'prefix': 125},
                {'start_address': 'dd66::23:8', 'end_address': 'dd66::23:b', 'prefix': 126},
                {'start_address': 'dd66::23:c', 'end_address': 'dd66::23:d', 'prefix': 126}
            ]
        })
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 3)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'prefixlen', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv6RangeRecord.objects.count(), 4)
        self.assertEqual(IPv6Range.objects.count(), 14)
        ir1, ir2, ir3 = IPv6Range.objects.order_by('start_address')[11:14]
        self.assertEqual(ir1.start_address, ipaddress.IPv6Address('dd66::23:3').packed)
        self.assertEqual(ir1.end_address, ipaddress.IPv6Address('dd66::23:7').packed)
        self.assertEqual(ir1.prefixlen, 125)
        self.assertEqual(ir2.start_address, ipaddress.IPv6Address('dd66::23:8').packed)
        self.assertEqual(ir2.end_address, ipaddress.IPv6Address('dd66::23:b').packed)
        self.assertEqual(ir2.prefixlen, 126)
        self.assertEqual(ir3.start_address, ipaddress.IPv6Address('dd66::23:c').packed)
        self.assertEqual(ir3.end_address, ipaddress.IPv6Address('dd66::23:d').packed)
        self.assertEqual(ir3.prefixlen, 126)

    def test_merge(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ir1_sub1 = IPv6RangeManager.create_ipv6_range(
            name='预留1', start_ip='1000::0:0', end_ip='1000::0:ffff', prefixlen=112, asn=88,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.WAIT.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark1', remark='remark1'
        )
        nt = dj_timezone.now()
        ir1_sub2 = IPv6RangeManager.create_ipv6_range(
            name='预留2', start_ip='1000::1:0', end_ip='1000::1:ffff', prefixlen=112, asn=88,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )
        nt = dj_timezone.now()
        ir1_sub3 = IPv6RangeManager.create_ipv6_range(
            name='预留3', start_ip='1000::2:0', end_ip='1000::2:ffff', prefixlen=112, asn=66,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.WAIT.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark3', remark='remark3'
        )
        nt = dj_timezone.now()
        ir1_sub4 = IPv6RangeManager.create_ipv6_range(
            name='预留4', start_ip='1000::3:0', end_ip='1000::3:ffff', prefixlen=112, asn=88,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark4', remark='remark4'
        )

        base_url = reverse('net_ipam-api:ipam-ipv6range-merge')
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={
            'new_prefix': 112, 'ip_range_ids': ['test1', 'test2'], 'fake': True})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # new_prefix
        response = self.client.post(base_url, data={
            'new_prefix': 0, 'ip_range_ids': ['test1', 'test2'], 'fake': True})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.client.post(base_url, data={
            'new_prefix': 128, 'ip_range_ids': ['test1', 'test2'], 'fake': True})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ip_range_ids
        response = self.client.post(base_url, data={'new_prefix': 112, 'ip_range_ids': '', 'fake': True})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.client.post(base_url, data={'new_prefix': 112, 'ip_range_ids': [], 'fake': True})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.client.post(base_url, data={'new_prefix': 112, 'ip_range_ids': ['test1' * 8], 'fake': True})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.post(base_url, data={'new_prefix': 112, 'ip_range_ids': ['test1'], 'fake': True})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.post(base_url, data={'new_prefix': 112, 'ip_range_ids': ['test1'], 'fake': True})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        response = self.client.post(base_url, data={'new_prefix': 112, 'ip_range_ids': ['test1'], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # new_prefix 必须小于等于 ip_range.prefixlen
        response = self.client.post(base_url, data={'new_prefix': 113, 'ip_range_ids': [ir1_sub1.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok，merge 1 ip_range，prefix not change，no merge happened
        response = self.client.post(base_url, data={'new_prefix': 112, 'ip_range_ids': [ir1_sub1.id], 'fake': True})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(supernet['id'], ir1_sub1.id)
        self.assertEqual(ipaddress.IPv6Address(supernet['start_address']).packed, ir1_sub1.start_address)
        self.assertEqual(ipaddress.IPv6Address(supernet['end_address']).packed, ir1_sub1.end_address)
        self.assertEqual(supernet['prefixlen'], ir1_sub1.prefixlen)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(IPv6RangeRecord.objects.count(), 0)
        self.assertEqual(IPv6Range.objects.count(), 4)

        # ok，merge 1 ip_range，prefix changed
        response = self.client.post(base_url, data={'new_prefix': 111, 'ip_range_ids': [ir1_sub1.id], 'fake': True})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(supernet['id'], '')
        self.assertEqual(ipaddress.IPv6Address(supernet['start_address']).packed, ir1_sub1.start_address)
        self.assertEqual(ipaddress.IPv6Address(supernet['end_address']).packed, ir1_sub1.end_address)
        self.assertEqual(supernet['prefixlen'], 111)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(supernet['asn']['id'], ir1_sub1.asn_id)
        self.assertIsNone(supernet['org_virt_obj'])
        self.assertEqual(IPv6RangeRecord.objects.count(), 0)
        self.assertEqual(IPv6Range.objects.count(), 4)

        # "已分配状态"
        response = self.client.post(base_url, data={'new_prefix': 111, 'ip_range_ids': [ir1_sub4.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        response = self.client.post(base_url, data={
            'new_prefix': 111, 'ip_range_ids': [ir1_sub3.id, ir1_sub4.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # 分配状态不一致
        response = self.client.post(base_url, data={
            'new_prefix': 111, 'ip_range_ids': [ir1_sub1.id, ir1_sub2.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # AS number 不一致
        response = self.client.post(base_url, data={
            'new_prefix': 111, 'ip_range_ids': [ir1_sub2.id, ir1_sub3.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('AS编码不一致', response.data['message'])
        ir1_sub3.asn = ir1_sub2.asn
        ir1_sub3.save(update_fields=['asn'])

        # 分配状态不一致
        response = self.client.post(base_url, data={
            'new_prefix': 111, 'ip_range_ids': [ir1_sub2.id, ir1_sub3.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('分配状态必须一致', response.data['message'])
        ir1_sub3.status = IPv6Range.Status.RESERVED.value
        ir1_sub3.save(update_fields=['status'])

        # 预留 状态时，关联机构二级对象不一致
        response = self.client.post(base_url, data={
            'new_prefix': 111, 'ip_range_ids': [ir1_sub2.id, ir1_sub3.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('关联的机构二级对象必须一致', response.data['message'])
        ir1_sub3.org_virt_obj = ir1_sub2.org_virt_obj
        ir1_sub3.save(update_fields=['org_virt_obj'])

        # 不属于同一个超网
        response = self.client.post(base_url, data={
            'new_prefix': 111, 'ip_range_ids': [ir1_sub2.id, ir1_sub3.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('不属于同一个超网', response.data['message'])

        # 地址段不连续
        ir1_sub1.status = ir1_sub3.status
        ir1_sub1.save(update_fields=['status'])
        response = self.client.post(base_url, data={
            'new_prefix': 110, 'ip_range_ids': [ir1_sub1.id, ir1_sub3.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('地址必须是连续的', response.data['message'])

        # ok
        response = self.client.post(base_url, data={
            'new_prefix': 110, 'ip_range_ids': [ir1_sub2.id, ir1_sub3.id], 'fake': True})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(supernet['id'], '')
        self.assertEqual(ipaddress.IPv6Address(supernet['start_address']).packed, ir1_sub2.start_address)
        self.assertEqual(ipaddress.IPv6Address(supernet['end_address']).packed, ir1_sub3.end_address)
        self.assertEqual(supernet['prefixlen'], 110)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(supernet['asn']['id'], ir1_sub1.asn_id)
        self.assertEqual(supernet['org_virt_obj']['id'], ir1_sub1.org_virt_obj_id)
        self.assertEqual(IPv6RangeRecord.objects.count(), 0)
        self.assertEqual(IPv6Range.objects.count(), 4)

        # sub1,sub2合并
        response = self.client.post(base_url, data={
            'new_prefix': 111, 'ip_range_ids': [ir1_sub2.id, ir1_sub1.id]})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertNotEqual(supernet['id'], '')
        self.assertEqual(ipaddress.IPv6Address(supernet['start_address']).packed, ir1_sub1.start_address)
        self.assertEqual(ipaddress.IPv6Address(supernet['end_address']).packed, ir1_sub2.end_address)
        self.assertEqual(supernet['prefixlen'], 111)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(supernet['asn']['id'], ir1_sub1.asn_id)
        self.assertEqual(supernet['org_virt_obj']['id'], ir1_sub1.org_virt_obj_id)
        super111net1_2 = IPv6Range.objects.get(id=supernet['id'])
        self.assertEqual(super111net1_2.start_address, ir1_sub1.start_address)
        self.assertEqual(super111net1_2.end_address, ir1_sub2.end_address)
        self.assertEqual(super111net1_2.prefixlen, 111)
        self.assertEqual(super111net1_2.status, ir1_sub1.status)
        self.assertEqual(IPv6RangeRecord.objects.count(), 1)
        self.assertEqual(IPv6Range.objects.count(), 3)
        # 合并记录
        record = IPv6RangeRecord.objects.first()
        self.assertEqual(record.start_address, super111net1_2.start_address)
        self.assertEqual(record.end_address, super111net1_2.end_address)
        self.assertEqual(record.prefixlen, 111)
        self.assertEqual(len(record.ip_ranges), 2)
        self.assertEqual(ipaddress.IPv6Address(record.ip_ranges[0]['start']).packed, ir1_sub1.start_address)
        self.assertEqual(ipaddress.IPv6Address(record.ip_ranges[0]['end']).packed, ir1_sub1.end_address)
        self.assertEqual(record.ip_ranges[0]['prefix'], 112)
        self.assertEqual(ipaddress.IPv6Address(record.ip_ranges[1]['start']).packed, ir1_sub2.start_address)
        self.assertEqual(ipaddress.IPv6Address(record.ip_ranges[1]['end']).packed, ir1_sub2.end_address)
        self.assertEqual(record.ip_ranges[1]['prefix'], 112)

        # sub1,sub2合并的超网 super111net1_2 和 sub3 合并超网
        response = self.client.post(base_url, data={
            'new_prefix': 111, 'ip_range_ids': [ir1_sub3.id, super111net1_2.id]})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('不属于同一个超网', response.data['message'])

        response = self.client.post(base_url, data={
            'new_prefix': 110, 'ip_range_ids': [ir1_sub3.id, super111net1_2.id]})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(ipaddress.IPv6Address(supernet['start_address']).packed, ir1_sub1.start_address)
        self.assertEqual(ipaddress.IPv6Address(supernet['end_address']).packed, ir1_sub3.end_address)
        self.assertEqual(supernet['prefixlen'], 110)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(supernet['asn']['id'], ir1_sub1.asn_id)
        self.assertEqual(supernet['org_virt_obj']['id'], ir1_sub1.org_virt_obj_id)
        super110net1_2_3 = IPv6Range.objects.get(id=supernet['id'])
        self.assertEqual(super110net1_2_3.start_address, ir1_sub1.start_address)
        self.assertEqual(super110net1_2_3.end_address, ir1_sub3.end_address)
        self.assertEqual(super110net1_2_3.prefixlen, 110)
        self.assertEqual(super110net1_2_3.status, ir1_sub1.status)
        self.assertEqual(IPv6RangeRecord.objects.count(), 2)
        self.assertEqual(IPv6Range.objects.count(), 2)

        # 超网 super110net1_2_3 和 sub4 合并超网
        response = self.client.post(base_url, data={
            'new_prefix': 110, 'ip_range_ids': [ir1_sub4.id, super110net1_2_3.id], 'fake': False})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('状态必须为"未分配"和“预留”', response.data['message'])

        ir1_sub4.status = ir1_sub1.status
        ir1_sub4.save(update_fields=['status'])
        response = self.client.post(base_url, data={
            'new_prefix': 110, 'ip_range_ids': [ir1_sub4.id, super110net1_2_3.id], 'fake': False})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(ipaddress.IPv6Address(supernet['start_address']).packed, ir1_sub1.start_address)
        self.assertEqual(ipaddress.IPv6Address(supernet['end_address']).packed, ir1_sub4.end_address)
        self.assertEqual(supernet['prefixlen'], 110)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(supernet['org_virt_obj']['id'], ir1_sub1.org_virt_obj_id)
        super110net1_2_3_4 = IPv6Range.objects.get(id=supernet['id'])
        self.assertEqual(super110net1_2_3_4.start_address, ir1_sub1.start_address)
        self.assertEqual(super110net1_2_3_4.end_address, ir1_sub4.end_address)
        self.assertEqual(super110net1_2_3_4.prefixlen, 110)
        self.assertEqual(super110net1_2_3_4.status, ir1_sub1.status)
        self.assertEqual(IPv6RangeRecord.objects.count(), 3)
        self.assertEqual(IPv6Range.objects.count(), 1)

        nt = dj_timezone.now()
        ir2_sub5 = IPv6RangeManager.create_ipv6_range(
            name='未分配1', start_ip='1000::4:0', end_ip='1000::4:ffff', prefixlen=112, asn=886,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.WAIT.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark1', remark='remark1'
        )
        nt = dj_timezone.now()
        ir2_sub6 = IPv6RangeManager.create_ipv6_range(
            name='未分配1', start_ip='1000::5:0', end_ip='1000::5:ffff', prefixlen=112, asn=886,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.WAIT.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark1', remark='remark1'
        )
        nt = dj_timezone.now()
        ir2_sub7 = IPv6RangeManager.create_ipv6_range(
            name='未分配2', start_ip='1000::6:0', end_ip='1000::6:ffff', prefixlen=112, asn=886,
            create_time=nt, update_time=nt, status_code=IPv6Range.Status.WAIT.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )
        self.assertEqual(IPv6RangeRecord.objects.count(), 3)
        self.assertEqual(IPv6Range.objects.count(), 4)

        # sub6 和 sub7 合并超网
        response = self.client.post(base_url, data={
            'new_prefix': 110, 'ip_range_ids': [ir2_sub7.id, ir2_sub6.id], 'fake': 'False'})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(ipaddress.IPv6Address(supernet['start_address']).packed, ir2_sub6.start_address)
        self.assertEqual(ipaddress.IPv6Address(supernet['end_address']).packed, ir2_sub7.end_address)
        self.assertEqual(supernet['prefixlen'], 110)
        self.assertEqual(supernet['status'], ir2_sub6.status)
        self.assertEqual(supernet['asn']['id'], ir2_sub6.asn_id)
        self.assertIsNone(supernet['org_virt_obj'])
        super110net6_7 = IPv6Range.objects.get(id=supernet['id'])
        self.assertEqual(super110net6_7.start_address, ir2_sub6.start_address)
        self.assertEqual(super110net6_7.end_address, ir2_sub7.end_address)
        self.assertEqual(super110net6_7.prefixlen, 110)
        self.assertEqual(super110net6_7.status, ir2_sub6.status)
        self.assertEqual(IPv6RangeRecord.objects.count(), 4)
        self.assertEqual(IPv6Range.objects.count(), 3)

        # 合并2个超网
        response = self.client.post(base_url, data={
            'new_prefix': 109, 'ip_range_ids': [super110net6_7.id, super110net1_2_3_4.id]})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('AS编码不一致', response.data['message'])
        super110net1_2_3_4.asn = super110net6_7.asn
        super110net1_2_3_4.save(update_fields=['asn'])

        response = self.client.post(base_url, data={
            'new_prefix': 109, 'ip_range_ids': [super110net6_7.id, super110net1_2_3_4.id]})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('分配状态必须一致', response.data['message'])
        super110net1_2_3_4.status = IPv6Range.Status.WAIT.value
        super110net1_2_3_4.org_virt_obj = None
        super110net1_2_3_4.save(update_fields=['status', 'org_virt_obj'])

        response = self.client.post(base_url, data={
            'new_prefix': 109, 'ip_range_ids': [super110net6_7.id, super110net1_2_3_4.id]})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('地址必须是连续的', response.data['message'])

        response = self.client.post(base_url, data={
            'new_prefix': 109, 'ip_range_ids': [super110net6_7.id, super110net1_2_3_4.id, ir2_sub5.id]})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(ipaddress.IPv6Address(supernet['start_address']).packed, super110net1_2_3_4.start_address)
        self.assertEqual(ipaddress.IPv6Address(supernet['end_address']).packed, super110net6_7.end_address)
        self.assertEqual(supernet['prefixlen'], 109)
        self.assertEqual(supernet['status'], IPv6Range.Status.WAIT.value)
        self.assertEqual(supernet['asn']['id'], super110net6_7.asn_id)
        self.assertIsNone(supernet['org_virt_obj'])
        super109net1_4_7 = IPv6Range.objects.get(id=supernet['id'])
        self.assertEqual(super109net1_4_7.start_address, super110net1_2_3_4.start_address)
        self.assertEqual(super109net1_4_7.end_address, super110net6_7.end_address)
        self.assertEqual(super109net1_4_7.prefixlen, 109)
        self.assertEqual(super109net1_4_7.status, IPv6Range.Status.WAIT.value)
        self.assertEqual(IPv6RangeRecord.objects.count(), 5)
        self.assertEqual(IPv6Range.objects.count(), 1)
