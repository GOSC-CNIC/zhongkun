import requests
from typing import Tuple, Union

from core import errors


class WebMonitorTaskClient:
    def __init__(self, endpoint_url: str, username: str, passwd: str):
        self.endpoint_url = endpoint_url.strip(' /')
        self.username = username
        self.passwd = passwd

    @property
    def post_task_url(self):
        return f'{self.endpoint_url}/api/app_probe/task/submit'

    def add_task(
            self, web_url: str, url_hash: str, is_tamper_resistant: bool
    ) -> Tuple[bool, Union[errors.Error, None], Union[requests.Response, None]]:
        try:
            r = self._post_request(
                url=self.post_task_url,
                data={
                    'action': 'add',
                    'task': {
                        'url': web_url,
                        'url_hash': url_hash,
                        'is_tamper_resistant': is_tamper_resistant
                    }
                },
                auth=(self.username, self.passwd)
            )
        except requests.exceptions.RequestException as exc:
            err = errors.Error(message=str(exc))
            return False, err, None

        if r.status_code == 200:
            return True, None, r

        err = errors.Error(message=r.text)
        return False, err, r

    def remove_task(
            self, web_url: str, url_hash: str, is_tamper_resistant: bool
    ) -> Tuple[bool, Union[errors.Error, None], Union[requests.Response, None]]:
        try:
            r = self._post_request(
                url=self.post_task_url,
                data={
                    'action': 'delete',
                    'task': {
                        'url': web_url,
                        'url_hash': url_hash,
                        'is_tamper_resistant': is_tamper_resistant
                    }
                },
                auth=(self.username, self.passwd)
            )
        except requests.exceptions.RequestException as exc:
            err = errors.Error(message=str(exc))
            return False, err, None

        if r.status_code == 200:
            return True, None, r

        err = errors.Error(message=r.text)
        return False, err, r

    def change_task(
            self, web_url: str, url_hash: str, is_tamper_resistant: bool,
            new_web_url: str, new_url_hash: str, new_is_tamper_resistant: bool
    ) -> Tuple[bool, Union[errors.Error, None], Union[requests.Response, None]]:
        try:
            r = self._post_request(
                url=self.post_task_url,
                data={
                    'action': 'update',
                    'task': {
                        'url': web_url,
                        'url_hash': url_hash,
                        'is_tamper_resistant': is_tamper_resistant
                    },
                    'newtask': {
                        'url': new_web_url,
                        'url_hash': new_url_hash,
                        'is_tamper_resistant': new_is_tamper_resistant
                    }
                },
                auth=(self.username, self.passwd)
            )
        except requests.exceptions.RequestException as exc:
            err = errors.Error(message=str(exc))
            return False, err, None

        if r.status_code == 200:
            return True, None, r

        err = errors.Error(message=r.text)
        return False, err, r

    @staticmethod
    def _post_request(url, data, auth):
        return requests.post(
            url=url, data=data, auth=auth, timeout=(6, 60)
        )
