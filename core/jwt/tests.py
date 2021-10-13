import pytz
from datetime import datetime

from django.test import TestCase
from django.http.request import HttpRequest

from . import jwt
from .authentication import CreateUserJWTAuthentication, JWTInvalidError


class TimeTestCase(TestCase):
    def test_make_utc(self):
        dt1 = datetime.now()
        dt2 = jwt.make_utc(dt1)
        self.assertEqual(dt2.tzinfo, pytz.utc, msg='not utc time')

        dt1 = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        dt2 = jwt.make_utc(dt1)
        self.assertEqual(dt2.tzinfo, pytz.utc, msg='not utc time')
        self.assertEqual(dt2, dt1, msg='time not equal after make_utc()')


class JWTTestCase(TestCase):
    token = ''

    def test_jwt(self):
        token = 'test'
        request = HttpRequest()
        request.META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        with self.assertRaises(JWTInvalidError):
            CreateUserJWTAuthentication().authenticate(request=request)

        token = self.token
        if not self.token:
            return

        request = HttpRequest()
        request.META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        user, t = CreateUserJWTAuthentication().authenticate(request=request)
        print(t.payload)
