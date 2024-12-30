from typing import Union, Tuple, List
from collections import namedtuple
import asyncio

import aiohttp
from django.utils import timezone as dj_timezone

from core import errors
from apps.app_monitor.models import WebsiteDetectionPoint, ProbeTaskSubmitLog


WebTask = namedtuple('WebTask', ['url', 'url_hash', 'is_tamper_resistant'])


class ProbeTaskResult:
    ACTION_ADD = ProbeTaskSubmitLog.ActionType.ADD.value
    ACTION_UPDATE = ProbeTaskSubmitLog.ActionType.UPDATE.value
    ACTION_DELETE = ProbeTaskSubmitLog.ActionType.DELETE.value

    def __init__(self, probe: WebsiteDetectionPoint, ok: bool, version: int, action: str,
                 task: WebTask, new_task: WebTask = None, err_msg: str = ''):
        self.probe = probe
        self.version = version
        self.ok = ok
        self.action = action
        self.task = task
        self.new_task = new_task
        self.err_msg = err_msg

    def __str__(self):
        return self.display()

    def task_display(self):
        tk = self.task
        if tk:
            return f'task(url={tk.url}, is_tamper_resistant={tk.is_tamper_resistant})'

        return ''

    def new_task_display(self):
        tk = self.new_task
        if tk:
            return f'task(url={tk.url}, is_tamper_resistant={tk.is_tamper_resistant})'

        return ''

    def display(self):
        task_str = self.task_display()
        probe_name = self.probe.name
        if self.action == self.ACTION_ADD:
            if self.ok:
                return '成功添加监控任务到探测点“{name}”，{task}'.format(name=probe_name, task=task_str)
            else:
                return '添加监控任务到探测点“{name}”失败，{err_msg}，{task}'.format(
                    name=probe_name, err_msg=self.err_msg, task=task_str)
        elif self.action == self.ACTION_UPDATE:
            if self.ok:
                return '向探测点“{name}”请求更新监控任务成功，{task} to {new_task}'.format(
                    name=probe_name, task=task_str, new_task=self.new_task_display())
            else:
                return '向探测点“{name}”请求更新监控任务失败，{err_msg}，{task} to {new_task}'.format(
                    name=probe_name, err_msg=self.err_msg, task=task_str, new_task=self.new_task_display())
        elif self.action == self.ACTION_DELETE:
            if self.ok:
                return '成功从探测点“{name}”删除监控任务，{task}'.format(name=probe_name, task=task_str)
            else:
                return '从探测点“{name}”删除监控任务失败，{err_msg}，{task}'.format(
                    name=probe_name, err_msg=self.err_msg, task=task_str)

        return task_str

    def build_task_submit_log(self) -> ProbeTaskSubmitLog:
        new_url = ''
        new_url_hash = ''
        new_is_tamper = False
        if self.new_task:
            new_url = self.new_task.url
            new_url_hash = self.new_task.url_hash
            new_is_tamper = self.new_task.is_tamper_resistant

        return ProbeTaskSubmitLog(
            probe=self.probe, action_type=self.action,
            status=ProbeTaskSubmitLog.Status.SUCCESS.value if self.ok else ProbeTaskSubmitLog.Status.FAILED.value,
            task_url=self.task.url, task_url_hash=self.task.url_hash, task_is_tamper=self.task.is_tamper_resistant,
            new_url=new_url, new_url_hash=new_url_hash, new_is_tamper=new_is_tamper,
            task_version=self.version, desc=self.err_msg, creation=dj_timezone.now()
        )


