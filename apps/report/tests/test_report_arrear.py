import datetime
from decimal import Decimal

from django.utils import timezone as dj_timezone
from django.test.testcases import TransactionTestCase
from django.conf import settings

from core import site_configs_manager
from utils.test import get_or_create_user, get_or_create_organization, get_or_create_org_data_center
from utils.time import utc
from utils.model import PayType, OwnerType
from vo.models import VirtualOrganization
from apps.app_wallet.models import PayApp, PayAppService
from apps.app_wallet.managers import PaymentManager, CashCouponManager
from storage.models import ObjectsService, Bucket
from servers.models import Server, ServiceConfig
from servers.tests import create_server_metadata
from report.models import ArrearBucket, ArrearServer
from apps.report.workers.storage_trend import ArrearBucketReporter
from apps.report.workers.server_notifier import ArrearServerReporter


PAY_APP_ID = site_configs_manager.get_pay_app_id(settings)


class ArrearServerReporterTests(TransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='lilei@cnic.cn')
        self.user2 = get_or_create_user(username='tom@qq.com')
        self.user3 = get_or_create_user(username='zhangsan@qq.com')
        self.vo1 = VirtualOrganization(name='vo1', owner_id=self.user1.id)
        self.vo1.save(force_insert=True)
        self.vo2 = VirtualOrganization(name='vo2', owner_id=self.user2.id)
        self.vo2.save(force_insert=True)

        # 余额支付有关配置
        self.app = PayApp(name='app', id=PAY_APP_ID)
        self.app.save(force_insert=True)
        self.org1 = get_or_create_organization(name='机构')
        self.app_service1 = PayAppService(
            id='123', name='service1', app=self.app, orgnazition=self.org1,
            category=PayAppService.Category.VMS_SERVER.value
        )
        self.app_service1.save(force_insert=True)
        self.app_service2 = PayAppService(
            id='1234', name='service2', app=self.app, orgnazition=self.org1,
            category=PayAppService.Category.VMS_SERVER.value
        )
        self.app_service2.save(force_insert=True)

        odc = get_or_create_org_data_center()
        self.service1 = ServiceConfig(
            name='service1', org_data_center_id=odc.id,
            endpoint_url='service1', username='', password='', pay_app_service_id=self.app_service1.id
        )
        self.service1.save(force_insert=True)
        self.service2 = ServiceConfig(
            name='service2', org_data_center_id=odc.id,
            endpoint_url='service2', username='', password='', pay_app_service_id=self.app_service2.id
        )
        self.service2.save(force_insert=True)

    def init_server_data(self):
        service1 = self.service1
        service2 = self.service2

        nt = dj_timezone.now()
        # user1, 过期
        self.server1 = create_server_metadata(
            service=service1, user=self.user1, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.1', pay_type=PayType.PREPAID.value, expiration_time=nt - datetime.timedelta(days=10)
        )
        # 过期1天
        self.server2 = create_server_metadata(
            service=service2, user=self.user1, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.2', pay_type=PayType.PREPAID.value, expiration_time=nt - datetime.timedelta(days=1)
        )
        # 按量计费
        self.server3 = create_server_metadata(
            service=service1, user=self.user1, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.3', pay_type=PayType.POSTPAID.value, expiration_time=None
        )
        self.server4 = create_server_metadata(
            service=service2, user=self.user1, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.4', pay_type=PayType.POSTPAID.value, expiration_time=None
        )
        # user2, 按量计费
        self.server5 = create_server_metadata(
            service=service1, user=self.user2, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.5', pay_type=PayType.POSTPAID.value, expiration_time=None
        )
        self.server6 = create_server_metadata(
            service=service2, user=self.user2, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.6', pay_type=PayType.POSTPAID.value, expiration_time=None
        )
        # ------ vo ------
        # vo1, 过期
        self.server1_vo1 = create_server_metadata(
            service=service1, user=self.user1, vo_id=self.vo1.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.11', pay_type=PayType.PREPAID.value, expiration_time=nt - datetime.timedelta(days=1)
        )
        # 按量计费
        self.server2_vo1 = create_server_metadata(
            service=service1, user=self.user1, vo_id=self.vo1.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.12', pay_type=PayType.POSTPAID.value, expiration_time=None
        )
        self.server3_vo1 = create_server_metadata(
            service=service2, user=self.user1, vo_id=self.vo1.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.13', pay_type=PayType.POSTPAID.value, expiration_time=None
        )

        # vo2, 3天后到期
        self.server4_vo2 = create_server_metadata(
            service=service1, user=self.user2, vo_id=self.vo2.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.14', pay_type=PayType.PREPAID.value, expiration_time=nt + datetime.timedelta(days=3)
        )
        # 过期16天
        self.server5_vo2 = create_server_metadata(
            service=service1, user=self.user1, vo_id=self.vo2.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.15', pay_type=PayType.PREPAID.value, expiration_time=nt - datetime.timedelta(days=16)
        )
        # 到期2天
        self.server6_vo2 = create_server_metadata(
            service=service2, user=self.user1, vo_id=self.vo2.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.16', pay_type=PayType.PREPAID.value, expiration_time=nt - datetime.timedelta(days=2)
        )

    def test_no_arrear(self):
        """
        无欠费，无券
        """
        self.init_server_data()

        self.assertEqual(ArrearBucket.objects.count(), 0)
        ArrearServerReporter().run()
        self.assertEqual(ArrearBucket.objects.count(), 0)

    def test_arrear(self):
        """
        有余额欠费，有券
        """
        now_time = dj_timezone.now()
        self.init_server_data()
        # user1，balance < 0, service1 coupon, 只有service1的云主机不欠费
        u1_account = PaymentManager.get_user_point_account(user_id=self.user1.id)
        u1_account.balance = Decimal('-1.00')
        u1_account.save(update_fields=['balance'])
        u1_coupon1 = CashCouponManager().create_one_coupon_to_user_or_vo(
            user=self.user1, vo=None, app_service_id=self.service1.pay_app_service_id, face_value=Decimal('10'),
            effective_time=now_time - datetime.timedelta(days=1),
            expiration_time=now_time + datetime.timedelta(days=10), issuer=''
        )
        # expired
        u1_coupon2 = CashCouponManager().create_one_coupon_to_user_or_vo(
            user=self.user1, vo=None, app_service_id=self.service2.pay_app_service_id, face_value=Decimal('66'),
            effective_time=now_time - datetime.timedelta(days=10),
            expiration_time=now_time - datetime.timedelta(days=1), issuer=''
        )

        # user2，balance > 0, no coupon
        u2_account = PaymentManager.get_user_point_account(user_id=self.user2.id)
        u2_account.balance = Decimal('0.01')
        u2_account.save(update_fields=['balance'])
        # expired
        u2_coupon1 = CashCouponManager().create_one_coupon_to_user_or_vo(
            user=self.user2, vo=None, app_service_id=self.service1.pay_app_service_id, face_value=Decimal('10'),
            effective_time=now_time - datetime.timedelta(days=11),
            expiration_time=now_time - datetime.timedelta(days=2), issuer=''
        )
        u2_coupon2 = CashCouponManager().create_one_coupon_to_user_or_vo(
            user=self.user2, vo=None, app_service_id=self.service2.pay_app_service_id, face_value=Decimal('66'),
            effective_time=now_time - datetime.timedelta(days=10),
            expiration_time=now_time - datetime.timedelta(days=1), issuer=''
        )

        # vo1，balance < 0, service1 coupon, 只有service1的包年包月过期云主机不欠费
        vo1_account = PaymentManager.get_vo_point_account(vo_id=self.vo1.id)
        vo1_account.balance = Decimal('-0.20')
        vo1_account.save(update_fields=['balance'])
        vo1_coupon1 = CashCouponManager().create_one_coupon_to_user_or_vo(
            user=self.user1, vo=self.vo1, app_service_id=self.service1.pay_app_service_id, face_value=Decimal('10'),
            effective_time=now_time - datetime.timedelta(days=1),
            expiration_time=now_time + datetime.timedelta(days=10), issuer=''
        )
        # expired
        vo1_coupon2 = CashCouponManager().create_one_coupon_to_user_or_vo(
            user=None, vo=self.vo1, app_service_id=self.service2.pay_app_service_id, face_value=Decimal('66'),
            effective_time=now_time - datetime.timedelta(days=10),
            expiration_time=now_time - datetime.timedelta(days=1), issuer=''
        )

        # vo2，balance < 0, no coupon
        vo2_account = PaymentManager.get_vo_point_account(vo_id=self.vo2.id)
        vo2_account.balance = Decimal('-0.11')
        vo2_account.save(update_fields=['balance'])
        # expired
        vo2_coupon1 = CashCouponManager().create_one_coupon_to_user_or_vo(
            user=None, vo=self.vo2, app_service_id=self.service1.pay_app_service_id, face_value=Decimal('10'),
            effective_time=now_time - datetime.timedelta(days=11),
            expiration_time=now_time - datetime.timedelta(days=2), issuer=''
        )
        vo2_coupon2 = CashCouponManager().create_one_coupon_to_user_or_vo(
            user=None, vo=self.vo2, app_service_id=self.service2.pay_app_service_id, face_value=Decimal('66'),
            effective_time=now_time - datetime.timedelta(days=10),
            expiration_time=now_time - datetime.timedelta(days=1), issuer=''
        )

        self.assertEqual(ArrearServer.objects.count(), 0)
        ArrearServerReporter().run()
        # user1: server2\4
        # user2: no
        # vo1: vo_server3
        # vo2: vo_server5\6
        self.assertEqual(ArrearServer.objects.count(), 5)
        u1_s2 = self.server2
        asv: ArrearServer = ArrearServer.objects.filter(server_id=u1_s2.id).first()
        self.assertIsNotNone(asv)
        self.assertEqual(asv.service_id, u1_s2.service_id)
        self.assertEqual(asv.service_name, u1_s2.service.name)
        self.assertEqual(asv.ipv4, u1_s2.ipv4)
        self.assertEqual(asv.vcpus, u1_s2.vcpus)
        self.assertEqual(asv.ram, u1_s2.ram)
        self.assertEqual(asv.image, u1_s2.image)
        self.assertEqual(asv.pay_type, u1_s2.pay_type)
        self.assertEqual(asv.user_id, u1_s2.user_id)
        self.assertEqual(asv.username, u1_s2.user.username)
        self.assertEqual(asv.owner_type, OwnerType.USER.value)
        self.assertEqual(asv.server_creation, u1_s2.creation_time)
        self.assertEqual(asv.server_expire, u1_s2.expiration_time)
        self.assertEqual(asv.remarks, u1_s2.remarks)
        self.assertEqual(asv.balance_amount, Decimal('-1.00'))
        self.assertEqual(asv.date, now_time.date())

        asv4: ArrearServer = ArrearServer.objects.filter(server_id=self.server4.id).first()
        self.assertIsNotNone(asv4)
        self.assertEqual(asv4.ipv4, self.server4.ipv4)
        self.assertEqual(asv4.balance_amount, Decimal('-1.00'))

        # vo1
        asv: ArrearServer = ArrearServer.objects.filter(server_id=self.server3_vo1.id).first()
        self.assertIsNotNone(asv)
        self.assertEqual(asv.ipv4, self.server3_vo1.ipv4)
        self.assertEqual(asv.balance_amount, Decimal('-0.20'))

        # vo2
        asv: ArrearServer = ArrearServer.objects.filter(server_id=self.server5_vo2.id).first()
        self.assertIsNotNone(asv)
        self.assertEqual(asv.ipv4, self.server5_vo2.ipv4)
        self.assertEqual(asv.balance_amount, Decimal('-0.11'))
        asv: ArrearServer = ArrearServer.objects.filter(server_id=self.server6_vo2.id).first()
        self.assertIsNotNone(asv)
        self.assertEqual(asv.ipv4, self.server6_vo2.ipv4)
        self.assertEqual(asv.balance_amount, Decimal('-0.11'))


