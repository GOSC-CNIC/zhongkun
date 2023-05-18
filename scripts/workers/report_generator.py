import datetime
import logging
import sys
from pathlib import Path
from decimal import Decimal

from django.utils import timezone
from django.db.models import Sum, Count
from django.db import transaction
from django.template.loader import get_template
from django.core.mail import send_mail
from django.conf import settings

from users.models import UserProfile
from vo.models import VirtualOrganization, VoMember
from metering.managers import (
    MeteringServerManager, MeteringStorageManager, StatementStorageManager, StatementServerManager
)
from metering.models import PaymentStatus
from report.models import MonthlyReport, BucketMonthlyReport
from storage.models import Bucket, BucketArchive
from order.models import Order
from utils.model import OwnerType, PayType
from bill.models import CashCoupon, CashCouponPaymentHistory
from concurrent_log_handler import ConcurrentRotatingFileHandler

from . import config_logger


def get_target_month_first_day_last_day(target_date: datetime.date):
    """
    :return: (
        date,   # target month first day
        date    # target month last day
    )
    """
    lmld = datetime.date(year=target_date.year, month=target_date.month, day=1) - datetime.timedelta(days=1)
    return datetime.date(year=lmld.year, month=lmld.month, day=1), lmld


def get_last_month_first_day_last_day():
    """
    :return: (
        date,   # last month first day
        date    # last month last day
    )
    """
    today = datetime.date.today()
    return get_target_month_first_day_last_day(target_date=today)


def hours_to_days(hours: float) -> float:
    if hours is None:
        return 0.0

    return hours / 24


