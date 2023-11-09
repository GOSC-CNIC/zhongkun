from utils.test import get_or_create_user, MyAPITransactionTestCase
from link.managers.connectorbox_manager import ConnectorBoxManager
from django.urls import reverse
from link.managers.elementlink_manager import ElementLinkManager
from urllib import parse
from link.models import ConnectorBox, LinkUserRole, ElementLink

class ConnectorBoxTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        urole = LinkUserRole(user=self.user2, is_admin=False, is_readonly=True)
        urole.save(force_insert=True)
        urole = LinkUserRole(user=self.user3, is_admin=True, is_readonly=False)
        urole.save(force_insert=True)
        ConnectorBoxManager.create_connectorbox(
            number='test_connector1',
            place='test_place1',
            remarks='',
            location='',
        )
        ConnectorBoxManager.create_connectorbox(
            number='test_connector2',
            place='test_place2',
            remarks='',
            location='',
        )
    def test_list_connectorbox(self):
        # user role 
        base_url = reverse('api:link-connectorbox-list')
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
        connectorbox = response.data['results'][0]
        self.assertKeysIn([
            'id', 'number', 'place', 'remarks', 'location', 'place', 'is_linked', 'element_id'
        ], connectorbox)
        id = connectorbox['id']
        db_connectorbox = ConnectorBox.objects.filter(id=id).first()
        self.assertEqual(connectorbox['number'], db_connectorbox.number)
        self.assertEqual(connectorbox['place'], db_connectorbox.place)
        self.assertEqual(connectorbox['remarks'], db_connectorbox.remarks)
        self.assertEqual(connectorbox['location'], db_connectorbox.location)
        self.assertEqual(connectorbox['place'], db_connectorbox.place)
        self.assertEqual(connectorbox['is_linked'], False)
        self.assertEqual(connectorbox['element_id'], db_connectorbox.element.id)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)

        # query "is_linked"
        query = parse.urlencode(query={'is_linked': '1'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(
            status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={'is_linked': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'is_linked': 'False'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['results'][0]['is_linked'], False)
        connectorbox = ConnectorBox.objects.all().first()
        elementlink = ElementLinkManager.create_elementlink(
            number="test_link",
            id_list=[
                connectorbox.element.id,
            ],
            remarks="test_remarks",
            link_status=ElementLink.LinkStatus.IDLE,
            task=None
        )
        query = parse.urlencode(query={'is_linked': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], connectorbox.id)
        self.assertEqual(response.data['results'][0]['is_linked'], True)
