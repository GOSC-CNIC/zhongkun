from utils.test import get_or_create_user, MyAPITransactionTestCase
from link.managers.linkorg_manager import LinkOrgManager
from datetime import date
from django.urls import reverse
from link.managers.userrole_manager import UserRoleWrapper
from urllib import parse
from service.models import DataCenter
from link.models import LinkOrg, LinkUserRole

class LinkOrgTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        urole = LinkUserRole(user=self.user2, is_admin=False, is_readonly=True)
        urole.save(force_insert=True)
        urole = LinkUserRole(user=self.user3, is_admin=True, is_readonly=False)
        urole.save(force_insert=True)
        org1 = DataCenter(name='org1', name_en='org1 en')
        org1.save(force_insert=True)
        LinkOrgManager.create_linkorg(
            data_center=org1,
            name='空天院',
            remarks='',
            location=''
        )
        LinkOrgManager.create_linkorg(
            data_center=org1,
            name='中国遥感卫星地面站',
            remarks='',
            location=''
        )
    def test_list_linkorg(self):
        # user role 
        base_url = reverse('api:link-linkorg-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user2)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.client.force_login(self.user3)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)

        # data
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 2)
        linkorg = response.data['results'][0]
        self.assertKeysIn([
            'id', 'name', 'remarks', 'location', 'data_center'
        ], linkorg)
        self.assertKeysIn([
            'id', 'name', 'name_en'
        ], linkorg['data_center'])
        id = linkorg['id']
        db_linkorg = LinkOrg.objects.filter(id=id).first()
        self.assertEqual(linkorg['name'], db_linkorg.name)
        self.assertEqual(linkorg['data_center']['id'], db_linkorg.data_center.id)
        self.assertEqual(linkorg['data_center']['name'], db_linkorg.data_center.name)
        self.assertEqual(linkorg['data_center']['name_en'], db_linkorg.data_center.name_en)
        self.assertEqual(linkorg['location'], db_linkorg.location)
        self.assertEqual(linkorg['remarks'], db_linkorg.remarks)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)