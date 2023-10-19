import ipaddress
from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone

from service.models import DataCenter
from ..managers import UserIpamRoleWrapper, IPv4RangeManager
from ..models import ASN, OrgVirtualObject, IPv4Range
from utils.test import get_or_create_user, MyAPITransactionTestCase


class IPv4RangeTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

    def test_list_ipv4_ranges(self):
        org1 = DataCenter(name='org1', name_en='org1 en')
        org1.save(force_insert=True)
        org2 = DataCenter(name='org2', name_en='org2 en')
        org2.save(force_insert=True)

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
