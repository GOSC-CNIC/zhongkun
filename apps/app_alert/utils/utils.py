import hashlib
import time
import datetime
from zoneinfo import ZoneInfo
from urllib3 import exceptions as urllib3_exceptions

from retrying import retry
import requests
from requests import exceptions as requests_exceptions
from django.forms.models import model_to_dict

from apps.app_alert.utils import errors


tz_utc = datetime.timezone.utc
tz_shanghai = ZoneInfo('Asia/Shanghai')


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
    def ts_to_date(cls, timestamp, fmt="%Y-%m-%d %H:%M:%S", timezone=tz_shanghai):
        """
        时间戳转日期
        """
        timestamp_s = int(timestamp) if len(str(timestamp)) <= 10 else int(timestamp) / 1000
        dt_tz = datetime.datetime.fromtimestamp(timestamp_s, timezone)
        return dt_tz.strftime(fmt)

    @classmethod
    def date_to_ts(cls, dt, fmt="%Y-%m-%d %H:%M:%S", timezone=tz_shanghai):
        """
        日期转时间戳（秒）
        """
        if isinstance(dt, datetime.datetime):
            return int(dt.timestamp())
        else:
            dt_tz = datetime.datetime.strptime(dt, fmt)
            if dt_tz.tzinfo is None:
                dt_tz = dt_tz.replace(tzinfo=timezone)  # 时间不变，只添加时区信息
            return int(dt_tz.timestamp())

    @classmethod
    def now(cls, timezone=tz_shanghai):
        """
        当前时间
        """
        return datetime.datetime.now(tz=timezone)

    @classmethod
    def timestamp(cls):
        """
        当前时间戳
        """
        return int(time.time())

    @classmethod
    def timestamp_round(cls, ts):
        """
        时间戳精确度到分钟
        """
        return int(ts / 60) * 60

    @classmethod
    def beijing_timetuple(cls, *args, **kwargs):
        if time.strftime('%z') == "+0800":
            return datetime.datetime.now().timetuple()
        return (datetime.datetime.now() + datetime.timedelta(hours=8)).timetuple()


@retry(stop_max_attempt_number=20)
def download(*args, **kwargs):
    try:
        resp = requests.request(*args, **kwargs)
        if resp.status_code != 200:
            raise errors.APIError()
        return resp
    except (urllib3_exceptions.MaxRetryError, requests_exceptions.ConnectionError) as e:
        raise errors.APIError()
