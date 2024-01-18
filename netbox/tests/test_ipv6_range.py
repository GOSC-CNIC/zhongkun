import ipaddress
from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone

from utils.test import get_or_create_user, MyAPITransactionTestCase, get_or_create_organization
from ..managers.common import NetBoxUserRoleWrapper
from ..managers.ipv6_mgrs import IPv6RangeManager
from ..models import ASN, OrgVirtualObject, IPv6Range, IPv6RangeRecord


class IPv6RangeTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

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

        base_url = reverse('netbox-api:ipam-ipv6range-list')
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

        u1_role_wrapper = NetBoxUserRoleWrapper(user=self.user1)
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

        u2_role_wrapper = NetBoxUserRoleWrapper(user=self.user2)
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
        base_url = reverse('netbox-api:ipam-ipv6range-list')
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

        # asn 0-65535
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 65536, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = NetBoxUserRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_role()
        u1_role_wrapper.set_ipam_readonly(True)
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '2400:dd01:1010:30::',
            'end_address': '2400:dd01:1010:30:ffff:ffff:ffff:ffff', 'prefixlen': 64,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        u1_role_wrapper = NetBoxUserRoleWrapper(user=self.user1)
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
            'asn': 88, 'admin_remark': 'remark test'
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
        self.assertEqual(iprange.asn.number, 88)
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

        base_url = reverse('netbox-api:ipam-ipv6range-detail', kwargs={'id': 'test'})
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

        base_url = reverse('netbox-api:ipam-ipv6range-detail', kwargs={'id': ip_range1.id})
        response = self.client.put(base_url, data={
            'name': 'test', 'prefixlen': 64,
            'start_address': '2400:dd01:1010:31::', 'end_address': '2400:dd01:1010:31:ffff:ffff:ffff:0',
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetBoxUserRoleWrapper(self.user1)
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
        base_url = reverse('netbox-api:ipam-ipv6range-detail', kwargs={'id': ip_range2.id})
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

        base_url = reverse('netbox-api:ipam-ipv6range-detail', kwargs={'id': 'test'})
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetBoxUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        base_url = reverse('netbox-api:ipam-ipv6range-detail', kwargs={'id': ip_range1.id})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok
        ip_range1.status = IPv6Range.Status.WAIT.value
        ip_range1.save(update_fields=['status'])
        self.assertEqual(IPv6Range.objects.count(), 2)
        self.assertEqual(IPv6RangeRecord.objects.count(), 0)
        base_url = reverse('netbox-api:ipam-ipv6range-detail', kwargs={'id': ip_range1.id})
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
        base_url = reverse('netbox-api:ipam-ipv6range-detail', kwargs={'id': ip_range2.id})
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

        base_url = reverse('netbox-api:ipam-ipv6range-recover', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetBoxUserRoleWrapper(self.user1)
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
        base_url = reverse('netbox-api:ipam-ipv6range-recover', kwargs={'id': ip_range1.id})
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
        base_url = reverse('netbox-api:ipam-ipv6range-recover', kwargs={'id': ip_range2.id})
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

        base_url = reverse('netbox-api:ipam-ipv6range-reserve', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'org_virt_obj_id': 'notfound'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetBoxUserRoleWrapper(self.user1)
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
        base_url = reverse('netbox-api:ipam-ipv6range-reserve', kwargs={'id': ip_range1.id})
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

        base_url = reverse('netbox-api:ipam-ipv6range-reserve', kwargs={'id': ip_range1.id})
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
        base_url = reverse('netbox-api:ipam-ipv6range-reserve', kwargs={'id': ip_range2.id})
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
