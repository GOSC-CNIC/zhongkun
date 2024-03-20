import datetime
from django.db import transaction, models
from scan.models import VtReport, VtScanner, VtTask
from django.core.validators import URLValidator
from django.utils.translation import gettext as _
from core import errors
from django.utils import timezone
from decimal import Decimal


class ScanManager:
    @staticmethod
    def get_enabled_scanners():
        """
        获取服务中的扫描器实例
        """
        vtscanners = VtScanner.objects.filter(status=VtScanner.Status.ENABLE)
        return vtscanners

    @staticmethod
    def get_disabled_scanners():
        """
        获取服务中的扫描器实例
        """
        vtscanners = VtScanner.objects.filter(status=VtScanner.Status.DISABLE)
        return vtscanners

    @staticmethod
    def get_own_tasks(scanner: VtScanner):
        """
        获取扫描器正在执行中的任务
        """
        return scanner.tasks.filter(task_status=VtTask.Status.RUNNING)

    @staticmethod
    def get_queued_tasks(scan_type: str, num: int):
        """
        获取正在排队等待的某个类型的任务，按照优先级和时间排序
        scan_type: [web, host]
        """
        return VtTask.objects.filter(
            task_status=VtTask.Status.QUEUED, type=scan_type
        ).order_by('-priority', 'create_time')[:num]


class ScanGvmManager:
    @staticmethod
    def reset_host_task_status(task: VtTask):
        """
        将任务重置为等待运行
        """
        try:
            task.task_status = VtTask.Status.QUEUED
            task.scanner = None
            task.running_id = None
            task.save(update_fields=['task_status', 'scanner', 'running_id'])
            return True
        except Exception as e:
            return False

    @staticmethod
    def host_create_report_and_save(task: VtTask, content):
        """
        创建任务报告并更新任务状态
        """
        try:
            time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = task.name + "_" + time + '.pdf'
            size = len(content)
            report = VtReport(
                filename=filename, type=VtReport.FileType.PDF, content=content, size=size
            )
            with transaction.atomic():
                report.save(force_insert=True)
                task.task_status = VtTask.Status.DONE.value
                task.report = report
                task.finish_time = timezone.now()
                task.save(update_fields=['task_status', 'report', 'finish_time'])

            return True
        except Exception as e:
            return False

    @staticmethod
    def set_host_task_running(task: VtTask, scanner: VtScanner, running_id: str):
        """
        将任务状态设置为运行中
        """
        try:
            task.task_status = VtTask.Status.RUNNING
            task.scanner = scanner
            task.running_id = running_id
            task.save(update_fields=['task_status', 'scanner', 'running_id'])
            return True
        except Exception as e:
            return False


class ScanZapManager:
    @staticmethod
    def web_create_report_and_save(task: VtTask, content):
        """
        创建任务报告并更新任务状态
        """
        try:
            if isinstance(content, str):
                content = content.encode('utf-8')
            size = len(content)
            time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = task.name + "_" + time + '.html'
            report = VtReport(
                filename=filename, type=VtReport.FileType.HTML, content=content, size=size
            )
            with transaction.atomic():
                report.save(force_insert=True)
                task.task_status = VtTask.Status.DONE
                task.report = report
                task.finish_time = timezone.now()
                task.save(update_fields=['task_status', 'report', 'finish_time'])

            return True
        except Exception as e:
            return False

    @staticmethod
    def set_web_task_running(task: VtTask, scanner: VtScanner, running_status: str):
        """
        设置任务状态运行中
        """
        try:
            task.task_status = VtTask.Status.RUNNING
            task.scanner = scanner
            task.running_status = running_status
            task.save(update_fields=['task_status', 'scanner', 'running_status'])
            return True
        except Exception as e:
            return False

    @staticmethod
    def set_web_task_status(task: VtTask, running_status: str, errmsg: str = None):
        """
        设置任务扫描器内部状态
        """
        try:
            task.running_status = running_status
            if running_status == VtTask.RunningStatus.FAILED:
                task.task_status = VtTask.Status.FAILED
            if errmsg:
                task.errmsg = errmsg
            task.save(update_fields=['running_status', 'task_status', 'errmsg'])
            return True
        except Exception as e:
            return False


