from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone

from utils.test import get_or_create_user, MyAPITransactionTestCase, get_or_create_organization
from ..managers import UserIpamRoleWrapper, OrgVirtualObject


class OrgObjTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

    def test_create(self):
        org1 = get_or_create_organization(name='org1')

        base_url = reverse('ipam-api:org-obj-list')
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = UserIpamRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_ipam_role()
        u1_role_wrapper.user_role.organizations.add(org1)
        response = self.client.post(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper.user_role.is_readonly = True
        u1_role_wrapper.user_role.save(update_fields=['is_readonly'])
        response = self.client.post(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper.user_role.is_admin = True
        u1_role_wrapper.user_role.save(update_fields=['is_admin'])

        response = self.client.post(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization'], response.data)
        self.assertEqual(response.data['organization']['id'], org1.id)
        self.assertEqual(response.data['organization']['name'], org1.name)
        self.assertEqual(response.data['organization']['name_en'], org1.name_en)
        self.assertEqual(OrgVirtualObject.objects.count(), 1)

        response = self.client.post(base_url, data={'name': 'test', 'organization_id': 'test', 'remark': ''})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={'name': 'test测试', 'organization_id': org1.id, 'remark': '备注test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(OrgVirtualObject.objects.count(), 2)
        org_obj = OrgVirtualObject.objects.get(id=response.data['id'])
        self.assertEqual(org_obj.name, 'test测试')
        self.assertEqual(org_obj.remark, '备注test')
        self.assertEqual(org_obj.organization_id, org1.id)

    def test_list(self):
        org1 = get_or_create_organization(name='org1')
        org2 = get_or_create_organization(name='org2')
        virt_obj1 = OrgVirtualObject(
            name='obj1 test org', organization=org1, creation_time=dj_timezone.now(), remark='remark1 org')
        virt_obj1.save(force_insert=True)
        virt_obj2 = OrgVirtualObject(
            name='obj2 test', organization=org2, creation_time=dj_timezone.now(), remark='remark2 test org')
        virt_obj2.save(force_insert=True)
        virt_obj3 = OrgVirtualObject(
            name='obj3 test', organization=None, creation_time=dj_timezone.now(), remark='remark3 no org')
        virt_obj3.save(force_insert=True)

        base_url = reverse('ipam-api:org-obj-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = UserIpamRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_ipam_role()
        u1_role_wrapper.user_role.is_readonly = True
        u1_role_wrapper.user_role.save(update_fields=['is_readonly'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization'], response.data['results'][0])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['results'][1]['organization'])

        u1_role_wrapper.user_role.is_readonly = False
        u1_role_wrapper.user_role.is_admin = True
        u1_role_wrapper.user_role.save(update_fields=['is_admin', 'is_readonly'])

        # org_id
        query = parse.urlencode(query={'org_id': org1.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], virt_obj1.id)

        # search
        query = parse.urlencode(query={'search': 'test org'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], virt_obj2.id)
        self.assertEqual(response.data['results'][1]['id'], virt_obj1.id)

        query = parse.urlencode(query={'search': 'no org'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], virt_obj3.id)
        print(response.json())
