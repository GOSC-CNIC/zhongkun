import time
from datetime import datetime, timedelta, date
from functools import wraps
from decimal import Decimal

from django.utils import timezone
from django.db import close_old_connections

from servers.models import Server, ServerArchive, ServerBase, Disk, DiskChangeLog
from metering.models import MeteringServer, MeteringObjectStorage, MeteringDisk, MeteringMonitorWebsite
from monitor.models import MonitorWebsite, MonitorWebsiteRecord, MonitorWebsiteBase
from order.managers import PriceManager
from utils.decimal_utils import quantize_10_2
from utils.model import PayType, OwnerType
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


class BaseMeasurer:
    """
    计量器
    """

    def __init__(self, metering_date: date = None, raise_exception: bool = False):
        """
        :param metering_date: 指定计量日期
        :param raise_exception: True(发生错误直接抛出退出)
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
        self.raise_exception = raise_exception


class ServerMeasurer(BaseMeasurer):
    """
    计量器
    """

    def __init__(self, metering_date: date = None, raise_exception: bool = False):
        """
        :param metering_date: 指定计量日期
        :param raise_exception: True(发生错误直接抛出退出)
        """
        super().__init__(metering_date=metering_date, raise_exception=raise_exception)
        self.price_mgr = PriceManager()
        self._metering_server_count = 0  # 计量云主机计数
        self._metering_archieve_count = 0  # 计量归档云主机计数
        self._new_count = 0  # 新产生计量账单计数

    def run(self, raise_exception: bool = None):
        print(f'Server metering start, {self.start_datetime} - {self.end_datetime}')
        if self.end_datetime >= timezone.now():
            print('Exit, metering time invalid.')
            return

        if raise_exception is not None:
            self.raise_exception = raise_exception

        # 顺序先server后archive，因为数据库数据流向从server到archive
        self.metering_loop(loop_server=True)
        self.metering_loop(loop_server=False)
        print(f'Metering {self._metering_server_count} servers, {self._metering_archieve_count} archieves, '
              f'all {self._metering_archieve_count + self._metering_server_count}, '
              f'new produce {self._new_count} metering bill.')

    def metering_loop(self, loop_server):
        last_creatition_time = None
        last_id = ''
        continuous_error_count = 0  # 连续错误计数
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

                continuous_error_count = 0
            except Exception as e:
                print(str(e))
                if self.raise_exception:
                    raise e

                continuous_error_count += 1
                if continuous_error_count > 100:    # 连续错误次数后报错退出
                    raise e

                time.sleep(continuous_error_count / 100)  # 10ms - 1000ms

    def metering_server_or_archive(self, obj):
        if obj.creation_time >= self.end_datetime:
            return None

        metering_date = self.start_datetime.date()
        if isinstance(obj, Server):
            server_id = obj.id
            meter_end = self.end_datetime
            self._metering_server_count += 1
        elif isinstance(obj, ServerArchive):
            server_id = obj.server_id
            meter_end = min(obj.deleted_time, self.end_datetime)  # server计费结束时间
            self._metering_archieve_count += 1
        else:
            return None

        metering = self.server_metering_exists(metering_date=metering_date, server_id=server_id)
        if metering is not None:
            return metering

        return self._metering_one_server_or_archive(
            server_or_archive=obj, server_id=server_id, server_start_time=obj.start_time, server_meter_end=meter_end)

    def _metering_one_server_or_archive(
            self, server_or_archive: ServerBase, server_id: str,
            server_start_time: datetime, server_meter_end: datetime
    ):
        hours, need_other = self._server_delta_hours(server_or_archive=server_or_archive, meter_end=server_meter_end)
        ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours = self.get_server_metering_hours(
            server=server_or_archive, hours=hours)
        if need_other:
            ip_h, cpu_h, ram_h, disk_h = self.metering_one_server_rebuild_hours(
                server_id=server_id, server_start_time=server_start_time)
            ip_hours += ip_h
            cpu_hours += cpu_h
            ram_gb_hours += ram_h
            disk_gb_hours += disk_h

            if server_or_archive.pay_type == PayType.PREPAID.value:
                # 可能按量付费转的包年包月，需要计量可能的按量付费用量
                ip_h, cpu_h, ram_h, disk_h = self.metering_one_post2prepaid_server_hours(
                    server_id=server_id, server_start_time=server_start_time
                )
                ip_hours += ip_h
                cpu_hours += cpu_h
                ram_gb_hours += ram_h
                disk_gb_hours += disk_h

                trade_amount = self.price_mgr.describe_server_metering_price(
                    ram_gib_hours=ram_h,
                    cpu_hours=cpu_h,
                    disk_gib_hours=disk_h,
                    public_ip_hours=ip_h
                )
            else:
                trade_amount = None
        else:
            trade_amount = None

        metering = self.save_server_or_archive_metering_record(
            server_or_archive=server_or_archive,
            ip_hours=ip_hours,
            cpu_hours=cpu_hours,
            ram_gb_hours=ram_gb_hours,
            disk_gb_hours=disk_gb_hours,
            trade_amount=trade_amount
        )
        return metering

    def _server_delta_hours(self, server_or_archive: ServerBase, meter_end: datetime):
        """
        :param server_or_archive: Server or Archive
        :param meter_end:   server计量截止时间
        """
        need_other = False  # 是否需要计量其他可能存在的用量
        if server_or_archive.start_time <= self.start_datetime:
            start = self.start_datetime
        elif server_or_archive.start_time < self.end_datetime:
            start = server_or_archive.start_time
            if server_or_archive.creation_time < server_or_archive.start_time:  # 可能要包含server配置、付费方式修改记录部分
                need_other = True
        else:
            start = self.end_datetime
            need_other = True

        hours = self.delta_hours(end=meter_end, start=start)
        return hours, need_other

    @staticmethod
    def delta_hours(end, start):
        delta = end - start
        seconds = delta.total_seconds()
        seconds = max(seconds, 0)
        return seconds / 3600

    def save_server_or_archive_metering_record(
            self, server_or_archive: ServerBase, ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours, trade_amount: Decimal
    ):
        """
        创建server或归档server计量日期的资源使用量记录

        :return:
            MeteringServer()

        :raises: Exception
        """
        if isinstance(server_or_archive, ServerArchive):
            server_id = server_or_archive.server_id
        else:
            server_id = server_or_archive.id

        return self.save_metering_record(
            server_base=server_or_archive, service_id=server_or_archive.service_id, server_id=server_id,
            vo_id=server_or_archive.vo_id, user_id=server_or_archive.user_id,
            ip_hours=ip_hours, cpu_hours=cpu_hours, ram_gb_hours=ram_gb_hours, disk_gb_hours=disk_gb_hours,
            trade_amount=trade_amount
        )

    def save_metering_record(
            self, server_base: ServerBase,
            service_id, server_id, vo_id, user_id,
            ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours,
            trade_amount: Decimal
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

        self.metering_bill_amount(_metering=metering, auto_commit=False, trade_amount=trade_amount)
        try:
            metering.save(force_insert=True)
            self._new_count += 1
        except Exception as e:
            _metering = self.server_metering_exists(metering_date=metering_date, server_id=server_id)
            if _metering is None:
                raise e
            if _metering.original_amount != metering.original_amount:
                self.metering_bill_amount(_metering=_metering, auto_commit=True, trade_amount=trade_amount)

            metering = _metering

        return metering

    def metering_one_server_change_type_hours(self, server_id, server_start_time: datetime, _type: str):
        """
        从计量日的开始时间 到 min(server_start_time, self.end_datetime)之前 这段时间内 可能存在server变更的记录 需要计量

        :return:
            ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours
        """
        ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours = 0, 0, 0, 0

        meter_end_time = min(server_start_time, self.end_datetime)
        archives = ServerArchive.objects.filter(
            server_id=server_id, archive_type=_type,
            start_time__lt=meter_end_time, deleted_time__gt=self.start_datetime
        ).all()

        for archive in archives:
            start = max(self.start_datetime, archive.start_time)
            end = min(meter_end_time, archive.deleted_time)
            hours = self.delta_hours(end=end, start=start)
            hours = min(hours, 24)
            ip_h, cpu_h, ram_h, disk_h = self.get_server_metering_hours(server=archive, hours=hours)
            ip_hours += ip_h
            cpu_hours += cpu_h
            ram_gb_hours += ram_h
            disk_gb_hours += disk_h

        return ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours

    def metering_one_server_rebuild_hours(self, server_id, server_start_time: datetime):
        """
        从计量日的开始时间 到 server start_time之前 这段时间内 可能存在server修改配置的记录 需要计量

        :return:
            ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours
        """
        return self.metering_one_server_change_type_hours(
            server_id=server_id, server_start_time=server_start_time, _type=ServerArchive.ArchiveType.REBUILD.value
        )

    def metering_one_post2prepaid_server_hours(self, server_id, server_start_time: datetime):
        """
        从计量日的开始时间 到 server start_time之前 这段时间内 可能存在server按量付费转包年包月的记录
        计费方式转变前的按量计费需要计量

        :return:
            ip_hours, cpu_hours, ram_gb_hours, disk_gb_hours
        """
        return self.metering_one_server_change_type_hours(
            server_id=server_id, server_start_time=server_start_time, _type=ServerArchive.ArchiveType.POST2PRE.value
        )

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
        * 创建时间在计量周期结束时间之前的都可能需要计量
        * 不能用 start_time 做为查询条件，start_time是根据资源变更变动的，可能不在计量周期内，但是可能在变更记录有资源用量需要计量
        :param end_datetime: 计量日结束时间点
        :param gte_creation_time: 大于等于创建时间，用于断点续查
        """
        lookups = {
            'creation_time__lt': end_datetime,
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
        * 删除时间在计量周期之内的server
        * 不能用 start_time 做为查询条件，start_time是根据资源变更变动的，可能不在计量周期内，但是可能在变更记录有资源用量需要计量
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

    def metering_bill_amount(self, _metering: MeteringServer, auto_commit: bool = True, trade_amount: Decimal = None):
        """
        计算资源使用量的账单金额
        :trade_amount: 应付金额，如果非指定就按付费方式算
        """
        amount = self.price_mgr.describe_server_metering_price(
            ram_gib_hours=_metering.ram_hours,
            cpu_hours=_metering.cpu_hours,
            disk_gib_hours=_metering.disk_hours,
            public_ip_hours=_metering.public_ip_hours
        )
        _metering.original_amount = quantize_10_2(amount)
        if trade_amount is None:
            if _metering.pay_type == PayType.POSTPAID.value:
                _metering.trade_amount = _metering.original_amount
            else:
                _metering.trade_amount = Decimal('0')
        else:
            _metering.trade_amount = quantize_10_2(trade_amount)

        if auto_commit:
            _metering.save(update_fields=['original_amount', 'trade_amount'])

        return _metering


class StorageMeasurer(BaseMeasurer):
    """
    对象存储计量
    """

    def __init__(self, metering_date: date = None, raise_exception: bool = False):
        """
        :param metering_date: 指定计量日期
        :param raise_exception: True 发生错误直接抛出
        """
        super().__init__(metering_date=metering_date, raise_exception=raise_exception)
        self.price_mgr = PriceManager()
        self._metering_bucket_count = 0  # 计量的桶的数目 这里暂时不用考虑归档的桶
        self._new_count = 0  # 新产生的计量账单的数目
        self._error_http_count = 0   # 请求桶容量的错误的数目

    def run(self, raise_exception: bool = None):
        print(f'Storage Metering start, {self.start_datetime} - {self.end_datetime}')
        if self.end_datetime >= timezone.now():
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
        continuous_error_count = 0
        while True:
            try:
                buckets = self.get_buckets(gte_creation_time=last_creation_time)
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

                continuous_error_count = 0
            except Exception as e:
                print(str(e))
                if self.raise_exception:
                    raise e

                continuous_error_count += 1
                if continuous_error_count > 100:  # 连续错误次数后报错退出
                    raise e

                time.sleep(continuous_error_count / 100)  # 10ms - 1000ms

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
        elif bucket.creation_time < self.end_datetime:
            hours = self.delta_hours(end=self.end_datetime, start=bucket.creation_time)
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
            bucket=bucket, storage_gib_hours=storage_size_gib * hours, storage_byte=storage_size_byte, hours=hours
        )
        return metering

    def save_bucket_metering_record(self, bucket: Bucket, storage_gib_hours, storage_byte: int, hours: float):
        return self.save_metering_record(
            service=bucket.service, user_id=bucket.user_id, storage_bucket_id=bucket.id,
            bucket_name=bucket.name, creation_time=bucket.creation_time, storage_gib_hours=storage_gib_hours,
            storage_byte=storage_byte, hours=hours
        )

    def save_metering_record(
            self, service, user_id, storage_bucket_id, bucket_name, creation_time, storage_gib_hours,
            storage_byte: int, hours: float
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
        self.metering_bill_amount(_metering=metering, hours=hours, auto_commit=False)

        try:
            metering.save(force_insert=True)
            self._new_count += 1
        except Exception as e:
            _metering = self.bucket_metering_exists(bucket_id=storage_bucket_id, metering_date=metering_date)
            if _metering is None:
                raise e
            if _metering.original_amount != metering.original_amount:
                self.metering_bill_amount(_metering=_metering, hours=hours, auto_commit=True)
            metering = _metering

        return metering

    @staticmethod
    def delta_hours(end, start):
        delta = end - start
        seconds = delta.total_seconds()
        seconds = max(seconds, 0)
        return seconds / 3600

    def metering_bill_amount(self, _metering: MeteringObjectStorage, hours: float, auto_commit: bool = True):
        """
        计算资源使用量的账单金额
        """
        price = self.price_mgr.enforce_price()
        _metering.original_amount = self.price_mgr.calculate_bucket_amounts(
            price=price, storage_gib_hours=_metering.storage, hours=hours)
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
    def get_buckets(self, gte_creation_time, limit: int = 100):
        queryset = self.get_buckets_queryset(gte_creation_time=gte_creation_time)
        return queryset[0:limit]

    @staticmethod
    def bucket_metering_exists(bucket_id, metering_date: date):
        return MeteringObjectStorage.objects.filter(date=metering_date, storage_bucket_id=bucket_id).first()

    @staticmethod
    def get_buckets_queryset(gte_creation_time=None):
        """
        查询bucket的集合， 按照创建的时间 以及 id 正序排序
        :param gte_creation_time: 大于等于给定的创建时间，用于断点查询
        """
        lookups = {}
        if gte_creation_time is not None:
            lookups['creation_time__gte'] = gte_creation_time

        queryset = Bucket.objects.select_related('service').filter(**lookups).order_by('creation_time', 'id')
        return queryset


class DiskMeasurer(BaseMeasurer):
    def __init__(self, metering_date: date = None, raise_exception: bool = False):
        """
        :param metering_date: 指定计量日期
        :param raise_exception: True(发生错误直接抛出退出)
        """
        super().__init__(metering_date=metering_date, raise_exception=raise_exception)
        self.price_mgr = PriceManager()
        self._metering_normal_disk_count = 0  # 计量正常云硬盘计数
        self._metering_deleted_disk_count = 0  # 计量已删除云硬盘计数
        self._new_count = 0  # 新产生计量账单计数

    def run(self, raise_exception: bool = None):
        print(f'Disk metering start, {self.start_datetime} - {self.end_datetime}')
        if self.end_datetime >= timezone.now():
            print('Exit, metering time invalid.')
            return

        if raise_exception is not None:
            self.raise_exception = raise_exception

        self.loop_normal_disks()
        self.loop_deleted_disks()
        print(f'Metering {self._metering_normal_disk_count} normal disks, '
              f'{self._metering_deleted_disk_count} deleted disks, '
              f'all {self._metering_normal_disk_count + self._metering_deleted_disk_count}, '
              f'new produce {self._new_count} metering bill.')

    def loop_normal_disks(self):
        self._metering_loop(loop_normal_disk=True)

    def loop_deleted_disks(self):
        self._metering_loop(loop_normal_disk=False)

    def _metering_loop(self, loop_normal_disk=False):
        last_creatition_time = None
        last_id = ''
        continuous_error_count = 0
        while True:
            try:
                if loop_normal_disk:
                    disks = self.get_normal_disks(
                        gte_creation_time=last_creatition_time, end_datetime=self.end_datetime)
                else:
                    disks = self.get_deleted_disks(
                        gte_creation_time=last_creatition_time, start_datetime=self.start_datetime)

                if len(disks) == 0:
                    break

                # 多个creation_time相同数据时，会查询获取到多个数据（计量过也会重复查询到）
                if disks[len(disks) - 1].id == last_id:
                    break

                for dk in disks:
                    if dk.id == last_id:
                        continue

                    self.metering_disk(dk)
                    last_creatition_time = dk.creation_time
                    last_id = dk.id

                continuous_error_count = 0
            except Exception as e:
                print(str(e))
                if self.raise_exception:
                    raise e

                continuous_error_count += 1
                if continuous_error_count > 100:  # 连续错误次数后报错退出
                    raise e

                time.sleep(continuous_error_count / 100)  # 10ms - 1000ms

    def metering_disk(self, disk: Disk):
        if disk.creation_time >= self.end_datetime:
            return None

        if disk.deleted:
            self._metering_deleted_disk_count += 1
            meter_end = min(disk.deleted_time, self.end_datetime)  # disk计费结束时间
        else:
            self._metering_normal_disk_count += 1
            meter_end = self.end_datetime

        disk_id = disk.id
        metering_date = self.start_datetime.date()
        metering = self.disk_metering_exists(metering_date=metering_date, disk_id=disk_id)
        if metering is not None:
            return metering

        delta_hours, need_other = self._disk_delta_hours(disk=disk, meter_end=meter_end)
        size_gib_hours = disk.size * delta_hours
        original_amount = self.calculate_original_amount(size_gib_hours=size_gib_hours)
        if disk.pay_type == PayType.PREPAID.value:
            trade_amount = Decimal('0.00')
        else:
            trade_amount = original_amount

        if need_other:
            post2pre_hours = self.metering_one_disk_post2pre_hours(disk_id=disk_id, disk_start_time=disk.start_time)
            size_gib_hours += post2pre_hours

            must_pay_amount = self.calculate_original_amount(size_gib_hours=post2pre_hours)
            original_amount += must_pay_amount
            trade_amount += must_pay_amount

        metering = self.save_disk_metering_record(
            disk=disk, size_gib_hours=size_gib_hours, original_amount=original_amount, trade_amount=trade_amount
        )
        return metering

    def _disk_delta_hours(self, disk: Disk, meter_end: datetime):
        need_other = False  # 是否需要计量其他可能存在的用量
        # disk计费开始时间 在计量日期之前，从计量周期起始时间开始计
        if disk.start_time <= self.start_datetime:
            start = self.start_datetime
        # disk计费开始时间 在计量日期之间
        elif disk.start_time < self.end_datetime:
            start = disk.start_time
            if disk.creation_time < disk.start_time:
                need_other = True
        else:
            start = self.end_datetime
            need_other = True

        hours = self.delta_hours(end=meter_end, start=start)
        return hours, need_other

    @staticmethod
    def delta_hours(end, start):
        delta = end - start
        seconds = delta.total_seconds()
        seconds = max(seconds, 0)
        return seconds / 3600

    def save_disk_metering_record(
            self, disk: Disk, size_gib_hours: float, original_amount: Decimal, trade_amount: Decimal) -> MeteringDisk:
        """
        创建disk计量日期的资源使用量记录

        :raises: Exception
        """
        metering_date = self.start_datetime.date()
        metering = MeteringDisk(
            service_id=disk.service_id,
            disk_id=disk.id,
            date=metering_date,
            size_hours=size_gib_hours,
            pay_type=disk.pay_type,
            daily_statement_id='',
            original_amount=original_amount,
            trade_amount=trade_amount
        )
        if disk.belong_to_vo():
            metering.vo_id = disk.vo_id
            metering.owner_type = OwnerType.VO.value
            metering.user_id = ''
            vo = VirtualOrganization.objects.filter(id=disk.vo_id).first()
            vo_name = vo.name if vo else ''
            metering.vo_name = vo_name
        else:
            metering.vo_id = ''
            metering.owner_type = OwnerType.USER.value
            metering.user_id = disk.user_id
            user = UserProfile.objects.filter(id=disk.user_id).first()
            username = user.username if user else ''
            metering.username = username

        try:
            metering.save(force_insert=True)
            self._new_count += 1
        except Exception as e:
            _metering = self.disk_metering_exists(metering_date=metering_date, disk_id=disk.id)
            if _metering is None:
                raise e

            metering = _metering

        return metering

    @staticmethod
    def get_normal_disk_queryset(end_datetime, gte_creation_time=None):
        """
        查询正常的disk查询集, 按创建时间正序排序

        * 不能用 start_time 做为查询条件，start_time是根据资源变更变动的，可能不在计量周期内，但是可能在变更记录有资源用量需要计量
        :param end_datetime: 计量日结束时间点
        :param gte_creation_time: 大于等于创建时间，用于断点续查
        """
        lookups = {
            'creation_time__lt': end_datetime,
            'task_status': Disk.TaskStatus.OK.value,
            'deleted': False
        }
        if gte_creation_time is not None:
            lookups['creation_time__gte'] = gte_creation_time

        queryset = Disk.objects.filter(**lookups).order_by('creation_time', 'id')
        return queryset

    @wrap_close_old_connections
    def get_normal_disks(self, gte_creation_time, end_datetime, limit: int = 100):
        queryset = self.get_normal_disk_queryset(gte_creation_time=gte_creation_time, end_datetime=end_datetime)
        return queryset[0:limit]

    @staticmethod
    def get_deleted_disk_queryset(start_datetime, gte_creation_time=None):
        """
        查询已删除的disk查询集, 按创建时间正序排序

        * 不能用 start_time 做为查询条件，start_time是根据资源变更变动的，可能不在计量周期内，但是可能在变更记录有资源用量需要计量
        :param start_datetime: 计量日开始时间点
        :param gte_creation_time: 大于等于创建时间，用于断点续查
        """
        lookups = {
            'deleted_time__gt': start_datetime,
            'task_status': Disk.TaskStatus.OK.value,
            'deleted': True
        }
        if gte_creation_time is not None:
            lookups['creation_time__gte'] = gte_creation_time

        return Disk.objects.filter(**lookups).order_by('creation_time', 'id')

    @wrap_close_old_connections
    def get_deleted_disks(self, start_datetime, gte_creation_time=None, limit: int = 100):
        queryset = self.get_deleted_disk_queryset(
            start_datetime=start_datetime,
            gte_creation_time=gte_creation_time
        )
        return queryset[0:limit]

    @staticmethod
    def disk_metering_exists(disk_id, metering_date: date):
        return MeteringDisk.objects.filter(date=metering_date, disk_id=disk_id).first()

    def calculate_original_amount(self, size_gib_hours: float):
        price = self.price_mgr.enforce_price()
        size_gib_days = size_gib_hours / 24
        amount = self.price_mgr.calculate_disk_amounts(
            price=price, size_gib_days=size_gib_days
        )
        return quantize_10_2(amount)

    def metering_one_disk_change_type_hours(self, disk_id, disk_start_time: datetime, _type: str) -> float:
        """
        从计量日的开始时间 到 min(disk_start_time, 计量日期截止时间)之前 这段时间内 可能存在disk变更的记录 需要计量

        :return:
            size_gb_hours
        """
        size_gb_hours = 0

        meter_end_time = min(disk_start_time, self.end_datetime)
        disk_changes = DiskChangeLog.objects.filter(
            disk_id=disk_id, log_type=_type,
            start_time__lt=meter_end_time, change_time__gt=self.start_datetime
        ).all()

        for disk in disk_changes:
            start = max(self.start_datetime, disk.start_time)
            end = min(meter_end_time, disk.change_time)
            hours = self.delta_hours(end=end, start=start)
            hours = min(hours, 24)
            size_gb_hours += disk.size * hours

        return size_gb_hours

    def metering_one_disk_post2pre_hours(self, disk_id, disk_start_time: datetime):
        """
        从计量日的开始时间 到 min(disk_start_time, 计量日期截止时间)之前 这段时间内 可能存在disk按量转包年包月变更的记录 需要计量

        :return:
            size_gb_hours
        """
        return self.metering_one_disk_change_type_hours(
            disk_id=disk_id, disk_start_time=disk_start_time, _type=DiskChangeLog.LogType.POST2PRE.value)


class MonitorWebsiteMeasurer(BaseMeasurer):
    def __init__(self, metering_date: date = None, raise_exception: bool = False):
        """
        :param metering_date: 指定计量日期
        :param raise_exception: True(发生错误直接抛出退出)
        """
        super().__init__(metering_date=metering_date, raise_exception=raise_exception)
        self.price_mgr = PriceManager()
        self._metering_normal_count = 0  # 计量正常计数
        self._metering_deleted_count = 0  # 计量已删除计数
        self._new_count = 0  # 新产生计量账单计数

    def run(self, raise_exception: bool = None):
        print(f'Monitor website metering start, {self.start_datetime} - {self.end_datetime}')
        if self.end_datetime >= timezone.now():
            print('Exit, metering time invalid.')
            return

        if raise_exception is not None:
            self.raise_exception = raise_exception

        self.loop_normal_websites()
        self.loop_deleted_websites()
        print(f'Metering {self._metering_normal_count} normal websites, '
              f'{self._metering_deleted_count} deleted websites, '
              f'all {self._metering_normal_count + self._metering_deleted_count}, '
              f'new produce {self._new_count} metering bill.')

    def loop_normal_websites(self):
        self._metering_loop(loop_normal_disk=True)

    def loop_deleted_websites(self):
        self._metering_loop(loop_normal_disk=False)

    def _metering_loop(self, loop_normal_disk=False):
        last_creatition_time = None
        last_id = ''
        continuous_error_count = 0
        while True:
            try:
                if loop_normal_disk:
                    websites = self.get_normal_websites(
                        gte_creation_time=last_creatition_time, end_datetime=self.end_datetime)
                else:
                    websites = self.get_deleted_websites(
                        gte_creation_time=last_creatition_time, start_datetime=self.start_datetime)

                if len(websites) == 0:
                    break

                # 多个creation_time相同数据时，会查询获取到多个数据（计量过也会重复查询到）
                if websites[len(websites) - 1].id == last_id:
                    break

                for site in websites:
                    if site.id == last_id:
                        continue

                    self.metering_site(site)
                    last_creatition_time = site.creation
                    last_id = site.id

                continuous_error_count = 0
            except Exception as e:
                if self.raise_exception:
                    raise e

                continuous_error_count += 1
                if continuous_error_count > 100:  # 连续错误次数后报错退出
                    raise e

                time.sleep(continuous_error_count / 100)  # 10ms - 1000ms

    def metering_site(self, site: MonitorWebsite):
        if site.creation >= self.end_datetime:
            return None

        if isinstance(site, MonitorWebsiteRecord):
            self._metering_deleted_count += 1
            meter_end = min(site.record_time, self.end_datetime)  # 计费结束时间
        else:
            self._metering_normal_count += 1
            meter_end = self.end_datetime

        site_id = site.id
        metering_date = self.start_datetime.date()
        metering = self.website_metering_exists(metering_date=metering_date, website_id=site_id)
        if metering is not None:
            return metering

        delta_hours = self._site_delta_hours(site=site, meter_end=meter_end)
        metering = self.save_site_metering_record(
            site=site, hours=delta_hours
        )
        return metering

    def _site_delta_hours(self, site: MonitorWebsite, meter_end: datetime):
        # 创建时间 在计量日期之前，从计量周期起始时间开始计
        if site.creation <= self.start_datetime:
            start = self.start_datetime
        # 创建时间 在计量日期之间
        elif site.creation < self.end_datetime:
            start = site.creation
        else:
            start = self.end_datetime

        hours = self.delta_hours(end=meter_end, start=start)
        return hours

    @staticmethod
    def delta_hours(end, start):
        delta = end - start
        seconds = delta.total_seconds()
        seconds = max(seconds, 0)
        return seconds / 3600

    def save_site_metering_record(self, site: MonitorWebsiteBase, hours: float):
        """
        创建计量日期的资源使用量记录

        :raises: Exception
        """
        metering_date = self.start_datetime.date()
        if isinstance(site, MonitorWebsiteRecord):
            user_id = site.user_id
            username = site.username
        elif isinstance(site, MonitorWebsite):
            user_id = site.user_id
            username = site.user.username
        else:
            return None

        metering = MeteringMonitorWebsite(
            website_id=site.id,
            website_name=site.name,
            date=metering_date,
            hours=hours,
            detection_count=0,
            tamper_resistant_count=1 if site.is_tamper_resistant else 0,
            security_count=0,
            user_id=user_id,
            username=username,
            creation_time=timezone.now()
        )

        original_amount = self.calculate_original_amount(hours=hours, mt=metering)
        metering.original_amount = original_amount
        metering.trade_amount = original_amount

        try:
            metering.save(force_insert=True)
            self._new_count += 1
        except Exception as e:
            _metering = self.website_metering_exists(metering_date=metering_date, website_id=site.id)
            if _metering is None:
                raise e

            metering = _metering

        return metering

    def calculate_original_amount(self, hours: float, mt: MeteringMonitorWebsite):
        price = self.price_mgr.enforce_price()
        amount = self.price_mgr.calculate_monitor_site_amounts(
            price=price, days=hours / 24, detection_count=mt.detection_count,
            tamper_count=mt.tamper_resistant_count, security_count=mt.security_count
        )
        return quantize_10_2(amount)

    @staticmethod
    def get_normal_website_queryset(end_datetime, gte_creation_time=None):
        """
        查询正常的website查询集, 按创建时间正序排序

        * 不能用 start_time 做为查询条件，start_time是根据资源变更变动的，可能不在计量周期内，但是可能在变更记录有资源用量需要计量
        :param end_datetime: 计量日结束时间点
        :param gte_creation_time: 大于等于创建时间，用于断点续查
        """
        lookups = {
            'creation__lt': end_datetime,
        }
        if gte_creation_time is not None:
            lookups['creation__gte'] = gte_creation_time

        queryset = MonitorWebsite.objects.filter(**lookups).order_by('creation', 'id')
        return queryset

    @wrap_close_old_connections
    def get_normal_websites(self, gte_creation_time, end_datetime, limit: int = 100):
        queryset = self.get_normal_website_queryset(gte_creation_time=gte_creation_time, end_datetime=end_datetime)
        return queryset[0:limit]

    @staticmethod
    def get_deleted_website_queryset(start_datetime, gte_creation_time=None):
        """
        查询已删除的website查询集, 按创建时间正序排序

        :param start_datetime: 计量日开始时间点
        :param gte_creation_time: 大于等于创建时间，用于断点续查
        """
        lookups = {
            'record_time__gt': start_datetime,
            'type': MonitorWebsiteRecord.RecordType.DELETED.value
        }
        if gte_creation_time is not None:
            lookups['creation__gte'] = gte_creation_time

        return MonitorWebsiteRecord.objects.filter(**lookups).order_by('creation', 'id')

    @wrap_close_old_connections
    def get_deleted_websites(self, start_datetime, gte_creation_time=None, limit: int = 100):
        queryset = self.get_deleted_website_queryset(
            start_datetime=start_datetime,
            gte_creation_time=gte_creation_time
        )
        return queryset[0:limit]

    @staticmethod
    def website_metering_exists(website_id, metering_date: date):
        return MeteringMonitorWebsite.objects.filter(date=metering_date, website_id=website_id).first()
