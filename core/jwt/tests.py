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
    token = 'eyJ0eXBlIjoiYWNjZXNzVG9rZW4iLCJ0eXAiOiJKV1QiLCJhbGciOiJSUzUxMiJ9.eyJ0cnVlTmFtZSI6IueOi-eOiemhuiIsInR5cGUiOiJjb3JlTWFpbCIsInVtdElkIjoiMTA4NDA4NjIiLCJzZWN1cml0eUVtYWlsIjpudWxsLCJjc3RuZXRJZFN0YXR1cyI6ImFjdGl2ZSIsIm9yZ05hbWUiOiLkuK3lm73np5HlrabpmaLorqHnrpfmnLrnvZHnu5zkv6Hmga_kuK3lv4MiLCJjc3RuZXRJZCI6Indhbmd5dXNodW5AY25pYy5jbiIsImV4cCI6MTYzMjg4NzQzNiwiaXNzIjoid2FuZ3l1c2h1bkBjbmljLmNuIiwiaWF0IjoxNjMyODgzODM2fQ.kqKmdVsiWnqPotEWW4fPY9pzSILCqSxUe1eAlraNqGkfN_7thk7noh3aYGmbyW5ojyoXhSeC6JOqPQ0bMwGWEkvsR4Xi3lN1oYXKOA015HNPZx-MfCnZUeZZxSEj-YyPylBVNn4hwbhzJ322Razozlomy97OrFk1vyiM1uxqXiA'

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
