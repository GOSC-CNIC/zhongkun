import time
import datetime
from decimal import Decimal
from functools import wraps

from django.db import close_old_connections
from django.db.models import Sum
from django.utils import timezone

from apps.app_wallet.managers.payment import PaymentManager
from apps.storage.models import Bucket, BucketArchive, ObjectsService
from apps.app_report.models import BucketStatsMonthly
from apps.app_report.managers import ArrearBucketManager
from apps.app_metering.managers import MeteringStorageManager
from .report_generator import get_report_period_start_and_end


def wrap_close_old_connections(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        close_old_connections()
        return func(*args, **kwargs)

    return wrapper


class StorageSizeCounter:
    def __init__(self, target_date: datetime.date = None):
        self.period_start, self.period_end = get_report_period_start_and_end(target_date=target_date)
        self.period_date = datetime.date(
            year=self.period_end.year, month=self.period_end.month, day=1)
        self.period_start_time = datetime.datetime.combine(
            date=self.period_start,
            time=datetime.time(hour=0, minute=0, second=0, microsecond=0, tzinfo=datetime.timezone.utc))
        self.period_end_time = datetime.datetime.combine(
            date=self.period_end,
            time=datetime.time(hour=23, minute=59, second=59, microsecond=999999, tzinfo=datetime.timezone.utc))

        self._new_count = 0
        self._bucket_count = 0
        self._deleted_bucket_count = 0

    def run(self, check_time: bool = True):
        print(f'Start, bucket mothly stats, {self.period_start_time} - {self.period_end_time}.')
        if check_time:
            nt = timezone.now()
            if nt <= self.period_end_time:
                print(f'Exit，生成存储桶月度趋势统计数据的当前时间{nt} 必须在月度周期时间{self.period_end_time}之后。')
                return None

        self.metering_loop(deleted=False)
        self.metering_loop(deleted=True)
        print(f'END，bucket count {self._bucket_count}, deleted bucket count {self._deleted_bucket_count}, '
              f'creat data {self._new_count}。')
        return True

    def metering_loop(self, deleted: bool):
        last_creation_time = None
        last_id = ''
        continuous_error_count = 0
        limit = 100
        while True:
            try:
                if deleted:
                    buckets = self.get_deleted_buckets(
                        gte_delete_time=self.period_start_time, gte_creation_time=last_creation_time, limit=limit)
                else:
                    buckets = self.get_buckets(
                        lte_creation_time=self.period_end_time, gte_creation_time=last_creation_time, limit=limit)

                if len(buckets) == 0:
                    break
                # 最后一条数据是上次last_id，说明遍历完了
                # 如果creation_time相同的数据多过了limit，这种极端情况下，只会遍历前limit条数据后退出，是无法遍历的表所有数据
                if buckets[len(buckets) - 1].id == last_id:
                    break

                for b in buckets:
                    if b.id == last_id:
                        continue
                    self.stats_one_bucket(bucket_or_archive=b)
                    last_creation_time = b.creation_time
                    last_id = b.id

                continuous_error_count = 0
            except Exception as e:
                print(str(e))
                continuous_error_count += 1
                if continuous_error_count > 100:  # 连续错误次数后报错退出
                    raise e

    def stats_one_bucket(self, bucket_or_archive):
        # 本周期后创建的
        if bucket_or_archive.creation_time > self.period_end_time:
            return None

        if isinstance(bucket_or_archive, Bucket):
            bucket_id = bucket_or_archive.id
            self._bucket_count += 1
        elif isinstance(bucket_or_archive, BucketArchive):
            bucket_id = bucket_or_archive.original_id
            self._deleted_bucket_count += 1
        else:
            return None

        period_date = self.period_date
        b_stats_ins = self.get_bucket_stats_ins(bucket_id=bucket_id, _date=period_date)
        if b_stats_ins is not None:
            return b_stats_ins

        # 本周期桶计量计费金额
        b_meter_qs = MeteringStorageManager().filter_obs_metering_queryset(
            date_start=self.period_start, date_end=self.period_end, bucket_id=bucket_id
        )
        r = b_meter_qs.aggregate(total_original_amount=Sum('original_amount', default=Decimal('0.00')))
        original_amount = r['total_original_amount']

        pre_period_date = self.pre_period_date(period_date=period_date)
        pre_stats_ins = self.get_bucket_stats_ins(bucket_id=bucket_id, _date=pre_period_date)
        if isinstance(bucket_or_archive, BucketArchive):
            # 本周期之后删除的，创建本周期的数据，下周期还需要创建一个删除对应的数据
            if bucket_or_archive.delete_time > self.period_end_time:
                storage_size = bucket_or_archive.storage_size
                object_count = bucket_or_archive.object_count
            else:
                storage_size = 0
                object_count = 0

            if pre_stats_ins:
                increment_byte = storage_size - pre_stats_ins.size_byte
                increment_amount = original_amount - pre_stats_ins.original_amount
            else:
                increment_amount = original_amount
                # 本周期之后删除的，创建本周期的数据，下周期还需要创建一个删除对应的数据
                if bucket_or_archive.delete_time > self.period_end_time:
                    # 本周期创建，下周期删除的
                    if bucket_or_archive.creation_time >= self.period_start_time:
                        increment_byte = storage_size
                    else:   # 本周期前创建，下周期删除的
                        increment_byte = 0
                else:
                    # 本周期内创建，本周期内删除
                    if bucket_or_archive.creation_time >= self.period_start_time:
                        increment_byte = 0
                    else:   # 本周期前创建，本周期内删除
                        increment_byte = -bucket_or_archive.storage_size
        elif isinstance(bucket_or_archive, Bucket):
            storage_size = bucket_or_archive.storage_size
            object_count = bucket_or_archive.object_count
            if pre_stats_ins:
                increment_byte = storage_size - pre_stats_ins.size_byte
                increment_amount = original_amount - pre_stats_ins.original_amount
            else:
                increment_amount = original_amount
                # 桶创建时间判断是否在本周期
                if bucket_or_archive.creation_time >= self.period_start_time:
                    increment_byte = storage_size
                else:
                    increment_byte = 0
        else:
            return None

        ins = self.create_bucket_monthly_ins(
            _date=period_date, service_id=bucket_or_archive.service_id,
            bucket_id=bucket_id, bucket_name=bucket_or_archive.name,
            size_byte=storage_size, increment_byte=increment_byte, object_count=object_count,
            original_amount=original_amount, increment_amount=increment_amount, user=bucket_or_archive.user
        )
        self._new_count += 1
        return ins

    @staticmethod
    def pre_period_date(period_date: datetime.date):
        d = period_date.replace(day=1)
        d = d - datetime.timedelta(days=1)
        return d.replace(day=1)

    @staticmethod
    def create_bucket_monthly_ins(
            _date, service_id: str, bucket_id: str, bucket_name: str, size_byte: int, increment_byte: int,
            object_count: int, original_amount: Decimal, increment_amount: Decimal, user
    ):
        user_id = username = ''
        if user:
            user_id = user.id
            username = user.username

        ins = BucketStatsMonthly(
            service_id=service_id,
            bucket_id=bucket_id,
            bucket_name=bucket_name,
            size_byte=size_byte,
            increment_byte=increment_byte,
            object_count=object_count,
            original_amount=original_amount,
            increment_amount=increment_amount,
            user_id=user_id, username=username,
            date=_date, creation_time=timezone.now()
        )
        ins.save(force_insert=True)
        return ins

    @staticmethod
    def get_bucket_stats_ins(bucket_id: str, _date: datetime.date) -> BucketStatsMonthly:
        return BucketStatsMonthly.objects.filter(bucket_id=bucket_id, date=_date).first()

    @wrap_close_old_connections
    def get_buckets(self, lte_creation_time, gte_creation_time, limit: int = 100):
        """
        param lte_creation_time: 过滤掉本周期之后新建的
        """
        queryset = self.get_buckets_queryset(lte_creation_time=lte_creation_time, gte_creation_time=gte_creation_time)
        return queryset[0:limit]

    @staticmethod
    def get_buckets_queryset(lte_creation_time, gte_creation_time=None):
        """
        查询bucket的集合， 按照创建的时间 以及 id 正序排序
        :param lte_creation_time: 指定时间之前创建的
        :param gte_creation_time: 大于等于给定的创建时间，用于断点查询
        """
        lookups = {'creation_time__lte': lte_creation_time}
        if gte_creation_time is not None:
            lookups['creation_time__gte'] = gte_creation_time

        queryset = Bucket.objects.select_related(
            'service', 'user').filter(**lookups).order_by('creation_time', 'id')
        return queryset

    @wrap_close_old_connections
    def get_deleted_buckets(self, gte_delete_time, gte_creation_time, limit: int = 100):
        queryset = self.get_deleted_buckets_queryset(
            gte_delete_time=gte_delete_time, gte_creation_time=gte_creation_time)
        return queryset[0:limit]

    @staticmethod
    def get_deleted_buckets_queryset(gte_delete_time, gte_creation_time=None):
        """
        查询已删除的bucket的集合， 按照创建的时间 以及 id 正序排序
        :param gte_delete_time: 删除时间在指定时间之后
        :param gte_creation_time: 大于等于给定的创建时间，用于断点查询
        """
        lookups = {'delete_time__gte': gte_delete_time}
        if gte_creation_time is not None:
            lookups['creation_time__gte'] = gte_creation_time

        queryset = BucketArchive.objects.select_related(
            'service', 'user').filter(**lookups).order_by('creation_time', 'id')
        return queryset


class ArrearBucketReporter:
    """
        欠费云主机查询 保存到数据库
        """

    def __init__(self, raise_exception: bool = False):
        """
        """
        self.raise_exception = raise_exception
        self._date = timezone.now().date()
        self.arrear_map = {}

    @staticmethod
    def get_user_balance(user_id):
        account = PaymentManager.get_user_point_account(user_id=user_id)
        return account.balance

    def is_user_arrear_in_service(self, user_id: str, service: ObjectsService) -> bool:
        """
        用户在指定服务单元是否欠费
        """
        key = f'user_{user_id}_{service.id}'
        if key not in self.arrear_map:
            is_enough = PaymentManager().has_enough_balance_user(
                user_id=user_id, money_amount=Decimal('0'), with_coupons=True,
                app_service_id=service.pay_app_service_id)
            self.arrear_map[key] = not is_enough

        return self.arrear_map[key]

    def run(self):
        count_arrear = self.loop_buckets()  # 按量付费
        print(f'[{self._date}] 欠费存储桶数：{count_arrear}')

    def loop_buckets(self, limit: int = 100):
        count_arrear = 0
        last_creatition_time = None
        last_id = ''
        continuous_error_count = 0  # 连续错误计数
        while True:
            try:
                buckets = self.get_buckets(gte_creation_time=last_creatition_time, limit=limit)
                if len(buckets) == 0:
                    break

                # 多个creation_time相同数据时，会查询获取到多个数据（计量过也会重复查询到）
                if buckets[len(buckets) - 1].id == last_id:
                    break

                for bkt in buckets:
                    if bkt.id == last_id:
                        continue

                    ins = None
                    try:
                        ins = self.check_arrear_bucket(bucket=bkt, date_=self._date)
                    except Exception:
                        try:
                            ins = self.check_arrear_bucket(bucket=bkt, date_=self._date)
                        except Exception as exc:
                            pass

                    last_creatition_time = bkt.creation_time
                    last_id = bkt.id

                    if ins is not None:
                        count_arrear += 1

                continuous_error_count = 0
            except Exception as e:
                if self.raise_exception:
                    raise e

                continuous_error_count += 1
                if continuous_error_count > 100:  # 连续错误次数后报错退出
                    raise e

                time.sleep(continuous_error_count / 100)  # 10ms - 1000ms

        return count_arrear

    def check_arrear_bucket(self, bucket: Bucket, date_: datetime.date):
        user = bucket.user
        user_id = user.id
        username = user.username
        service = bucket.service

        if self.is_user_arrear_in_service(user_id=user_id, service=service):
            balance_amount = self.get_user_balance(user_id=user_id)
            ins = ArrearBucketManager.create_arrear_bucket(
                bucket_id=bucket.id, bucket_name=bucket.name, service_id=service.id, service_name=service.name,
                size_byte=bucket.storage_size, object_count=bucket.object_count, bucket_creation=bucket.creation_time,
                user_id=user_id, username=username, balance_amount=balance_amount, date_=date_,
                remarks='', situation=bucket.situation, situation_time=bucket.situation_time
            )
            return ins

        return None

    @wrap_close_old_connections
    def get_buckets(self, gte_creation_time, limit: int = 100):
        """
        """
        queryset = self.get_buckets_queryset(gte_creation_time=gte_creation_time)
        return queryset[0:limit]

    @staticmethod
    def get_buckets_queryset(gte_creation_time=None):
        """
        查询bucket的集合， 按照创建的时间 以及 id 正序排序
        :param gte_creation_time: 大于等于给定的创建时间，用于断点查询
        """
        lookups = {}
        if gte_creation_time is not None:
            lookups['creation_time__gte'] = gte_creation_time

        queryset = Bucket.objects.select_related(
            'service', 'user').filter(**lookups).order_by('creation_time', 'id')
        return queryset
