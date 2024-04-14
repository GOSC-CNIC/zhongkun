from retrying import retry
import requests
import hashlib
import json
import time
import datetime
from apps.app_alert.utils import errors
from urllib3 import exceptions as urllib3_exceptions
from requests import exceptions as requests_exceptions
from django.forms.models import model_to_dict


def custom_model_to_dict(obj):
    """
    Add id field
    """
    item = {'id': obj.id}
    item.update(model_to_dict(obj))
    return item


def hash_md5(s: str):
    """
    md5 hash值
    """
    return hashlib.md5(s.encode(encoding='utf-8')).hexdigest()


def hash_sha1(s: str):
    """
    sha1 hash值
    """
    return hashlib.sha1(s.encode(encoding='utf-8')).hexdigest()


class DateUtils:
    @classmethod
    def ts_to_date(cls, _ts, _format="%Y-%m-%d %H:%M:%S"):
        """
        时间戳转日期
        """
        return time.strftime(_format, time.localtime(int(_ts)))

    @classmethod
    def date_to_ts(cls, _date, _format="%Y-%m-%d %H:%M"):
        """
        日期(年月日时分秒)->时间戳（秒）
        """
        return round(time.mktime(time.strptime(_date, _format)))

    @classmethod
    def current_minute(cls):
        """
        当前日期时间
        """
        return str(datetime.datetime.now().strftime('%Y-%m-%d %H:%M'))

    def minute_timestamp(self):
        """
        当前时间戳 （分钟）
        """
        return self.date_to_ts(self.current_minute())


@retry(stop_max_attempt_number=20)
def download(*args, **kwargs):
    try:
        resp = requests.request(*args, **kwargs)
        if resp.status_code != 200:
            raise errors.APIError()
        return resp
    except (urllib3_exceptions.MaxRetryError, requests_exceptions.ConnectionError) as e:
        raise errors.APIError()
