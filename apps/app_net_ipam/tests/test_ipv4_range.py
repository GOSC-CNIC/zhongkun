import datetime
import ipaddress
from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone
from django.test import TestCase

from utils.test import get_or_create_user, MyAPITransactionTestCase, get_or_create_organization
from apps.app_net_ipam.managers.common import NetIPamUserRoleWrapper
from apps.app_net_ipam.managers.ipv4_mgrs import IPv4RangeManager, IPv4RangeSplitter
from apps.app_net_ipam.models import ASN, OrgVirtualObject, IPv4Range, IPv4RangeRecord, IPRangeIntItem
from apps.app_net_ipam.permissions import IPamIPRestrictor


class IPv4RangeTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

        IPamIPRestrictor.add_ip_rule('127.0.0.1')
        IPamIPRestrictor.clear_cache()

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

        base_url = reverse('net_ipam-api:ipam-ipv4range-list')
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

        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_role()
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
        u1_role_wrapper.set_ipam_readonly(True)
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

        u2_role_wrapper = NetIPamUserRoleWrapper(user=self.user2)
        u2_role_wrapper.user_role = u2_role_wrapper.get_or_create_user_role()
        u2_role_wrapper.set_ipam_admin(True)

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
        base_url = reverse('net_ipam-api:ipam-ipv4range-list')
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

        # asn 0-4294967295
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.0.1', 'end_address': '10.0.1.255', 'mask_len': 24,
            'asn': 4294967295 + 1, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.1.1', 'end_address': '10.0.0.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_role()
        u1_role_wrapper.set_ipam_readonly(True)
        response = self.client.post(base_url, data={
            'name': 'test', 'start_address': '10.0.1.1', 'end_address': '10.0.0.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        u1_role_wrapper = NetIPamUserRoleWrapper(user=self.user1)
        u1_role_wrapper.set_ipam_readonly(False)
        u1_role_wrapper.set_ipam_admin(True)

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
            'asn': 4294967295, 'admin_remark': ''
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

        base_url = reverse('net_ipam-api:ipam-ipv4range-detail', kwargs={'id': 'test'})
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

        base_url = reverse('net_ipam-api:ipam-ipv4range-detail', kwargs={'id': ip_range1.id})
        response = self.client.put(base_url, data={
            'name': 'test', 'start_address': '127.0.1.1', 'end_address': '127.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.put(base_url, data={
            'name': 'test', 'start_address': '127.0.1.1', 'end_address': '127.0.1.255', 'mask_len': 24,
            'asn': 88, 'admin_remark': 'remark test'
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)
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
        self.assertEqual(record.start_address, int(ipaddress.IPv4Address('127.0.0.1')))
        self.assertEqual(record.end_address, int(ipaddress.IPv4Address('127.0.0.255')))
        self.assertEqual(record.mask_len, 24)
        self.assertEqual(record.ip_ranges[0]['start'], '127.0.1.1')
        self.assertEqual(record.ip_ranges[0]['end'], '127.0.1.255')
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
        base_url = reverse('net_ipam-api:ipam-ipv4range-detail', kwargs={'id': ip_range2.id})
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

        base_url = reverse('net_ipam-api:ipam-ipv4range-split', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        # new_prefix
        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={'new_prefix': 'ss'}, format='json')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={'new_prefix': 0})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={'new_prefix': 32})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.post(base_url, data={'new_prefix': 31})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.post(base_url, data={'new_prefix': 31})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        response = self.client.post(base_url, data={'new_prefix': 31})
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # new_prefix 必须大于 ip_range.mask_len
        base_url = reverse('net_ipam-api:ipam-ipv4range-split', kwargs={'id': ip_range1.id})
        response = self.client.post(base_url, data={'new_prefix': 20, 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # assigned
        response = self.client.post(base_url, data={'new_prefix': 26, 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        ip_range1.status = IPv4Range.Status.WAIT.value
        ip_range1.save(update_fields=['status'])

        # ok, fake, 10.0.0.1 - 200 -> 1-63, 64-127, 128-191, 191-200
        self.assertEqual(IPv4RangeRecord.objects.count(), 0)
        self.assertEqual(IPv4Range.objects.count(), 2)

        base_url = reverse('net_ipam-api:ipam-ipv4range-split', kwargs={'id': ip_range1.id})
        response = self.client.post(base_url, data={'new_prefix': 26, 'fake': True})
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
        base_url = reverse('net_ipam-api:ipam-ipv4range-split', kwargs={'id': ip_range1.id})
        response = self.client.post(base_url, data={'new_prefix': 26})
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
        base_url = reverse('net_ipam-api:ipam-ipv4range-split', kwargs={'id': ip_range2.id})
        response = self.client.post(base_url, data={'new_prefix': 27, 'fake': False})
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
            name='预留2', start_ip='159.0.2.101', end_ip='159.0.2.103', mask_len=28, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )
        self.assertEqual(IPv4RangeRecord.objects.count(), 2)
        self.assertEqual(IPv4Range.objects.count(), 8)

        base_url = reverse('net_ipam-api:ipam-ipv4range-split', kwargs={'id': ip_range3.id})
        response = self.client.post(base_url, data={'new_prefix': 31, 'fake': 'false'})
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 2)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv4RangeRecord.objects.count(), 3)
        self.assertEqual(IPv4Range.objects.count(), 9)
        ir1, ir2 = IPv4Range.objects.order_by('start_address')[7:9]
        self.assertEqual(ir1.start_address, int(ipaddress.IPv4Address('159.0.2.101')))
        self.assertEqual(ir1.end_address, int(ipaddress.IPv4Address('159.0.2.101')))
        self.assertEqual(ir1.mask_len, 31)
        self.assertEqual(ir2.start_address, int(ipaddress.IPv4Address('159.0.2.102')))
        self.assertEqual(ir2.end_address, int(ipaddress.IPv4Address('159.0.2.103')))
        self.assertEqual(ir2.mask_len, 31)

        # 掩码长度限制8
        nt = dj_timezone.now()
        ip_range4 = IPv4RangeManager.create_ipv4_range(
            name='预留4', start_ip='159.0.100.0', end_ip='159.0.200.255', mask_len=16, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark4', remark='remark4'
        )
        base_url = reverse('net_ipam-api:ipam-ipv4range-split', kwargs={'id': ip_range4.id})
        response = self.client.post(base_url, data={'new_prefix': 25, 'fake': 'false'})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

    def test_merge_ipv4_range(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ir1_sub1 = IPv4RangeManager.create_ipv4_range(
            name='预留1', start_ip='159.0.0.0', end_ip='159.0.0.255', mask_len=24, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.WAIT.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark1', remark='remark1'
        )
        nt = dj_timezone.now()
        ir1_sub2 = IPv4RangeManager.create_ipv4_range(
            name='预留2', start_ip='159.0.1.0', end_ip='159.0.1.255', mask_len=24, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )
        nt = dj_timezone.now()
        ir1_sub3 = IPv4RangeManager.create_ipv4_range(
            name='预留3', start_ip='159.0.2.0', end_ip='159.0.2.255', mask_len=24, asn=66,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.WAIT.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark3', remark='remark3'
        )
        nt = dj_timezone.now()
        ir1_sub4 = IPv4RangeManager.create_ipv4_range(
            name='预留4', start_ip='159.0.3.0', end_ip='159.0.3.255', mask_len=24, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark4', remark='remark4'
        )

        base_url = reverse('net_ipam-api:ipam-ipv4range-merge')
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={'new_prefix': 24, 'ip_range_ids': ['test1', 'test2'], 'fake': True})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # new_prefix
        response = self.client.post(base_url, data={'new_prefix': 0, 'ip_range_ids': ['test1', 'test2'], 'fake': True})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.client.post(base_url, data={'new_prefix': 32, 'ip_range_ids': ['test1', 'test2'], 'fake': True})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ip_range_ids
        response = self.client.post(base_url, data={'new_prefix': 24, 'ip_range_ids': '', 'fake': True})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.client.post(base_url, data={'new_prefix': 24, 'ip_range_ids': [], 'fake': True})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        response = self.client.post(base_url, data={'new_prefix': 24, 'ip_range_ids': ['test1' * 8], 'fake': True})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.post(base_url, data={'new_prefix': 24, 'ip_range_ids': ['test1'], 'fake': True})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.post(base_url, data={'new_prefix': 24, 'ip_range_ids': ['test1'], 'fake': True})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        response = self.client.post(base_url, data={'new_prefix': 24, 'ip_range_ids': ['test1'], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # new_prefix 必须小于等于 ip_range.mask_len
        response = self.client.post(base_url, data={'new_prefix': 25, 'ip_range_ids': [ir1_sub1.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok，merge 1 ip_range，prefix not change，no merge happened
        response = self.client.post(base_url, data={'new_prefix': 24, 'ip_range_ids': [ir1_sub1.id], 'fake': True})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(supernet['id'], ir1_sub1.id)
        self.assertEqual(supernet['start_address'], ir1_sub1.start_address)
        self.assertEqual(supernet['end_address'], ir1_sub1.end_address)
        self.assertEqual(supernet['mask_len'], ir1_sub1.mask_len)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(IPv4RangeRecord.objects.count(), 0)
        self.assertEqual(IPv4Range.objects.count(), 4)

        # ok，merge 1 ip_range，prefix changed
        response = self.client.post(base_url, data={'new_prefix': 23, 'ip_range_ids': [ir1_sub1.id], 'fake': True})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(supernet['id'], '')
        self.assertEqual(supernet['start_address'], ir1_sub1.start_address)
        self.assertEqual(supernet['end_address'], ir1_sub1.end_address)
        self.assertEqual(supernet['mask_len'], 23)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(supernet['asn']['id'], ir1_sub1.asn_id)
        self.assertIsNone(supernet['org_virt_obj'])
        self.assertEqual(IPv4RangeRecord.objects.count(), 0)
        self.assertEqual(IPv4Range.objects.count(), 4)

        # "已分配状态"
        response = self.client.post(base_url, data={'new_prefix': 23, 'ip_range_ids': [ir1_sub4.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        response = self.client.post(base_url, data={
            'new_prefix': 23, 'ip_range_ids': [ir1_sub3.id, ir1_sub4.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # 分配状态不一致
        response = self.client.post(base_url, data={
            'new_prefix': 23, 'ip_range_ids': [ir1_sub1.id, ir1_sub2.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # AS number 不一致
        response = self.client.post(base_url, data={
            'new_prefix': 23, 'ip_range_ids': [ir1_sub2.id, ir1_sub3.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('AS编码不一致', response.data['message'])
        ir1_sub3.asn = ir1_sub2.asn
        ir1_sub3.save(update_fields=['asn'])

        # 分配状态不一致
        response = self.client.post(base_url, data={
            'new_prefix': 23, 'ip_range_ids': [ir1_sub2.id, ir1_sub3.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('分配状态必须一致', response.data['message'])
        ir1_sub3.status = IPv4Range.Status.RESERVED.value
        ir1_sub3.save(update_fields=['status'])

        # 预留 状态时，关联机构二级对象不一致
        response = self.client.post(base_url, data={
            'new_prefix': 23, 'ip_range_ids': [ir1_sub2.id, ir1_sub3.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('关联的机构二级对象必须一致', response.data['message'])
        ir1_sub3.org_virt_obj = ir1_sub2.org_virt_obj
        ir1_sub3.save(update_fields=['org_virt_obj'])

        # 不属于同一个超网
        response = self.client.post(base_url, data={
            'new_prefix': 23, 'ip_range_ids': [ir1_sub2.id, ir1_sub3.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('不属于同一个超网', response.data['message'])

        # 地址段不连续
        ir1_sub1.status = ir1_sub3.status
        ir1_sub1.save(update_fields=['status'])
        response = self.client.post(base_url, data={
            'new_prefix': 22, 'ip_range_ids': [ir1_sub1.id, ir1_sub3.id], 'fake': True})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('地址必须是连续的', response.data['message'])

        # ok
        response = self.client.post(base_url, data={
            'new_prefix': 22, 'ip_range_ids': [ir1_sub2.id, ir1_sub3.id], 'fake': True})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(supernet['id'], '')
        self.assertEqual(supernet['start_address'], ir1_sub2.start_address)
        self.assertEqual(supernet['end_address'], ir1_sub3.end_address)
        self.assertEqual(supernet['mask_len'], 22)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(supernet['asn']['id'], ir1_sub1.asn_id)
        self.assertEqual(supernet['org_virt_obj']['id'], ir1_sub1.org_virt_obj_id)
        self.assertEqual(IPv4RangeRecord.objects.count(), 0)
        self.assertEqual(IPv4Range.objects.count(), 4)

        # sub1,sub2合并
        response = self.client.post(base_url, data={
            'new_prefix': 23, 'ip_range_ids': [ir1_sub2.id, ir1_sub1.id]})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertNotEqual(supernet['id'], '')
        self.assertEqual(supernet['start_address'], ir1_sub1.start_address)
        self.assertEqual(supernet['end_address'], ir1_sub2.end_address)
        self.assertEqual(supernet['mask_len'], 23)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(supernet['asn']['id'], ir1_sub1.asn_id)
        self.assertEqual(supernet['org_virt_obj']['id'], ir1_sub1.org_virt_obj_id)
        super23net1_2 = IPv4Range.objects.get(id=supernet['id'])
        self.assertEqual(super23net1_2.start_address, ir1_sub1.start_address)
        self.assertEqual(super23net1_2.end_address, ir1_sub2.end_address)
        self.assertEqual(super23net1_2.mask_len, 23)
        self.assertEqual(super23net1_2.status, ir1_sub1.status)
        self.assertEqual(IPv4RangeRecord.objects.count(), 1)
        self.assertEqual(IPv4Range.objects.count(), 3)
        # 合并记录
        record = IPv4RangeRecord.objects.first()
        self.assertEqual(record.start_address, super23net1_2.start_address)
        self.assertEqual(record.end_address, super23net1_2.end_address)
        self.assertEqual(record.mask_len, 23)
        self.assertEqual(len(record.ip_ranges), 2)
        self.assertEqual(record.ip_ranges[0]['start'], str(ir1_sub1.start_address_obj))
        self.assertEqual(record.ip_ranges[0]['end'], str(ir1_sub1.end_address_obj))
        self.assertEqual(record.ip_ranges[0]['mask'], 24)
        self.assertEqual(record.ip_ranges[1]['start'], str(ir1_sub2.start_address_obj))
        self.assertEqual(record.ip_ranges[1]['end'], str(ir1_sub2.end_address_obj))
        self.assertEqual(record.ip_ranges[1]['mask'], 24)

        # sub1,sub2合并的超网 super23net1_2 和 sub3 合并超网
        response = self.client.post(base_url, data={
            'new_prefix': 23, 'ip_range_ids': [ir1_sub3.id, super23net1_2.id]})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('不属于同一个超网', response.data['message'])

        response = self.client.post(base_url, data={
            'new_prefix': 22, 'ip_range_ids': [ir1_sub3.id, super23net1_2.id]})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(supernet['start_address'], ir1_sub1.start_address)
        self.assertEqual(supernet['end_address'], ir1_sub3.end_address)
        self.assertEqual(supernet['mask_len'], 22)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(supernet['asn']['id'], ir1_sub1.asn_id)
        self.assertEqual(supernet['org_virt_obj']['id'], ir1_sub1.org_virt_obj_id)
        super22net1_2_3 = IPv4Range.objects.get(id=supernet['id'])
        self.assertEqual(super22net1_2_3.start_address, ir1_sub1.start_address)
        self.assertEqual(super22net1_2_3.end_address, ir1_sub3.end_address)
        self.assertEqual(super22net1_2_3.mask_len, 22)
        self.assertEqual(super22net1_2_3.status, ir1_sub1.status)
        self.assertEqual(IPv4RangeRecord.objects.count(), 2)
        self.assertEqual(IPv4Range.objects.count(), 2)

        # 超网 super22net1_2_3 和 sub4 合并超网
        response = self.client.post(base_url, data={
            'new_prefix': 22, 'ip_range_ids': [ir1_sub4.id, super22net1_2_3.id], 'fake': False})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('状态必须为"未分配"和“预留”', response.data['message'])

        ir1_sub4.status = ir1_sub1.status
        ir1_sub4.save(update_fields=['status'])
        response = self.client.post(base_url, data={
            'new_prefix': 22, 'ip_range_ids': [ir1_sub4.id, super22net1_2_3.id], 'fake': False})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(supernet['start_address'], ir1_sub1.start_address)
        self.assertEqual(supernet['end_address'], ir1_sub4.end_address)
        self.assertEqual(supernet['mask_len'], 22)
        self.assertEqual(supernet['status'], ir1_sub1.status)
        self.assertEqual(supernet['org_virt_obj']['id'], ir1_sub1.org_virt_obj_id)
        super22net1_2_3 = IPv4Range.objects.get(id=supernet['id'])
        self.assertEqual(super22net1_2_3.start_address, ir1_sub1.start_address)
        self.assertEqual(super22net1_2_3.end_address, ir1_sub4.end_address)
        self.assertEqual(super22net1_2_3.mask_len, 22)
        self.assertEqual(super22net1_2_3.status, ir1_sub1.status)
        self.assertEqual(IPv4RangeRecord.objects.count(), 3)
        self.assertEqual(IPv4Range.objects.count(), 1)

        nt = dj_timezone.now()
        ir2_sub5 = IPv4RangeManager.create_ipv4_range(
            name='未分配1', start_ip='159.0.4.0', end_ip='159.0.4.255', mask_len=24, asn=886,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.WAIT.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark1', remark='remark1'
        )
        nt = dj_timezone.now()
        nt = dj_timezone.now()
        ir2_sub6 = IPv4RangeManager.create_ipv4_range(
            name='未分配1', start_ip='159.0.5.0', end_ip='159.0.5.255', mask_len=24, asn=886,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.WAIT.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark1', remark='remark1'
        )
        nt = dj_timezone.now()
        ir2_sub7 = IPv4RangeManager.create_ipv4_range(
            name='未分配2', start_ip='159.0.6.0', end_ip='159.0.6.200', mask_len=22, asn=886,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.WAIT.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )
        self.assertEqual(IPv4RangeRecord.objects.count(), 3)
        self.assertEqual(IPv4Range.objects.count(), 4)

        # sub5 和 sub6 合并超网
        response = self.client.post(base_url, data={
            'new_prefix': 22, 'ip_range_ids': [ir2_sub7.id, ir2_sub6.id], 'fake': 'False'})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(supernet['start_address'], ir2_sub6.start_address)
        self.assertEqual(supernet['end_address'], ir2_sub7.end_address)
        self.assertEqual(supernet['mask_len'], 22)
        self.assertEqual(supernet['status'], ir2_sub6.status)
        self.assertEqual(supernet['asn']['id'], ir2_sub6.asn_id)
        self.assertIsNone(supernet['org_virt_obj'])
        super22net6_7 = IPv4Range.objects.get(id=supernet['id'])
        self.assertEqual(super22net6_7.start_address, ir2_sub6.start_address)
        self.assertEqual(super22net6_7.end_address, ir2_sub7.end_address)
        self.assertEqual(super22net6_7.mask_len, 22)
        self.assertEqual(super22net6_7.status, ir2_sub6.status)
        self.assertEqual(IPv4RangeRecord.objects.count(), 4)
        self.assertEqual(IPv4Range.objects.count(), 3)

        # 合并2个超网
        response = self.client.post(base_url, data={
            'new_prefix': 20, 'ip_range_ids': [super22net6_7.id, super22net1_2_3.id]})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('AS编码不一致', response.data['message'])
        super22net1_2_3.asn = super22net6_7.asn
        super22net1_2_3.save(update_fields=['asn'])

        response = self.client.post(base_url, data={
            'new_prefix': 20, 'ip_range_ids': [super22net6_7.id, super22net1_2_3.id]})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('分配状态必须一致', response.data['message'])
        super22net1_2_3.status = IPv4Range.Status.WAIT.value
        super22net1_2_3.org_virt_obj = None
        super22net1_2_3.save(update_fields=['status', 'org_virt_obj'])

        response = self.client.post(base_url, data={
            'new_prefix': 20, 'ip_range_ids': [super22net6_7.id, super22net1_2_3.id]})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)
        self.assertIn('地址必须是连续的', response.data['message'])

        response = self.client.post(base_url, data={
            'new_prefix': 20, 'ip_range_ids': [super22net6_7.id, super22net1_2_3.id, ir2_sub5.id]})
        self.assertEqual(response.status_code, 200)
        supernet = response.data['ip_range']
        self.assertEqual(supernet['start_address'], super22net1_2_3.start_address)
        self.assertEqual(supernet['end_address'], super22net6_7.end_address)
        self.assertEqual(supernet['mask_len'], 20)
        self.assertEqual(supernet['status'], IPv4Range.Status.WAIT.value)
        self.assertEqual(supernet['asn']['id'], super22net6_7.asn_id)
        self.assertIsNone(supernet['org_virt_obj'])
        super20net1_4_7 = IPv4Range.objects.get(id=supernet['id'])
        self.assertEqual(super20net1_4_7.start_address, super22net1_2_3.start_address)
        self.assertEqual(super20net1_4_7.end_address, super22net6_7.end_address)
        self.assertEqual(super20net1_4_7.mask_len, 20)
        self.assertEqual(super20net1_4_7.status, IPv4Range.Status.WAIT.value)
        self.assertEqual(IPv4RangeRecord.objects.count(), 5)
        self.assertEqual(IPv4Range.objects.count(), 1)

    def test_delete_ipv4_range(self):
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

        base_url = reverse('net_ipam-api:ipam-ipv4range-detail', kwargs={'id': 'test'})
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

        base_url = reverse('net_ipam-api:ipam-ipv4range-detail', kwargs={'id': ip_range1.id})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok
        ip_range1.status = IPv4Range.Status.WAIT.value
        ip_range1.save(update_fields=['status'])
        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.count(), 0)
        base_url = reverse('net_ipam-api:ipam-ipv4range-detail', kwargs={'id': ip_range1.id})
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(IPv4Range.objects.count(), 1)
        self.assertEqual(IPv4RangeRecord.objects.count(), 1)
        record: IPv4RangeRecord = IPv4RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv4RangeRecord.RecordType.DELETE.value)
        self.assertEqual(record.start_address, ip_range1.start_address)
        self.assertEqual(record.end_address, ip_range1.end_address)
        self.assertEqual(record.mask_len, 24)
        self.assertEqual(record.ip_ranges, [])

        # ok
        base_url = reverse('net_ipam-api:ipam-ipv4range-detail', kwargs={'id': ip_range2.id})
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(IPv4Range.objects.count(), 0)
        self.assertEqual(IPv4RangeRecord.objects.count(), 2)

    def test_recover_ipv4_range(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv4RangeManager.create_ipv4_range(
            name='已分配1', start_ip='127.0.0.1', end_ip='127.0.0.255', mask_len=24, asn=66,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv4RangeManager.create_ipv4_range(
            name='预留2', start_ip='159.0.1.1', end_ip='159.0.2.255', mask_len=22, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-ipv4range-recover', kwargs={'id': 'test'})
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
        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.count(), 0)
        base_url = reverse('net_ipam-api:ipam-ipv4range-recover', kwargs={'id': ip_range1.id})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'
        ], response.data)

        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.start_address, int(ipaddress.IPv4Address('127.0.0.1')))
        self.assertEqual(ip_range1.end_address, int(ipaddress.IPv4Address('127.0.0.255')))
        self.assertEqual(ip_range1.mask_len, 24)
        self.assertIsNone(ip_range1.org_virt_obj)
        self.assertIsNone(ip_range1.assigned_time)
        self.assertEqual(ip_range1.remark, '')
        self.assertEqual(ip_range1.status, IPv4Range.Status.WAIT.value)

        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.count(), 1)

        record: IPv4RangeRecord = IPv4RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv4RangeRecord.RecordType.RECOVER.value)
        self.assertEqual(record.start_address, ip_range1.start_address)
        self.assertEqual(record.end_address, ip_range1.end_address)
        self.assertEqual(record.mask_len, 24)
        self.assertEqual(record.ip_ranges, [])
        self.assertEqual(record.org_virt_obj_id, virt_obj1.id)

        # ok
        base_url = reverse('net_ipam-api:ipam-ipv4range-recover', kwargs={'id': ip_range2.id})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'
        ], response.data)

        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.start_address, int(ipaddress.IPv4Address('159.0.1.1')))
        self.assertEqual(ip_range2.end_address, int(ipaddress.IPv4Address('159.0.2.255')))
        self.assertEqual(ip_range2.mask_len, 22)
        self.assertIsNone(ip_range2.org_virt_obj)
        self.assertIsNone(ip_range2.assigned_time)
        self.assertEqual(ip_range2.remark, '')
        self.assertEqual(ip_range2.status, IPv4Range.Status.WAIT.value)

        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.count(), 2)

    def test_reserve_ipv4_range(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv4RangeManager.create_ipv4_range(
            name='已分配1', start_ip='127.0.0.1', end_ip='127.0.0.255', mask_len=24, asn=66,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv4RangeManager.create_ipv4_range(
            name='预留2', start_ip='159.0.1.1', end_ip='159.0.2.255', mask_len=22, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=None, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-ipv4range-reserve', kwargs={'id': 'test'})
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
        base_url = reverse('net_ipam-api:ipam-ipv4range-reserve', kwargs={'id': ip_range1.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok
        ip_range1.org_virt_obj = None
        ip_range1.status = IPv4Range.Status.WAIT.value
        ip_range1.save(update_fields=['status', 'org_virt_obj'])
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.status, IPv4Range.Status.WAIT.value)
        self.assertIsNone(ip_range1.org_virt_obj)
        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.count(), 0)

        base_url = reverse('net_ipam-api:ipam-ipv4range-reserve', kwargs={'id': ip_range1.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'
        ], response.data)

        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.start_address, int(ipaddress.IPv4Address('127.0.0.1')))
        self.assertEqual(ip_range1.end_address, int(ipaddress.IPv4Address('127.0.0.255')))
        self.assertEqual(ip_range1.mask_len, 24)
        self.assertEqual(ip_range1.org_virt_obj_id, virt_obj1.id)
        self.assertIsNone(ip_range1.assigned_time)
        self.assertEqual(ip_range1.remark, '')
        self.assertEqual(ip_range1.status, IPv4Range.Status.RESERVED.value)

        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.count(), 1)

        record: IPv4RangeRecord = IPv4RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv4RangeRecord.RecordType.RESERVE.value)
        self.assertEqual(record.start_address, ip_range1.start_address)
        self.assertEqual(record.end_address, ip_range1.end_address)
        self.assertEqual(record.mask_len, 24)
        self.assertEqual(record.ip_ranges, [])
        self.assertEqual(record.org_virt_obj_id, virt_obj1.id)

        # ok
        base_url = reverse('net_ipam-api:ipam-ipv4range-reserve', kwargs={'id': ip_range2.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        ip_range2.status = IPv4Range.Status.WAIT.value
        ip_range2.org_virt_obj = None
        ip_range2.save(update_fields=['status', 'org_virt_obj'])
        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.status, IPv4Range.Status.WAIT.value)
        self.assertIsNone(ip_range2.org_virt_obj)
        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.count(), 1)

        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'
        ], response.data)

        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.start_address, int(ipaddress.IPv4Address('159.0.1.1')))
        self.assertEqual(ip_range2.end_address, int(ipaddress.IPv4Address('159.0.2.255')))
        self.assertEqual(ip_range2.mask_len, 22)
        self.assertEqual(ip_range2.org_virt_obj_id, virt_obj1.id)
        self.assertIsNone(ip_range2.assigned_time)
        self.assertEqual(ip_range2.remark, '')
        self.assertEqual(ip_range2.status, IPv4Range.Status.RESERVED.value)

        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.filter(
            record_type=IPv4RangeRecord.RecordType.RESERVE.value).count(), 2)

    def test_assign_ipv4_range(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)
        virt_obj2 = OrgVirtualObject(name='org virt obj2', organization=org1, creation_time=dj_timezone.now())
        virt_obj2.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv4RangeManager.create_ipv4_range(
            name='已分配1', start_ip='127.0.0.1', end_ip='127.0.0.255', mask_len=24, asn=66,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv4RangeManager.create_ipv4_range(
            name='预留2', start_ip='159.0.1.1', end_ip='159.0.2.255', mask_len=22, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-ipv4range-assign', kwargs={'id': 'test'})
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
        base_url = reverse('net_ipam-api:ipam-ipv4range-assign', kwargs={'id': ip_range2.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj2.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        # ok
        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.count(), 0)
        base_url = reverse('net_ipam-api:ipam-ipv4range-assign', kwargs={'id': ip_range2.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'
        ], response.data)

        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.start_address, int(ipaddress.IPv4Address('159.0.1.1')))
        self.assertEqual(ip_range2.end_address, int(ipaddress.IPv4Address('159.0.2.255')))
        self.assertEqual(ip_range2.mask_len, 22)
        self.assertEqual(ip_range2.org_virt_obj_id, virt_obj1.id)
        self.assertIsNotNone(ip_range2.assigned_time)
        self.assertEqual(ip_range2.remark, '')
        self.assertEqual(ip_range2.status, IPv4Range.Status.ASSIGNED.value)

        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.count(), 1)

        record: IPv4RangeRecord = IPv4RangeRecord.objects.first()
        self.assertEqual(record.record_type, IPv4RangeRecord.RecordType.ASSIGN.value)
        self.assertEqual(record.start_address, ip_range2.start_address)
        self.assertEqual(record.end_address, ip_range2.end_address)
        self.assertEqual(record.mask_len, 22)
        self.assertEqual(record.ip_ranges, [])
        self.assertEqual(record.org_virt_obj_id, virt_obj1.id)

        # ip_range1
        # status
        base_url = reverse('net_ipam-api:ipam-ipv4range-assign', kwargs={'id': ip_range1.id})
        query = parse.urlencode(query={'org_virt_obj_id': virt_obj2.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        ip_range1.status = IPv4Range.Status.WAIT.value
        ip_range1.org_virt_obj = None
        ip_range1.save(update_fields=['status', 'org_virt_obj'])
        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.status, IPv4Range.Status.WAIT.value)
        self.assertIsNone(ip_range1.org_virt_obj)
        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.count(), 1)

        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn([
            'id', 'name', 'status', 'creation_time', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'
        ], response.data)

        ip_range1.refresh_from_db()
        self.assertEqual(ip_range1.start_address, int(ipaddress.IPv4Address('127.0.0.1')))
        self.assertEqual(ip_range1.end_address, int(ipaddress.IPv4Address('127.0.0.255')))
        self.assertEqual(ip_range1.mask_len, 24)
        self.assertEqual(ip_range1.org_virt_obj_id, virt_obj2.id)
        self.assertIsInstance(ip_range1.assigned_time, datetime.datetime)
        self.assertEqual(ip_range1.remark, '')
        self.assertEqual(ip_range1.status, IPv4Range.Status.ASSIGNED.value)

        self.assertEqual(IPv4Range.objects.count(), 2)
        self.assertEqual(IPv4RangeRecord.objects.filter(
            record_type=IPv4RangeRecord.RecordType.ASSIGN.value).count(), 2)

    def test_remark(self):
        org1 = get_or_create_organization(name='org1')
        virt_obj1 = OrgVirtualObject(name='org virt obj1', organization=org1, creation_time=dj_timezone.now())
        virt_obj1.save(force_insert=True)

        nt = dj_timezone.now()
        ip_range1 = IPv4RangeManager.create_ipv4_range(
            name='已分配1', start_ip='127.0.0.1', end_ip='127.0.0.255', mask_len=24, asn=66,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.ASSIGNED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin1', remark='remark1'
        )
        nt = dj_timezone.now()
        ip_range2 = IPv4RangeManager.create_ipv4_range(
            name='预留2', start_ip='159.0.1.1', end_ip='159.0.2.255', mask_len=22, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )

        base_url = reverse('net_ipam-api:ipam-ipv4range-remark', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        query = parse.urlencode(query={'remark': 'notfound'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        query = parse.urlencode(query={'admin_remark': 'notfound66'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # not org admin
        base_url = reverse('net_ipam-api:ipam-ipv4range-remark', kwargs={'id': ip_range1.id})
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
        base_url = reverse('net_ipam-api:ipam-ipv4range-remark', kwargs={'id': ip_range2.id})
        query = parse.urlencode(query={'remark': 'notfound'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # ---- test as-admin ----
        uirw.user_role.organizations.remove(org1)

        base_url = reverse('net_ipam-api:ipam-ipv4range-remark', kwargs={'id': ip_range1.id})
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

        base_url = reverse('net_ipam-api:ipam-ipv4range-remark', kwargs={'id': ip_range2.id})
        query = parse.urlencode(query={'remark': 'test66', 'admin_remark': 'admin remark66', 'as-admin': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        ip_range2.refresh_from_db()
        self.assertEqual(ip_range2.remark, 'test66')
        self.assertEqual(ip_range2.admin_remark, 'admin remark66')

    def test_split_to_plan(self):
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

        base_url = reverse('net_ipam-api:ipam-ipv4range-plan-split', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        # sub_ranges
        self.client.force_login(self.user1)
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': -1, 'end_address': 6, 'prefix': 24},
                {'start_address': 7, 'end_address': 16, 'prefix': 23}
            ]
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 1, 'end_address': 6, 'prefix': 24},
                {'start_address': 7, 'end_address': 16, 'prefix': 33}
            ]
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'sub_ranges': []
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # 必须正序排序
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 7, 'end_address': 16, 'prefix': 23},
                {'start_address': 1, 'end_address': 6, 'prefix': 24}
            ]
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # AccessDenied
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 1, 'end_address': 6, 'prefix': 24},
                {'start_address': 7, 'end_address': 16, 'prefix': 23}
            ]
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetIPamUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.set_ipam_readonly(True)
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 1, 'end_address': 6, 'prefix': 24},
                {'start_address': 7, 'end_address': 16, 'prefix': 23}
            ]
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 1, 'end_address': 6, 'prefix': 24},
                {'start_address': 7, 'end_address': 16, 'prefix': 23}
            ]
        })
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        base_url = reverse('net_ipam-api:ipam-ipv4range-plan-split', kwargs={'id': ip_range1.id})
        # assigned
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': 1, 'end_address': 6, 'prefix': 24},
                {'start_address': 7, 'end_address': 16, 'prefix': 23}
            ]
        })
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        ip_range1.status = IPv4Range.Status.WAIT.value
        ip_range1.save(update_fields=['status'])

        # 10.0.0.1 - 200 -> 1-63, 64-127, 128-191, 192-200
        # 子网和超网ip范围不一致
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': int(ipaddress.IPv4Address('10.0.0.1')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.63')), 'prefix': 26},
                {'start_address': int(ipaddress.IPv4Address('10.0.0.64')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.127')), 'prefix': 26},
                {'start_address': int(ipaddress.IPv4Address('10.0.0.128')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.191')), 'prefix': 26}
            ]
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # 不连续
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': int(ipaddress.IPv4Address('10.0.0.1')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.63')), 'prefix': 26},
                {'start_address': int(ipaddress.IPv4Address('10.0.0.64')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.127')), 'prefix': 26},
                {'start_address': int(ipaddress.IPv4Address('10.0.0.128')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.191')), 'prefix': 26},
                {'start_address': int(ipaddress.IPv4Address('10.0.0.193')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.200')), 'prefix': 26}
            ]
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # 掩码长度
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': int(ipaddress.IPv4Address('10.0.0.1')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.63')), 'prefix': 26},
                {'start_address': int(ipaddress.IPv4Address('10.0.0.64')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.127')), 'prefix': 26},
                {'start_address': int(ipaddress.IPv4Address('10.0.0.128')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.191')), 'prefix': 23},
                {'start_address': int(ipaddress.IPv4Address('10.0.0.192')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.200')), 'prefix': 26}
            ]
        })
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ok, 10.0.0.1 - 200 -> 1-63, 64-127, 128-191, 191-200
        self.assertEqual(IPv4RangeRecord.objects.count(), 0)
        self.assertEqual(IPv4Range.objects.count(), 2)

        base_url = reverse('net_ipam-api:ipam-ipv4range-plan-split', kwargs={'id': ip_range1.id})
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': int(ipaddress.IPv4Address('10.0.0.1')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.63')), 'prefix': 26},
                {'start_address': int(ipaddress.IPv4Address('10.0.0.64')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.127')), 'prefix': 26},
                {'start_address': int(ipaddress.IPv4Address('10.0.0.128')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.191')), 'prefix': 26},
                {'start_address': int(ipaddress.IPv4Address('10.0.0.192')),
                 'end_address': int(ipaddress.IPv4Address('10.0.0.200')), 'prefix': 26}
            ]
        })
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
        base_url = reverse('net_ipam-api:ipam-ipv4range-plan-split', kwargs={'id': ip_range2.id})
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': int(ipaddress.IPv4Address('159.0.1.100')),
                 'end_address': int(ipaddress.IPv4Address('159.0.1.127')), 'prefix': 27},
                {'start_address': int(ipaddress.IPv4Address('159.0.1.128')),
                 'end_address': int(ipaddress.IPv4Address('159.0.1.180')), 'prefix': 26}
            ]
        })
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 2)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv4RangeRecord.objects.count(), 2)
        self.assertEqual(IPv4Range.objects.count(), 6)

        ir1, ir2 = IPv4Range.objects.order_by('start_address')[4:6]
        self.assertEqual(ir1.start_address, int(ipaddress.IPv4Address('159.0.1.100')))
        self.assertEqual(ir1.end_address, int(ipaddress.IPv4Address('159.0.1.127')))
        self.assertEqual(ir1.mask_len, 27)
        self.assertEqual(ir2.start_address, int(ipaddress.IPv4Address('159.0.1.128')))
        self.assertEqual(ir2.end_address, int(ipaddress.IPv4Address('159.0.1.180')))
        self.assertEqual(ir2.mask_len, 26)

        # mask_len 31 test
        nt = dj_timezone.now()
        ip_range3 = IPv4RangeManager.create_ipv4_range(
            name='预留2', start_ip='159.0.2.101', end_ip='159.0.2.103', mask_len=28, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark2', remark='remark2'
        )
        self.assertEqual(IPv4RangeRecord.objects.count(), 2)
        self.assertEqual(IPv4Range.objects.count(), 7)

        base_url = reverse('net_ipam-api:ipam-ipv4range-plan-split', kwargs={'id': ip_range3.id})
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': int(ipaddress.IPv4Address('159.0.2.101')),
                 'end_address': int(ipaddress.IPv4Address('159.0.2.101')), 'prefix': 32},
                {'start_address': int(ipaddress.IPv4Address('159.0.2.102')),
                 'end_address': int(ipaddress.IPv4Address('159.0.2.103')), 'prefix': 31}
            ]
        })
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 2)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv4RangeRecord.objects.count(), 3)
        self.assertEqual(IPv4Range.objects.count(), 8)
        ir1, ir2 = IPv4Range.objects.order_by('start_address')[6:8]
        self.assertEqual(ir1.start_address, int(ipaddress.IPv4Address('159.0.2.101')))
        self.assertEqual(ir1.end_address, int(ipaddress.IPv4Address('159.0.2.101')))
        self.assertEqual(ir1.mask_len, 32)
        self.assertEqual(ir2.start_address, int(ipaddress.IPv4Address('159.0.2.102')))
        self.assertEqual(ir2.end_address, int(ipaddress.IPv4Address('159.0.2.103')))
        self.assertEqual(ir2.mask_len, 31)

        nt = dj_timezone.now()
        ip_range4 = IPv4RangeManager.create_ipv4_range(
            name='预留4', start_ip='159.0.100.0', end_ip='159.0.200.255', mask_len=16, asn=88,
            create_time=nt, update_time=nt, status_code=IPv4Range.Status.RESERVED.value,
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='admin remark4', remark='remark4'
        )
        base_url = reverse('net_ipam-api:ipam-ipv4range-plan-split', kwargs={'id': ip_range4.id})
        self.assertEqual(IPv4RangeRecord.objects.count(), 3)
        self.assertEqual(IPv4Range.objects.count(), 9)
        response = self.client.post(base_url, data={
            'sub_ranges': [
                {'start_address': int(ipaddress.IPv4Address('159.0.100.0')),
                 'end_address': int(ipaddress.IPv4Address('159.0.127.255')), 'prefix': 19},
                {'start_address': int(ipaddress.IPv4Address('159.0.128.0')),
                 'end_address': int(ipaddress.IPv4Address('159.0.191.255')), 'prefix': 18},
                {'start_address': int(ipaddress.IPv4Address('159.0.192.0')),
                 'end_address': int(ipaddress.IPv4Address('159.0.199.255')), 'prefix': 21},
                {'start_address': int(ipaddress.IPv4Address('159.0.200.0')),
                 'end_address': int(ipaddress.IPv4Address('159.0.200.255')), 'prefix': 24}
            ]
        })
        self.assertEqual(response.status_code, 200)
        split_ranges = response.data['ip_ranges']
        self.assertEqual(len(split_ranges), 4)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'status', 'update_time', 'assigned_time', 'admin_remark',
            'remark', 'start_address', 'end_address', 'mask_len', 'asn', 'org_virt_obj'], split_ranges[0])
        self.assertEqual(IPv4RangeRecord.objects.count(), 4)
        self.assertEqual(IPv4Range.objects.count(), 12)
        ir1, ir2, ir3, ir4 = IPv4Range.objects.order_by('start_address')[8:12]
        self.assertEqual(ir1.start_address, int(ipaddress.IPv4Address('159.0.100.0')))
        self.assertEqual(ir1.end_address, int(ipaddress.IPv4Address('159.0.127.255')))
        self.assertEqual(ir1.mask_len, 19)
        self.assertEqual(ir2.start_address, int(ipaddress.IPv4Address('159.0.128.0')))
        self.assertEqual(ir2.end_address, int(ipaddress.IPv4Address('159.0.191.255')))
        self.assertEqual(ir2.mask_len, 18)
        self.assertEqual(ir3.start_address, int(ipaddress.IPv4Address('159.0.192.0')))
        self.assertEqual(ir3.end_address, int(ipaddress.IPv4Address('159.0.199.255')))
        self.assertEqual(ir3.mask_len, 21)
        self.assertEqual(ir4.start_address, int(ipaddress.IPv4Address('159.0.200.0')))
        self.assertEqual(ir4.end_address, int(ipaddress.IPv4Address('159.0.200.255')))
        self.assertEqual(ir4.mask_len, 24)