class MonthlyReportGenerator:
    def __init__(self, report_data: datetime.date = None, log_stdout: bool = False, limit: int = 1000):
        self.limit = limit if limit > 0 else 1000      # 每次从数据库获取vo和user的数量
        self.logger = config_logger(name='monthly_report_logger', filename='monthly_report.log', stdout=log_stdout)
        if report_data:
            self.last_month_1st, self.last_month_last_day = get_target_month_first_day_last_day(report_data)
        else:
            self.last_month_1st, self.last_month_last_day = get_last_month_first_day_last_day()

        self.last_month_1st_time = datetime.datetime.combine(
            date=self.last_month_1st,
            time=datetime.time(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc))
        self.last_month_last_day_time = datetime.datetime.combine(
            date=self.last_month_last_day,
            time=datetime.time(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc))

        self.new_create_report_count = 0    # 新生成报表数量
        self.already_report_count = 0       # 已存在报表数量
        self.failed_create_report_count = 0  # 生成失败报表数量

    def run(self):
        self.logger.warning(f'Time: {self.last_month_1st_time} - {self.last_month_last_day_time}')
        self.generate_vos_report()
        self.generate_users_report()

        exit_str = f'Exit, new generate count {self.new_create_report_count},' \
                   f'failed count {self.failed_create_report_count}, already exists count {self.already_report_count};'
        try:
            user_count = self.get_user_count(date_joined__lt=self.last_month_last_day_time)  # 需要出报表的用户数
            vo_count = self.get_vo_count(creation_time_lt=self.last_month_last_day_time)  # 需要出报表的vo数
            exit_str += f"user count {user_count}, vo count {vo_count}."
        except Exception as exc:
            pass

        self.logger.warning(exit_str)

    def generate_users_report(self):
        self.logger.warning('Start user monthly report generate.')
        last_joined_time = None
        while True:
            try:
                users = self.get_users(limit=self.limit, time_joined_gt=last_joined_time,
                                       date_joined__lt=self.last_month_last_day_time)
                if len(users) <= 0:
                    break

                for user in users:
                    print(f'{user.username}')
                    try:
                        created, report = self.generate_report_for_user(
                            user=user, last_month_1st=self.last_month_1st,
                            last_month_last_day=self.last_month_last_day,
                            last_month_1st_time=self.last_month_1st_time,
                            last_month_last_day_time=self.last_month_last_day_time
                        )
                    except Exception as exc:
                        try:
                            created, report = self.generate_report_for_user(
                                user=user, last_month_1st=self.last_month_1st,
                                last_month_last_day=self.last_month_last_day,
                                last_month_1st_time=self.last_month_1st_time,
                                last_month_last_day_time=self.last_month_last_day_time
                            )
                        except Exception as exc:
                            last_joined_time = user.date_joined
                            self.failed_create_report_count += 1
                            self.logger.error(f'Generate monthly report for user({user.username}) error, {str(exc)}')
                            continue

                    last_joined_time = user.date_joined
                    if created:
                        self.new_create_report_count += 1
                    else:
                        self.already_report_count += 1
            except Exception as exc:
                self.logger.error(f'error, {str(exc)}')

        self.logger.warning('End user monthly report generate.')

    def generate_vos_report(self):
        self.logger.warning('Start VO monthly report generate.')
        last_creation_time = None
        while True:
            try:
                vos = self.get_vos(limit=self.limit, creation_time_gt=last_creation_time,
                                   creation_time_lt=self.last_month_last_day_time)
                if len(vos) <= 0:
                    break

                for vo in vos:
                    print(f'{vo.name}')
                    try:
                        created, report = self.generate_report_for_vo(
                            vo=vo, last_month_1st=self.last_month_1st,
                            last_month_last_day=self.last_month_last_day,
                            last_month_1st_time=self.last_month_1st_time,
                            last_month_last_day_time=self.last_month_last_day_time
                        )
                    except Exception as exc:
                        try:
                            created, report = self.generate_report_for_vo(
                                vo=vo, last_month_1st=self.last_month_1st,
                                last_month_last_day=self.last_month_last_day,
                                last_month_1st_time=self.last_month_1st_time,
                                last_month_last_day_time=self.last_month_last_day_time
                            )
                        except Exception as exc:
                            last_creation_time = vo.creation_time
                            self.failed_create_report_count += 1
                            self.logger.error(
                                f'Generate monthly report for VO(id={vo.id}, name={vo.name}) error, {str(exc)}')
                            continue

                    last_creation_time = vo.creation_time
                    if created:
                        self.new_create_report_count += 1
                    else:
                        self.already_report_count += 1
            except Exception as exc:
                self.logger.error(f'error, {str(exc)}')

        self.logger.warning('End VO monthly report generate.')

    def generate_report_for_user(
            self, user: UserProfile,
            last_month_1st: datetime.date, last_month_last_day: datetime.date,
            last_month_1st_time: datetime.datetime, last_month_last_day_time: datetime.datetime
    ):
        """
        为用户生成月度报表

        :return: (
            created,    # True(新生成的)；False(已存在的)
            report      # 月度报表对象
        )
        """
        with transaction.atomic(savepoint=False):
            month_report = MonthlyReport.objects.filter(
                report_date=last_month_1st, user_id=user.id, owner_type=OwnerType.USER.value).first()
            if month_report:
                if month_report.is_reported:
                    return False, month_report
                else:
                    month_report.delete()

            report = self._generate_report_for_user(
                user=user, last_month_1st=last_month_1st, last_month_last_day=last_month_last_day,
                last_month_1st_time=last_month_1st_time, last_month_last_day_time=last_month_last_day_time
            )

            return True, report

    @staticmethod
    def _generate_report_for_user(
            user: UserProfile,
            last_month_1st: datetime.date, last_month_last_day: datetime.date,
            last_month_1st_time: datetime.datetime, last_month_last_day_time: datetime.datetime
    ):
        """
        为用户生成月度报表
        """
        # 用户每个桶的月度报表记录
        MonthlyReportGenerator.do_user_bucket_reports(
            user=user, last_month_1st=last_month_1st, last_month_last_day=last_month_last_day)

        # 对象存储计量数据
        storage_meter_qs = MeteringStorageManager().filter_obs_metering_queryset(
            date_start=last_month_1st, date_end=last_month_last_day, user_id=user.id
        )
        storage_meter_agg = storage_meter_qs.aggregate(
            total_storage=Sum('storage'),
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            bucket_count=Count('storage_bucket_id', distinct=True)
        )
        # 对象存储日结算单
        state_storage_agg = StatementStorageManager().filter_statement_storage_queryset(
            date_start=last_month_1st, date_end=last_month_last_day,
            payment_status=PaymentStatus.PAID.value, user_id=user.id
        ).aggregate(
            total_trade_amount=Sum('trade_amount')
        )

        # 云主机计量信息
        server_meter_qs = MeteringServerManager().filter_user_server_metering(
            user=user, date_start=last_month_1st, date_end=last_month_last_day
        )
        server_m_agg = server_meter_qs.aggregate(
            total_cpu_hours=Sum('cpu_hours'),
            total_ram_hours=Sum('ram_hours'),
            total_disk_hours=Sum('disk_hours'),
            total_public_ip_hours=Sum('public_ip_hours'),
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            server_count=Count('server_id', distinct=True)
        )

        # 云主机日结算单
        state_server_agg = StatementServerManager().filter_statement_server_queryset(
            date_start=last_month_1st, date_end=last_month_last_day,
            payment_status=PaymentStatus.PAID.value, user_id=user.id
        ).aggregate(
            total_trade_amount=Sum('trade_amount')
        )

        # 云主机订购预付费金额
        order_agg = Order.objects.filter(
            user_id=user.id, owner_type=OwnerType.USER.value,
            payment_time__gte=last_month_1st_time, payment_time__lte=last_month_last_day_time,
            status=Order.Status.PAID.value, pay_type=PayType.PREPAID.value
        ).aggregate(
            total_pay_amount=Sum('pay_amount')
        )

        month_report = MonthlyReport(
            creation_time=timezone.now(),
            report_date=last_month_1st,
            is_reported=True,
            notice_time=None,
            user_id=user.id,
            username=user.username,
            vo_id=None,
            vo_name='',
            owner_type=OwnerType.USER.value
        )
        # 对象存储
        month_report.bucket_count = storage_meter_agg['bucket_count'] or 0
        month_report.storage_days = hours_to_days(storage_meter_agg['total_storage'])
        month_report.storage_original_amount = storage_meter_agg['total_original_amount'] or Decimal('0')
        month_report.storage_payable_amount = storage_meter_agg['total_trade_amount'] or Decimal('0')
        month_report.storage_postpaid_amount = state_storage_agg['total_trade_amount'] or Decimal('0')

        # 云主机
        month_report.server_cpu_days = hours_to_days(server_m_agg['total_cpu_hours'])
        month_report.server_ram_days = hours_to_days(server_m_agg['total_ram_hours'])
        month_report.server_disk_days = hours_to_days(server_m_agg['total_disk_hours'])
        month_report.server_ip_days = hours_to_days(server_m_agg['total_public_ip_hours'])
        month_report.server_count = server_m_agg['server_count'] or 0
        month_report.server_original_amount = server_m_agg['total_original_amount'] or Decimal('0')
        month_report.server_payable_amount = server_m_agg['total_trade_amount'] or Decimal('0')
        month_report.server_postpaid_amount = state_server_agg['total_trade_amount'] or Decimal('0')
        month_report.server_prepaid_amount = order_agg['total_pay_amount'] or Decimal('0')
        month_report.save(force_insert=True)
        return month_report

    def generate_report_for_vo(
            self, vo: VirtualOrganization,
            last_month_1st: datetime.date, last_month_last_day: datetime.date,
            last_month_1st_time: datetime.datetime, last_month_last_day_time: datetime.datetime
    ):
        """
        为vo生成月度报表

        :return: (
            created,    # True(新生成的)；False(已存在的)
            report      # 月度报表对象
        )
        """
        with transaction.atomic(savepoint=False):
            month_report = MonthlyReport.objects.filter(
                report_date=last_month_1st, vo_id=vo.id, owner_type=OwnerType.VO.value).first()
            if month_report:
                if month_report.is_reported:
                    return False, month_report
                else:
                    month_report.delete()

            report = self._generate_report_for_vo(
                vo=vo, last_month_1st=last_month_1st, last_month_last_day=last_month_last_day,
                last_month_1st_time=last_month_1st_time, last_month_last_day_time=last_month_last_day_time
            )

            return True, report

    @staticmethod
    def _generate_report_for_vo(
            vo: VirtualOrganization,
            last_month_1st: datetime.date, last_month_last_day: datetime.date,
            last_month_1st_time: datetime.datetime, last_month_last_day_time: datetime.datetime
    ):
        """
        为vo生成月度报表
        """
        # 云主机计量信息
        server_meter_qs = MeteringServerManager().filter_server_metering_queryset(
            vo_id=vo.id, date_start=last_month_1st, date_end=last_month_last_day
        )
        server_m_agg = server_meter_qs.aggregate(
            total_cpu_hours=Sum('cpu_hours'),
            total_ram_hours=Sum('ram_hours'),
            total_disk_hours=Sum('disk_hours'),
            total_public_ip_hours=Sum('public_ip_hours'),
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount'),
            server_count=Count('server_id', distinct=True)
        )

        # 云主机日结算单
        state_server_agg = StatementServerManager().filter_statement_server_queryset(
            date_start=last_month_1st, date_end=last_month_last_day,
            payment_status=PaymentStatus.PAID.value, vo_id=vo.id, user_id=None
        ).aggregate(
            total_trade_amount=Sum('trade_amount')
        )

        # 云主机订购预付费金额
        order_agg = Order.objects.filter(
            vo_id=vo.id, owner_type=OwnerType.VO.value,
            payment_time__gte=last_month_1st_time, payment_time__lte=last_month_last_day_time,
            status=Order.Status.PAID.value, pay_type=PayType.PREPAID.value
        ).aggregate(
            total_pay_amount=Sum('pay_amount')
        )

        month_report = MonthlyReport(
            creation_time=timezone.now(),
            report_date=last_month_1st,
            is_reported=True,
            notice_time=None,
            user_id=None,
            username='',
            vo_id=vo.id,
            vo_name=vo.name,
            owner_type=OwnerType.VO.value
        )
        # 云主机
        month_report.server_cpu_days = hours_to_days(server_m_agg['total_cpu_hours'])
        month_report.server_ram_days = hours_to_days(server_m_agg['total_ram_hours'])
        month_report.server_disk_days = hours_to_days(server_m_agg['total_disk_hours'])
        month_report.server_ip_days = hours_to_days(server_m_agg['total_public_ip_hours'])
        month_report.server_count = server_m_agg['server_count'] or 0
        month_report.server_original_amount = server_m_agg['total_original_amount'] or Decimal('0')
        month_report.server_payable_amount = server_m_agg['total_trade_amount'] or Decimal('0')
        month_report.server_prepaid_amount = order_agg['total_pay_amount'] or Decimal('0')
        month_report.server_postpaid_amount = state_server_agg['total_trade_amount'] or Decimal('0')

        # 对象存储
        month_report.bucket_count = 0
        month_report.storage_days = 0
        month_report.storage_original_amount = Decimal('0')
        month_report.storage_payable_amount = Decimal('0')
        month_report.storage_postpaid_amount = Decimal('0')
        month_report.save(force_insert=True)
        return month_report

    @staticmethod
    def _get_buckets_with_service(bucket_ids: list):
        """
        :return:{
            bucket_id: {
                'id': 'xx', 'name': 'xx',
                'service__id': 'xx', 'service__name': 'xx'
            }
        }
        """
        buckets = Bucket.objects.filter(
            id__in=bucket_ids).values(
            'id', 'name', 'service__id', 'service__name')
        archives = BucketArchive.objects.filter(
            original_id__in=bucket_ids,
        ).values(
            'original_id', 'name', 'service__id', 'service__name')

        buckets_dict = {s['id']: s for s in buckets}
        for a in archives:
            bkt_id = a['id'] = a.pop('original_id', None)
            buckets_dict[bkt_id] = a

        return buckets_dict

    @staticmethod
    def do_user_bucket_reports(
            user: UserProfile, last_month_1st: datetime.date, last_month_last_day: datetime.date
    ):
        """
        生成用户存储桶月度报表
        """
        b_meter_qs = MeteringStorageManager().filter_obs_metering_queryset(
            date_start=last_month_1st, date_end=last_month_last_day, user_id=user.id
        )
        b_anno_qs = b_meter_qs.values('storage_bucket_id').annotate(
            total_storage_hours=Sum('storage'),
            total_original_amount=Sum('original_amount'),
            total_trade_amount=Sum('trade_amount')
        ).order_by()

        bucket_ids = [b['storage_bucket_id'] for b in b_anno_qs]
        if not bucket_ids:
            return True, []

        bkts = MonthlyReportGenerator._get_buckets_with_service(bucket_ids=bucket_ids)

        bucket_reports = []
        for ba in b_anno_qs:
            bkt_id = ba['storage_bucket_id']
            bkt = bkts.get(bkt_id, None)
            service_id = service_name = bucket_name = ''
            if bkt:
                service_id = bkt['service__id'] or ''
                service_name = bkt['service__name'] or ''
                bucket_name = bkt['name'] or ''

            bmr = BucketMonthlyReport(
                creation_time=timezone.now(),
                report_date=last_month_1st,
                user_id=user.id,
                username=user.username,
                service_id=service_id,
                service_name=service_name,
                bucket_id=bkt_id,
                bucket_name=bucket_name,
                storage_days=hours_to_days(ba['total_storage_hours']),
                original_amount=ba['total_original_amount'] or Decimal('0'),
                payable_amount=ba['total_trade_amount'] or Decimal('0')
            )
            bmr.enforce_id()
            bucket_reports.append(bmr)

        return True, BucketMonthlyReport.objects.bulk_create(bucket_reports)

    @staticmethod
    def get_users(limit: int, time_joined_gt=None, date_joined__lt=None):
        qs = UserProfile.objects.filter(
            is_active=True
        ).order_by('date_joined')

        if time_joined_gt:
            qs = qs.filter(date_joined__gt=time_joined_gt)

        if date_joined__lt:
            qs = qs.filter(date_joined__lt=date_joined__lt)

        return qs[0:limit]

    @staticmethod
    def get_user_count(date_joined__lt):
        qs = UserProfile.objects.filter(is_active=True)
        if date_joined__lt:
            qs = qs.filter(date_joined__lt=date_joined__lt)

        return qs.count()

    @staticmethod
    def get_vos(limit: int, creation_time_gt=None, creation_time_lt=None):
        qs = VirtualOrganization.objects.filter(
            deleted=False
        ).order_by('creation_time')

        if creation_time_gt:
            qs = qs.filter(creation_time__gt=creation_time_gt)

        if creation_time_lt:
            qs = qs.filter(creation_time__lt=creation_time_lt)

        return qs[0:limit]

    @staticmethod
    def get_vo_count(creation_time_lt):
        qs = VirtualOrganization.objects.filter(deleted=False)
        if creation_time_lt:
            qs = qs.filter(creation_time__lt=creation_time_lt)

        return qs.count()


