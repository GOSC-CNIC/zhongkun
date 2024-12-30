from typing import Union
from decimal import Decimal
from datetime import datetime, date

from django.utils.translation import gettext as _
from django.db.models import TextChoices, Sum
from django.utils import timezone as dj_timezone

from core import errors
from apps.storage.managers.objects_service import ObjectsServiceManager
from .models import BucketStatsMonthly, ArrearServer, ArrearBucket


class BktStatsMonthQueryOrderBy(TextChoices):
    DATE_ASC = 'date', _('按日期升序')
    DATE_DESC = '-date', _('按日期降序')
    INCR_SIZE_ASC = 'increment_byte', _('按容量增量升序')
    INCR_SIZE_DESC = '-increment_byte', _('按容量增量降序')
    AMOUNT_ASC = 'original_amount', _('按计量金额升序')
    AMOUNT_DESC = '-original_amount', _('按计量金额降序')
    CREATION_TIME_DESC = '-creation_time', _('按创建时间降序')


class StorageAggQueryOrderBy(TextChoices):
    INCR_SIZE_ASC = 'total_increment_byte', _('按容量增量升序')
    INCR_SIZE_DESC = '-total_increment_byte', _('按容量增量降序')
    AMOUNT_ASC = 'total_original_amount', _('按计量金额升序')
    AMOUNT_DESC = '-total_original_amount', _('按计量金额降序')


class ArrearServerQueryOrderBy(TextChoices):
    BALANCE_ASC = 'balance_amount', _('按余额升序')
    BALANCE_DESC = '-balance_amount', _('按余额降序')
    CREATION_TIME_DESC = '-creation_time', _('按创建时间降序')


class ArrearBucketQueryOrderBy(TextChoices):
    BALANCE_ASC = 'balance_amount', _('按余额升序')
    BALANCE_DESC = '-balance_amount', _('按余额降序')
    CREATION_TIME_DESC = '-creation_time', _('按创建时间降序')


class BucketStatsMonthlyManager:
    @staticmethod
    def get_queryset():
        return BucketStatsMonthly.objects.all()

    @staticmethod
    def filter_queryset(
            queryset, user_id: str = None, service_ids: list = None, bucket_id: str = None,
            date_start=None, date_end=None, order_by: str = None
    ):
        """
        date_start: 大于等于此日期
        date_end: 小于等于此日期
        """
        lookups = {}
        if service_ids:
            if len(service_ids) == 1:
                lookups['service_id'] = service_ids[0]
            else:
                lookups['service_id__in'] = service_ids

        if bucket_id:
            lookups['bucket_id'] = bucket_id

        if date_start and date_end and date_start == date_end:
            lookups['date'] = date_start
        else:
            if date_start:
                lookups['date__gte'] = date_start

            if date_end:
                lookups['date__lte'] = date_end

        if user_id:
            lookups['user_id'] = user_id

        if lookups:
            queryset = queryset.filter(**lookups)

        if order_by:
            queryset = queryset.order_by(order_by)

        return queryset

    def get_user_bkt_stats_queryset(
            self, user_id: str, service_ids: list = None, bucket_id: str = None,
            date_start=None, date_end=None, order_by: str = None
    ):
        """
        查询用户自己存储桶的月度统计数据
        """
        if not user_id:
            raise errors.NotAuthenticated()

        queryset = self.get_queryset()
        return self.filter_queryset(
            queryset=queryset, user_id=user_id, service_ids=service_ids, bucket_id=bucket_id,
            date_start=date_start, date_end=date_end, order_by=order_by
        )

    def admin_bkt_stats_queryset(
            self, user_id: str = None, service_ids: list = None, bucket_id: str = None,
            date_start=None, date_end=None, order_by: str = None
    ):
        """
        管理员查询存储桶的月度统计数据
        """
        queryset = self.get_queryset()
        return self.filter_queryset(
            queryset=queryset, user_id=user_id, service_ids=service_ids, bucket_id=bucket_id,
            date_start=date_start, date_end=date_end, order_by=order_by
        )

    def admin_aggregate_storage_stats_by_date(
            self, service_ids: list = None, date_start=None, date_end=None
    ):
        """
        管理员查询存储的月度统计数据
        """
        queryset = self.admin_bkt_stats_queryset(
            service_ids=service_ids, date_start=date_start, date_end=date_end
        )
        return self._aggregate_by_date(queryset)

    def user_aggregate_storage_stats_by_date(
            self, user_id: str, service_ids: list = None, date_start=None, date_end=None
    ):
        """
        用户查询存储桶的月度统计数据
        """
        queryset = self.get_user_bkt_stats_queryset(
            user_id=user_id, service_ids=service_ids, date_start=date_start, date_end=date_end
        )
        return self._aggregate_by_date(queryset)

    @staticmethod
    def _aggregate_by_date(queryset):
        return queryset.values('date').annotate(
            total_size_byte=Sum('size_byte', default=0),
            total_increment_byte=Sum('increment_byte', default=0),
            total_original_amount=Sum('original_amount', default=Decimal('0.00')),
            total_increment_amount=Sum('increment_amount', default=Decimal('0.00')),
        ).order_by('-date')

    def admin_aggregate_storage_by_service(self, _date, order_by=None, service_ids: list = None):
        """
        管理员查询存储的指定月度各服务单元统计数据
        """
        queryset = self.admin_bkt_stats_queryset(
            service_ids=service_ids, date_start=_date, date_end=_date
        )
        return self._aggregate_by_service(queryset, order_by=order_by)

    @staticmethod
    def _aggregate_by_service(queryset, order_by: str = None):
        if not order_by:
            order_by = 'service_id'

        return queryset.values('service_id').annotate(
            total_size_byte=Sum('size_byte', default=0),
            total_increment_byte=Sum('increment_byte', default=0),
            total_original_amount=Sum('original_amount', default=Decimal('0.00')),
            total_increment_amount=Sum('increment_amount', default=Decimal('0.00')),
        ).order_by(order_by)

    @staticmethod
    def agg_by_service_mixin_data(data: list):
        """
        按服务单元聚合的数据混合额外数据
        """
        if not data:
            return data

        service_ids = [i['service_id'] for i in data]
        services = ObjectsServiceManager.get_service_qs_by_ids(
            service_ids=service_ids).order_by().values('id', 'name', 'name_en')

        service_map = {s['id']: s for s in services}

        for d in data:
            s_id = d['service_id']
            if s_id in service_map:
                d['service'] = (service_map[s_id])
            else:
                d['service'] = None

        return data


