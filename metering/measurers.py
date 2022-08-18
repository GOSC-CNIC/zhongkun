from datetime import datetime, timedelta, date
from functools import wraps

from django.utils import timezone
from django.db import close_old_connections

from servers.models import Server, ServerArchive, ServerBase
from metering.models import MeteringServer, PaymentStatus
from order.managers import PriceManager
from utils.decimal_utils import quantize_10_2
from vo.models import VirtualOrganization
from users.models import UserProfile


def wrap_close_old_connections(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        close_old_connections()
        return func(*args, **kwargs)

    return wrapper


class ServerMeasurer:
    """
    计量器
    """
    def __init__(self, metering_date: date = None, raise_exeption: bool = False):
        """
        :param metering_date: 指定计量日期
        :param raise_exeption: True(发生错误直接抛出退出)
        """
        if metering_date:
            start_datetime = timezone.now().replace(
                year=metering_date.year, month=metering_date.month, day=metering_date.day,
                hour=0, minute=0, second=0, microsecond=0)
            end_datetime = start_datetime + timedelta(days=1)
        else:
            # 计量当前时间前一天的资源使用量
            end_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)    # 计量结束时间
            start_datetime = end_datetime - timedelta(days=1)  # 计量开始时间

        self.end_datetime = end_datetime
        self.start_datetime = start_datetime
        self.raise_exeption = raise_exeption
        self.price_mgr = PriceManager()
        self._metering_server_count = 0  # 计量云主机计数
        self._metering_archieve_count = 0  # 计量归档云主机计数
        self._new_count = 0      # 新产生计量账单计数

    def run(self, raise_exeption: bool = None):
        print(f'Metering start, {self.start_datetime} - {self.end_datetime}')
        if self.end_datetime >= timezone.now():
            print('Exit, metering time invalid.')
            return

        if raise_exeption is not None:
            self.raise_exeption = raise_exeption

        # 顺序先server后archive，因为数据库数据流向从server到archive
        self.metering_loop(loop_server=True)
        self.metering_loop(loop_server=False)
        print(f'Metering {self._metering_server_count} servers, {self._metering_archieve_count} archieves, '
              f'all {self._metering_archieve_count + self._metering_server_count}, '
              f'new produce {self._new_count} metering bill.')

    def metering_loop(self, loop_server):
        last_creatition_time = None
        last_id = ''
        while True:
            try:
                if loop_server:
                    servers = self.get_servers(
                        gte_creation_time=last_creatition_time, end_datetime=self.end_datetime)
                else:
                    servers = self.get_archives(
                        gte_creation_time=last_creatition_time, start_datetime=self.start_datetime)

                if len(servers) == 0:
                    break
                if len(servers) == 1 and servers[0].id == last_id:
                    break

                for s in servers:
                    if s.id == last_id:
                        continue

                    self.metering_server_or_archive(s)
                    last_creatition_time = s.creation_time
                    last_id = s.id
            except Exception as e:
                print(str(e))
                if self.raise_exeption:
                    raise e

    def metering_server_or_archive(self, obj):
        if isinstance(obj, Server):
            self._metering_server_count += 1
            return self.metering_one_server(server=obj)

        self._metering_archieve_count += 1
        return self.metering_one_archive(archive=obj)

    def metering_one_server(self, server: Server):
        metering_date = self.start_datetime.date()
        metering = self.server_metering_exists(metering_date=metering_date, server_id=server.id)
        if metering is not None:
            return metering

        need_rebuild = False
        # server计费开始时间 在计量日期之前，计量日期内server没有变化，计24h
        if server.start_time <= self.start_datetime:
            hours = 24
        # server计费开始时间 在计量日期之间
        elif server.start_time < self.end_datetime:
            hours = self.delta_hours(end=self.end_datetime, start=server.start_time)
            if server.creation_time < server.start_time:    # 计量可能要包含server配置修改记录部分
                need_rebuild = True
        else:
            return None

        ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours = self.get_server_metering_hours(server=server, hours=hours)
        if need_rebuild:
            ip_h, cpu_h, ram_h, disk_h = self.metering_one_server_rebuild_hours(
                server_id=server.id, server_start_time=server.start_time)
            ip_hours += ip_h
            cpu_hours += cpu_h
            ram_gb_hours += ram_h
            disk_gb_hours += disk_h

        metering = self.save_server_metering_record(
            server=server,
            ip_hours=ip_hours,
            cpu_hours=cpu_hours,
            ram_gb_hours=ram_gb_hours,
            disk_gb_hours=disk_gb_hours
        )
        return metering

    def metering_one_archive(self, archive: ServerArchive):
        metering_date = self.start_datetime.date()
        metering = self.server_metering_exists(metering_date=metering_date, server_id=archive.server_id)
        if metering is not None:
            return metering

        need_rebuild = False
        end = min(archive.deleted_time, self.end_datetime)      # server计费结束时间
        if archive.start_time <= self.start_datetime:
            start = self.start_datetime
        elif archive.start_time < self.end_datetime:
            start = archive.start_time
            if archive.creation_time < archive.start_time:    # 计量可能要包含server配置修改记录部分
                need_rebuild = True
        else:
            return None

        hours = self.delta_hours(end=end, start=start)
        ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours = self.get_server_metering_hours(server=archive, hours=hours)
        if need_rebuild:
            ip_h, cpu_h, ram_h, disk_h = self.metering_one_server_rebuild_hours(
                server_id=archive.server_id, server_start_time=archive.start_time)
            ip_hours += ip_h
            cpu_hours += cpu_h
            ram_gb_hours += ram_h
            disk_gb_hours += disk_h

        metering = self.save_archive_metering_record(
            archive=archive,
            ip_hours=ip_hours,
            cpu_hours=cpu_hours,
            ram_gb_hours=ram_gb_hours,
            disk_gb_hours=disk_gb_hours
        )
        return metering

    @staticmethod
    def delta_hours(end, start):
        delta = end - start
        seconds = delta.total_seconds()
        seconds = max(seconds, 0)
        return seconds / 3600

    def save_server_metering_record(self, server: Server, ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours):
        """
        创建server计量日期的资源使用量记录

        :return:
            MeteringServer()

        :raises: Exception
        """
        return self.save_metering_record(
            server_base=server, service_id=server.service_id, server_id=server.id,
            vo_id=server.vo_id, user_id=server.user_id,
            ip_hours=ip_hours, cpu_hours=cpu_hours, ram_gb_hours=ram_gb_hours, disk_gb_hours=disk_gb_hours
        )

    def save_archive_metering_record(self, archive: ServerArchive, ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours):
        """
        创建归档server计量日期的资源使用量记录

        :return:
            MeteringServer()

        :raises: Exception
        """
        return self.save_metering_record(
            server_base=archive, service_id=archive.service_id, server_id=archive.server_id,
            vo_id=archive.vo_id, user_id=archive.user_id,
            ip_hours=ip_hours, cpu_hours=cpu_hours, ram_gb_hours=ram_gb_hours, disk_gb_hours=disk_gb_hours
        )

    def save_metering_record(
            self, server_base: ServerBase,
            service_id, server_id, vo_id, user_id,
            ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours
    ):
        """
        创建server计量日期的资源使用量记录

        :return:
            MeteringServer()

        :raises: Exception
        """
        metering_date = self.start_datetime.date()
        metering = MeteringServer(
            service_id=service_id,
            server_id=server_id,
            date=metering_date,
            cpu_hours=cpu_hours,
            public_ip_hours=ip_hours,
            ram_hours=ram_gb_hours,
            disk_hours=disk_gb_hours,
            pay_type=server_base.pay_type,
            daily_statement_id=''
        )
        if server_base.belong_to_vo():
            metering.vo_id = vo_id
            metering.owner_type = MeteringServer.OwnerType.VO.value
            metering.user_id = ''
            vo = VirtualOrganization.objects.filter(id=vo_id).first()
            vo_name = vo.name if vo else ''
            metering.vo_name = vo_name
        else:
            metering.vo_id = ''
            metering.owner_type = MeteringServer.OwnerType.USER.value
            metering.user_id = user_id
            user = UserProfile.objects.filter(id=user_id).first()
            username = user.username if user else ''
            metering.username = username

        self.metering_bill_amount(_metering=metering, auto_commit=False)
        try:
            metering.save(force_insert=True)
            self._new_count += 1
        except Exception as e:
            _metering = self.server_metering_exists(metering_date=metering_date, server_id=server_id)
            if _metering is None:
                raise e
            if _metering.original_amount != metering.original_amount:
                self.metering_bill_amount(_metering=_metering, auto_commit=True)

            metering = _metering

        return metering

    def metering_one_server_rebuild_hours(self, server_id, server_start_time: datetime):
        """
        从计量日的开始时间 到 server start_time之前 这段时间内 可能存在server修改配置的记录 需要计量

        :return:
            ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours
        """
        ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours = 0, 0, 0, 0

        archives = ServerArchive.objects.filter(
            server_id=server_id, archive_type=ServerArchive.ArchiveType.REBUILD.value,
            start_time__lt=server_start_time, deleted_time__gt=self.start_datetime
        ).all()

        for archive in archives:
            start = max(self.start_datetime, archive.start_time)
            end = min(server_start_time, archive.deleted_time)
            hours = self.delta_hours(end=end, start=start)
            hours = min(hours, 24)
            ip_h, cpu_h, ram_h, disk_h = self.get_server_metering_hours(server=archive, hours=hours)
            ip_hours += ip_h
            cpu_hours += cpu_h
            ram_gb_hours += ram_h
            disk_gb_hours += disk_h

        return ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours

    @staticmethod
    def get_server_metering_hours(server: ServerBase, hours: float):
        if server.public_ip:
            ip_hours = hours
        else:
            ip_hours = 0

        cpu_hours = server.vcpus * hours
        ram_gb_hours = server.ram / 1024 * hours
        disk_gb_hours = server.disk_size * hours
        return ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours

    @staticmethod
    def get_servers_queryset(end_datetime, gte_creation_time=None):
        """
        查询server查询集, 按创建时间正序排序

        :param end_datetime: 计量日结束时间点
        :param gte_creation_time: 大于等于创建时间，用于断点续查
        """
        lookups = {
            'start_time__lt': end_datetime,
            'task_status': Server.TASK_CREATED_OK
        }
        if gte_creation_time is not None:
            lookups['creation_time__gte'] = gte_creation_time

        queryset = Server.objects.filter(**lookups).order_by('creation_time')
        return queryset

    @wrap_close_old_connections
    def get_servers(self, gte_creation_time, end_datetime, limit: int = 100):
        queryset = self.get_servers_queryset(gte_creation_time=gte_creation_time, end_datetime=end_datetime)
        return queryset[0:limit]

    @staticmethod
    def get_archives_queryset(start_datetime, gte_creation_time=None):
        """
        查询归档的server查询集, 按创建时间正序排序

        :param start_datetime: 计量日开始时间点
        :param gte_creation_time: 大于等于创建时间，用于断点续查
        """
        lookups = {
            'deleted_time__gt': start_datetime,
            'task_status': Server.TASK_CREATED_OK,
            'archive_type': ServerArchive.ArchiveType.ARCHIVE.value
        }
        if gte_creation_time is not None:
            lookups['creation_time__gte'] = gte_creation_time

        return ServerArchive.objects.filter(**lookups).order_by('creation_time')

    @wrap_close_old_connections
    def get_archives(self, start_datetime, gte_creation_time=None, limit: int = 100):
        queryset = self.get_archives_queryset(
            start_datetime=start_datetime,
            gte_creation_time=gte_creation_time
        )
        return queryset[0:limit]

    @staticmethod
    def server_metering_exists(server_id, metering_date: date):
        return MeteringServer.objects.filter(date=metering_date, server_id=server_id).first()

    def metering_bill_amount(self, _metering: MeteringServer, auto_commit: bool = True):
        """
        计算资源使用量的账单金额
        """
        amount = self.price_mgr.describe_server_metering_price(
            ram_gib_hours=_metering.ram_hours,
            cpu_hours=_metering.cpu_hours,
            disk_gib_hours=_metering.disk_hours,
            public_ip_hours=_metering.public_ip_hours
        )
        _metering.original_amount = quantize_10_2(amount)
        if auto_commit:
            _metering.save(update_fields=['original_amount'])

        return _metering