class TaskManager:
    @staticmethod
    def reset_task_status(task: VtTask):
        """
        将任务重置为等待运行
        """
        try:
            task.task_status = VtTask.Status.QUEUED
            task.scanner = None
            task.running_id = None
            task.running_status = None
            task.save(update_fields=['task_status', 'scanner', 'running_id', 'running_status'])
            return True
        except Exception as e:
            return False

    @staticmethod
    def get_user_task_queryset(user_id: str, type: str = None):
        """
        获取用户任务查询集
        type: one in [None, web, host]
        """
        q = models.Q(user_id=user_id)
        if type:
            q = q & models.Q(type=type)

        return (
            VtTask.objects.select_related('user')
            .filter(q)
            .order_by('-create_time')
            .distinct()
        )

    @staticmethod
    def get_user_web_tasks(user_id: str):
        """
        获取用户的站点扫描任务
        """
        return TaskManager.get_user_task_queryset(user_id=user_id, type='web')

    @staticmethod
    def get_user_host_tasks(user_id: str):
        """
        获取用户的主机扫描任务
        """
        return TaskManager.get_user_task_queryset(user_id=user_id, type='host')

    @staticmethod
    def get_user_all_tasks(user_id: str):
        """
        获取用户的所有任务
        """
        return TaskManager.get_user_task_queryset(user_id=user_id)

    @staticmethod
    def create_task(
            user_id: str, name: str, type: str, target: str, remark: str,
            pay_amount: Decimal = Decimal('0'), balance_amount: Decimal = Decimal('0'),
            coupon_amount: Decimal = Decimal('0'), task_id: str = None
    ):
        """创建用户扫描任务"""
        task = VtTask(
            user_id=user_id, name=name, type=type, target=target, remark=remark,
            pay_amount=pay_amount, balance_amount=balance_amount, coupon_amount=coupon_amount
        )
        if task_id:
            task.id = task_id

        task.save(force_insert=True)
        return task

    @staticmethod
    def create_task_command(
        name: str, type: str, target: str, remark: str, priority: int
    ):
        """通过命令创建扫描任务"""
        task = VtTask(name=name, type=type, target=target, remark=remark, priority=priority)
        task.save(force_insert=True)
        return task

    @staticmethod
    def get_task_by_id(task_id: str, user_id:str):
        """通过task_id获取任务"""
        return (
            VtTask.objects.select_related('report')
            .filter(id=task_id, user_id=user_id)
            .first()
        )

    @staticmethod
    def set_task_payment_id(task: VtTask, payment_history_id: str):
        task.payment_history_id = payment_history_id
        task.save(update_fields=['payment_history_id'])

    @staticmethod
    def get_disable_scanner_task():
        tasks = VtTask.objects.filter(scanner__status='disable', task_status='running')
        return tasks


class ScannerManager:
    @staticmethod
    def create_scanner(
        name: str,
        type: str,
        ipaddr: str,
        port: int,
        key: str,
        engine: str,
        max_concurrency: int,
        status: str,
    ):
        """
        新建扫描器
        """
        scanner = VtScanner(
            name=name,
            type=type,
            engine=engine,
            ipaddr=ipaddr,
            port=port,
            key=key,
            max_concurrency=max_concurrency,
            status=status,
        )
        scanner.save(force_insert=True)
        return scanner

    @staticmethod
    def enable_scanner(scanner: VtScanner):
        """
        启用扫描器
        """
        scanner.status = VtScanner.Status.ENABLE.value
        scanner.save(update_fields=['status'])
        return scanner

    @staticmethod
    def disable_scanner(scanner: VtScanner):
        """
        停用扫描器
        """
        scanner.status = VtScanner.Status.DISABLE.value
        scanner.save(update_fields=['status'])
        return scanner

    @staticmethod
    def delete_scanner(scanner: VtScanner):
        """
        删除扫描器
        """
        scanner.status = VtScanner.Status.DELETED
        scanner.save(update_fields=['status'])
        return scanner

    @staticmethod
    def get_scanner(name: str):
        """
        获取扫描器
        """
        scanner = VtScanner.objects.filter(name=name).first()
        if scanner is None:
            raise errors.NotFound(message=_(f'{name}扫描器不存在。'))
        return scanner


class URLHTTPValidator(URLValidator):
    schemes = ["http", "https"]
