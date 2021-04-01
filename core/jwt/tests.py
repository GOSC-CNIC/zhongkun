import pytz
from datetime import datetime

from django.test import TestCase
from . import jwt


class TimeTestCase(TestCase):
    def test_make_utc(self):
        dt1 = datetime.now()
        dt2 = jwt.make_utc(dt1)
        self.assertEqual(dt2.tzinfo, pytz.utc, msg='not utc time')

        dt1 = datetime.now(tz=pytz.timezone('Asia/Shanghai'))
        dt2 = jwt.make_utc(dt1)
        self.assertEqual(dt2.tzinfo, pytz.utc, msg='not utc time')
        self.assertEqual(dt2, dt1, msg='time not equal after make_utc()')
