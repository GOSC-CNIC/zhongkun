from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone

from utils.test import get_or_create_user, MyAPITransactionTestCase, get_or_create_organization
from apps.app_net_ipam.managers.common import NetIPamUserRoleWrapper
from apps.app_net_ipam.managers.ipv4_mgrs import IPv4RangeManager, IPv4RangeRecordManager
from apps.app_net_ipam.models import ASN, OrgVirtualObject, IPv4Range, IPv4RangeRecord, IPRangeItem


class IPv4RangeRecordTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

    def test_list(self):
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
            name='已分配1', start_ip='127.0.0.0', end_ip='127.0.0.255', mask_len=24, asn=asn66,
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

        record1 = IPv4RangeRecordManager.create_record(
            user=self.user1, record_type=IPv4RangeRecord.RecordType.ADD.value,
            start_address=ip_range1.start_address, end_address=ip_range1.end_address, mask_len=ip_range1.mask_len,
            remark='', ip_ranges=[], org_virt_obj=None
        )

        record2 = IPv4RangeRecordManager.create_record(
            user=self.user1, record_type=IPv4RangeRecord.RecordType.SPLIT.value,
            start_address=ip_range1.start_address, end_address=ip_range1.end_address, mask_len=ip_range1.mask_len,
            remark='', ip_ranges=[
                IPRangeItem(start='127.0.0.0', end='127.0.0.127', mask=25),
                IPRangeItem(start='127.0.0.128', end='127.0.0.255', mask=25),
            ], org_virt_obj=virt_obj1
        )
        record3 = IPv4RangeRecordManager.create_record(
            user=self.user2, record_type=IPv4RangeRecord.RecordType.MERGE.value,
            start_address=ip_range2.start_address, end_address=ip_range2.end_address, mask_len=ip_range2.mask_len,
            remark='', ip_ranges=[
                IPRangeItem(start='159.0.1.1', end='159.0.1.255', mask=24),
                IPRangeItem(start='159.0.2.0', end='159.0.2.255', mask=24),
            ], org_virt_obj=virt_obj2
        )
        record4 = IPv4RangeRecordManager.create_record(
            user=self.user2, record_type=IPv4RangeRecord.RecordType.RESERVE.value,
            start_address=ip_range2.start_address, end_address=ip_range2.end_address, mask_len=ip_range2.mask_len,
            remark='', ip_ranges=[], org_virt_obj=virt_obj2
        )
        record5 = IPv4RangeRecordManager.create_record(
            user=self.user2, record_type=IPv4RangeRecord.RecordType.RESERVE.value,
            start_address=ip_range3.start_address, end_address=ip_range3.end_address, mask_len=ip_range3.mask_len,
            remark='', ip_ranges=[], org_virt_obj=virt_obj3
        )

        base_url = reverse('net_ipam-api:record-ipv4range-list')
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
        self.assertEqual(response.data['count'], 5)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 5)

        u1_role_wrapper.set_ipam_admin(True)
        u1_role_wrapper.set_ipam_readonly(False)

        # record_type
        query = parse.urlencode(query={'record_type': IPv4RangeRecord.RecordType.SPLIT.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], record2.id)
        self.assertKeysIn([
            'id', 'record_type', 'creation_time', 'start_address', 'end_address', 'mask_len',
            'ip_ranges', 'remark', 'user', 'org_virt_obj'
        ], response.data['results'][0])
        self.assertEqual(response.data['results'][0]['user']['id'], self.user1.id)
        self.assertEqual(response.data['results'][0]['user']['username'], self.user1.username)
        self.assertKeysIn([
            'id', 'name', 'creation_time', 'remark', 'organization'], response.data['results'][0]['org_virt_obj'])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['results'][0]['org_virt_obj']['organization'])
        self.assertIsInstance(response.data['results'][0]['ip_ranges'], list)
        self.assertEqual(len(response.data['results'][0]['ip_ranges']), 2)
        self.assertKeysIn(['start', 'end', 'mask'], response.data['results'][0]['ip_ranges'][0])

        query = parse.urlencode(query={'record_type': IPv4RangeRecord.RecordType.RESERVE.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'record_type': 'test'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # ipv4
        query = parse.urlencode(query={'ipv4': '127.0.0.0'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], record2.id)
        self.assertEqual(response.data['results'][1]['id'], record1.id)

        query = parse.urlencode(query={'ipv4': '159.0.2.0'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], record4.id)
        self.assertEqual(response.data['results'][1]['id'], record3.id)

        query = parse.urlencode(query={'ipv4': '159.0.2.022'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