class ArrearServerManager:
    @staticmethod
    def create_arrear_server(
            server_id: str, service_id: str, service_name: str, ipv4: str, vcpus: int, ram_gib: int, image: str,
            pay_type: str, server_creation: datetime, server_expire: Union[datetime, None],
            user_id: str, username: str, vo_id: str, vo_name: str, owner_type: str,
            balance_amount: Decimal, date_: date, remark: str
    ):
        ins = ArrearServer(
            server_id=server_id, service_id=service_id, service_name=service_name,
            ipv4=ipv4, vcpus=vcpus, ram=ram_gib, image=image,
            pay_type=pay_type, server_creation=server_creation, server_expire=server_expire,
            user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type,
            balance_amount=balance_amount, date=date_, creation_time=dj_timezone.now(),
            remarks=remark
        )
        ins.save(force_insert=True)
        return ins

    @staticmethod
    def get_arrear_server_qs(date_start: date, date_end: date, order_by: str, service_id: str = None):
        lookups = {}
        if date_start and date_end and date_start == date_end:
            lookups['date'] = date_start
        else:
            if date_start:
                lookups['date__gte'] = date_start
            if date_end:
                lookups['date__lte'] = date_end

        if service_id:
            lookups['service_id'] = service_id

        return ArrearServer.objects.filter(**lookups).order_by(order_by)


class ArrearBucketManager:
    @staticmethod
    def create_arrear_bucket(
            bucket_id: str, bucket_name: str, service_id: str, service_name: str,
            size_byte: int, object_count: int, bucket_creation: datetime, situation: str,
            situation_time: Union[datetime, None],
            user_id: str, username: str, balance_amount: Decimal, date_: date, remarks: str
    ):
        ins = ArrearBucket(
            bucket_id=bucket_id, bucket_name=bucket_name, service_id=service_id, service_name=service_name,
            size_byte=size_byte, object_count=object_count, bucket_creation=bucket_creation,
            situation=situation, situation_time=situation_time, user_id=user_id, username=username,
            balance_amount=balance_amount, date=date_, creation_time=dj_timezone.now(), remarks=remarks
        )
        ins.save(force_insert=True)
        return ins

    @staticmethod
    def get_arrear_bucket_qs(date_start: date, date_end: date, order_by: str, service_id: str = None):
        lookups = {}
        if date_start and date_end and date_start == date_end:
            lookups['date'] = date_start
        else:
            if date_start:
                lookups['date__gte'] = date_start
            if date_end:
                lookups['date__lte'] = date_end

        if service_id:
            lookups['service_id'] = service_id

        return ArrearBucket.objects.filter(**lookups).order_by(order_by)