class IPv4RangeMgrTests(TestCase):
    @staticmethod
    def _split_test(ip_range: IPRangeIntItem, new_prefix: int, prefixlen_diff: int):
        subnets = IPv4RangeSplitter.mini_split_plan(
            ip_range=ip_range, new_prefix=new_prefix, prefixlen_diff=prefixlen_diff)

        sub_ranges = []
        for sn in subnets:
            sub_ranges.append(
                {
                    'start_address': sn.start,
                    'end_address': sn.end,
                    'prefix': sn.mask,
                }
            )

        ipv4_range = IPv4Range(start_address=ip_range.start, end_address=ip_range.end, mask_len=ip_range.mask)
        IPv4RangeSplitter.validate_sub_ranges_plan(ipv4_range=ipv4_range, sub_ranges=sub_ranges)

    def _test_prefix_diff(self, prefixlen_diff: int):
        # 测试完整子网
        self._split_test(ip_range=IPRangeIntItem(
            start=int(ipaddress.IPv4Address('10.0.0.1')),
            end=int(ipaddress.IPv4Address('10.0.255.255')),
            mask=16
        ), new_prefix=24, prefixlen_diff=prefixlen_diff)

        # 测试 大跨度 前缀长度，完整子网
        self._split_test(ip_range=IPRangeIntItem(
            start=int(ipaddress.IPv4Address('10.0.0.1')),
            end=int(ipaddress.IPv4Address('10.255.255.255')),
            mask=8
        ), new_prefix=24, prefixlen_diff=prefixlen_diff)

        # 测试 大跨度前缀长度，前半部分只有一点ip子网
        self._split_test(ip_range=IPRangeIntItem(
            start=int(ipaddress.IPv4Address('10.127.255.250')),
            end=int(ipaddress.IPv4Address('10.255.255.255')),
            mask=8
        ), new_prefix=30, prefixlen_diff=prefixlen_diff)

        # 测试前半部分只有一点ip，后半部分完整
        self._split_test(ip_range=IPRangeIntItem(
            start=int(ipaddress.IPv4Address('10.0.126.1')),
            end=int(ipaddress.IPv4Address('10.0.255.255')),
            mask=16
        ), new_prefix=24, prefixlen_diff=prefixlen_diff)

        # 测试只有中间小部分ip
        self._split_test(ip_range=IPRangeIntItem(
            start=int(ipaddress.IPv4Address('10.0.127.1')),
            end=int(ipaddress.IPv4Address('10.0.128.255')),
            mask=16
        ), new_prefix=24, prefixlen_diff=prefixlen_diff)

    def test_mini_split_plan(self):
        self._test_prefix_diff(prefixlen_diff=1)
        self._test_prefix_diff(prefixlen_diff=3)
        self._test_prefix_diff(prefixlen_diff=8)
        self._test_prefix_diff(prefixlen_diff=9)