class ArrearBucketReporterTests(TransactionTestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='lilei@cnic.cn')
        self.user2 = get_or_create_user(username='tom@qq.com')
        self.user3 = get_or_create_user(username='zhangsan@qq.com')

        # 余额支付有关配置
        self.app = PayApp(name='app', id=PAY_APP_ID)
        self.app.save(force_insert=True)
        self.po = get_or_create_organization(name='机构')
        self.po.save()
        self.app_service1 = PayAppService(
            id='123', name='service1', app=self.app, orgnazition=self.po
        )
        self.app_service1.save()
        self.app_service2 = PayAppService(
            id='1234', name='service2', app=self.app, orgnazition=self.po
        )
        self.app_service2.save()

        odc = get_or_create_org_data_center()
        self.service1 = ObjectsService(
            name='service1', org_data_center_id=odc.id,
            endpoint_url='service1', username='', password='', pay_app_service_id=self.app_service1.id
        )
        self.service1.save(force_insert=True)
        self.service2 = ObjectsService(
            name='service2', org_data_center_id=odc.id,
            endpoint_url='service2', username='', password='', pay_app_service_id=self.app_service2.id
        )
        self.service2.save(force_insert=True)

    def init_bucket_data(self):
        service1 = self.service1
        service2 = self.service2

        u1_s1_b1 = Bucket(
            name='bucket1', service_id=service1.id, user_id=self.user1.id,
            creation_time=datetime.datetime(year=2023, month=10, day=1, tzinfo=utc),
            storage_size=1000, object_count=10)
        u1_s1_b1.save(force_insert=True)
        u1_s2_b2 = Bucket(
            name='bucket2', service_id=service2.id, user_id=self.user1.id,
            creation_time=datetime.datetime(year=2023, month=6, day=1, tzinfo=utc),
            storage_size=2000, object_count=20)
        u1_s2_b2.save(force_insert=True)

        u2_s1_b3 = Bucket(
            name='bucket3', service_id=service1.id, user_id=self.user2.id,
            creation_time=datetime.datetime(year=2024, month=1, day=1, tzinfo=utc),
            storage_size=3000, object_count=30)
        u2_s1_b3.save(force_insert=True)
        u2_s2_b4 = Bucket(
            name='bucket4', service_id=service2.id, user_id=self.user2.id,
            creation_time=datetime.datetime(year=2022, month=8, day=12, tzinfo=utc),
            storage_size=4000, object_count=40)
        u2_s2_b4.save(force_insert=True)
        u3_s1_b5 = Bucket(
            name='bucket5', service_id=service1.id, user_id=self.user3.id,
            creation_time=dj_timezone.now(), storage_size=0, object_count=0)
        u3_s1_b5.save(force_insert=True)

        return u1_s1_b1, u1_s2_b2, u2_s1_b3, u2_s2_b4, u3_s1_b5

    def test_no_arrear(self):
        """
        无欠费，无券
        """
        self.init_bucket_data()

        self.assertEqual(ArrearBucket.objects.count(), 0)
        ArrearBucketReporter().run()
        self.assertEqual(ArrearBucket.objects.count(), 0)

    def test_arrear(self):
        """
        有余额欠费，有券
        """
        now_time = dj_timezone.now()
        u1_s1_b1, u1_s2_b2, u2_s1_b3, u2_s2_b4, u3_s1_b5 = self.init_bucket_data()
        # user1，balance < 0, no coupon
        u1_account = PaymentManager.get_user_point_account(user_id=self.user1.id)
        u1_account.balance = Decimal('-1.00')
        u1_account.save(update_fields=['balance'])

        # user2，balance < 0, service1 coupon
        u2_account = PaymentManager.get_user_point_account(user_id=self.user2.id)
        u2_account.balance = Decimal('-0.01')
        u2_account.save(update_fields=['balance'])
        u2_coupon1 = CashCouponManager().create_one_coupon_to_user_or_vo(
            user=self.user2, vo=None, app_service_id=self.service1.pay_app_service_id, face_value=Decimal('10'),
            effective_time=now_time - datetime.timedelta(days=1),
            expiration_time=now_time + datetime.timedelta(days=10), issuer=''
        )
        # expired
        u2_coupon2 = CashCouponManager().create_one_coupon_to_user_or_vo(
            user=self.user2, vo=None, app_service_id=self.service2.pay_app_service_id, face_value=Decimal('66'),
            effective_time=now_time - datetime.timedelta(days=10),
            expiration_time=now_time - datetime.timedelta(days=1), issuer=''
        )

        self.assertEqual(ArrearBucket.objects.count(), 0)
        ArrearBucketReporter().run()
        # u1_s1_b1, u1_s2_b2, u2_s2_b4
        self.assertEqual(ArrearBucket.objects.count(), 3)
        ab: ArrearBucket = ArrearBucket.objects.filter(bucket_id=u1_s1_b1.id).first()
        self.assertIsNotNone(ab)
        self.assertEqual(ab.bucket_name, u1_s1_b1.name)
        self.assertEqual(ab.service_id, u1_s1_b1.service_id)
        self.assertEqual(ab.service_name, u1_s1_b1.service.name)
        self.assertEqual(ab.size_byte, u1_s1_b1.storage_size)
        self.assertEqual(ab.user_id, u1_s1_b1.user_id)
        self.assertEqual(ab.username, u1_s1_b1.user.username)
        self.assertEqual(ab.bucket_creation, u1_s1_b1.creation_time)
        self.assertEqual(ab.balance_amount, Decimal('-1.00'))
        self.assertEqual(ab.date, now_time.date())

        ab: ArrearBucket = ArrearBucket.objects.filter(bucket_id=u1_s2_b2.id).first()
        self.assertIsNotNone(ab)
        self.assertEqual(ab.bucket_name, u1_s2_b2.name)
        self.assertEqual(ab.balance_amount, Decimal('-1.00'))

        ab: ArrearBucket = ArrearBucket.objects.filter(bucket_id=u2_s2_b4.id).first()
        self.assertIsNotNone(ab)
        self.assertEqual(ab.bucket_name, u2_s2_b4.name)
        self.assertEqual(ab.balance_amount, Decimal('-0.01'))
