from utils.test import get_or_create_user, MyAPITransactionTestCase
from link.managers.fibercable_manager import FiberCableManager
from django.urls import reverse
from link.managers.elementlink_manager import ElementLinkManager
from urllib import parse
from link.models import OpticalFiber, LinkUserRole, ElementLink

class OpticalFiberTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        urole = LinkUserRole(user=self.user2, is_admin=False, is_readonly=True)
        urole.save(force_insert=True)
        urole = LinkUserRole(user=self.user3, is_admin=True, is_readonly=False)
        urole.save(force_insert=True)
        FiberCableManager.create_fibercable(
            number='SM-test',
            fiber_count=30,
            length=30.5,
            endpoint_1='软件园',
            endpoint_2='古脊椎',
            remarks='test-remark'
        )
        
    def test_list_opticalfiber(self):
        # user role 
        base_url = reverse('api:link-opticalfiber-list')
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
        self.assertEqual(response.data['count'], 30)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 20)
        opticalfiber = response.data['results'][0]
        self.assertKeysIn([
            'id', 'sequence', 'fiber_cable', 'is_linked', 'element_id'
        ], opticalfiber)
        self.assertKeysIn([
            'id', 'number'
        ], opticalfiber['fiber_cable'])
        id = opticalfiber['id']
        db_opticalfiber = OpticalFiber.objects.filter(id=id).first()
        self.assertEqual(opticalfiber['sequence'], db_opticalfiber.sequence)
        self.assertEqual(opticalfiber['fiber_cable']['id'], db_opticalfiber.fiber_cable.id)
        self.assertEqual(opticalfiber['fiber_cable']['number'], db_opticalfiber.fiber_cable.number)
        self.assertEqual(opticalfiber['is_linked'], False)
        self.assertEqual(opticalfiber['element_id'], db_opticalfiber.element.id)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 2})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 30)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)

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
        opticalfiber = OpticalFiber.objects.all().first()
        elementlink = ElementLinkManager.create_elementlink(
            number="test_link",
            id_list=[
                opticalfiber.element.id,
            ],
            remarks="test_remarks",
            link_status=ElementLink.LinkStatus.IDLE,
            task=None
        )
        query = parse.urlencode(query={'is_linked': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], opticalfiber.id)
        self.assertEqual(response.data['results'][0]['is_linked'], True)
