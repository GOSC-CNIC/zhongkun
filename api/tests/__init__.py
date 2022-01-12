from rest_framework.test import APITestCase

from utils.test import get_or_create_user


class MyAPITestCase(APITestCase):
    def assertKeysIn(self, keys: list, container):
        for k in keys:
            self.assertIn(k, container)

    def assertErrorResponse(self, status_code: int, code: str, response):
        self.assertEqual(response.status_code, status_code)
        self.assertKeysIn(['code', 'message'], response.data)
        self.assertEqual(response.data['code'], code)

    def assert_is_subdict_of(self, sub: dict, d: dict):
        for k, v in sub.items():
            if k in d and v == d[k]:
                continue
            else:
                self.fail(f'{sub} is not sub dict of {d}, Not Equal key is {k}, {v} != {d.get(k)}')

        return True


def set_auth_header(test_case: APITestCase):
    password = 'password'
    user = get_or_create_user(password=password)
    # token = AccessToken.for_user(user)
    # test_case.client.credentials(HTTP_AUTHORIZATION='JWT ' + str(token))
    test_case.client.force_login(user=user)
    test_case.user = user
