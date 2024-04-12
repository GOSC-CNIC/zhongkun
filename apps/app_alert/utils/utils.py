from retrying import retry
import requests
import hashlib
import json
import time
from apps.app_alert.utils import errors
from urllib3 import exceptions as urllib3_exceptions
from requests import exceptions as requests_exceptions


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


@retry(stop_max_attempt_number=20)
def download(*args, **kwargs):
    try:
        resp = requests.request(*args, **kwargs)
        if resp.status_code != 200:
            raise errors.APIError()
        return resp
    except (urllib3_exceptions.MaxRetryError, requests_exceptions.ConnectionError) as e:
        raise errors.APIError()
