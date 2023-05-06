from datetime import datetime, timedelta, date
from functools import wraps
from decimal import Decimal

from django.utils import timezone
from django.db import close_old_connections

from servers.models import Server, ServerArchive, ServerBase
from metering.models import MeteringServer, MeteringObjectStorage
from order.managers import PriceManager
from utils.decimal_utils import quantize_10_2
from utils.model import PayType
from vo.models import VirtualOrganization
from users.models import UserProfile
from storage.models import Bucket
from storage.adapter import inputs
from storage import request
from core import errors


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
            end_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)  # 计量结束时间
            start_datetime = end_datetime - timedelta(days=1)  # 计量开始时间

        self.end_datetime = end_datetime
        self.start_datetime = start_datetime
        self.raise_exeption = raise_exeption
        self.price_mgr = PriceManager()
        self._metering_server_count = 0  # 计量云主机计数
        self._metering_archieve_count = 0  # 计量归档云主机计数
        self._new_count = 0  # 新产生计量账单计数

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

                # 多个creation_time相同数据时，会查询获取到多个数据（计量过也会重复查询到）
                if servers[len(servers) - 1].id == last_id:
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
            if server.creation_time < server.start_time:  # 计量可能要包含server配置修改记录部分
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
        end = min(archive.deleted_time, self.end_datetime)  # server计费结束时间
        if archive.start_time <= self.start_datetime:
            start = self.start_datetime
        elif archive.start_time < self.end_datetime:
            start = archive.start_time
            if archive.creation_time < archive.start_time:  # 计量可能要包含server配置修改记录部分
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
        ram_gb_hours = server.ram_gib * hours
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

        queryset = Server.objects.filter(**lookups).order_by('creation_time', 'id')
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

        return ServerArchive.objects.filter(**lookups).order_by('creation_time', 'id')

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
        if _metering.pay_type == PayType.POSTPAID.value:
            _metering.trade_amount = _metering.original_amount
        else:
            _metering.trade_amount = Decimal('0')

        if auto_commit:
            _metering.save(update_fields=['original_amount', 'trade_amount'])

        return _metering


