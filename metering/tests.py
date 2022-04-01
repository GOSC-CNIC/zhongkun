from decimal import Decimal
from datetime import datetime, timedelta

from django.test import TransactionTestCase
from django.utils import timezone

from utils.test import get_or_create_user, get_or_create_service
from utils.model import PayType
from utils.decimal_utils import quantize_10_2
from servers.models import Server, ServerArchive
from vo.managers import VoManager
from metering.measurers import ServerMeasurer
from metering.models import MeteringServer, PaymentStatus
from order.models import Price


def create_server_metadata(
        service, user,
        vcpu: int, ram: int, disk_size: int, public_ip: bool,
        start_time, creation_time, vo_id=None,
        classification=Server.Classification.PERSONAL.value,
        task_status=Server.TASK_CREATED_OK,
        pay_type=PayType.PREPAID.value
):
    server = Server(
        service=service,
        instance_id='test',
        remarks='',
        user=user,
        vcpus=vcpu,
        ram=ram,
        disk_size=disk_size,
        ipv4='127.0.0.1',
        image='test-image',
        task_status=task_status,
        user_quota=None,
        public_ip=public_ip,
        classification=classification,
        vo_id=vo_id,
        image_id='',
        image_desc='image desc',
        default_user='root',
        creation_time=creation_time,
        start_time=start_time,
        pay_type=pay_type
    )
    server.raw_default_password = ''
    server.save()
    return server


def up_int(val, base=100):
    return int(val * base)


