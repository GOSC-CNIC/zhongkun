import base64
from scan.managers import ScanGvmManager, ScanManager, ScanZapManager, TaskManager
from scan.models import VtScanner, VtTask
import requests
import logging


class Scanner:
    def __init__(self, vtscanner: VtScanner) -> None:
        self.vtscanner = vtscanner
        self.name = vtscanner.name
        self.ipaddr = vtscanner.ipaddr
        self.port = vtscanner.port
        self.key = vtscanner.key
        self.max_concurrency = vtscanner.max_concurrency
        self.type = vtscanner.type
        self.tasks = []

    def build_url(self, ip, port):
        return f"http://{ip}:{port}/"

    def get_own_tasks(self):
        vttasks = ScanManager.get_own_tasks(scanner=self.vtscanner)
        self.tasks = list(vttasks)

    def process_running_tasks(self):
        pass

    def process_new_tasks(self):
        pass


class WebZapScanner(Scanner):
    class ZapStatus:
        SPIDER = 'spider'
        AJAXSPIDER = 'ajaxspider'
        ACTIVE = 'active'
        PASSIVE = 'passive'
        DONE = 'done'

    def __init__(self, vtscanner: VtScanner) -> None:
        super().__init__(vtscanner)
        self.url = self.build_url(self.ipaddr, self.port)

    def get_task_status(self, running_status: str, target: str):
        """
            reponse:
            {
                ok: False/True, 为False表明扫描引擎出现问题
                errmsg: 错误原因
                running_status: 任务状态, spider / ajaxspider / active / passive / done
            }
        """
        try:
            response = requests.get(
                self.url + 'zap/get_task',
                params={'running_status': running_status, 'target': target},
                headers={'secret-key': self.key},
            )
            response.raise_for_status()
            data = response.json()
            if not data['ok']:
                logging.error(f"Get task from zap {self.url} failed, {data['errmsg']}")
                return None
            running_status = data['running_status']
            return running_status
        except Exception as e:
            logging.error(f"Get task from zap {self.url} failed, {str(e)}")
            return None

    def get_report(self):
        """
            reponse:
            {
                ok: False/True, 为False表明扫描引擎出现问题
                errmsg: 错误原因
                content: 文件内容
            }
        """
        try:
            response = requests.get(
                self.url + 'zap/get_report', headers={'secret-key': self.key}
            )
            response.raise_for_status()
            data = response.json()
            if not data['ok']:
                logging.error(
                    f"Get report from zap {self.url} failed, {data['errmsg']}"
                )
                return None
            content = data['content']
            content = content.encode('utf-8')
            return content
        except Exception as e:
            logging.error(f"Get report from zap {self.url} failed, {str(e)}")
            return None

    def create_task(self, target: str):
        """
            reponse:
            {
                ok: False/True, 为False表明扫描引擎出现问题
                errmsg: 错误原因
                running_status: 扫描器中任务状态
            }
        """
        try:
            response = requests.post(
                self.url + 'zap/create_task',
                headers={'secret-key': self.key},
                params={'target': target},
            )
            response.raise_for_status()
            data = response.json()
            if not data['ok']:
                logging.error(f"Create task of zap {self.url} failed, {data['errmsg']}")
                return None
            running_status = data['running_status']
            return running_status
        except Exception as e:
            logging.error(f"Create task of zap {self.url} failed, {str(e)}")
            return None

    def delete_task(self):
        """
            reponse:
            {
                ok: False/True, 为False表明扫描引擎出现问题
                errmsg: 错误原因
            }
        """
        try:
            response = requests.delete(
                self.url + 'zap/delete_task', headers={'secret-key': self.key}
            )
            response.raise_for_status()
            data = response.json()
            if not data['ok']:
                logging.error(
                    f"Delete task from gvm {self.url} failed, {data['errmsg']}"
                )
        except Exception as e:
            logging.error(f"Delete task from gvm {self.url} failed, {str(e)}")

    def create_task_and_update_vtwebtask(self, vttask: VtTask):
        running_status = self.create_task(target=vttask.target)
        if running_status:
            if not ScanZapManager.set_web_task_running(
                task=vttask, scanner=self.vtscanner, running_status=running_status
            ):
                self.delete_task()

    def process_running_tasks(self):
        """
        处理运行中的任务， ZAP扫描引擎的并发度为1
            1. 获取任务状态
            2. 如果任务完成，则下载报告并更新状态
            3. 任务未完成则更新内部状态
        """
        self.get_own_tasks()
        for task in self.tasks:
            running_status = self.get_task_status(
                running_status=task.running_status, target=task.target
            )
            if running_status is None:
                continue
            elif running_status == self.ZapStatus.DONE:
                content = self.get_report()
                if content is not None:
                    ScanZapManager.web_create_report_and_save(
                        task=task, content=content
                    )
            elif running_status != task.running_status:
                ScanZapManager.set_web_task_status(
                    task=task, running_status=running_status
                )

    def process_new_tasks(self):
        self.get_own_tasks()
        allowed_num = self.max_concurrency - len(self.tasks)
        if allowed_num <= 0:
            return
        vttasks = ScanManager.get_queued_tasks(scan_type=self.type, num=allowed_num)
        for vttask in vttasks:
            self.create_task_and_update_vtwebtask(vttask=vttask)