class StorageMeasure:
    """
    对象存储计量
    """

    def __init__(self, metering_data: date = None, raise_exception: bool = False):
        """
        :param metering_data: 指定计量日期
        :param raise_exception: True 发生错误直接抛出
        """
        if metering_data:
            start_datetime = timezone.now().replace(
                year=metering_data.year, month=metering_data.month, day=metering_data.day,
                hour=0, minute=0, second=0, microsecond=0)
            end_datetime = start_datetime + timedelta(days=1)
        else:
            # 计量当前时间的前一天的资源使用量
            end_datetime = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            start_datetime = end_datetime - timedelta(days=1)

        self.end_datatime = end_datetime
        self.start_datetime = start_datetime
        self.raise_exception = raise_exception
        self.price_mgr = PriceManager()
        self._metering_bucket_count = 0  # 计量的桶的数目 这里暂时不用考虑归档的桶
        self._new_count = 0  # 新产生的计量账单的数目
        self._error_http_count = 0   # 请求桶容量的错误的数目

    def run(self, raise_exception: bool = None):
        print(f'Storage Metering start, {self.start_datetime} - {self.end_datatime}')
        if self.end_datatime >= timezone.now():
            print('Exit, metering time invalid')
            return

        if raise_exception is not None:
            self.raise_exception = raise_exception

        self.metering_loop()

        print(f'Metering {self._metering_bucket_count} buckets, new produce {self._new_count} metering bill，'
              f'Error http request about bucket {self._error_http_count}.')

    def metering_loop(self):
        last_creation_time = None
        last_id = ''
        while True:
            try:
                buckets = self.get_buckets(
                    gte_creation_time=last_creation_time, end_datetime=self.end_datatime)
                if len(buckets) == 0:
                    break
                # 多个creation_time 的数据相同时，会查询到多个数据 (计量过的也会重复查询到)
                if buckets[len(buckets) - 1].id == last_id:
                    break
                for b in buckets:
                    if b.id == last_id:
                        continue
                    self.metering_bucket(b)
                    last_creation_time = b.creation_time
                    last_id = b.id
            except Exception as e:
                print(str(e))
                if self.raise_exception:
                    raise e

    def metering_bucket(self, obj):
        self._metering_bucket_count += 1
        return self.metering_one_bucket(bucket=obj)

    def metering_one_bucket(self, bucket: Bucket):
        metering_date = self.start_datetime.date()
        metering = self.bucket_metering_exists(metering_date=metering_date, bucket_id=bucket.id)
        if metering is not None:
            return metering
        '''
        这里和云主机的区别在于 没有start_time 的字段
        需要统计的是 桶中的对象的size大小
        '''
        if bucket.creation_time <= self.start_datetime:
            hours = 24
        elif bucket.creation_time < self.end_datatime:
            hours = self.delta_hours(end=self.end_datatime, start=bucket.creation_time)
        else:
            return None

        try:
            storage_size_byte = self.get_bucket_metering_size(bucket=bucket)
        except Exception as exc:
            self._error_http_count += 1
            print(f'Error stats bucket({bucket.id}, {bucket.name}) request, {str(exc)}')
            return None

        if storage_size_byte is None:
            return None

        storage_size_gib = storage_size_byte / 1024**3
        metering = self.save_bucket_metering_record(
            bucket=bucket, storage_gib_hours=storage_size_gib * hours, storage_byte=storage_size_byte
        )
        return metering

    def save_bucket_metering_record(self, bucket: Bucket, storage_gib_hours, storage_byte: int):
        return self.save_metering_record(
            service=bucket.service, user_id=bucket.user_id, storage_bucket_id=bucket.id,
            bucket_name=bucket.name, creation_time=bucket.creation_time, storage_gib_hours=storage_gib_hours,
            storage_byte=storage_byte
        )

    def save_metering_record(
            self, service, user_id, storage_bucket_id, bucket_name, creation_time, storage_gib_hours,
            storage_byte: int
    ):
        """
           创建当前日期的桶的计量记录
           :return MeteringObjectStorage
        """
        metering_date = self.start_datetime.date()
        username = UserProfile.objects.filter(id=user_id).first()
        metering = MeteringObjectStorage(
            service=service,
            user_id=user_id,
            username=username,
            storage_bucket_id=storage_bucket_id,
            bucket_name=bucket_name,
            date=metering_date,
            creation_time=creation_time,
            storage=storage_gib_hours,
            daily_statement_id='',
            storage_byte=storage_byte
        )
        self.metering_bill_amount(_metering=metering, auto_commit=False)

        try:
            metering.save(force_insert=True)
            self._new_count += 1
        except Exception as e:
            _metering = self.bucket_metering_exists(bucket_id=storage_bucket_id, metering_date=metering_date)
            if _metering is None:
                raise e
            if _metering.original_amount != metering.original_amount:
                self.metering_bill_amount(_metering=_metering, auto_commit=True)
            metering = _metering

        return metering

    @staticmethod
    def delta_hours(end, start):
        delta = end - start
        seconds = delta.total_seconds()
        seconds = max(seconds, 0)
        return seconds / 3600

    def metering_bill_amount(self, _metering: MeteringObjectStorage, auto_commit: bool = True):
        """
        计算资源使用量的账单金额
        """
        price = self.price_mgr.enforce_price()
        _metering.original_amount = self.price_mgr.calculate_bucket_amounts(
            price=price, storage_gib_hours=_metering.storage)
        _metering.trade_amount = _metering.original_amount

        if auto_commit:
            _metering.save(update_fields=['original_amount', 'trade_amount'])

        return _metering

    @staticmethod
    def get_bucket_metering_size(bucket: Bucket):
        """
        :return:
            None    # 桶记录和对象存储服务中桶数据可能不一致, 不计费
            int     # ok
        """
        bucket_name = bucket.name
        bucket_service = bucket.service
        params = inputs.BucketStatsInput(bucket_name=bucket_name)
        try:
            r = request.request_service(service=bucket_service, method='bucket_stats', params=params)
        except errors.APIException as exc:
            if exc.code in ['Adapter.NoSuchBucket', 'Adapter.AuthenticationFailed', 'Adapter.AccessDenied']:
                raise exc
            else:
                r = request.request_service(service=bucket_service, method='bucket_stats', params=params)

        # 桶记录和对象存储服务中桶数据可能不一致
        if r.username and r.username != bucket.user.username:
            return None

        try:
            bucket.storage_size = r.bucket_size_byte
            bucket.object_count = r.objects_count
            bucket.stats_time = r.stats_time or timezone.now()
            bucket.save(update_fields=['storage_size', 'object_count', 'stats_time'])
        except Exception as exc:
            pass

        return r.bucket_size_byte

    @wrap_close_old_connections
    def get_buckets(self, gte_creation_time, end_datetime, limit: int = 100):
        queryset = self.get_buckets_queryset(gte_creation_time=gte_creation_time, end_datetime=end_datetime)
        return queryset[0:limit]

    @staticmethod
    def bucket_metering_exists(bucket_id, metering_date: date):
        return MeteringObjectStorage.objects.filter(date=metering_date, storage_bucket_id=bucket_id).first()

    @staticmethod
    def get_buckets_queryset(end_datetime, gte_creation_time=None):
        """
        查询bucket的集合， 按照创建的时间 以及 id 正序排序
        :param end_datetime: 计量日结束的时间点
        :param gte_creation_time: 大于等于给定的创建时间，用于断点查询
        """
        lookups = {}
        if gte_creation_time is not None:
            lookups['creation_time__gte'] = gte_creation_time

        queryset = Bucket.objects.select_related('service').filter(**lookups).order_by('creation_time', 'id')
        return queryset
