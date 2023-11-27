from django.urls import reverse

from utils.test import get_or_create_user, MyAPITransactionTestCase, get_or_create_organization
from ..managers import UserIpamRoleWrapper, OrgVirtualObject


class OrgObjTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

    def test_list_ipv4_ranges(self):
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
