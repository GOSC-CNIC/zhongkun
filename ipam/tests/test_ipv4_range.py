import ipaddress
from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone

from utils.test import get_or_create_user, MyAPITransactionTestCase, get_or_create_organization
from ..managers import UserIpamRoleWrapper, IPv4RangeManager
from ..models import ASN, OrgVirtualObject, IPv4Range, IPv4RangeRecord


class IPv4RangeTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

    def test_list_ipv4_ranges(self):
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
        ip_range1 = IPv4RangeManager.create_ipv4_range(
            name='已分配1', start_ip='127.0.0.1', end_ip='127.0.0.255', mask_len=24, asn=asn66,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv4RangeManager.create_ipv4_range(
            name='预留2', start_ip='159.0.1.1', end_ip='159.0.2.255', mask_len=22, asn=asn88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj2, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )
        ip_range3 = IPv4RangeManager.create_ipv4_range(
            name='预留3', start_ip='10.0.1.1', end_ip='10.0.1.255', mask_len=24, asn=asn88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark3', remark='remark3'
        )
        ip_range4 = IPv4RangeManager.create_ipv4_range(
            name='待分配4', start_ip='10.0.2.1', end_ip='10.0.2.255', mask_len=24, asn=asn88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.WAIT.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark4', remark='remark4'
        )

        base_url = reverse('api:ipam-ipv4range-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 0)

        u1_role_wrapper = UserIpamRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_ipam_role()
        u1_role_wrapper.user_role.organizations.add(org1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 1)
        iprange = response.data['results'][0]
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'
        ], iprange)
        self.assertKeysIn(['id', 'number'], iprange['asn'])
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization'], iprange['org_virt_obj'])
        self.assertKeysIn(['id', 'name', 'name_en'], iprange['org_virt_obj']['organization'])
        self.assertEqual(iprange['id'], ip_range1.id)
        self.assertEqual(iprange['start_address'], int(ipaddress.IPv4Address('127.0.0.1')))
        self.assertEqual(iprange['end_address'], int(ipaddress.IPv4Address('127.0.0.255')))
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
        query = parse.urlencode(query={'ip': '127.0.0.256'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'ip': '127.0.0.88'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

        query = parse.urlencode(query={'ip': '127.0.1.0'})
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
        query = parse.urlencode(query={'status': IPv4Range.Status.ASSIGNED.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ---- admin ----
        # user1 as-admin
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 只读管理权限
        u1_role_wrapper.user_role.is_readonly = True
        u1_role_wrapper.user_role.save(update_fields=['is_readonly'])
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 4)

        # order by 'start_address'
        self.assertEqual(response.data['results'][0]['id'], ip_range3.id)
        self.assertEqual(response.data['results'][1]['id'], ip_range4.id)
        self.assertEqual(response.data['results'][2]['id'], ip_range1.id)
        self.assertEqual(response.data['results'][3]['id'], ip_range2.id)

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
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u2_role_wrapper = UserIpamRoleWrapper(user=self.user2)
        u2_role_wrapper.user_role = u2_role_wrapper.get_or_create_user_ipam_role()
        u2_role_wrapper.user_role.is_admin = True
        u2_role_wrapper.user_role.save(update_fields=['is_admin'])

        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
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

        query = parse.urlencode(query={'as-admin': '', 'status': IPv4Range.Status.RESERVED.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_create_ipv4_range(self):
        base_url = reverse('api:ipam-ipv4range-list')
        response = self.client.post(base_url, data={
            'name': '', 'start_address': '', 'end_address': '', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.0', 'end_address': '10.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # start_address
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.256', 'end_address': '10.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # end_address
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.1', 'end_address': '10.0.1.256', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # mask_len 0-32
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.1', 'end_address': '10.0.1.255', 'mask_len': 33,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # asn 0-65535
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.1', 'end_address': '10.0.1.255', 'mask_len': 24,
            'asn': 65536, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.1.1', 'end_address': '10.0.0.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = UserIpamRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_ipam_role()
        u1_role_wrapper.user_role.is_readonly = True
        u1_role_wrapper.user_role.save(update_fields=['is_readonly'])
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.1.1', 'end_address': '10.0.0.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        u1_role_wrapper = UserIpamRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role.is_readonly = False
        u1_role_wrapper.user_role.is_admin = True
        u1_role_wrapper.user_role.save(update_fields=['is_readonly', 'is_admin'])

        # start_address > end_address
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.1.1', 'end_address': '10.0.0.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # start_address, end_address, mask_len, not in same network
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.1', 'end_address': '10.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.1', 'end_address': '10.0.0.255', 'mask_len': 25,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        self.assertEqual(IPv4RangeRecord.objects.count(), 0)
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.1', 'end_address': '10.0.0.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
                           'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'], response.data)
        iprange = IPv4Range.objects.get(id=response.data['id'])
        self.assertEqual(iprange.start_address, int(ipaddress.IPv4Address('10.0.0.1')))
        self.assertEqual(iprange.end_address, int(ipaddress.IPv4Address('10.0.0.255')))
        self.assertEqual(iprange.mask_len, 24)
        self.assertEqual(iprange.status, IPv4Range.Status.WAIT.value)
        self.assertEqual(iprange.asn.number, 88)
        self.assertEqual(iprange.name, 'test')

        self.assertEqual(IPv4RangeRecord.objects.count(), 1)
        record: IPv4RangeRecord = IPv4RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv4RangeRecord.RecordType.ADD.value)
        self.assertEqual(record.start_address, int(ipaddress.IPv4Address('10.0.0.1')))
        self.assertEqual(record.end_address, int(ipaddress.IPv4Address('10.0.0.255')))
        self.assertEqual(record.mask_len, 24)

        # 存在重叠
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.1', 'end_address': '10.0.0.200', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.100', 'end_address': '10.0.1.1', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.255', 'end_address': '10.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.post(base_url, data={
            'name': '', 'start_address': '10.0.1.1', 'end_address': '10.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IPv4RangeRecord.objects.count(), 2)

    def test_update_ipv4_range(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv4RangeManager.create_ipv4_range(
            name='已分配1', start_ip='127.0.0.1', end_ip='127.0.0.255', mask_len=24, asn=66,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.ASSIGNED.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv4RangeManager.create_ipv4_range(
            name='预留2', start_ip='159.0.1.1', end_ip='159.0.2.255', mask_len=22, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('api:ipam-ipv4range-detail', kwargs={'id': 'test'})
        response = self.client.put(base_url, data={
            'name': 'test', 'start_address': '127.0.1.1', 'end_address': '127.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.put(base_url, data={
            'name': 'test', 'start_address': '127.0.1.1', 'end_address': '127.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        base_url = reverse('api:ipam-ipv4range-detail', kwargs={'id': ip_range1.id})
        response = self.client.put(base_url, data={
            'name': 'test', 'start_address': '127.0.1.1', 'end_address': '127.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = UserIpamRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_ipam_role()
        uirw.user_role.is_readonly = True
        uirw.user_role.save(update_fields=['is_readonly'])
        response = self.client.put(base_url, data={
            'name': 'test', 'start_address': '127.0.1.1', 'end_address': '127.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.user_role.is_admin = True
        uirw.user_role.save(update_fields=['is_admin'])
        response = self.client.put(base_url, data={
            'name': 'test', 'start_address': '127.0.1.1', 'end_address': '127.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok
        ip_range1.status = IPv4Range.Status.WAIT.value
        ip_range1.save(update_fields=['status'])
        response = self.client.put(base_url, data={
            'name': 'test', 'start_address': '127.0.1.1', 'end_address': '127.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
                           'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'], response.data)
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.start_address, int(ipaddress.IPv4Address('127.0.1.1')))
        self.assertEqual(ip_range1.end_address, int(ipaddress.IPv4Address('127.0.1.255')))
        self.assertEqual(ip_range1.start_address, response.data['start_address'])
        self.assertEqual(ip_range1.end_address, response.data['end_address'])

        self.assertEqual(IPv4RangeRecord.objects.count(), 1)
        record: IPv4RangeRecord = IPv4RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv4RangeRecord.RecordType.CHANGE.value)
        self.assertEqual(record.start_address, int(ipaddress.IPv4Address('127.0.1.1')))
        self.assertEqual(record.end_address, int(ipaddress.IPv4Address('127.0.1.255')))
        self.assertEqual(record.mask_len, 24)
        self.assertEqual(record.ip_ranges[0]['start'], '127.0.0.1')
        self.assertEqual(record.ip_ranges[0]['end'], '127.0.0.255')
        self.assertEqual(record.ip_ranges[0]['mask'], 24)

        response = self.client.put(base_url, data={
            'name': 'test', 'start_address': '127.0.1.1', 'end_address': '127.0.2.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok
        response = self.client.put(base_url, data={
            'name': 'test88', 'start_address': '127.0.0.1', 'end_address': '127.0.1.255', 'mask_len': 23,
            'asn': 88, 'admin_remark': 'remark test 66'
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(IPv4RangeRecord.objects.count(), 2)

        # ip mask不变不产生记录
        response = self.client.put(base_url, data={
            'name': '66test88', 'start_address': '127.0.0.1', 'end_address': '127.0.1.255', 'mask_len': 23,
            'asn': 99, 'admin_remark': '88remark test 66'
        })
        self.assertEqual(response.status_code, 200)
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.name, '66test88')
        self.assertEqual(ip_range1.admin_remark, '88remark test 66')
        self.assertEqual(ip_range1.asn.number, 99)
        self.assertEqual(IPv4RangeRecord.objects.count(), 2)

        # ok
        base_url = reverse('api:ipam-ipv4range-detail', kwargs={'id': ip_range2.id})
        response = self.client.put(base_url, data={
            'name': 'test', 'start_address': '159.0.1.1', 'end_address': '159.0.1.255', 'mask_len': 23,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
                           'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'], response.data)
        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.start_address, int(ipaddress.IPv4Address('159.0.1.1')))
        self.assertEqual(ip_range2.end_address, int(ipaddress.IPv4Address('159.0.1.255')))
        self.assertEqual(ip_range2.start_address, response.data['start_address'])
        self.assertEqual(ip_range2.end_address, response.data['end_address'])
        self.assertEqual(ip_range2.org_virt_obj_id, virt_obj1.id)

        self.assertEqual(IPv4RangeRecord.objects.count(), 3)

    def test_split_ipv4_range(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv4RangeManager.create_ipv4_range(
            name='已分配1', start_ip='10.0.0.1', end_ip='10.0.0.200', mask_len=24, asn=66,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.ASSIGNED.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv4RangeManager.create_ipv4_range(
            name='预留2', start_ip='159.0.1.100', end_ip='159.0.1.180', mask_len=24, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('api:ipam-ipv4range-split', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        # new_prefix
        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'new_prefix': 'ss'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'new_prefix': 0})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'new_prefix': 32})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        query = parse.urlencode(query={'new_prefix': 31})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = UserIpamRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_ipam_role()
        uirw.user_role.is_readonly = True
        uirw.user_role.save(update_fields=['is_readonly'])
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.user_role.is_admin = True
        uirw.user_role.save(update_fields=['is_admin'])

        query = parse.urlencode(query={'new_prefix': 31})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # new_prefix 必须大于 ip_range.mask_len
        base_url = reverse('api:ipam-ipv4range-split', kwargs={'id': ip_range1.id})
        query = parse.urlencode(query={'new_prefix': 20, 'fake': True})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # assigned
        query = parse.urlencode(query={'new_prefix': 26, 'fake': True})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        ip_range1.status = IPv4Range.Status.WAIT.value
        ip_range1.save(update_fields=['status'])

        # ok, fake, 10.0.0.1 - 200 -> 1-63, 64-127, 128-191, 191-200
        self.assertEqual(IPv4RangeRecord.objects.count(), 0)
        self.assertEqual(IPv4Range.objects.count(), 2)

        base_url = reverse('api:ipam-ipv4range-split', kwargs={'id': ip_range1.id})
        query = parse.urlencode(query={'new_prefix': 26, 'fake': True})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 4)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv4RangeRecord.objects.all().count(), 0)
        self.assertEqual(IPv4Range.objects.count(), 2)

        ir1 = split_ranges[0]
        self.assertEqual(ir1['start_address'], int(ipaddress.IPv4Address('10.0.0.1')))
        self.assertEqual(ir1['end_address'], int(ipaddress.IPv4Address('10.0.0.63')))
        self.assertEqual(ir1['mask_len'], 26)
        ir2 = split_ranges[1]
        self.assertEqual(ir2['start_address'], int(ipaddress.IPv4Address('10.0.0.64')))
        self.assertEqual(ir2['end_address'], int(ipaddress.IPv4Address('10.0.0.127')))
        self.assertEqual(ir2['mask_len'], 26)
        ir3 = split_ranges[2]
        self.assertEqual(ir3['start_address'], int(ipaddress.IPv4Address('10.0.0.128')))
        self.assertEqual(ir3['end_address'], int(ipaddress.IPv4Address('10.0.0.191')))
        self.assertEqual(ir3['mask_len'], 26)
        ir4 = split_ranges[3]
        self.assertEqual(ir4['start_address'], int(ipaddress.IPv4Address('10.0.0.192')))
        self.assertEqual(ir4['end_address'], int(ipaddress.IPv4Address('10.0.0.200')))
        self.assertEqual(ir4['mask_len'], 26)

        # ok, 10.0.0.1 - 200 -> 1-63, 64-127, 128-191, 191-200
        base_url = reverse('api:ipam-ipv4range-split', kwargs={'id': ip_range1.id})
        query = parse.urlencode(query={'new_prefix': 26})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 4)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv4RangeRecord.objects.count(), 1)
        self.assertEqual(IPv4Range.objects.count(), 5)

        ir1, ir2, ir3, ir4 = IPv4Range.objects.order_by('start_address')[0:4]
        self.assertEqual(ir1.start_address, int(ipaddress.IPv4Address('10.0.0.1')))
        self.assertEqual(ir1.end_address, int(ipaddress.IPv4Address('10.0.0.63')))
        self.assertEqual(ir1.mask_len, 26)
        self.assertEqual(ir2.start_address, int(ipaddress.IPv4Address('10.0.0.64')))
        self.assertEqual(ir2.end_address, int(ipaddress.IPv4Address('10.0.0.127')))
        self.assertEqual(ir2.mask_len, 26)
        self.assertEqual(ir3.start_address, int(ipaddress.IPv4Address('10.0.0.128')))
        self.assertEqual(ir3.end_address, int(ipaddress.IPv4Address('10.0.0.191')))
        self.assertEqual(ir3.mask_len, 26)
        self.assertEqual(ir4.start_address, int(ipaddress.IPv4Address('10.0.0.192')))
        self.assertEqual(ir4.end_address, int(ipaddress.IPv4Address('10.0.0.200')))
        self.assertEqual(ir4.mask_len, 26)
        # 拆分记录
        record = IPv4RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv4RangeRecord.RecordType.SPLIT.value)
        self.assertEqual(record.start_address, int(ipaddress.IPv4Address('10.0.0.1')))
        self.assertEqual(record.end_address, int(ipaddress.IPv4Address('10.0.0.200')))
        self.assertEqual(record.mask_len, 24)
        ir1, ir2, ir3, ir4 = record.ip_ranges
        self.assertEqual(ir1['start'], '10.0.0.1')
        self.assertEqual(ir1['end'], '10.0.0.63')
        self.assertEqual(ir1['mask'], 26)
        self.assertEqual(ir2['start'], '10.0.0.64')
        self.assertEqual(ir2['end'], '10.0.0.127')
        self.assertEqual(ir2['mask'], 26)
        self.assertEqual(ir3['start'], '10.0.0.128')
        self.assertEqual(ir3['end'], '10.0.0.191')
        self.assertEqual(ir3['mask'], 26)
        self.assertEqual(ir4['start'], '10.0.0.192')
        self.assertEqual(ir4['end'], '10.0.0.200')
        self.assertEqual(ir4['mask'], 26)

        # ok, 159.0.1.100 - 180 -> 100-127, 128-159, 160-180
        self.assertEqual(IPv4RangeRecord.objects.count(), 1)
        self.assertEqual(IPv4Range.objects.count(), 5)
        base_url = reverse('api:ipam-ipv4range-split', kwargs={'id': ip_range2.id})
        query = parse.urlencode(query={'new_prefix': 27})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 3)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv4RangeRecord.objects.count(), 2)
        self.assertEqual(IPv4Range.objects.count(), 7)

        ir1, ir2, ir3 = IPv4Range.objects.order_by('start_address')[4:7]
        self.assertEqual(ir1.start_address, int(ipaddress.IPv4Address('159.0.1.100')))
        self.assertEqual(ir1.end_address, int(ipaddress.IPv4Address('159.0.1.127')))
        self.assertEqual(ir1.mask_len, 27)
        self.assertEqual(ir2.start_address, int(ipaddress.IPv4Address('159.0.1.128')))
        self.assertEqual(ir2.end_address, int(ipaddress.IPv4Address('159.0.1.159')))
        self.assertEqual(ir2.mask_len, 27)
        self.assertEqual(ir3.start_address, int(ipaddress.IPv4Address('159.0.1.160')))
        self.assertEqual(ir3.end_address, int(ipaddress.IPv4Address('159.0.1.180')))
        self.assertEqual(ir3.mask_len, 27)

        # mask_len 31 test
        nt = dj_timezone.now()
        ip_range3 = IPv4RangeManager.create_ipv4_range(
            name='预留2', start_ip='159.0.2.100', end_ip='159.0.2.103', mask_len=28, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )
        self.assertEqual(IPv4RangeRecord.objects.count(), 2)
        self.assertEqual(IPv4Range.objects.count(), 8)

        base_url = reverse('api:ipam-ipv4range-split', kwargs={'id': ip_range3.id})
        query = parse.urlencode(query={'new_prefix': 31})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 2)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv4RangeRecord.objects.count(), 3)
        self.assertEqual(IPv4Range.objects.count(), 9)
        ir1, ir2 = IPv4Range.objects.order_by('start_address')[7:9]
        self.assertEqual(ir1.start_address, int(ipaddress.IPv4Address('159.0.2.100')))
        self.assertEqual(ir1.end_address, int(ipaddress.IPv4Address('159.0.2.101')))
        self.assertEqual(ir1.mask_len, 31)
        self.assertEqual(ir2.start_address, int(ipaddress.IPv4Address('159.0.2.102')))
        self.assertEqual(ir2.end_address, int(ipaddress.IPv4Address('159.0.2.103')))
        self.assertEqual(ir2.mask_len, 31)


class IPAMUserRoleTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

    def test_list_user_role(self):
        org1 = get_or_create_organization(name='org1')
        org2 = get_or_create_organization(name='org2')

        base_url = reverse('api:ipam-userrole-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'user', 'is_admin', 'is_readonly', 'creation_time', 'update_time', 'organizations'], response.data)
        self.assertKeysIn(['id', 'username'], response.data['user'])
        self.assertEqual(response.data['user']['id'], self.user1.id)
        self.assertEqual(len(response.data['organizations']), 0)

        # 不会自动创建ipam用户角色
        u1_role_wrapper = UserIpamRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role.organizations.add(org1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], '')
        self.assertKeysIn(
            ['id', 'user', 'is_admin', 'is_readonly', 'creation_time', 'update_time', 'organizations'], response.data)
        self.assertKeysIn(['id', 'username'], response.data['user'])
        self.assertEqual(response.data['user']['id'], self.user1.id)
        self.assertEqual(len(response.data['organizations']), 0)

        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_ipam_role()
        u1_role_wrapper.user_role.organizations.add(org1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(
            ['id', 'user', 'is_admin', 'is_readonly', 'creation_time', 'update_time', 'organizations'], response.data)
        self.assertKeysIn(['id', 'username'], response.data['user'])
        self.assertEqual(response.data['user']['id'], self.user1.id)
        self.assertEqual(len(response.data['organizations']), 1)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['organizations'][0])
        self.assertEqual(response.data['organizations'][0]['id'], org1.id)

        u2_role_wrapper = UserIpamRoleWrapper(user=self.user2)
        u2_role_wrapper.user_role = u2_role_wrapper.get_or_create_user_ipam_role()
        u2_role_wrapper.user_role.organizations.add(org1)
        u2_role_wrapper.user_role.organizations.add(org2)

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['organizations']), 1)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['organizations'][0])
        self.assertEqual(response.data['organizations'][0]['id'], org1.id)
