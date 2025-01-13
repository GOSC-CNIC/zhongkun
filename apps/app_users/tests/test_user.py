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
