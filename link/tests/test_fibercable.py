from utils.test import get_or_create_user, MyAPITransactionTestCase
from link.managers.leaseline_manager import LeaseLineManager
from link.managers.elementlink_manager import ElementLinkManager
from link.managers.fibercable_manager import FiberCableManager
from datetime import date
from django.urls import reverse
from link.models import FiberCable, Element, ElementLink, OpticalFiber
from link.managers.userrole_manager import UserRoleWrapper
from urllib import parse

class FiberCableTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')
        self.user2 = get_or_create_user(username='lisi@cnic.cn')
        self.user3 = get_or_create_user(username='zhangs@cnic.cn')
        UserRoleWrapper(user=self.user2).add_read_permission()
        UserRoleWrapper(user=self.user3).add_write_permission()

    def test_creat(self):       
        base_url = reverse('api:link-fibercable-list')
        data = {
            'number':'SM-test',
            'fiber_count':'30',
            'length':'30.5',
            'endpoint_1':'软件园',
            'endpoint_2':'古脊椎',
            'remarks':'test-remark'
            }
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user1)
        response = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user2)
        response = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.force_login(self.user3)
        response = self.client.post(base_url, data=data)
        self.assertEqual(response.status_code, 200)
        fibercable = response.data
        self.assertKeysIn([
            'id', 'number', 'fiber_count', 'length', 'endpoint_1', 'endpoint_2', 'remarks'
        ], fibercable)
        fibercable = FiberCable.objects.all().first()
        self.assertEqual(fibercable.number, 'SM-test')
        self.assertEqual(fibercable.fiber_count, 30)
        self.assertEqual(fibercable.length, 30.5)
        self.assertEqual(fibercable.fiber_count, OpticalFiber.objects.count())
        self.assertEqual(fibercable.fiber_count, Element.objects.count())
        self.assertEqual(OpticalFiber.objects.filter(sequence=30).exists(), True)
        self.assertEqual(OpticalFiber.objects.filter(sequence=30).first().fiber_cable, fibercable)
        self.assertEqual(OpticalFiber.objects.filter(sequence=31).exists(), False)
    def test_list(self):
        FiberCableManager.create_fibercable(
            number='SM-test',
            fiber_count=30,
            length=30.5,
            endpoint_1='软件园',
            endpoint_2='古脊椎',
            remarks='test-remark'
        )
        FiberCableManager.create_fibercable(
            number='SM-test2',
            fiber_count=10,
            length=24.1,
            endpoint_1='软件园',
            endpoint_2='微生物所',
            remarks='test-remark2'
        )

        base_url = reverse('api:link-fibercable-list')
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
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 2)
        fibercable = response.data['results'][0]
        self.assertKeysIn([
            'id', 'number', 'fiber_count', 'length', 'endpoint_1', 'endpoint_2', 'remarks'
        ], fibercable)

        # query "page"、"page_size"
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)

        # query "search"
        query = parse.urlencode(query={'search': '软件园'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'search': ' '})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'search': '微生物'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 1)
    
        query = parse.urlencode(query={'search': '地理'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 0)