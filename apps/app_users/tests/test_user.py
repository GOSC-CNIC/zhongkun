from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_service, MyAPITestCase, get_or_create_user, get_or_create_organization


class UserTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='tom@cnic.cn')
        self.service = get_or_create_service()

    def test_account(self):
        org = get_or_create_organization(name='机构test')
        base_url = reverse('users-api:user-account')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "username", "fullname", "organization"], response.data)

        self.assertEqual(response.data['id'], self.user.id)
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['fullname'], self.user.get_full_name())
        self.assertIs(response.data['is_fed_admin'], False)
        self.assertIsNone(response.data['organization'])

        self.user.organization = org
        self.user.save(update_fields=['organization'])

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "username", "fullname", "organization"], response.data)

        self.assertEqual(response.data['id'], self.user.id)
        self.assertEqual(response.data['username'], self.user.username)
        self.assertEqual(response.data['fullname'], self.user.get_full_name())
        self.assertIs(response.data['is_fed_admin'], False)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['organization'])
        self.assertEqual(response.data['organization']['name'], '机构test')

    def test_change_org(self):
        org = get_or_create_organization(name='机构test')
        base_url = reverse('users-api:user-change-org')
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user)
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        query = parse.urlencode(query={'organization_id': 'notfound'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        self.user.refresh_from_db()
        self.assertIsNone(self.user.organization)
        query = parse.urlencode(query={'organization_id': org.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "username", "fullname", "organization"], response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.organization_id, org.id)

        query = parse.urlencode(query={'organization_id': ''})
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertIsNone(self.user.organization)

    def test_list_user(self):
        org = get_or_create_organization(name='机构test')
        self.user.organization = org
        self.user.save(update_fields=['organization'])

        user_lilei = get_or_create_user(username='lilei@cnic.cn')
        get_or_create_user(username='zhangsan@cnic.cn')
        get_or_create_user(username='lisi@cnic.cn')

        base_url = reverse('users-api:user-list')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)

        self.client.force_login(self.user)
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user.set_federal_admin()
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(len(response.data['results']), 4)

        # query "search"
        query = parse.urlencode(query={'search': 'li'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        query = parse.urlencode(query={'search': 'lil'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], user_lilei.id)
        self.assertIsNone(response.data['results'][0]['organization'])

        # query "federal_admin"
        query = parse.urlencode(query={'federal_admin': 'tru'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={'federal_admin': 'false'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'federal_admin': 'true'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(keys=['id', 'username', 'fullname', 'organization'], container=response.data['results'][0])
        self.assertEqual(response.data['results'][0]['id'], self.user.id)
        self.assertIs(response.data['results'][0]['is_fed_admin'], True)
        self.assertKeysIn(keys=['id', 'name', 'name_en'], container=response.data['results'][0]['organization'])
