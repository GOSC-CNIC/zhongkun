from decimal import Decimal
import datetime
from datetime import timedelta

from django.utils import timezone
from django.test.testcases import TransactionTestCase
from django.core import mail

from utils.model import PayType, OwnerType, ResourceType
from utils.test import get_or_create_user, get_or_create_center
from order.models import Order
from metering.models import (
    MeteringServer, MeteringObjectStorage, DailyStatementServer, DailyStatementObjectStorage,PaymentStatus
)
from bill.models import PayApp, PayOrgnazition, PayAppService, CashCoupon
from storage.models import ObjectsService, Bucket, BucketArchive
from vo.models import VirtualOrganization, VoMember
from report.models import MonthlyReport, BucketMonthlyReport
from scripts.workers.report_generator import MonthlyReportGenerator, get_last_month_first_day_last_day


class MonthlyReportTests(TransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='lilei@cnic.cn')
        self.user2 = get_or_create_user(username='tom@qq.com')
        self.vo1 = VirtualOrganization(name='vo1', owner_id=self.user1.id)
        self.vo1.save(force_insert=True)
        self.vo2 = VirtualOrganization(name='vo2', owner_id=self.user2.id)
        self.vo2.save(force_insert=True)
        VoMember(user=self.user2, vo=self.vo1, role=VoMember.Role.MEMBER.value).save(force_insert=True)
        VoMember(user=self.user1, vo=self.vo2, role=VoMember.Role.LEADER.value).save(force_insert=True)

        # 余额支付有关配置
        app = PayApp(name='app')
        app.save()
        self.app = app
        po = PayOrgnazition(name='机构')
        po.save()
        self.app_service1 = PayAppService(
            name='service1', app=app, orgnazition=po, service_id='service.id',
            category=PayAppService.Category.VMS_SERVER.value
        )
        self.app_service1.save()
        self.app_service2 = PayAppService(
            name='service2', app=app, orgnazition=po, category=PayAppService.Category.VMS_OBJECT.value
        )
        self.app_service2.save()

        self.last_month_1st, self.last_month_last_day = get_last_month_first_day_last_day()
        self.last_month_1st_time = datetime.datetime.combine(
            date=self.last_month_1st,
            time=datetime.time(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc))
        self.last_month_last_day_time = datetime.datetime.combine(
            date=self.last_month_last_day,
            time=datetime.time(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc))

    @staticmethod
    def create_order_date(payment_time: datetime.datetime, vo, user, length: int):
        order_list = []
        for i in range(length):
            order = Order(
                order_type=Order.OrderType.NEW.value,
                total_amount=Decimal(f'{i}.68'),
                payable_amount=Decimal(f'{i}.00'),
                pay_amount=Decimal(f'{i}.00'),
                balance_amount=Decimal('0'),
                coupon_amount=Decimal('0'),
                app_service_id='pay_app_service_id',
                service_id='service_id',
                service_name='service_name',
                resource_type=ResourceType.VM.value,
                instance_config='',
                period=6,
                pay_type=PayType.PREPAID.value,
                status=Order.Status.PAID.value,
                payment_time=payment_time,
                deleted=False,
                trading_status=Order.TradingStatus.OPENING.value,
                completion_time=None,
                creation_time=timezone.now()
            )
            if vo:
                order.vo_id = vo.id
                order.vo_name = vo.name
                order.owner_type = OwnerType.VO.value
            else:
                order.user_id = user.id
                order.username = user.username
                order.owner_type = OwnerType.USER.value

            order.save(force_insert=True)
            order_list.append(order)

        return order_list

    def init_order_date(self, nt: datetime.datetime):
        # user1
        order_list = self.create_order_date(payment_time=self.last_month_1st_time, user=self.user1, vo=None, length=6)
        # 1，2，3，4 in last month; ok (1, 2, 4), 0+1+3=4
        order1, order2, order3, order4, order5, order6 = order_list
        order2.payment_time = self.last_month_1st_time + timedelta(minutes=10)
        order2.status = Order.Status.PAID.value
        order2.trading_status = Order.TradingStatus.COMPLETED.value
        order2.save(update_fields=['payment_time', 'status', 'trading_status'])
        order3.payment_time = self.last_month_1st_time + timedelta(days=10)
        order3.status = Order.Status.UNPAID.value
        order3.save(update_fields=['payment_time', 'status'])
        order4.payment_time = self.last_month_1st_time + timedelta(days=20, minutes=40)
        order4.status = Order.Status.PAID.value
        order4.trading_status = Order.TradingStatus.COMPLETED.value
        order4.save(update_fields=['payment_time', 'status', 'trading_status'])

        order5.payment_time = self.last_month_1st_time - timedelta(minutes=50)
        order5.status = Order.Status.REFUND.value
        order5.save(update_fields=['payment_time', 'status'])
        order6.payment_time = self.last_month_last_day_time + timedelta(minutes=60)
        order6.status = Order.Status.PAID.value
        order6.save(update_fields=['payment_time', 'status'])

        # vo1
        order_list = self.create_order_date(payment_time=self.last_month_1st_time, user=None, vo=self.vo1, length=7)
        # 1，2，3，4, 7 in last month; ok (1, 2, 4, 7), 0+1+3+6=10
        order1, order2, order3, order4, order5, order6, order7 = order_list
        order2.payment_time = self.last_month_1st_time + timedelta(minutes=10)
        order2.status = Order.Status.PAID.value
        order2.trading_status = Order.TradingStatus.COMPLETED.value
        order2.save(update_fields=['payment_time', 'status', 'trading_status'])
        order3.payment_time = self.last_month_1st_time + timedelta(days=10)
        order3.status = Order.Status.UNPAID.value
        order3.save(update_fields=['payment_time', 'status'])
        order4.payment_time = self.last_month_1st_time + timedelta(days=20, minutes=40)
        order4.status = Order.Status.PAID.value
        order4.trading_status = Order.TradingStatus.COMPLETED.value
        order4.save(update_fields=['payment_time', 'status', 'trading_status'])

        order5.payment_time = self.last_month_1st_time - timedelta(minutes=50)
        order5.status = Order.Status.REFUND.value
        order5.save(update_fields=['payment_time', 'status'])
        order6.payment_time = self.last_month_last_day_time + timedelta(minutes=60)
        order6.status = Order.Status.PAID.value
        order6.save(update_fields=['payment_time', 'status'])

        order7.payment_time = self.last_month_1st_time + timedelta(days=25, minutes=6, seconds=1)
        order7.status = Order.Status.PAID.value
        order7.save(update_fields=['payment_time', 'status'])

    @staticmethod
    def create_server_metering(_date, server_id: str, user, vo, length: int):
        # 0,1 not in;  2,3,4,5,... in last month, when length < 28
        for i in range(length):
            ms = MeteringServer(
                cpu_hours=float(i),
                ram_hours=float(i+1),
                public_ip_hours=float(i + 2),
                disk_hours=float(i + 3),
                trade_amount=Decimal(f'{i}'),
                original_amount=Decimal(f'{2*i}'),
                service_id=None,
                server_id=server_id,
                date=_date + timedelta(days=i-2)
            )
            if user:
                ms.user_id = user.id
                ms.owner_type = OwnerType.USER.value
            else:
                ms.vo_id = vo.id
                ms.owner_type = OwnerType.VO.value

            ms.save(force_insert=True)

    def init_server_metering_data(self):
        # user1, 2,3,4,5;
        self.create_server_metering(
            _date=self.last_month_1st, server_id='server_id1', user=self.user1, vo=None, length=6)
        # user1, 2,3,4,5,6;
        self.create_server_metering(
            _date=self.last_month_1st, server_id='server_id2', user=self.user1, vo=None, length=7)
        # vo1, 2,3,4,5,6;
        self.create_server_metering(_date=self.last_month_1st, server_id='server_id3', user=None, vo=self.vo1, length=7)
        # vo1, 2,3,4,5,6,7;
        self.create_server_metering(_date=self.last_month_1st, server_id='server_id4', user=None, vo=self.vo1, length=8)
        # vo2, 2,3,4,5,6,7,8;
        self.create_server_metering(_date=self.last_month_1st, server_id='server_id5', user=None, vo=self.vo2, length=9)

    def init_server_daily_statement(self):
        # user1, 2,3,4,5;
        self.create_server_daily_statement(_date=self.last_month_1st, user=self.user1, vo=None, length=6)
        # user2, 2,3,4,5,6,7;
        self.create_server_daily_statement(_date=self.last_month_1st, user=self.user2, vo=None, length=8)
        # vo1, 2,3,4,5,6;
        self.create_server_daily_statement(_date=self.last_month_1st, user=None, vo=self.vo1, length=7)
        # vo2, 2,3,4,5,6,7,8;
        self.create_server_daily_statement(_date=self.last_month_1st, user=None, vo=self.vo2, length=9)

    @staticmethod
    def create_server_daily_statement(_date, user, vo, length: int):
        # 0,1 not in;  2,3,4,5,... in last month, when length < 28
        for i in range(length):
            u_st0 = DailyStatementServer(
                original_amount=Decimal(f'{i}.12'),
                payable_amount=Decimal(f'{i}.12'),
                trade_amount=Decimal(f'{i}.12'),
                payment_status=PaymentStatus.PAID.value,
                payment_history_id='',
                service_id=None,
                date=_date + timedelta(days=i - 2)
            )
            if user:
                u_st0.user_id = user.id
                u_st0.owner_type = OwnerType.USER.value
            else:
                u_st0.vo_id = vo.id
                u_st0.owner_type = OwnerType.VO.value

            u_st0.save(force_insert=True)

    def init_bucket_data(self):
        center = get_or_create_center()
        service1 = ObjectsService(
            name='service1', data_center_id=center.id,
            endpoint_url='service1', username='', password=''
        )
        service1.save(force_insert=True)
        service2 = ObjectsService(
            name='service2', data_center_id=center.id,
            endpoint_url='service2', username='', password=''
        )
        service2.save(force_insert=True)

        u1_b1 = Bucket(name='bucket1', service_id=service1.id, user_id=self.user1.id, creation_time=timezone.now())
        u1_b1.save(force_insert=True)
        u1_b2 = Bucket(name='bucket2', service_id=service1.id, user_id=self.user1.id, creation_time=timezone.now())
        u1_b2.save(force_insert=True)
        u1_b3 = Bucket(name='bucket3', service_id=service2.id, user_id=self.user1.id, creation_time=timezone.now())
        u1_b3.save(force_insert=True)
        u2_b4 = Bucket(name='bucket4', service_id=service1.id, user_id=self.user2.id, creation_time=timezone.now())
        u2_b4.save(force_insert=True)

        # user1, 2,3,4,5
        self.create_bucket_metering(
            _date=self.last_month_1st, service_id=u1_b1.service_id, bucket_id=u1_b1.id, user=u1_b1.user, length=6)
        # user1, 2,3,4,5,6
        self.create_bucket_metering(
            _date=self.last_month_1st, service_id=u1_b2.service_id, bucket_id=u1_b2.id, user=u1_b2.user, length=7)
        # user1, 2,3,4,5,6,7
        self.create_bucket_metering(
            _date=self.last_month_1st, service_id=u1_b3.service_id, bucket_id=u1_b3.id, user=u1_b3.user, length=8)

        # user2, 2,3,4,5,6,7,8
        self.create_bucket_metering(
            _date=self.last_month_1st, service_id=u2_b4.service_id, bucket_id=u2_b4.id, user=u2_b4.user, length=9)

        u1_b2_id = u1_b2.id
        ok = u1_b2.do_archive(archiver='test')
        self.assertIs(ok, True)
        u1_ba2 = BucketArchive.objects.get(original_id=u1_b2_id)

        return u1_b1, u1_ba2, u1_b3, u2_b4

    @staticmethod
    def create_bucket_metering(_date, service_id, bucket_id: str, user, length: int):
        # 0,1 not in;  2,3,4,5,... in last month, when length < 28
        for i in range(length):
            ms = MeteringObjectStorage(
                storage=i,
                trade_amount=Decimal(f'{i}'),
                original_amount=Decimal(f'{2 * i}'),
                daily_statement_id='',
                service_id=service_id,
                storage_bucket_id=bucket_id,
                user_id=user.id,
                username=user.username,
                date=_date + timedelta(days=i - 2)
            )

            ms.save(force_insert=True)

    def init_storage_daily_statement(self):
        # user1, 2,3,4,5;
        self.create_storage_daily_statement(_date=self.last_month_1st, user=self.user1, length=6)
        # user2, 2,3,4,5,6,7;
        self.create_storage_daily_statement(_date=self.last_month_1st, user=self.user2, length=8)

    @staticmethod
    def create_storage_daily_statement(_date, user, length: int):
        # 0,1 not in;  2,3,4,5,... in last month, when length < 28
        for i in range(length):
            u_st0 = DailyStatementObjectStorage(
                original_amount=Decimal(f'{i*2}.12'),
                payable_amount=Decimal(f'{i*3}.12'),
                trade_amount=Decimal(f'{i*4}.12'),
                payment_status=PaymentStatus.PAID.value,
                payment_history_id='',
                service_id=None,
                date=_date + timedelta(days=i - 2),
                user_id=user.id,
                username=user.username
            )

            u_st0.save(force_insert=True)

    @staticmethod
    def create_cashcoupons(now_time: datetime.datetime, app_service_id: str, vo, user, length: int):
        coupon_list = []
        for i in range(length):
            coupon = CashCoupon(
                face_value=Decimal(f'{i}.{i}'),
                balance=Decimal(f'{i}.{i}'),
                effective_time=now_time - timedelta(days=10*(i-3)),
                expiration_time=now_time + timedelta(days=10*(i-2)),
                status=CashCoupon.Status.AVAILABLE.value,
                app_service_id=app_service_id
            )
            if vo:
                coupon.vo_id = vo.id
                coupon.vo_name = vo.name
                coupon.owner_type = OwnerType.VO.value
            else:
                coupon.user_id = user.id
                coupon.username = user.username
                coupon.owner_type = OwnerType.USER.value

            coupon.save(force_insert=True)
            coupon_list.append(coupon)

        return coupon_list

    def init_coupons(self):
        # user1
        self.create_cashcoupons(
            now_time=self.last_month_last_day_time, user=self.user1, vo=None,
            app_service_id=self.app_service1.id, length=5)

        # user2
        self.create_cashcoupons(
            now_time=self.last_month_last_day_time, user=self.user2, vo=None,
            app_service_id=self.app_service2.id, length=6)

        # vo1
        self.create_cashcoupons(
            now_time=self.last_month_last_day_time, user=None, vo=self.vo1,
            app_service_id=self.app_service1.id, length=7)

    def test_monthly_report(self):
        # ----- no data ----
        mrg = MonthlyReportGenerator(limit=1, log_stdout=True)
        mrg.run()
        self.assertEqual(0, MonthlyReport.objects.count())

        # 用户和vo组在上月内和之前创建的才会生成月度报表
        self.user1.date_joined = mrg.last_month_1st_time
        self.user1.save(update_fields=['date_joined'])
        self.user2.date_joined = mrg.last_month_1st_time - timedelta(days=6)
        self.user2.save(update_fields=['date_joined'])
        self.vo1.creation_time = mrg.last_month_1st_time + timedelta(days=8)
        self.vo1.save(update_fields=['creation_time'])

        mrg.run()
        self.assertEqual(3, MonthlyReport.objects.count())

        self.vo2.creation_time = mrg.last_month_1st_time + timedelta(days=20)
        self.vo2.save(update_fields=['creation_time'])

        # user1
        u1_report: MonthlyReport = MonthlyReport.objects.filter(
            report_date=self.last_month_1st, user_id=self.user1.id, owner_type=OwnerType.USER.value).first()
        self.assertEqual(u1_report.server_prepaid_amount, Decimal('0'))
        self.assertEqual(u1_report.server_count, 0)
        self.assertEqual(u1_report.server_original_amount, Decimal('0'))
        self.assertEqual(u1_report.server_payable_amount, Decimal('0'))
        self.assertEqual(u1_report.server_cpu_days, 0)
        self.assertEqual(u1_report.server_ram_days, 0)
        self.assertEqual(u1_report.server_ip_days, 0)
        self.assertEqual(u1_report.server_disk_days, 0)
        self.assertEqual(u1_report.server_postpaid_amount, Decimal('0'))
        self.assertEqual(u1_report.bucket_count, 0)
        self.assertEqual(u1_report.storage_days, 0)
        self.assertEqual(u1_report.storage_original_amount, Decimal('0'))
        self.assertEqual(u1_report.storage_payable_amount, Decimal('0'))
        self.assertEqual(u1_report.storage_postpaid_amount, Decimal('0'))
        self.assertEqual(BucketMonthlyReport.objects.filter(
            user_id=self.user1.id, report_date=self.last_month_1st).count(), 0)

        # ----- init data ----
        nt = timezone.now()
        self.init_order_date(nt=nt)
        self.init_server_metering_data()
        self.init_server_daily_statement()
        u1_b1, u1_ba2, u1_b3, u2_b4 = self.init_bucket_data()
        self.init_storage_daily_statement()
        self.init_coupons()

        # 再此运行不会重复产生月度报表
        MonthlyReportGenerator(limit=1, log_stdout=True).run()
        self.assertEqual(4, MonthlyReport.objects.count())

        # user1
        u1_report: MonthlyReport = MonthlyReport.objects.filter(
            report_date=self.last_month_1st, user_id=self.user1.id, owner_type=OwnerType.USER.value).first()
        self.assertEqual(u1_report.server_prepaid_amount, Decimal('0'))
        self.assertEqual(u1_report.server_count, 0)
        self.assertEqual(u1_report.server_original_amount, Decimal('0'))
        self.assertEqual(u1_report.server_payable_amount, Decimal('0'))
        self.assertEqual(u1_report.server_cpu_days, 0)
        self.assertEqual(u1_report.server_ram_days, 0)
        self.assertEqual(u1_report.server_ip_days, 0)
        self.assertEqual(u1_report.server_disk_days, 0)
        self.assertEqual(u1_report.server_postpaid_amount, Decimal('0'))
        self.assertEqual(u1_report.bucket_count, 0)
        self.assertEqual(u1_report.storage_days, 0)
        self.assertEqual(u1_report.storage_original_amount, Decimal('0'))
        self.assertEqual(u1_report.storage_payable_amount, Decimal('0'))
        self.assertEqual(u1_report.storage_postpaid_amount, Decimal('0'))
        self.assertEqual(BucketMonthlyReport.objects.filter(
            user_id=self.user1.id, report_date=self.last_month_1st).count(), 0)

        # 重新产生月度报表
        MonthlyReport.objects.all().delete()

        MonthlyReportGenerator(limit=1, log_stdout=True).run()
        self.assertEqual(4, MonthlyReport.objects.count())

        # user1
        u1_report: MonthlyReport = MonthlyReport.objects.filter(
            report_date=self.last_month_1st, user_id=self.user1.id, owner_type=OwnerType.USER.value).first()
        self.assertEqual(u1_report.server_prepaid_amount, Decimal('4'))
        self.assertEqual(u1_report.server_count, 2)
        val = (2 + 3 + 4 + 5) * 2 + (2 + 3 + 4 + 5 + 6) * 2
        self.assertEqual(u1_report.server_original_amount, Decimal(f'{val}'))
        val = (2 + 3 + 4 + 5) + (2 + 3 + 4 + 5 + 6)
        self.assertEqual(u1_report.server_payable_amount, Decimal(f'{val}'))
        val = (2 + 3 + 4 + 5) + (2 + 3 + 4 + 5 + 6)
        self.assertEqual(u1_report.server_cpu_days * 24, val)
        val = (2 + 3 + 4 + 5) + (2 + 3 + 4 + 5 + 6) + 9
        self.assertEqual(u1_report.server_ram_days * 24, val)
        val = (2 + 3 + 4 + 5) + (2 + 3 + 4 + 5 + 6) + 9*2
        self.assertEqual(u1_report.server_ip_days * 24, val)
        val = (2 + 3 + 4 + 5) + (2 + 3 + 4 + 5 + 6) + 9 * 3
        self.assertEqual(u1_report.server_disk_days * 24, val)
        val = Decimal.from_float(2 + 3 + 4 + 5) + Decimal('0.12') * 4
        self.assertEqual(u1_report.server_postpaid_amount, val)

        self.assertEqual(u1_report.bucket_count, 3)
        val = (2 + 3 + 4 + 5) + (2 + 3 + 4 + 5 + 6) + (2 + 3 + 4 + 5 + 6 + 7)
        self.assertEqual(u1_report.storage_days * 24, val)
        self.assertEqual(u1_report.storage_original_amount, Decimal.from_float(val * 2))
        self.assertEqual(u1_report.storage_payable_amount, Decimal.from_float(val))
        self.assertEqual(u1_report.storage_postpaid_amount,
                         Decimal.from_float((2 + 3 + 4 + 5) * 4) + Decimal('0.12') * 4)

        self.assertEqual(BucketMonthlyReport.objects.filter(
            user_id=self.user1.id, report_date=self.last_month_1st).count(), 3)
        self.assertEqual(BucketMonthlyReport.objects.filter(
            user_id=self.user2.id, report_date=self.last_month_1st).count(), 1)
        mr_u1_b1 = BucketMonthlyReport.objects.get(
            user_id=self.user1.id, report_date=self.last_month_1st, bucket_id=u1_b1.id)
        self.assertEqual(mr_u1_b1.username, self.user1.username)
        self.assertEqual(mr_u1_b1.service_id, u1_b1.service_id)
        self.assertEqual(mr_u1_b1.service_name, u1_b1.service.name)
        self.assertEqual(mr_u1_b1.bucket_name, u1_b1.name)
        self.assertEqual(mr_u1_b1.storage_days * 24, 2 + 3 + 4 + 5)
        self.assertEqual(mr_u1_b1.payable_amount, Decimal.from_float(2 + 3 + 4 + 5))
        self.assertEqual(mr_u1_b1.original_amount, Decimal.from_float((2 + 3 + 4 + 5) * 2))

        mr_u1_ba2 = BucketMonthlyReport.objects.get(
            user_id=self.user1.id, report_date=self.last_month_1st, bucket_id=u1_ba2.original_id)
        self.assertEqual(mr_u1_ba2.username, self.user1.username)
        self.assertEqual(mr_u1_ba2.service_id, u1_ba2.service_id)
        self.assertEqual(mr_u1_ba2.service_name, u1_ba2.service.name)
        self.assertEqual(mr_u1_ba2.bucket_name, u1_ba2.name)
        self.assertEqual(mr_u1_ba2.storage_days * 24, 2 + 3 + 4 + 5 + 6)
        self.assertEqual(mr_u1_ba2.payable_amount, Decimal.from_float(2 + 3 + 4 + 5 + 6))
        self.assertEqual(mr_u1_ba2.original_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6) * 2))

        mr_u2_b4 = BucketMonthlyReport.objects.get(
            user_id=self.user2.id, report_date=self.last_month_1st, bucket_id=u2_b4.id)
        self.assertEqual(mr_u2_b4.username, self.user2.username)
        self.assertEqual(mr_u2_b4.service_id, u2_b4.service_id)
        self.assertEqual(mr_u2_b4.service_name, u2_b4.service.name)
        self.assertEqual(mr_u2_b4.bucket_name, u2_b4.name)
        self.assertEqual(mr_u2_b4.storage_days * 24, 2 + 3 + 4 + 5 + 6 + 7 + 8)
        self.assertEqual(mr_u2_b4.payable_amount, Decimal.from_float(2 + 3 + 4 + 5 + 6 + 7 + 8))
        self.assertEqual(mr_u2_b4.original_amount, Decimal.from_float((2 + 3 + 4 + 5 + 6 + 7 + 8) * 2))

        # vo1
        vo1_report: MonthlyReport = MonthlyReport.objects.filter(
            report_date=self.last_month_1st, vo_id=self.vo1.id, owner_type=OwnerType.VO.value).first()
        self.assertEqual(vo1_report.server_prepaid_amount, Decimal('10'))
        self.assertEqual(vo1_report.server_count, 2)
        val = (2 + 3 + 4 + 5 + 6) * 2 + (2 + 3 + 4 + 5 + 6 + 7) * 2
        self.assertEqual(vo1_report.server_original_amount, Decimal(f'{val}'))
        val = (2 + 3 + 4 + 5 + 6) + (2 + 3 + 4 + 5 + 6 + 7)
        self.assertEqual(vo1_report.server_payable_amount, Decimal(f'{val}'))
        val = (2 + 3 + 4 + 5 + 6) + (2 + 3 + 4 + 5 + 6 + 7)
        self.assertEqual(vo1_report.server_cpu_days * 24, val)
        val = (2 + 3 + 4 + 5 + 6) + (2 + 3 + 4 + 5 + 6 + 7) + 11
        self.assertEqual(vo1_report.server_ram_days * 24, val)
        val = (2 + 3 + 4 + 5 + 6) + (2 + 3 + 4 + 5 + 6 + 7) + 11 * 2
        self.assertEqual(vo1_report.server_ip_days * 24, val)
        val = (2 + 3 + 4 + 5 + 6) + (2 + 3 + 4 + 5 + 6 + 7) + 11 * 3
        self.assertEqual(vo1_report.server_disk_days * 24, val)
        val = Decimal.from_float(2 + 3 + 4 + 5 + 6) + Decimal('0.12') * 5
        self.assertEqual(vo1_report.server_postpaid_amount, val)
        self.assertEqual(vo1_report.bucket_count, 0)
        self.assertEqual(vo1_report.storage_days, 0)
        self.assertEqual(vo1_report.storage_original_amount, Decimal('0'))
        self.assertEqual(vo1_report.storage_payable_amount, Decimal('0'))
        self.assertEqual(vo1_report.storage_postpaid_amount, Decimal('0'))

        # vo2
        vo2_report: MonthlyReport = MonthlyReport.objects.filter(
            report_date=self.last_month_1st, vo_id=self.vo2.id, owner_type=OwnerType.VO.value).first()
        self.assertEqual(vo2_report.server_prepaid_amount, Decimal('0'))
        self.assertEqual(vo2_report.server_count, 1)
        val = (2 + 3 + 4 + 5 + 6 + 7 + 8) * 2
        self.assertEqual(vo2_report.server_original_amount, Decimal(f'{val}'))
        val = 2 + 3 + 4 + 5 + 6 + 7 + 8
        self.assertEqual(vo2_report.server_payable_amount, Decimal(f'{val}'))
        val = 2 + 3 + 4 + 5 + 6 + 7 + 8
        self.assertEqual(vo2_report.server_cpu_days * 24, val)
        val = 2 + 3 + 4 + 5 + 6 + 7 + 8 + 7
        self.assertEqual(vo2_report.server_ram_days * 24, val)
        val = 2 + 3 + 4 + 5 + 6 + 7 + 8 + 7 * 2
        self.assertEqual(vo2_report.server_ip_days * 24, val)
        val = 2 + 3 + 4 + 5 + 6 + 7 + 8 + 7 * 3
        self.assertEqual(vo2_report.server_disk_days * 24, val)
        val = Decimal.from_float(2 + 3 + 4 + 5 + 6 + 7 + 8) + Decimal('0.12') * 7
        self.assertEqual(vo2_report.server_postpaid_amount, val)

        from scripts.workers.report_generator import MonthlyReportNotifier
        MonthlyReportNotifier(log_stdout=True).run()
        self.assertEqual(len(mail.outbox), 2)
        u1_report.refresh_from_db()
        self.assertIsInstance(u1_report.notice_time, datetime.datetime)
        u2_report: MonthlyReport = MonthlyReport.objects.filter(
            report_date=self.last_month_1st, user_id=self.user2.id, owner_type=OwnerType.USER.value).first()
        self.assertIsInstance(u2_report.notice_time, datetime.datetime)