class HostGvmScanner(Scanner):
    class GvmStatus:
        REQUESTED = 'Requested'
        QUEUED = 'Queued'
        RUNNING = 'Running'
        DONE = 'Done'
        FAILED = 'Failed'
        INTERAPTED = 'Interapted'

    def __init__(self, vtscanner: VtScanner) -> None:
        super().__init__(vtscanner)
        self.url = self.build_url(self.ipaddr, self.port)

    def get_task_status(self, running_id):
        """
            reponse:
            {
                ok: False/True, 为False表明扫描引擎出现问题
                errmsg: 错误原因
                running_status: 任务状态, Requested / Queued / Running / Done / Failed / Interapted
            }
        """
        try:
            response = requests.get(
                self.url + 'gvm/get_task',
                params={'running_id': running_id},
                headers={'secret-key': self.key},
            )    
            response.raise_for_status()
            data = response.json()
            if not data['ok']:
                logging.error(f"Get task from gvm {self.url} failed, {data['errmsg']}")
                return None
            status = data['running_status']
            return status
        except Exception as e:
            logging.error(f"Get task from gvm {self.url} failed, {str(e)}")
            return None

    def get_report(self, running_id):
        """
            reponse:
            {
                ok: False/True, 为False表明扫描引擎出现问题
                errmsg: 错误原因
                content: 文件内容
            }
        """
        try:
            response = requests.get(
                self.url + 'gvm/get_report',
                params={'running_id': running_id},
                headers={'secret-key': self.key},
            )
            response.raise_for_status()
            data = response.json()
            if not data['ok']:
                logging.error(
                    f"Get report from gvm {self.url} failed, {data['errmsg']}"
                )
                return None
            content = data['content']
            content = base64.b64decode(content)
            return content
        except Exception as e:
            logging.error(f"Get report from gvm {self.url} failed, {str(e)}")
            return None

    def delete_task(self, running_id):
        """
            reponse:
            {
                ok: False/True, 为False表明扫描引擎出现问题
                errmsg: 错误原因
            }
        """
        try:
            response = requests.delete(
                self.url + 'gvm/delete_task',
                params={'running_id': running_id},
                headers={'secret-key': self.key},
            )
            response.raise_for_status()
            data = response.json()
            if not data['ok']:
                logging.error(
                    f"Delete task from gvm {self.url} failed, {data['errmsg']}"
                )
        except Exception as e:
            logging.error(f"Delete task from gvm {self.url} failed, {str(e)}")

    def create_task(self, id: str, target: str):
        """
            reponse:
            {
                ok: False/True, 为False表明扫描引擎出现问题
                errmsg: 错误原因
                runnig_id: 扫描器中任务id
            }
            """
        try:
            response = requests.post(
                self.url + 'gvm/create_task',
                headers={'secret-key': self.key},
                params={'target': target, 'id': id},
            )
            response.raise_for_status()
            data = response.json()
            if not data['ok']:
                logging.error(f"Create task of gvm {self.url} failed, {data['errmsg']}")
                return None
            running_id = data['running_id']
            return running_id
        except Exception as e:
            logging.error(f"Create task of gvm {self.url} failed, {str(e)}")
            return None

    def create_task_and_update_vthosttask(self, vttask: VtTask):
        """
        远程扫描引擎任务创建
        如果任务状态更新失败，删除扫描器中的任务
        """
        running_id = self.create_task(id=vttask.id, target=vttask.target)
        if running_id:
            if not ScanGvmManager.set_host_task_running(
                task=vttask, scanner=self.vtscanner, running_id=running_id
            ):
                self.delete_task(runnig_id=running_id)

    def process_running_tasks(self):
        """
        处理运行中的任务
        TODO: 在多扫描器场景下，自动将无法正常工作的扫描器status设置为DISABLE
            1. 获得所有任务
            2. 遍历所有任务并做相同操作
            3. 获取任务状态
            4.1. 如果任务完成则更新状态并下载报告
            4.2. 如果任务失败则重新运行任务, 即设置为Queuing
            4.3. 任务依然运行中处理下一个任务
        """
        self.get_own_tasks()
        for task in self.tasks:
            status = self.get_task_status(running_id=task.running_id)
            if status is None:
                continue
            elif status == self.GvmStatus.DONE:
                content = self.get_report(running_id=task.running_id)
                if content is not None and ScanGvmManager.host_create_report_and_save(
                    task=task, content=content
                ):
                    self.delete_task(running_id=task.running_id)
            elif status in [self.GvmStatus.FAILED, self.GvmStatus.INTERAPTED]:
                ScanGvmManager.reset_host_task_status(task=task)
            elif status in [
                self.GvmStatus.REQUESTED,
                self.GvmStatus.QUEUED,
                self.GvmStatus.RUNNING,
            ]:
                continue

    def process_new_tasks(self):
        """
        运行新的任务
            1. 获得所有运行中任务
            2. 根据任务数获取新任务进行执行
            3. 执行任务并更新task状态
        """
        self.get_own_tasks()
        allowed_num = self.max_concurrency - len(self.tasks)
        if allowed_num <= 0:
            return
        vttasks = ScanManager.get_queued_tasks(self.type, allowed_num)
        for vttask in vttasks:
            self.create_task_and_update_vthosttask(vttask=vttask)


class ScanWorker:
    def __init__(self) -> None:
        vtscanners = ScanManager.get_enabled_scanners()
        self.scanners = []
        for vtscanner in vtscanners:
            if vtscanner.engine == VtScanner.ScannerEngine.GVM:
                self.scanners.append(HostGvmScanner(vtscanner))
            if vtscanner.engine == VtScanner.ScannerEngine.ZAP:
                self.scanners.append(WebZapScanner(vtscanner))

    def process_running_tasks(self):
        for scanner in self.scanners:
            scanner.process_running_tasks()

    def process_new_tasks(self):
        for scanner in self.scanners:
            scanner.process_new_tasks()

    def process_disable_scanner_task(self):
        """如果scanner被设置为disable，则它正在运行中的任务需要重新运行"""
        disable_scanner_tasks = TaskManager.get_disable_scanner_task()
        for task in disable_scanner_tasks:
            TaskManager.reset_task_status(task)

    def run(self):
        self.process_running_tasks()
        self.process_new_tasks()
        self.process_disable_scanner_task()
