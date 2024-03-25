import ipaddress
from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone

from utils.test import get_or_create_user, MyAPITransactionTestCase, get_or_create_organization
from ..managers.common import NetBoxUserRoleWrapper
from ..managers.ipv4_mgrs import IPv4RangeManager
from ..models import OrgVirtualObject, IPv4Range, IPv4Address


class IPv4AddressTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

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

        base_url = reverse('netbox-api:ipam-ipv4address-remark', kwargs={'ipv4': 'tes6'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        # ipv4
        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        base_url = reverse('netbox-api:ipam-ipv4address-remark', kwargs={'ipv4': -1})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        base_url = reverse('netbox-api:ipam-ipv4address-remark', kwargs={'ipv4': 2**32})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # remark
        base_url = reverse('netbox-api:ipam-ipv4address-remark', kwargs={'ipv4': int(ipaddress.IPv4Address('10.8.8.6'))})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        query = parse.urlencode(query={'admin_remark': 'ss', 'as-admin': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 分配机构管理员
        base_url = reverse('netbox-api:ipam-ipv4address-remark', kwargs={'ipv4': int(ipaddress.IPv4Address('10.8.8.6'))})
        query = parse.urlencode(query={'remark': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        base_url = reverse('netbox-api:ipam-ipv4address-remark', kwargs={'ipv4': int(ipaddress.IPv4Address('127.0.0.1'))})
        query = parse.urlencode(query={'remark': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw = NetBoxUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.user_role.organizations.add(org1)
        base_url = reverse('netbox-api:ipam-ipv4address-remark', kwargs={'ipv4': int(ipaddress.IPv4Address('127.0.0.1'))})
        query = parse.urlencode(query={'remark': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'ip_address', 'remark'], response.data)
        self.assertNotIn('admin_remark', response.data)

        ip_addr: IPv4Address = IPv4Address.objects.first()
        self.assertEqual(ip_addr.ip_address, int(ipaddress.IPv4Address('127.0.0.1')))
        self.assertEqual(ip_addr.remark, 'test')
        self.assertEqual(ip_addr.admin_remark, '')

        query = parse.urlencode(query={'remark': 'test888'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        ip_addr.refresh_from_db()
        self.assertEqual(ip_addr.remark, 'test888')
        self.assertEqual(ip_addr.admin_remark, '')

        query = parse.urlencode(query={'admin_remark': 'testadmin'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        base_url = reverse('netbox-api:ipam-ipv4address-remark', kwargs={'ipv4': int(ipaddress.IPv4Address('159.0.1.1'))})
        query = parse.urlencode(query={'remark': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        base_url = reverse('netbox-api:ipam-ipv4address-remark', kwargs={'ipv4': int(ipaddress.IPv4Address('66.0.0.1'))})
        query = parse.urlencode(query={'remark': 'test'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # ---- test kjw admin -----
        uirw.user_role.organizations.remove(org1)

        base_url = reverse('netbox-api:ipam-ipv4address-remark', kwargs={'ipv4': int(ipaddress.IPv4Address('66.0.0.1'))})
        query = parse.urlencode(query={'remark': 'test', 'as-admin': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_readonly(True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_admin(True)

        query = parse.urlencode(query={'remark': 'test88', 'admin_remark': 'admin remark88', 'as-admin': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'ip_address', 'remark', 'admin_remark'], response.data)
        ip_addr = IPv4Address.objects.get(ip_address=int(ipaddress.IPv4Address('66.0.0.1')))
        self.assertEqual(ip_addr.remark, 'test88')
        self.assertEqual(ip_addr.admin_remark, 'admin remark88')

        query = parse.urlencode(query={'remark': '测试test', 'as-admin': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        ip_addr.refresh_from_db()
        self.assertEqual(ip_addr.remark, '测试test')
        self.assertEqual(ip_addr.admin_remark, 'admin remark88')

        query = parse.urlencode(query={'admin_remark': '测试66', 'as-admin': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        ip_addr.refresh_from_db()
        self.assertEqual(ip_addr.remark, '测试test')
        self.assertEqual(ip_addr.admin_remark, '测试66')

        base_url = reverse('netbox-api:ipam-ipv4address-remark', kwargs={'ipv4': int(ipaddress.IPv4Address('16.6.6.8'))})
        query = parse.urlencode(query={'remark': 'test88', 'admin_remark': 'admin remark88', 'as-admin': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'ip_address', 'remark', 'admin_remark'], response.data)
        ip_addr = IPv4Address.objects.get(ip_address=int(ipaddress.IPv4Address('16.6.6.8')))
        self.assertEqual(ip_addr.remark, 'test88')
        self.assertEqual(ip_addr.admin_remark, 'admin remark88')

    def test_list(self):
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
            org_virt_obj=virt_obj1, assigned_time=nt, admin_remark='adminremark6688', remark='remark2887'
        )

        nt = dj_timezone.now()
        ip_addr1 = IPv4Address(
            ip_address=int(ipaddress.IPv4Address('223.66.88.1')), creation_time=nt, update_time=nt,
            admin_remark='admin remark223', remark=''
        )
        ip_addr1.save(force_insert=True)
        nt = dj_timezone.now()
        ip_addr2 = IPv4Address(
            ip_address=int(ipaddress.IPv4Address('127.0.0.66')), creation_time=nt, update_time=nt,
            admin_remark='admin remark', remark=''
        )
        ip_addr2.save(force_insert=True)
        nt = dj_timezone.now()
        ip_addr3 = IPv4Address(
            ip_address=int(ipaddress.IPv4Address('127.0.0.88')), creation_time=nt, update_time=nt,
            admin_remark='', remark='remark88'
        )
        ip_addr3.save(force_insert=True)
        nt = dj_timezone.now()
        ip_addr4 = IPv4Address(
            ip_address=int(ipaddress.IPv4Address('159.0.2.88')), creation_time=nt, update_time=nt,
            admin_remark='', remark=''
        )
        ip_addr4.save(force_insert=True)

        base_url = reverse('netbox-api:ipam-ipv4address-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)

        # ipv4range_id
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        query = parse.urlencode(query={'ipv4range_id': 'notfound'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        query = parse.urlencode(query={'ipv4range_id': ip_range1.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # 分配机构管理员
        uirw = NetBoxUserRoleWrapper(self.user1)
        uirw.user_role = uirw.get_or_create_user_role()
        uirw.user_role.organizations.add(org1)

        query = parse.urlencode(query={'ipv4range_id': ip_range1.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertKeysIn(['id', 'ip_address', 'remark'], response.data['results'][0])
        self.assertNotIn('admin_remark', response.data['results'][0])
        self.assertEqual(response.data['results'][0]['ip_address'], int(ipaddress.IPv4Address('127.0.0.66')))
        self.assertEqual(response.data['results'][1]['ip_address'], int(ipaddress.IPv4Address('127.0.0.88')))
        # remark
        query = parse.urlencode(query={'ipv4range_id': ip_range1.id, 'remark': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['ip_address'], int(ipaddress.IPv4Address('127.0.0.88')))
        query = parse.urlencode(query={'ipv4range_id': ip_range1.id, 'remark': 'test'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        query = parse.urlencode(query={'ipv4range_id': ip_range1.id, 'remark': 'remar'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['ip_address'], int(ipaddress.IPv4Address('127.0.0.88')))

        query = parse.urlencode(query={'ipv4range_id': ip_range2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # ---- as-admin ---
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        uirw.set_ipam_readonly(True)
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 4)

        uirw.set_ipam_readonly(False)
        uirw.set_ipam_admin(True)
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 4)

        # remark
        query = parse.urlencode(query={'as-admin': '', 'remark': ''})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['results'][0]['ip_address'], ip_addr2.ip_address)
        self.assertEqual(response.data['results'][1]['ip_address'], ip_addr3.ip_address)
        self.assertEqual(response.data['results'][2]['ip_address'], ip_addr1.ip_address)

        query = parse.urlencode(query={'as-admin': '', 'remark': 'admin'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['ip_address'], ip_addr2.ip_address)
        self.assertEqual(response.data['results'][1]['ip_address'], ip_addr1.ip_address)

        query = parse.urlencode(query={'as-admin': '', 'remark': 'remark'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['results'][0]['ip_address'], ip_addr2.ip_address)
        self.assertEqual(response.data['results'][1]['ip_address'], ip_addr3.ip_address)
        self.assertEqual(response.data['results'][2]['ip_address'], ip_addr1.ip_address)

        # ipv4range_id
        query = parse.urlencode(query={'as-admin': '', 'ipv4range_id': ip_range1.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['ip_address'], ip_addr2.ip_address)
        self.assertEqual(response.data['results'][1]['ip_address'], ip_addr3.ip_address)

        query = parse.urlencode(query={'as-admin': '', 'ipv4range_id': ip_range2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ip_address'], ip_addr4.ip_address)

        # page_size
        query = parse.urlencode(query={'as-admin': '', 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['ip_address'], ip_addr2.ip_address)
