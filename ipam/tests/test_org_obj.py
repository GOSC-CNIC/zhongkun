from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone

from utils.test import get_or_create_user, MyAPITransactionTestCase, get_or_create_organization
from link.managers.userrole_manager import UserRoleWrapper as LinkUserRoleWrapper
from ..managers import UserIpamRoleWrapper, OrgVirtualObjectManager, ContactPersonManager
from ..models import ContactPerson, OrgVirtualObject


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

        # test link
        u1_role_wrapper.user_role.is_admin = False
        u1_role_wrapper.user_role.save(update_fields=['is_admin'])
        response = self.client.post(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_link_roler = LinkUserRoleWrapper(user=self.user1)
        u1_link_roler.get_or_create_user_role()
        u1_link_roler.user_role.is_readonly = True
        u1_link_roler.user_role.save(update_fields=['is_readonly'])
        response = self.client.post(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_link_roler.user_role.is_admin = True
        u1_link_roler.user_role.save(update_fields=['is_admin'])
        response = self.client.post(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=response)

        # ok
        self.assertEqual(OrgVirtualObject.objects.count(), 2)
        response = self.client.post(base_url, data={'name': 'test2', 'organization_id': org1.id, 'remark': ''})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization'], response.data)
        self.assertEqual(response.data['organization']['id'], org1.id)
        self.assertEqual(response.data['organization']['name'], org1.name)
        self.assertEqual(response.data['organization']['name_en'], org1.name_en)
        self.assertEqual(OrgVirtualObject.objects.count(), 3)

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

        query = parse.urlencode(query={'search': 'org1'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], virt_obj1.id)

        # test link
        u1_role_wrapper.user_role.is_admin = False
        u1_role_wrapper.user_role.save(update_fields=['is_admin'])
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_link_roler = LinkUserRoleWrapper(user=self.user1)
        u1_link_roler.get_or_create_user_role()
        u1_link_roler.user_role.is_readonly = True
        u1_link_roler.user_role.save(update_fields=['is_readonly'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)

        u1_link_roler.user_role.is_readonly = False
        u1_link_roler.user_role.is_admin = True
        u1_link_roler.user_role.save(update_fields=['is_readonly', 'is_admin'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization'], response.data['results'][0])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['results'][1]['organization'])

    def test_update(self):
        org1 = get_or_create_organization(name='org1')
        org_obj = OrgVirtualObjectManager.create_org_virt_obj(
            name='test', org=org1, remark=''
        )
        org_obj2 = OrgVirtualObjectManager.create_org_virt_obj(
            name='test exists', org=org1, remark=''
        )

        base_url = reverse('ipam-api:org-obj-detail', kwargs={'id': org_obj.id})
        response = self.client.put(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.put(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.put(base_url, data={'name': 'test', 'organization_id': 'nofound', 'remark': ''})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        base_url = reverse('ipam-api:org-obj-detail', kwargs={'id': 'notfound'})
        response = self.client.put(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = UserIpamRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_ipam_role()
        u1_role_wrapper.user_role.organizations.add(org1)
        response = self.client.put(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper.user_role.is_readonly = True
        u1_role_wrapper.user_role.save(update_fields=['is_readonly'])
        response = self.client.put(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper.user_role.is_admin = True
        u1_role_wrapper.user_role.save(update_fields=['is_admin'])

        response = self.client.put(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        base_url = reverse('ipam-api:org-obj-detail', kwargs={'id': org_obj.id})
        response = self.client.put(base_url, data={'name': 'test', 'organization_id': org1.id, 'remark': ''})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization'], response.data)
        org_obj.refresh_from_db()
        self.assertEqual(org_obj.name, 'test')
        self.assertEqual(org_obj.organization_id, org1.id)
        self.assertEqual(org_obj.remark, '')

        response = self.client.put(base_url, data={'name': 'test666', 'organization_id': org1.id, 'remark': 'test测试'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization'], response.data)
        org_obj.refresh_from_db()
        self.assertEqual(org_obj.name, 'test666')
        self.assertEqual(org_obj.organization_id, org1.id)
        self.assertEqual(org_obj.remark, 'test测试')

        response = self.client.put(base_url, data={'name': 'test666', 'organization_id': org1.id, 'remark': '测试888'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization'], response.data)
        org_obj.refresh_from_db()
        self.assertEqual(org_obj.name, 'test666')
        self.assertEqual(org_obj.organization_id, org1.id)
        self.assertEqual(org_obj.remark, '测试888')

        # test link
        u1_role_wrapper.user_role.is_admin = False
        u1_role_wrapper.user_role.save(update_fields=['is_admin'])
        response = self.client.put(base_url, data={'name': 'test exists', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_link_roler = LinkUserRoleWrapper(user=self.user1)
        u1_link_roler.get_or_create_user_role()
        u1_link_roler.user_role.is_readonly = True
        u1_link_roler.user_role.save(update_fields=['is_readonly'])
        response = self.client.put(base_url, data={'name': 'test exists', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_link_roler.user_role.is_admin = True
        u1_link_roler.user_role.save(update_fields=['is_admin'])
        response = self.client.put(base_url, data={'name': 'test exists', 'organization_id': org1.id, 'remark': ''})
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=response)

        # ok
        response = self.client.put(base_url, data={'name': 'test2', 'organization_id': org1.id, 'remark': ''})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization'], response.data)
        self.assertEqual(response.data['organization']['id'], org1.id)
        self.assertEqual(response.data['organization']['name'], org1.name)
        self.assertEqual(response.data['organization']['name_en'], org1.name_en)
        org_obj.refresh_from_db()
        self.assertEqual(org_obj.name, 'test2')
        self.assertEqual(org_obj.organization_id, org1.id)
        self.assertEqual(org_obj.remark, '')

    def test_detail(self):
        org1 = get_or_create_organization(name='org1')
        org_obj = OrgVirtualObjectManager.create_org_virt_obj(
            name='test', org=org1, remark=''
        )
        cp1 = ContactPersonManager.create_contact_person(
            name='tom test', telephone='110', email='tom@qq.com', address='beijing', remarks=''
        )
        cp2 = ContactPersonManager.create_contact_person(
            name='张三', telephone='666', email='test@cnic.cn', address='', remarks=''
        )

        base_url = reverse('ipam-api:org-obj-detail', kwargs={'id': org_obj.id})
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
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization', 'contacts'], response.data)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['organization'])
        self.assertIsInstance(response.data['contacts'], list)

        u1_role_wrapper.user_role.is_readonly = False
        u1_role_wrapper.user_role.is_admin = True
        u1_role_wrapper.user_role.save(update_fields=['is_admin', 'is_readonly'])
        org_obj.contacts.add(cp1)

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization', 'contacts'], response.data)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['organization'])
        self.assertIsInstance(response.data['contacts'], list)
        self.assertEqual(len(response.data['contacts']), 1)
        self.assertKeysIn([
            'id', 'name', 'telephone', 'email', 'address', 'remarks', 'creation_time', 'update_time'
        ], response.data['contacts'][0])

        # TargetNotExist
        base_url = reverse('ipam-api:org-obj-detail', kwargs={'id': 'notf'})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # test link
        base_url = reverse('ipam-api:org-obj-detail', kwargs={'id': org_obj.id})
        u1_role_wrapper.user_role.is_admin = False
        u1_role_wrapper.user_role.save(update_fields=['is_admin'])
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_link_roler = LinkUserRoleWrapper(user=self.user1)
        u1_link_roler.get_or_create_user_role()
        u1_link_roler.user_role.is_readonly = True
        u1_link_roler.user_role.save(update_fields=['is_readonly'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'creation_time', 'remark', 'organization', 'contacts'], response.data)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['organization'])
        self.assertIsInstance(response.data['contacts'], list)
        self.assertEqual(len(response.data['contacts']), 1)
        self.assertKeysIn([
            'id', 'name', 'telephone', 'email', 'address', 'remarks', 'creation_time', 'update_time'
        ], response.data['contacts'][0])

        u1_link_roler.user_role.is_readonly = False
        u1_link_roler.user_role.is_admin = True
        u1_link_roler.user_role.save(update_fields=['is_readonly', 'is_admin'])
        org_obj.contacts.add(cp2)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['contacts']), 2)
        self.assertKeysIn([
            'id', 'name', 'telephone', 'email', 'address', 'remarks', 'creation_time', 'update_time'
        ], response.data['contacts'][0])

        # TargetNotExist
        base_url = reverse('ipam-api:org-obj-detail', kwargs={'id': 'notf'})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)


class ContactsTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')

    def test_create(self):
        base_url = reverse('ipam-api:contacts-list')
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(base_url, data={
            'name': 'zhangsan', 'telephone': '110', 'email': '', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = UserIpamRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_ipam_role()
        u1_role_wrapper.user_role.is_readonly = True
        u1_role_wrapper.user_role.save(update_fields=['is_readonly'])
        response = self.client.post(base_url, data={
            'name': 'zhangsan', 'telephone': '110', 'email': '', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper.user_role.is_admin = True
        u1_role_wrapper.user_role.save(update_fields=['is_admin'])

        response = self.client.post(base_url, data={
            'name': 'zhangsan', 'telephone': '110', 'email': '', 'address': '', 'remarks': ''})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'telephone', 'email', 'address', 'remarks',
                           'creation_time', 'update_time'], response.data)
        self.assertEqual(ContactPerson.objects.count(), 1)
        cp: ContactPerson = ContactPerson.objects.first()
        self.assertEqual(cp.name, 'zhangsan')
        self.assertEqual(cp.telephone, '110')
        self.assertEqual(cp.email, '')
        self.assertEqual(cp.address, '')
        self.assertEqual(cp.remarks, '')

        # name
        response = self.client.post(base_url, data={
            'name': '', 'telephone': '110', 'email': '', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # telephone
        response = self.client.post(base_url, data={
            'name': 'zhangsan', 'telephone': '', 'email': '', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # email invalid
        response = self.client.post(base_url, data={
            'name': 'zhangsan', 'telephone': '110', 'email': 'sss', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # same name and telephone
        response = self.client.post(base_url, data={
            'name': 'zhangsan', 'telephone': '110', 'email': 'test@cnic.cn', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=response)

        response = self.client.post(base_url, data={
            'name': '李四', 'telephone': '110', 'email': 'test@cnic.cn', 'address': 'beijing', 'remarks': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactPerson.objects.count(), 2)
        cp: ContactPerson = ContactPerson.objects.get(id=response.data['id'])
        self.assertEqual(cp.name, '李四')
        self.assertEqual(cp.telephone, '110')
        self.assertEqual(cp.email, 'test@cnic.cn')
        self.assertEqual(cp.address, 'beijing')
        self.assertEqual(cp.remarks, 'test')

        # test link
        u1_role_wrapper.user_role.is_admin = False
        u1_role_wrapper.user_role.save(update_fields=['is_admin'])
        response = self.client.post(base_url, data={
            'name': '李四', 'telephone': '110', 'email': 'test@cnic.cn', 'address': 'beijing', 'remarks': 'test'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_link_roler = LinkUserRoleWrapper(user=self.user1)
        u1_link_roler.get_or_create_user_role()
        u1_link_roler.user_role.is_readonly = True
        u1_link_roler.user_role.save(update_fields=['is_readonly'])
        response = self.client.post(base_url, data={
            'name': '李四', 'telephone': '110', 'email': 'test@cnic.cn', 'address': 'beijing', 'remarks': 'test'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_link_roler.user_role.is_admin = True
        u1_link_roler.user_role.save(update_fields=['is_admin'])
        response = self.client.post(base_url, data={
            'name': '李四', 'telephone': '110', 'email': 'test@cnic.cn', 'address': 'beijing', 'remarks': 'test'})
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=response)

        # ok
        self.assertEqual(ContactPerson.objects.count(), 2)
        response = self.client.post(base_url, data={
            'name': 'tom', 'telephone': '110', 'email': 'test@cnic.cn', 'address': 'beijing', 'remarks': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactPerson.objects.count(), 3)

    def test_update(self):
        cp = ContactPersonManager.create_contact_person(
            name='zhangsan', telephone='110', email='', address='', remarks=''
        )
        cp2 = ContactPersonManager.create_contact_person(
            name='test2', telephone='666', email='', address='', remarks=''
        )
        base_url = reverse('ipam-api:contacts-detail', kwargs={'id': cp.id})
        response = self.client.put(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.put(base_url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.put(base_url, data={
            'name': 'zhangsan', 'telephone': '110', 'email': '', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper = UserIpamRoleWrapper(user=self.user1)
        u1_role_wrapper.user_role = u1_role_wrapper.get_or_create_user_ipam_role()
        u1_role_wrapper.user_role.is_readonly = True
        u1_role_wrapper.user_role.save(update_fields=['is_readonly'])
        response = self.client.put(base_url, data={
            'name': 'zhangsan', 'telephone': '110', 'email': '', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_role_wrapper.user_role.is_admin = True
        u1_role_wrapper.user_role.save(update_fields=['is_admin'])

        response = self.client.put(base_url, data={
            'name': 'zhangsan', 'telephone': '110', 'email': 'test@cnic.cn', 'address': 'beijing', 'remarks': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'telephone', 'email', 'address', 'remarks',
                           'creation_time', 'update_time'], response.data)
        cp.refresh_from_db()
        self.assertEqual(cp.name, 'zhangsan')
        self.assertEqual(cp.telephone, '110')
        self.assertEqual(cp.email, 'test@cnic.cn')
        self.assertEqual(cp.address, 'beijing')
        self.assertEqual(cp.remarks, 'test')

        # name
        response = self.client.put(base_url, data={
            'name': '', 'telephone': '110', 'email': '', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # telephone
        response = self.client.put(base_url, data={
            'name': 'zhangsan', 'telephone': '', 'email': '', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # email invalid
        response = self.client.put(base_url, data={
            'name': 'zhangsan', 'telephone': '110', 'email': 'sss', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # same name and telephone
        response = self.client.put(base_url, data={
            'name': 'test2', 'telephone': '666', 'email': 'test@cnic.cn', 'address': '', 'remarks': ''})
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=response)

        response = self.client.put(base_url, data={
            'name': '李四', 'telephone': '110', 'email': 'test@cnic.cn', 'address': 'beijing', 'remarks': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactPerson.objects.count(), 2)
        cp.refresh_from_db()
        self.assertEqual(cp.name, '李四')
        self.assertEqual(cp.telephone, '110')
        self.assertEqual(cp.email, 'test@cnic.cn')
        self.assertEqual(cp.address, 'beijing')
        self.assertEqual(cp.remarks, 'test')

        # test link
        u1_role_wrapper.user_role.is_admin = False
        u1_role_wrapper.user_role.save(update_fields=['is_admin'])
        response = self.client.put(base_url, data={
            'name': '李四', 'telephone': '110', 'email': 'test@cnic.cn', 'address': 'beijing', 'remarks': 'test'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_link_roler = LinkUserRoleWrapper(user=self.user1)
        u1_link_roler.get_or_create_user_role()
        u1_link_roler.user_role.is_readonly = True
        u1_link_roler.user_role.save(update_fields=['is_readonly'])
        response = self.client.put(base_url, data={
            'name': '张三', 'telephone': '6', 'email': 'test123@cnic.cn', 'address': 'beijing66', 'remarks': 'test88'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_link_roler.user_role.is_admin = True
        u1_link_roler.user_role.save(update_fields=['is_admin'])

        # ok
        response = self.client.put(base_url, data={
            'name': '张三', 'telephone': '6', 'email': 'test123@cnic.cn', 'address': 'beijing66', 'remarks': 'test88'})
        self.assertEqual(response.status_code, 200)
        cp.refresh_from_db()
        self.assertEqual(cp.name, '张三')
        self.assertEqual(cp.telephone, '6')
        self.assertEqual(cp.email, 'test123@cnic.cn')
        self.assertEqual(cp.address, 'beijing66')
        self.assertEqual(cp.remarks, 'test88')
        self.assertEqual(ContactPerson.objects.count(), 2)

        base_url = reverse('ipam-api:contacts-detail', kwargs={'id': 'notf'})
        response = self.client.put(base_url, data={
            'name': '张三', 'telephone': '6', 'email': 'test123@cnic.cn', 'address': 'beijing66', 'remarks': 'test88'})
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

    def test_list(self):
        cp = ContactPersonManager.create_contact_person(
            name='tom test', telephone='110', email='tom@qq.com', address='beijing', remarks=''
        )
        cp2 = ContactPersonManager.create_contact_person(
            name='张三', telephone='666', email='test@cnic.cn', address='', remarks=''
        )
        cp3 = ContactPersonManager.create_contact_person(
            name='李四', telephone='123456789', email='', address='', remarks=''
        )

        base_url = reverse('ipam-api:contacts-list')
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
        self.assertKeysIn([
            'id', 'name', 'telephone', 'email', 'address', 'remarks', 'creation_time', 'update_time'
        ], response.data['results'][0])
        self.assertEqual(response.data['results'][0]['id'], cp3.id)
        self.assertEqual(response.data['results'][1]['id'], cp2.id)
        self.assertEqual(response.data['results'][2]['id'], cp.id)

        u1_role_wrapper.user_role.is_readonly = False
        u1_role_wrapper.user_role.is_admin = True
        u1_role_wrapper.user_role.save(update_fields=['is_admin', 'is_readonly'])

        # search
        query = parse.urlencode(query={'search': 'test'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], cp2.id)
        self.assertEqual(response.data['results'][1]['id'], cp.id)

        query = parse.urlencode(query={'search': '张三'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], cp2.id)

        # page, page_size
        query = parse.urlencode(query={'page': 1, 'page_size': 2})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], cp3.id)
        self.assertEqual(response.data['results'][1]['id'], cp2.id)

        query = parse.urlencode(query={'page': 3, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 3)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], cp.id)

        # test link
        u1_role_wrapper.user_role.is_admin = False
        u1_role_wrapper.user_role.save(update_fields=['is_admin'])
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        u1_link_roler = LinkUserRoleWrapper(user=self.user1)
        u1_link_roler.get_or_create_user_role()
        u1_link_roler.user_role.is_readonly = True
        u1_link_roler.user_role.save(update_fields=['is_readonly'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)

        u1_link_roler.user_role.is_readonly = False
        u1_link_roler.user_role.is_admin = True
        u1_link_roler.user_role.save(update_fields=['is_readonly', 'is_admin'])
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertKeysIn([
            'id', 'name', 'telephone', 'email', 'address', 'remarks', 'creation_time', 'update_time'
        ], response.data['results'][0])