class MeteringServerTests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()
        self.vo = VoManager().create_vo(user=self.user, name='test vo', company='test', description='test')
        self.price = Price(
            vm_ram=Decimal('0.012'),
            vm_cpu=Decimal('0.066'),
            vm_disk=Decimal('0.122'),
            vm_pub_ip=Decimal('0.66'),
            vm_upstream=Decimal('0.33'),
            vm_downstream=Decimal('1.44'),
            vm_disk_snap=Decimal('0.65'),
            disk_size=Decimal('1.02'),
            disk_snap=Decimal('0.77'),
            obj_size=Decimal('0'),
            obj_upstream=Decimal('0'),
            obj_downstream=Decimal('0'),
            obj_replication=Decimal('0'),
            obj_get_request=Decimal('0'),
            obj_put_request=Decimal('0'),
            prepaid_discount=66
        )
        self.price.save()

    def init_data_only_server(self, now: datetime):
        ago_hour_time = now - timedelta(hours=1)
        meter_time = now - timedelta(days=1)
        ago_time = now - timedelta(days=2)

        # 个人的 计量24h
        server1 = create_server_metadata(
            service=self.service,
            user=self.user,
            vcpu=4,
            ram=4096,
            disk_size=100,
            public_ip=True,
            start_time=ago_time,
            creation_time=ago_time,
            pay_type=PayType.PREPAID.value
        )
        # vo的 计量 < 24h
        server2 = create_server_metadata(
            service=self.service,
            user=self.user,
            vcpu=3,
            ram=3072,
            disk_size=88,
            public_ip=False,
            start_time=meter_time,
            creation_time=meter_time,
            classification=Server.Classification.VO.value,
            vo_id=self.vo.id,
            pay_type=PayType.POSTPAID.value
        )

        # vo的 不会计量
        server3 = create_server_metadata(
            service=self.service,
            user=self.user,
            vcpu=3,
            ram=3072,
            disk_size=88,
            public_ip=False,
            start_time=meter_time,
            creation_time=meter_time,
            task_status=Server.TASK_CREATE_FAILED,
            classification=Server.Classification.VO.value,
            vo_id=self.vo.id
        )
        # 个人的 不会会计量
        server4 = create_server_metadata(
            service=self.service,
            user=self.user,
            vcpu=2,
            ram=2048,
            disk_size=188,
            public_ip=False,
            start_time=ago_hour_time,
            creation_time=ago_hour_time
        )

        return server1, server2, server3, server4

    def do_assert_server(self, now: datetime, server1: Server, server2: Server):
        metering_date = (now - timedelta(days=1)).date()
        metering_end_time = now.replace(hour=0, minute=0, second=0, microsecond=0)    # 计量结束时间
        measurer = ServerMeasurer(raise_exeption=True)
        measurer.run()

        count = MeteringServer.objects.all().count()
        self.assertEqual(count, 2)

        # server1
        metering = measurer.server_metering_exists(metering_date=metering_date, server_id=server1.id)
        self.assertIsNotNone(metering)
        self.assertEqual(up_int(metering.cpu_hours), up_int(server1.vcpus * 24))
        self.assertEqual(up_int(metering.ram_hours), up_int(server1.ram / 1024 * 24))
        self.assertEqual(up_int(metering.disk_hours), up_int(server1.disk_size * 24))
        self.assertEqual(metering.owner_type, metering.OwnerType.USER.value)
        if server1.public_ip:
            self.assertEqual(up_int(metering.public_ip_hours), up_int(24))
        else:
            self.assertEqual(up_int(metering.public_ip_hours), 0)

        original_amount1 = (self.price.vm_cpu * 4) + (self.price.vm_ram * 4) + (
                self.price.vm_disk * 100) + self.price.vm_pub_ip
        self.assertEqual(metering.original_amount, quantize_10_2(original_amount1))
        self.assertEqual(metering.trade_amount, Decimal(0))
        self.assertEqual(metering.pay_type, PayType.PREPAID.value)
        self.assertEqual(metering.payment_status, PaymentStatus.UNPAID.value)

        # server2
        hours = (metering_end_time - server2.start_time).total_seconds() / 3600
        metering = measurer.server_metering_exists(metering_date=metering_date, server_id=server2.id)
        self.assertIsNotNone(metering)
        self.assertEqual(up_int(metering.cpu_hours), up_int(server2.vcpus * hours))
        self.assertEqual(up_int(metering.ram_hours), up_int(server2.ram / 1024 * hours))
        self.assertEqual(up_int(metering.disk_hours), up_int(server2.disk_size * hours))
        self.assertEqual(metering.owner_type, metering.OwnerType.VO.value)
        if server2.public_ip:
            self.assertEqual(up_int(metering.public_ip_hours), up_int(hours))
        else:
            self.assertEqual(up_int(metering.public_ip_hours), 0)

        original_amount2 = (self.price.vm_cpu * 3) + (self.price.vm_ram * 3) + (self.price.vm_disk * 88)
        original_amount2 = original_amount2 * Decimal.from_float(hours / 24)
        self.assertEqual(metering.original_amount, quantize_10_2(original_amount2))
        self.assertEqual(metering.trade_amount, Decimal(0))
        self.assertEqual(metering.pay_type, PayType.POSTPAID.value)
        self.assertEqual(metering.payment_status, PaymentStatus.UNPAID.value)

        measurer.run()
        count = MeteringServer.objects.all().count()
        self.assertEqual(count, 2)

    def test_only_server(self):
        now = timezone.now()
        server1, server2, server3, server4 = self.init_data_only_server(now)
        self.do_assert_server(now=now, server1=server1, server2=server2)

    def test_archive_server(self):
        now = timezone.now()
        server1, server2, server3, server4 = self.init_data_only_server(now)

        server1_id = server1.id
        ok = server1.do_archive(archive_user=self.user)
        self.assertIs(ok, True)
        server1.id = server1_id
        self.do_assert_server(now=now, server1=server1, server2=server2)

    def test_archive_rebuild_server(self):
        now = timezone.now()
        server1, server2, server3, server4 = self.init_data_only_server(now)

        server1_id = server1.id

        archive = ServerArchive.init_archive_fron_server(
            server=server1, archive_user=self.user, archive_type=ServerArchive.ArchiveType.REBUILD.value, commit=True)
        new_starttime = archive.deleted_time - timedelta(days=1)
        archive.deleted_time = new_starttime
        archive.save(update_fields=['deleted_time'])
        server1.start_time = archive.deleted_time
        server1.save(update_fields=['start_time'])

        ok = server1.do_archive(archive_user=self.user)
        self.assertIs(ok, True)
        server1.id = server1_id
        self.do_assert_server(now=now, server1=server1, server2=server2)
