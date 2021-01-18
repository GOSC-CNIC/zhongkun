import pytz
from datetime import datetime

from django.test import TestCase
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.exceptions import TokenError

from .authentication import CreateUserJWTAuthentication
from . import jwt


class JWTTestCase(TestCase):
    def setUp(self):
        self.username = 'test-username'
        token = AccessToken()
        token[api_settings.USER_ID_CLAIM] = self.username
        self.token = token
        self.jwt = str(token)

    def test_jwt(self):
        try:
            token = AccessToken(token=self.jwt)
        except TokenError as e:
            self.assertTrue(False, f'jwt token decode error, {str(e)}')
            return

        self.assertEqual(token.payload[api_settings.USER_ID_CLAIM], self.username)
        user = CreateUserJWTAuthentication().get_user(token.payload)
        self.assertEqual(user.username, self.username)


class TimeTestCase(TestCase):
    def test_make_utc(self):
        dt1 = datetime.now()
        dt2 = jwt.make_utc(dt1)
        self.assertEqual(dt2.tzinfo, pytz.utc, msg='not utc time')

        dt1 = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        dt2 = jwt.make_utc(dt1)
        self.assertEqual(dt2.tzinfo, pytz.utc, msg='not utc time')
        self.assertEqual(dt2, dt1, msg='time not equal after make_utc()')