class ProbeTaskClient:
    def __init__(self, probe: WebsiteDetectionPoint):
        self.probe = probe
        self.endpoint_url = probe.endpoint_url.strip(' /')
        self.username = probe.auth_username
        self.passwd = probe.auth_password

    @property
    def post_task_url(self):
        if self.endpoint_url:
            return f'{self.endpoint_url}/api/app_probe/task/submit'

        raise errors.Error(message='没有配置探测点监控任务服务地址')

    async def add_task(
            self, web_url: str, url_hash: str, is_tamper_resistant: bool, version: int
    ) -> Tuple[bool, Union[errors.Error, None], Union[aiohttp.ClientResponse, None]]:
        try:
            r = await self._post_request(
                url=self.post_task_url,
                data={
                    'operate': 'add',
                    'task': {
                        'url': web_url,
                        'url_hash': url_hash,
                        'is_tamper_resistant': is_tamper_resistant
                    },
                    'version': version
                },
                auth=(self.username, self.passwd)
            )
        except Exception as exc:
            err = errors.Error(message=str(exc))
            return False, err, None

        status_code = r.status
        if status_code == 200:
            return True, None, r

        text = await r.text()
        err = errors.Error(message=f"status: {status_code}, error: {text}")
        return False, err, r

    async def remove_task(
            self, web_url: str, url_hash: str, is_tamper_resistant: bool, version: int
    ) -> Tuple[bool, Union[errors.Error, None], Union[aiohttp.ClientResponse, None]]:
        try:
            r = await self._post_request(
                url=self.post_task_url,
                data={
                    'operate': 'delete',
                    'task': {
                        'url': web_url,
                        'url_hash': url_hash,
                        'is_tamper_resistant': is_tamper_resistant
                    },
                    'version': version
                },
                auth=(self.username, self.passwd)
            )
        except Exception as exc:
            err = errors.Error(message=str(exc))
            return False, err, None

        status_code = r.status
        if status_code == 200:
            return True, None, r

        text = await r.text()
        err = errors.Error(message=f"status: {status_code}, error: {text}")
        return False, err, r

    async def change_task(
            self, web_url: str, url_hash: str, is_tamper_resistant: bool,
            new_web_url: str, new_url_hash: str, new_is_tamper_resistant: bool, version: int
    ) -> Tuple[bool, Union[errors.Error, None], Union[aiohttp.ClientResponse, None]]:
        try:
            r = await self._post_request(
                url=self.post_task_url,
                data={
                    'operate': 'update',
                    'task': {
                        'url': web_url,
                        'url_hash': url_hash,
                        'is_tamper_resistant': is_tamper_resistant
                    },
                    'newtask': {
                        'url': new_web_url,
                        'url_hash': new_url_hash,
                        'is_tamper_resistant': new_is_tamper_resistant
                    },
                    'version': version
                },
                auth=(self.username, self.passwd)
            )
        except Exception as exc:
            err = errors.Error(message=str(exc))
            return False, err, None

        status_code = r.status
        if status_code == 200:
            return True, None, r

        text = await r.text()
        err = errors.Error(message=f"status: {status_code}, error: {text}")
        return False, err, r

    @staticmethod
    async def _post_request(url, data, auth: Tuple[str, str]) -> aiohttp.ClientResponse:
        try:
            async with aiohttp.ClientSession() as client:
                r = await client.post(
                    url=url, json=data, auth=aiohttp.BasicAuth(login=auth[0], password=auth[1]),
                    timeout=aiohttp.ClientTimeout(sock_connect=6, total=60))
        except aiohttp.ClientConnectionError:
            raise errors.Error(message='request timeout')
        except aiohttp.ClientError as exc:
            raise errors.Error(message=str(exc))

        return r

    async def add_task_to_probe(
            self, web_url: str, url_hash: str, is_tamper_resistant: bool, version: int
    ) -> ProbeTaskResult:
        task = WebTask(url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant)
        err_msg = ''

        ok, err, res = await self.add_task(
            web_url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant, version=version)
        if not ok:
            ok, err, res = await self.add_task(
                web_url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant, version=version)
            if not ok:
                err_msg = str(err)

        return ProbeTaskResult(
            probe=self.probe, ok=ok, action=ProbeTaskResult.ACTION_ADD,
            task=task, new_task=None, version=version, err_msg=err_msg
        )

    async def remove_task_from_probe(
            self, web_url: str, url_hash: str, is_tamper_resistant: bool, version: int
    ) -> ProbeTaskResult:
        """
        :return:
            OK: None
            Failed: raise Error
        """
        task = WebTask(url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant)
        err_msg = ''

        ok, err, res = await self.remove_task(
            web_url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant, version=version)
        if not ok:
            ok, err, res = await self.remove_task(
                web_url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant, version=version)
            if not ok:
                err_msg = str(err)

        return ProbeTaskResult(
            probe=self.probe, ok=ok, action=ProbeTaskResult.ACTION_DELETE,
            task=task, new_task=None, version=version, err_msg=err_msg
        )

    async def change_task_to_probe(
            self, web_url: str, url_hash: str, is_tamper_resistant: bool,
            new_web_url: str, new_url_hash: str, new_is_tamper_resistant: bool, version: int
    ) -> ProbeTaskResult:
        """
        :return:
            OK: None
            Failed: raise Error
        """
        task = WebTask(url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant)
        new_task = WebTask(url=new_web_url, url_hash=new_url_hash, is_tamper_resistant=new_is_tamper_resistant)
        err_msg = ''

        ok, err, res = await self.change_task(
            web_url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant,
            new_web_url=new_web_url, new_url_hash=new_url_hash, new_is_tamper_resistant=new_is_tamper_resistant,
            version=version
        )
        if not ok:
            ok, err, res = await self.change_task(
                web_url=web_url, url_hash=url_hash, is_tamper_resistant=is_tamper_resistant,
                new_web_url=new_web_url, new_url_hash=new_url_hash, new_is_tamper_resistant=new_is_tamper_resistant,
                version=version
            )
            if not ok:
                err_msg = str(err)

        return ProbeTaskResult(
            probe=self.probe, ok=ok, action=ProbeTaskResult.ACTION_UPDATE,
            task=task, new_task=new_task, version=version, err_msg=err_msg
        )

    @staticmethod
    async def do_async_requests(tasks):
        return await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def do_async_probe_tasks(tasks: List) -> List[ProbeTaskResult]:
        results = asyncio.run(ProbeTaskClient.do_async_requests(tasks))
        objs = []
        for r in results:
            if isinstance(r, ProbeTaskResult):
                tslog = r.build_task_submit_log()
                tslog.enforce_id()
                objs.append(tslog)

        try:
            objs = ProbeTaskSubmitLog.objects.bulk_create(objs=objs, batch_size=200)
        except Exception as exc:
            pass

        return results
