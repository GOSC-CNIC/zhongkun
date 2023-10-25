from urllib import parse

from django.urls import reverse
from django.utils import timezone as dj_timezone

from service.models import DataCenter, Contacts
from utils.test import get_or_create_user, MyAPITransactionTestCase


class OrganizationTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='tom@qq.com')

    def test_list_ipv4_ranges(self):
        contact1 = Contacts(
            name='lilei', telephone='12345678', email='', address='beijing',
            creation_time=dj_timezone.now(), update_time=dj_timezone.now()
        )
        contact1.save(force_insert=True)
        contact2 = Contacts(
            name='zhangsan', telephone='8612345678', email='zhangsan@@cnic.cn', address='beijing',
            creation_time=dj_timezone.now(), update_time=dj_timezone.now()
        )
        contact2.save(force_insert=True)
        org1 = DataCenter(name='org1', name_en='org1 en')
        org1.save(force_insert=True)
        org1.contacts.add(contact1)
        org2 = DataCenter(name='org2', name_en='org2 en', creation_time=dj_timezone.now())
        org2.save(force_insert=True)
        org2.contacts.add(contact1, contact2)
        org3 = DataCenter(name='org3', name_en='org3 en', creation_time=dj_timezone.now())
        org3.save(force_insert=True)

        base_url = reverse('api:organization-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertKeysIn(['id', 'name', 'name_en', 'abbreviation', 'creation_time', 'desc',
                           'longitude', 'latitude', 'sort_weight'], response.data['results'][0])
        self.assertEqual(response.data['results'][0]['id'], org3.id)
        self.assertEqual(response.data['results'][1]['id'], org2.id)
        self.assertEqual(response.data['results'][2]['id'], org1.id)

        # query 'page', 'page_size'
        query = parse.urlencode(query={'page_size': 2})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'page': 2, 'page_size': 2})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 2)
        self.assertEqual(len(response.data['results']), 1)