class MonthlyReportNotifier:
    def __init__(self, log_stdout: bool = False, limit: int = 1000):
        self.limit = limit if limit > 0 else 1000      # 每次从数据库获取vo和user的数量
        self.logger = config_logger(name='monthly_report_logger', filename='monthly_report.log', stdout=log_stdout)
        self.last_month_1st, self.last_month_last_day = get_last_month_first_day_last_day()
        self.last_month_1st_time = datetime.datetime.combine(
            date=self.last_month_1st,
            time=datetime.time(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc))
        self.last_month_last_day_time = datetime.datetime.combine(
            date=self.last_month_last_day,
            time=datetime.time(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc))
        self.template = get_template('monthly_report.html')

    def run(self):
        self.logger.warning(f"Start send Email for user's monthly report: {self.last_month_1st}")
        last_joined_time = None
        while True:
            try:
                users = self.get_users(limit=self.limit, time_joined_gt=last_joined_time)
                if len(users) <= 0:
                    break

                for user in users:
                    try:
                        ok = self.send_monthly_report_to_user(user=user, report_date=self.last_month_1st)
                        if ok is False:
                            raise Exception('发送邮件失败')   # 抛出错误 触发重试一次
                    except Exception as exc:
                        try:
                            ok = self.send_monthly_report_to_user(user=user, report_date=self.last_month_1st)
                            if ok is False:
                                self.logger.warning(
                                    f"Falied send email to User{user.username} monthly({self.last_month_1st}) report.")
                        except Exception as exc:
                            self.logger.error(f'Send email monthly report for user({user.username}), {str(exc)}')

                    last_joined_time = user.date_joined
            except Exception as exc:
                self.logger.error(f'{str(exc)}')

        self.logger.warning("End send email for user's monthly report.")

    def send_monthly_report_to_username(self, username: str, report_date=None):
        user = UserProfile.objects.filter(username=username).first()
        if user is None:
            print(f'User "{username}" not found.')
            return
        if report_date is None:
            report_date = self.last_month_1st

        self.send_monthly_report_to_user(user=user, report_date=report_date)

    def get_context(self, user, report_date):
        bucket_reports = BucketMonthlyReport.objects.filter(report_date=report_date, user_id=user.id).all()

        vo_dict = self.get_user_vo_dict(user=user)
        vo_ids = list(vo_dict.keys())
        vo_monthly_reports = MonthlyReport.objects.filter(
            report_date=report_date, vo_id__in=vo_ids, owner_type=OwnerType.VO.value).all()

        vo_total_amount = Decimal('0')
        for vmr in vo_monthly_reports:
            vo_total_amount += vmr.server_payment_amount
            vmr.vo_info = vo_dict.get(vmr.vo_id)

        user_coupons = self.get_user_coupons(user=user)
        user_normal_coupons, user_expired_coupons = self.split_coupons(coupons=user_coupons, split_time=timezone.now())
        self.set_coupons_last_month_pay_amount(
            user_normal_coupons, start_time=self.last_month_1st_time, end_time=self.last_month_last_day_time)
        self.set_coupons_last_month_pay_amount(
            user_expired_coupons, start_time=self.last_month_1st_time, end_time=self.last_month_last_day_time)

        vo_coupons = self.get_vos_coupons(vo_ids=vo_ids)
        vo_normal_coupons, vo_expired_coupons = self.split_coupons(coupons=vo_coupons, split_time=timezone.now())
        self.set_coupons_last_month_pay_amount(
            vo_normal_coupons, start_time=self.last_month_1st_time, end_time=self.last_month_last_day_time)
        self.set_coupons_last_month_pay_amount(
            vo_expired_coupons, start_time=self.last_month_1st_time, end_time=self.last_month_last_day_time)

        return {
            'report_date': report_date,
            'user': user,
            'bucket_reports': bucket_reports,
            'bucket_reports_len': len(bucket_reports),
            'vo_monthly_reports': vo_monthly_reports,
            'vo_total_amount': vo_total_amount,
            'user_coupons_length': len(user_coupons),
            'user_normal_coupons': user_normal_coupons,
            'user_expired_coupons': user_expired_coupons,
            'vo_normal_coupons': vo_normal_coupons,
            'vo_expired_coupons': vo_expired_coupons,
            'vo_coupons_length': len(vo_coupons)
        }

    def send_monthly_report_to_user(self, user, report_date):
        """
        :return:
            None        # 已发送过邮件，或者不满足发送条件
            True        # 发送成功
            False       # 发送失败
        """
        monthly_report: MonthlyReport = MonthlyReport.objects.filter(
            report_date=report_date, user_id=user.id, owner_type=OwnerType.USER.value).first()
        if monthly_report is None:
            self.logger.warning(f"User{user.username} monthly({report_date}) report not found, skip send email.")
            return None
        elif not monthly_report.is_reported:
            self.logger.warning(
                f"User{user.username} monthly({report_date}) report generate not completed, skip send email.")
            return None
        elif monthly_report.notice_time:
            return None

        context = self.get_context(user=user, report_date=report_date)
        context['monthly_report'] = monthly_report

        html_message = self.template.render(context, request=None)
        ok = send_mail(
            subject='test中国科技云一体化云服务平台月报表',  # 标题
            message='',  # 内容
            from_email=settings.EMAIL_HOST_USER,  # 发送者
            recipient_list=[user.username],  # 接收者
            html_message=html_message,    # 内容
            fail_silently=True,
        )
        if ok > 0:
            monthly_report.notice_time = timezone.now()
            monthly_report.save(update_fields=['notice_time'])
            return True

        return False

    @staticmethod
    def get_users(limit: int, time_joined_gt=None):
        qs = UserProfile.objects.filter(
            is_active=True
        ).order_by('date_joined')

        if time_joined_gt:
            qs = qs.filter(date_joined__gt=time_joined_gt)

        return qs[0:limit]

    @staticmethod
    def get_user_vo_dict(user: UserProfile):
        v_members = VoMember.objects.select_related('vo', 'vo__owner').filter(user_id=user.id).all()
        vos = VirtualOrganization.objects.select_related('owner').filter(owner_id=user.id, deleted=False)
        vos_dict = {}
        for m in v_members:
            vo = m.vo
            if not vo:
                continue

            own_role = '管理员' if m.role == VoMember.Role.LEADER.value else '组员'
            members = VoMember.objects.filter(vo_id=vo.id).values('role', 'user__username')
            vos_dict[vo.id] = {
                'vo': vo,
                'own_role': own_role,
                'members': members
            }

        for vo in vos:
            members = VoMember.objects.filter(vo_id=vo.id).values('role', 'user__username')
            vos_dict[vo.id] = {
                'vo': vo,
                'own_role': '组长',
                'members': members
            }

        return vos_dict

    @staticmethod
    def get_user_coupons(user):
        return CashCoupon.objects.select_related('app_service').filter(
            user_id=user.id, owner_type=OwnerType.USER.value, status=CashCoupon.Status.AVAILABLE.value)

    @staticmethod
    def get_vo_coupons(vo):
        return CashCoupon.objects.select_related('app_service').filter(
            vo_id=vo.id, owner_type=OwnerType.VO.value, status=CashCoupon.Status.AVAILABLE.value)

    @staticmethod
    def get_vos_coupons(vo_ids: list):
        return CashCoupon.objects.select_related('app_service').filter(
            vo_id__in=vo_ids, owner_type=OwnerType.VO.value, status=CashCoupon.Status.AVAILABLE.value)

    @staticmethod
    def split_coupons(coupons, split_time: datetime):
        expired_coupons = []
        normal_coupons = []
        for cp in coupons:
            if cp.expiration_time and cp.expiration_time <= split_time:
                expired_coupons.append(cp)
            else:
                normal_coupons.append(cp)

        return normal_coupons, expired_coupons

    @staticmethod
    def get_coupon_pay_amount(coupon: CashCoupon, start_time, end_time):
        # 给定时间段之前已过期
        if coupon.expiration_time <= start_time:
            return Decimal('0')

        # 给定时间段之后可用
        if coupon.effective_time > end_time:
            return Decimal('0')

        r = CashCouponPaymentHistory.objects.filter(
            cash_coupon_id=coupon.id, creation_time__gte=start_time, creation_time__lte=end_time
        ).aggregate(total_amounts=Sum('amounts'))

        amount = r['total_amounts'] or Decimal('0')
        if amount < Decimal('0'):
            return -amount

        return amount

    def set_coupons_last_month_pay_amount(self, coupons, start_time, end_time):
        for cp in coupons:
            amount = self.get_coupon_pay_amount(coupon=cp, start_time=start_time, end_time=end_time)
            setattr(cp, 'last_month_pay_amount', amount)
