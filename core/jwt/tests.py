from django.test import TestCase

from . import jwt


class JWTTestCase(TestCase):
    def setUp(self):
        self.username = 'test-username'
        token = jwt.Token()
        token['username'] = self.username
        self.token = token
        self.jwt = str(token)

    def test_jwt(self):
        try:
            token = jwt.Token(token=self.jwt)
        except jwt.JWTInvalidError as e:
            self.assertTrue(False, f'jwt token decode error, {str(e)}')
            return

        self.assertEqual(token.payload['username'], self.username)

