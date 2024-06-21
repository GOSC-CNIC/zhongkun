import uuid
from decimal import Decimal
from datetime import timedelta

from django.utils import timezone as dj_timezone

from core.adapters import inputs, outputs
from core import errors
from utils.model import PayType, OwnerType, ResourceType
from apps.order.models import Order, Resource
from apps.order.managers import OrderManager
from apps.order.managers.instance_configs import ServerConfig, ScanConfig, ServerSnapshotConfig
from apps.order.deliver_resource import OrderResourceDeliverer
from apps.order.tests import create_price
from utils.test import get_or_create_user, MyAPITransactionTestCase
from apps.servers.models import ServiceConfig, Server, ServerSnapshot
from apps.vo.models import VirtualOrganization
from apps.servers.managers import ServicePrivateQuotaManager, ServerSnapshotManager
from apps.servers.tests import create_server_metadata
from apps.app_scan.models import VtTask


class CreateServerRequest:
    def __init__(self):
        self.is_new_server_ok_once = False  # 用于标记请求创建server成功

    @staticmethod
    def request_create_server_ok(service, params: inputs.ServerCreateInput):
        return outputs.ServerCreateOutput(
            server=outputs.ServerCreateOutputServer(
                uuid=str(uuid.uuid1()), name='', default_user='root', default_password='password'
            )
        )

    @staticmethod
    def request_create_server_error(service, params: inputs.ServerCreateInput):
        raise errors.APIException(message="adapter error: test case")

    def clear_create_server_once_ok_flag(self):
        self.is_new_server_ok_once = False

    def request_create_server_once_ok(self, service, params: inputs.ServerCreateInput):
        if self.is_new_server_ok_once:
            raise errors.APIException(message="adapter error: test case")

        self.is_new_server_ok_once = True
        return self.request_create_server_ok(service=service, params=params)


class SnapshotRequest:
    def __init__(self, create_ok: bool, delete_ok: bool):
        self.create_ok = create_ok
        self.delete_ok = delete_ok

    def server_snapshot_create(self):
        if self.create_ok:
            return outputs.ServerSnapshotCreateOutput(
                snapshot=outputs.ServerSnapshot(snap_id='snap_id_test', description='snap desc')
            )

        raise errors.APIException(message="adapter error: test case create snapshot")

    def server_snapshot_delete(self):
        if self.delete_ok:
            return outputs.ServerSnapshotDeleteOutput(ok=True)

        raise errors.APIException(message="adapter error: test case delete snapshot")


class DelivererRequestService:
    def __init__(self, snap_request: SnapshotRequest):
        self.snap_request = snap_request

    def deliverer_request_service(self, service, method: str, params: inputs.InputBase):
        if method == 'server_snapshot_create':
            return self.snap_request.server_snapshot_create()
        elif method == 'server_snapshot_delete':
            return self.snap_request.server_snapshot_delete()

        raise Exception(f'未覆盖的请求，method={method}')


class DeliverTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.user2 = get_or_create_user(username='user2')

        self.vo = VirtualOrganization(
            name='test vo', owner=self.user
        )
        self.vo.save(force_insert=True)
        self.service1 = ServiceConfig(
            name='service1', name_en='service1 en'
        )
        self.service1.save(force_insert=True)
        self.price = create_price()

    def test_one_server_order_deliver(self):
        cs_req = CreateServerRequest()

        instance_config = ServerConfig(
            vm_cpu=2, vm_ram=4, systemdisk_size=100, public_ip=True,
            image_id='test', image_name='', network_id='network_id', network_name='',
            azone_id='', azone_name='', flavor_id=''
        )
        # 创建订单
        order1, resource_list = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=self.service1.pay_app_service_id,
            service_id=self.service1.id,
            service_name=self.service1.name,
            resource_type=ResourceType.VM.value,
            instance_config=instance_config,
            period=8,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.PREPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
            remark='testcase创建，可删除'
        )
        or_dlver = OrderResourceDeliverer()
        or_dlver._request_create_server = cs_req.request_create_server_error  # 替换创建请求方法

        # order unpaid
        with self.assertRaises(errors.OrderUnpaid):
            or_dlver.deliver_order(order1, resource=None)

        order1.set_paid(
            pay_amount=Decimal('0'), balance_amount=Decimal('0'), coupon_amount=Decimal('0'), payment_history_id='')

        s1_quota = ServicePrivateQuotaManager().get_quota(service=self.service1)
        ServicePrivateQuotaManager().update(service=self.service1, vcpus=2, ram_gib=3, public_ip=1)
        self.assertEqual(s1_quota.vcpu_used, 0)
        self.assertEqual(s1_quota.ram_used, 0)
        od1_res1 = resource_list[0]
        od1_res1.refresh_from_db()
        self.assertIsNone(od1_res1.last_deliver_time)
        self.assertEqual(order1.trading_status, order1.TradingStatus.OPENING.value)
        self.assertEqual(od1_res1.instance_status, od1_res1.InstanceStatus.WAIT.value)

        # 资源配额不足
        with self.assertRaises(errors.QuotaShortageError):
            or_dlver.deliver_order(order1, resource=None)

        s1_quota.refresh_from_db()
        self.assertEqual(s1_quota.vcpu_used, 0)
        self.assertEqual(s1_quota.ram_used, 0)
        order1.refresh_from_db()
        self.assertEqual(order1.trading_status, order1.TradingStatus.UNDELIVERED.value)
        od1_res1.refresh_from_db()
        self.assertIsNotNone(od1_res1.last_deliver_time)
        self.assertLess(od1_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od1_res1.instance_status, od1_res1.InstanceStatus.FAILED.value)

        # 请求太频繁
        ServicePrivateQuotaManager().update(service=self.service1, vcpus=2, ram_gib=4, public_ip=1)
        with self.assertRaises(errors.TryAgainLater) as cm:
            or_dlver.deliver_order(order1, resource=None)
        self.assertEqual(cm.exception.code, 'TryAgainLater')
        self.assertEqual(cm.exception.status_code, 409)

        od1_res1.last_deliver_time = dj_timezone.now() - timedelta(seconds=55)
        od1_res1.save(update_fields=['last_deliver_time'])

        with self.assertRaises(errors.TryAgainLater) as cm:
            or_dlver.deliver_order(order1, resource=None)
        self.assertEqual(cm.exception.code, 'TryAgainLater')
        self.assertEqual(cm.exception.status_code, 409)

        od1_res1.last_deliver_time = dj_timezone.now() - timedelta(seconds=60)
        od1_res1.save(update_fields=['last_deliver_time'])

        # 请求错误
        with self.assertRaises(errors.APIException) as cm:
            or_dlver.deliver_order(order1, resource=None)
        self.assertEqual(cm.exception.code, 'InternalError')
        self.assertEqual(cm.exception.status_code, 500)

        s1_quota.refresh_from_db()
        self.assertEqual(s1_quota.vcpu_used, 0)
        self.assertEqual(s1_quota.ram_used, 0)
        order1.refresh_from_db()
        self.assertEqual(order1.trading_status, order1.TradingStatus.UNDELIVERED.value)
        od1_res1.refresh_from_db()
        self.assertLess(od1_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od1_res1.instance_status, od1_res1.InstanceStatus.FAILED.value)
        self.assertFalse(Server.objects.filter(id=od1_res1.instance_id).exists())

        # 请求success
        now_time = dj_timezone.now()
        od1_res1.last_deliver_time = dj_timezone.now() - timedelta(minutes=2)
        od1_res1.save(update_fields=['last_deliver_time'])
        or_dlver._request_create_server = cs_req.request_create_server_ok    # 替换创建请求方法
        or_dlver.deliver_order(order1, resource=None)
        s1_quota.refresh_from_db()
        self.assertEqual(s1_quota.vcpu_used, 2)
        self.assertEqual(s1_quota.ram_used, 4)
        self.assertEqual(s1_quota.public_ip_used, 1)
        order1.refresh_from_db()
        self.assertEqual(order1.trading_status, order1.TradingStatus.COMPLETED.value)
        od1_res1.refresh_from_db()
        self.assertLess(od1_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od1_res1.instance_status, od1_res1.InstanceStatus.SUCCESS.value)
        self.assertTrue(Server.objects.filter(id=od1_res1.instance_id).exists())
        # server 过期时间
        s = Server.objects.filter(id=od1_res1.instance_id).first()
        self.assertTrue((s.expiration_time - now_time) > timedelta(days=30 * 8))
        self.assertTrue((s.expiration_time - now_time) < timedelta(days=30*8 + 1))

        with self.assertRaises(errors.OrderTradingCompleted):
            or_dlver.deliver_order(order1, resource=None)

        # 创建订单2
        order2, resource_list2 = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=self.service1.pay_app_service_id,
            service_id=self.service1.id,
            service_name=self.service1.name,
            resource_type=ResourceType.VM.value,
            instance_config=instance_config,
            period=100,
            period_unit=Order.PeriodUnit.DAY.value,
            pay_type=PayType.PREPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
            remark='testcase创建，可删除'
        )
        od2_res1 = resource_list2[0]
        order2.set_paid(
            pay_amount=Decimal('0'), balance_amount=Decimal('0'), coupon_amount=Decimal('0'), payment_history_id='')
        or_dlver = OrderResourceDeliverer()
        or_dlver._request_create_server = cs_req.request_create_server_ok  # 替换创建请求方法
        ServicePrivateQuotaManager().increase(service=self.service1, vcpus=2, ram_gib=4, public_ip=1)

        # 请求success
        now_time = dj_timezone.now()
        or_dlver.deliver_order(order2, resource=None)
        s1_quota.refresh_from_db()
        self.assertEqual(s1_quota.vcpu_used, 2 + 2)
        self.assertEqual(s1_quota.ram_used, 4 + 4)
        self.assertEqual(s1_quota.public_ip_used, 1 + 1)
        order2.refresh_from_db()
        self.assertEqual(order2.trading_status, order2.TradingStatus.COMPLETED.value)
        od2_res1.refresh_from_db()
        self.assertLess(od2_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od2_res1.instance_status, od2_res1.InstanceStatus.SUCCESS.value)
        self.assertTrue(Server.objects.filter(id=od2_res1.instance_id).exists())
        # server 过期时间
        s = Server.objects.filter(id=od2_res1.instance_id).first()
        self.assertTrue((s.expiration_time - now_time) > timedelta(days=100))
        self.assertTrue((s.expiration_time - now_time) < timedelta(days=101))

    def _assert_res(self, res: Resource, instance_status=Resource.InstanceStatus.FAILED.value):
        res.refresh_from_db()
        self.assertIsNotNone(res.last_deliver_time)
        self.assertLess(res.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(res.instance_status, instance_status)

    def test_many_server_order_deliver(self):
        cs_req = CreateServerRequest()
        s1_quota = ServicePrivateQuotaManager().get_quota(service=self.service1)
        instance_config = ServerConfig(
            vm_cpu=2, vm_ram=4, systemdisk_size=50, public_ip=True,
            image_id='test', image_name='', network_id='network_id', network_name='',
            azone_id='', azone_name='', flavor_id=''
        )
        # 创建订单
        order1, resource_list = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=self.service1.pay_app_service_id,
            service_id=self.service1.id,
            service_name=self.service1.name,
            resource_type=ResourceType.VM.value,
            instance_config=instance_config,
            period=8,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.PREPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
            remark='testcase创建，可删除',
            number=3
        )
        or_dlver = OrderResourceDeliverer()
        or_dlver._request_create_server = cs_req.request_create_server_error  # 替换创建请求方法

        # order unpaid
        with self.assertRaises(errors.OrderUnpaid):
            or_dlver.deliver_order(order1, resource=None)

        order1.set_paid(
            pay_amount=Decimal('0'), balance_amount=Decimal('0'), coupon_amount=Decimal('0'), payment_history_id='')

        ServicePrivateQuotaManager().update(service=self.service1, vcpus=2, ram_gib=3, public_ip=1)
        od1_res1, od1_res2, od1_res3 = resource_list
        od1_res1.refresh_from_db()
        od1_res2.refresh_from_db()
        od1_res3.refresh_from_db()
        self.assertIsNone(od1_res1.last_deliver_time)
        self.assertEqual(order1.trading_status, order1.TradingStatus.OPENING.value)
        self.assertEqual(od1_res1.instance_status, Resource.InstanceStatus.WAIT.value)
        self.assertEqual(od1_res2.instance_status, Resource.InstanceStatus.WAIT.value)
        self.assertEqual(od1_res3.instance_status, Resource.InstanceStatus.WAIT.value)

        # 资源配额不足
        with self.assertRaises(errors.QuotaShortageError):
            or_dlver.deliver_order(order1, resource=None)

        s1_quota.refresh_from_db()
        self.assertEqual(s1_quota.vcpu_used, 0)
        self.assertEqual(s1_quota.ram_used, 0)
        order1.refresh_from_db()
        self.assertEqual(order1.trading_status, order1.TradingStatus.UNDELIVERED.value)
        self._assert_res(res=od1_res1, instance_status=Resource.InstanceStatus.FAILED.value)
        self._assert_res(res=od1_res2, instance_status=Resource.InstanceStatus.FAILED.value)
        self._assert_res(res=od1_res3, instance_status=Resource.InstanceStatus.FAILED.value)

        # 请求太频繁
        ServicePrivateQuotaManager().update(service=self.service1, vcpus=6, ram_gib=12, public_ip=3)
        with self.assertRaises(errors.TryAgainLater):
            or_dlver.deliver_order(order1, resource=None)

        od1_res1: Resource
        od1_res1.last_deliver_time = dj_timezone.now() - timedelta(minutes=1)
        od1_res1.save(update_fields=['last_deliver_time'])

        with self.assertRaises(errors.TryAgainLater):
            or_dlver.deliver_order(order1, resource=None)

        Resource.objects.filter(id__in=[x.id for x in resource_list]).update(
            last_deliver_time=dj_timezone.now() - timedelta(minutes=1))

        # 请求错误
        with self.assertRaises(errors.APIException) as cm:
            or_dlver.deliver_order(order1, resource=None)
        self.assertEqual(cm.exception.code, 'InternalError')
        self.assertEqual(cm.exception.status_code, 500)

        s1_quota.refresh_from_db()
        self.assertEqual(s1_quota.vcpu_used, 0)
        self.assertEqual(s1_quota.ram_used, 0)
        self.assertFalse(Server.objects.filter(id__in=[x.instance_id for x in resource_list]).exists())
        order1.refresh_from_db()
        self.assertEqual(order1.trading_status, order1.TradingStatus.UNDELIVERED.value)
        self._assert_res(res=od1_res1, instance_status=Resource.InstanceStatus.FAILED.value)
        self._assert_res(res=od1_res2, instance_status=Resource.InstanceStatus.FAILED.value)
        self._assert_res(res=od1_res3, instance_status=Resource.InstanceStatus.FAILED.value)

        # 请求success
        Resource.objects.filter(id__in=[x.id for x in resource_list]).update(
            last_deliver_time=dj_timezone.now() - timedelta(minutes=2))

        now_time = dj_timezone.now()
        or_dlver._request_create_server = cs_req.request_create_server_ok    # 替换创建请求方法
        or_dlver.deliver_order(order1, resource=None)
        s1_quota.refresh_from_db()
        self.assertEqual(s1_quota.vcpu_used, 6)
        self.assertEqual(s1_quota.ram_used, 12)
        self.assertEqual(s1_quota.public_ip_used, 3)
        order1.refresh_from_db()
        self.assertEqual(order1.trading_status, order1.TradingStatus.COMPLETED.value)
        self._assert_res(res=od1_res1, instance_status=Resource.InstanceStatus.SUCCESS.value)
        self._assert_res(res=od1_res2, instance_status=Resource.InstanceStatus.SUCCESS.value)
        self._assert_res(res=od1_res3, instance_status=Resource.InstanceStatus.SUCCESS.value)
        self.assertEqual(Server.objects.filter(id__in=[x.instance_id for x in resource_list]).count(), 3)
        # server 过期时间
        for s in Server.objects.filter(id__in=[x.instance_id for x in resource_list]).all():
            self.assertTrue((s.expiration_time - now_time) > timedelta(days=30*8))
            self.assertTrue((s.expiration_time - now_time) < timedelta(days=30*8 + 1))

        with self.assertRaises(errors.OrderTradingCompleted):
            or_dlver.deliver_order(order1, resource=None)

        # ---- 部分交付成功测试 ----
        order2, resource_list2 = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=self.service1.pay_app_service_id,
            service_id=self.service1.id,
            service_name=self.service1.name,
            resource_type=ResourceType.VM.value,
            instance_config=instance_config,
            period=6,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.POSTPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
            remark='testcase创建，可删除',
            number=3
        )
        or_dlver2 = OrderResourceDeliverer()
        or_dlver2._request_create_server = cs_req.request_create_server_once_ok  # 替换创建请求方法

        # order unpaid
        with self.assertRaises(errors.OrderUnpaid):
            or_dlver2.deliver_order(order2, resource=None)

        order2.set_paid(
            pay_amount=Decimal('0'), balance_amount=Decimal('0'), coupon_amount=Decimal('0'), payment_history_id='')

        s1_quota = ServicePrivateQuotaManager().get_quota(service=self.service1)
        ServicePrivateQuotaManager().increase(service=self.service1, vcpus=6, ram_gib=12, public_ip=3)
        od1_res4, od1_res5, od1_res6 = resource_list2

        # 创建成功第1个server
        with self.assertRaises(errors.APIException):
            or_dlver2.deliver_order(order2, resource=None)

        s1_quota.refresh_from_db()
        self.assertEqual(s1_quota.vcpu_used, 6 + 2)
        self.assertEqual(s1_quota.ram_used, 12 + 4)
        self.assertEqual(s1_quota.public_ip_used, 3 + 1)
        order2.refresh_from_db()
        self.assertEqual(order2.trading_status, order2.TradingStatus.PART_DELIVER.value)
        self._assert_res(res=od1_res4, instance_status=Resource.InstanceStatus.SUCCESS.value)
        self._assert_res(res=od1_res5, instance_status=Resource.InstanceStatus.FAILED.value)
        self._assert_res(res=od1_res6, instance_status=Resource.InstanceStatus.FAILED.value)
        self.assertEqual(Server.objects.count(), 4)
        self.assertEqual(Server.objects.filter(id__in=[x.instance_id for x in resource_list2]).count(), 1)
        self.assertEqual(Server.objects.filter(id=od1_res4.instance_id).count(), 1)

        # 订单动作正在交付中
        order2.set_order_action(Order.OrderAction.DELIVERING.value)
        with self.assertRaises(errors.ConflictError) as cm:
            or_dlver2.deliver_order(order2, resource=None)
        self.assertEqual(cm.exception.code, 'OrderDelivering')
        self.assertEqual(cm.exception.status_code, 409)
        order2.set_order_action(Order.OrderAction.NONE.value)

        # 请求太频繁
        with self.assertRaises(errors.TryAgainLater):
            or_dlver2.deliver_order(order2, resource=None)

        Resource.objects.filter(id__in=[od1_res5.id, od1_res6.id]).update(
            last_deliver_time=dj_timezone.now() - timedelta(minutes=1))

        # 创建成功第2个server
        cs_req.clear_create_server_once_ok_flag()
        with self.assertRaises(errors.APIException):
            or_dlver2.deliver_order(order2, resource=None)

        s1_quota.refresh_from_db()
        self.assertEqual(s1_quota.vcpu_used, 6 + 2 + 2)
        self.assertEqual(s1_quota.ram_used, 12 + 4 + 4)
        self.assertEqual(s1_quota.public_ip_used, 3 + 1 + 1)
        order2.refresh_from_db()
        self.assertEqual(order2.trading_status, order2.TradingStatus.PART_DELIVER.value)
        self._assert_res(res=od1_res4, instance_status=Resource.InstanceStatus.SUCCESS.value)
        self._assert_res(res=od1_res5, instance_status=Resource.InstanceStatus.SUCCESS.value)
        self._assert_res(res=od1_res6, instance_status=Resource.InstanceStatus.FAILED.value)
        self.assertEqual(Server.objects.count(), 5)
        self.assertEqual(Server.objects.filter(id__in=[x.instance_id for x in resource_list2]).count(), 2)
        self.assertEqual(Server.objects.filter(id=od1_res4.instance_id).count(), 1)
        self.assertEqual(Server.objects.filter(id=od1_res5.instance_id).count(), 1)

        # 创建成功第3个server
        Resource.objects.filter(id=od1_res6.id).update(last_deliver_time=dj_timezone.now() - timedelta(minutes=2))
        cs_req.clear_create_server_once_ok_flag()
        or_dlver2.deliver_order(order2, resource=None)

        s1_quota.refresh_from_db()
        self.assertEqual(s1_quota.vcpu_used, 6 + 2 + 2 + 2)
        self.assertEqual(s1_quota.ram_used, 12 + 4 + 4 + 4)
        self.assertEqual(s1_quota.public_ip_used, 3 + 1 + 1 + 1)
        order2.refresh_from_db()
        self.assertEqual(order2.trading_status, order2.TradingStatus.COMPLETED.value)
        self._assert_res(res=od1_res4, instance_status=Resource.InstanceStatus.SUCCESS.value)
        self._assert_res(res=od1_res5, instance_status=Resource.InstanceStatus.SUCCESS.value)
        self._assert_res(res=od1_res6, instance_status=Resource.InstanceStatus.SUCCESS.value)
        self.assertEqual(Server.objects.count(), 6)
        self.assertEqual(Server.objects.filter(id__in=[x.instance_id for x in resource_list2]).count(), 3)
        self.assertEqual(Server.objects.filter(id=od1_res4.instance_id).count(), 1)
        self.assertEqual(Server.objects.filter(id=od1_res5.instance_id).count(), 1)
        self.assertEqual(Server.objects.filter(id=od1_res6.instance_id).count(), 1)
        # server 过期时间
        for s in Server.objects.filter(id__in=[x.instance_id for x in resource_list2]).all():
            self.assertIsNone(s.expiration_time)

        with self.assertRaises(errors.OrderTradingCompleted):
            or_dlver2.deliver_order(order2, resource=None)

    def test_scan_deliver(self):
        scan_config = ScanConfig(
            name='测试 scan，host and web', host_addr=' 10.8.8.6', web_url='https://test.cn ', remark='test remark')
        scan_order, ress = OrderManager().create_scan_order(
            service_id='scan_service_id',
            service_name='scan_service_name',
            pay_app_service_id='scan_pay_app_service_id',
            instance_config=scan_config,
            user_id=self.user.id,
            username=self.user.username
        )
        scan_order.set_paid(
            pay_amount=Decimal('0'), balance_amount=Decimal('0'), coupon_amount=Decimal('0'), payment_history_id='')
        self.assertEqual(VtTask.objects.count(), 0)
        OrderResourceDeliverer().deliver_order(order=scan_order)
        self.assertEqual(VtTask.objects.count(), 2)
        scan_order.refresh_from_db()
        self.assertEqual(scan_order.trading_status, scan_order.TradingStatus.COMPLETED.value)
        od1_res1, od1_res2 = ress
        od1_res1.refresh_from_db()
        self.assertLess(od1_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od1_res1.instance_status, od1_res1.InstanceStatus.SUCCESS.value)
        self.assertTrue(VtTask.objects.filter(id=od1_res1.instance_id).exists())
        od1_res2.refresh_from_db()
        self.assertLess(od1_res2.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od1_res2.instance_status, od1_res2.InstanceStatus.SUCCESS.value)
        self.assertTrue(VtTask.objects.filter(id=od1_res2.instance_id).exists())

        tasks = list(VtTask.objects.all())
        if tasks[0].target == '10.8.8.6':
            host_task = tasks[0]
            web_task = tasks[1]
        else:
            host_task = tasks[1]
            web_task = tasks[0]

        self.assertEqual(host_task.target, '10.8.8.6')
        self.assertEqual(host_task.type, VtTask.TaskType.HOST.value)
        self.assertEqual(host_task.name, '测试 scan，host and web')
        self.assertEqual(host_task.remark, 'test remark')
        self.assertEqual(host_task.user_id, self.user.id)
        self.assertEqual(web_task.target, 'https://test.cn')
        self.assertEqual(web_task.type, VtTask.TaskType.WEB.value)
        self.assertEqual(web_task.name, '测试 scan，host and web')
        self.assertEqual(web_task.remark, 'test remark')
        self.assertEqual(host_task.user_id, self.user.id)

    def test_snapshot_create_deliver(self):
        vo_server = create_server_metadata(
            service=self.service1, user=self.user, vo_id=self.vo.id, ram=2,
            classification=Server.Classification.VO, default_user='root',
            default_password='password', ipv4='127.0.0.12', remarks='test',
            disk_size=100
        )

        instance_config = ServerSnapshotConfig(
            server_id=vo_server.id, systemdisk_size=100, azone_id='',
            snapshot_name='snapshot_name1', snapshot_desc='snapshot_desc1'
        )
        # 创建订单
        order1, resource_list = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=self.service1.pay_app_service_id,
            service_id=self.service1.id,
            service_name=self.service1.name,
            resource_type=ResourceType.VM_SNAPSHOT.value,
            instance_config=instance_config,
            period=8,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.PREPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
            remark='testcase创建，可删除'
        )
        or_dlver = OrderResourceDeliverer()
        # 替换创建请求方法
        or_dlver.deliverer_request_service = DelivererRequestService(
            snap_request=SnapshotRequest(create_ok=False, delete_ok=True)).deliverer_request_service

        # order unpaid
        with self.assertRaises(errors.OrderUnpaid):
            or_dlver.deliver_order(order1, resource=None)

        order1.set_paid(
            pay_amount=Decimal('0'), balance_amount=Decimal('0'), coupon_amount=Decimal('0'), payment_history_id='')

        od1_res1 = resource_list[0]
        od1_res1.refresh_from_db()
        self.assertIsNone(od1_res1.last_deliver_time)
        self.assertEqual(order1.trading_status, order1.TradingStatus.OPENING.value)
        self.assertEqual(od1_res1.instance_status, od1_res1.InstanceStatus.WAIT.value)

        # 请求错误
        with self.assertRaises(errors.APIException) as cm:
            or_dlver.deliver_order(order1, resource=None)
        self.assertEqual(cm.exception.code, 'InternalError')
        self.assertEqual(cm.exception.status_code, 500)
        order1.refresh_from_db()
        self.assertEqual(order1.trading_status, order1.TradingStatus.UNDELIVERED.value)
        od1_res1.refresh_from_db()
        self.assertLess(od1_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od1_res1.instance_status, od1_res1.InstanceStatus.FAILED.value)
        self.assertFalse(ServerSnapshot.objects.filter(id=od1_res1.instance_id).exists())

        # 请求太频繁
        with self.assertRaises(errors.TryAgainLater) as cm:
            or_dlver.deliver_order(order1, resource=None)
        self.assertEqual(cm.exception.code, 'TryAgainLater')
        self.assertEqual(cm.exception.status_code, 409)

        od1_res1.last_deliver_time = dj_timezone.now() - timedelta(seconds=55)
        od1_res1.save(update_fields=['last_deliver_time'])

        with self.assertRaises(errors.TryAgainLater) as cm:
            or_dlver.deliver_order(order1, resource=None)
        self.assertEqual(cm.exception.code, 'TryAgainLater')
        self.assertEqual(cm.exception.status_code, 409)

        # 请求success
        now_time = dj_timezone.now()
        od1_res1.last_deliver_time = dj_timezone.now() - timedelta(seconds=60)
        od1_res1.save(update_fields=['last_deliver_time'])
        # 替换创建请求方法
        or_dlver.deliverer_request_service = DelivererRequestService(
            snap_request=SnapshotRequest(create_ok=True, delete_ok=True)).deliverer_request_service
        or_dlver.deliver_order(order1, resource=None)
        order1.refresh_from_db()
        self.assertEqual(order1.trading_status, order1.TradingStatus.COMPLETED.value)
        od1_res1.refresh_from_db()
        self.assertLess(od1_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od1_res1.instance_status, od1_res1.InstanceStatus.SUCCESS.value)
        self.assertTrue(ServerSnapshot.objects.filter(id=od1_res1.instance_id).exists())
        # snapshot 过期时间
        snapshot1: ServerSnapshot = ServerSnapshot.objects.filter(id=od1_res1.instance_id).first()
        self.assertTrue((snapshot1.expiration_time - now_time) > timedelta(days=30 * 8))
        self.assertTrue((snapshot1.expiration_time - now_time) < timedelta(days=30*8 + 1))
        self.assertEqual(snapshot1.name, 'snapshot_name1')
        self.assertEqual(snapshot1.remarks, 'testcase创建，可删除')
        self.assertEqual(snapshot1.server_id, vo_server.id)
        self.assertEqual(snapshot1.service_id, vo_server.service_id)
        self.assertEqual(snapshot1.size, 100)
        self.assertFalse(snapshot1.deleted)
        self.assertEqual(snapshot1.classification, snapshot1.Classification.VO.value)
        self.assertEqual(snapshot1.vo_id, self.vo.id)
        self.assertEqual(snapshot1.user_id, order1.user_id)
        self.assertEqual(snapshot1.pay_type, PayType.PREPAID.value)

        with self.assertRaises(errors.OrderTradingCompleted):
            or_dlver.deliver_order(order1, resource=None)

        # 创建订单2
        instance_config2 = ServerSnapshotConfig(
            server_id=vo_server.id, systemdisk_size=200, azone_id='',
            snapshot_name='snapshot_name2', snapshot_desc='snapshot_desc2'
        )
        order2, resource_list2 = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=self.service1.pay_app_service_id,
            service_id=self.service1.id,
            service_name=self.service1.name,
            resource_type=ResourceType.VM_SNAPSHOT.value,
            instance_config=instance_config2,
            period=128,
            period_unit=Order.PeriodUnit.DAY.value,
            pay_type=PayType.PREPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
            remark='testcase创建，可删除2'
        )
        od2_res1 = resource_list2[0]
        order2.set_paid(
            pay_amount=Decimal('0'), balance_amount=Decimal('0'), coupon_amount=Decimal('0'), payment_history_id='')
        or_dlver = OrderResourceDeliverer()
        # 替换创建请求方法
        or_dlver.deliverer_request_service = DelivererRequestService(
            snap_request=SnapshotRequest(create_ok=True, delete_ok=True)).deliverer_request_service

        # 系统盘大小不一致
        with self.assertRaises(errors.Error) as cm:
            or_dlver.deliver_order(order2, resource=None)
        self.assertEqual(cm.exception.code, 'InternalError')
        self.assertEqual(cm.exception.status_code, 500)
        order2.refresh_from_db()
        self.assertEqual(order2.trading_status, order2.TradingStatus.UNDELIVERED.value)
        od2_res1.refresh_from_db()
        self.assertLess(od2_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od2_res1.instance_status, od2_res1.InstanceStatus.FAILED.value)
        self.assertFalse(ServerSnapshot.objects.filter(id=od2_res1.instance_id).exists())

        # 请求太频繁
        with self.assertRaises(errors.TryAgainLater) as cm:
            or_dlver.deliver_order(order2, resource=None)
        self.assertEqual(cm.exception.code, 'TryAgainLater')
        self.assertEqual(cm.exception.status_code, 409)

        # 请求success
        now_time = dj_timezone.now()
        od2_res1.last_deliver_time = dj_timezone.now() - timedelta(seconds=60)
        od2_res1.save(update_fields=['last_deliver_time'])
        vo_server.disk_size = 200
        vo_server.save(update_fields=['disk_size'])

        or_dlver.deliver_order(order2, resource=None)
        order2.refresh_from_db()
        self.assertEqual(order2.trading_status, order2.TradingStatus.COMPLETED.value)
        od2_res1.refresh_from_db()
        self.assertLess(od2_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od2_res1.instance_status, od2_res1.InstanceStatus.SUCCESS.value)
        self.assertTrue(ServerSnapshot.objects.filter(id=od2_res1.instance_id).exists())
        # snapshot 过期时间
        snapshot2 = ServerSnapshot.objects.filter(id=od2_res1.instance_id).first()
        self.assertTrue((snapshot2.expiration_time - now_time) > timedelta(days=128))
        self.assertTrue((snapshot2.expiration_time - now_time) < timedelta(days=129))
        self.assertEqual(snapshot2.name, 'snapshot_name2')
        self.assertEqual(snapshot2.remarks, 'testcase创建，可删除2')
        self.assertEqual(snapshot2.server_id, vo_server.id)
        self.assertEqual(snapshot2.service_id, vo_server.service_id)
        self.assertEqual(snapshot2.size, 200)
        self.assertFalse(snapshot2.deleted)
        self.assertEqual(snapshot2.classification, snapshot2.Classification.VO.value)
        self.assertEqual(snapshot2.vo_id, self.vo.id)
        self.assertEqual(snapshot2.user_id, order1.user_id)
        self.assertEqual(snapshot2.pay_type, PayType.PREPAID.value)

    def test_snapshot_renew_deliver(self):
        vo_server = create_server_metadata(
            service=self.service1, user=self.user, vo_id=self.vo.id, ram=2,
            classification=Server.Classification.VO, default_user='root',
            default_password='password', ipv4='127.0.0.12', remarks='test',
            disk_size=100
        )
        now_time = dj_timezone.now()
        expiration_time = now_time - timedelta(days=1)
        snapshot1 = ServerSnapshotManager.create_snapshot_metadata(
            name='name1', size_dib=100, remarks='snapshot1 test', instance_id='11',
            creation_time=dj_timezone.now(), expiration_time=expiration_time,
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.VO.value, user=self.user, vo=self.vo,
            server=vo_server, service=vo_server.service
        )

        instance_config = ServerSnapshotConfig(
            server_id=vo_server.id, systemdisk_size=100, azone_id='',
            snapshot_name='snapshot_name1', snapshot_desc=''
        )
        # 创建订单
        service = vo_server.service
        order1, resource1 = OrderManager().create_renew_order(
            service_id=service.id, service_name=service.name, pay_app_service_id=service.pay_app_service_id,
            resource_type=ResourceType.VM_SNAPSHOT.value, instance_id=snapshot1.id,
            instance_config=instance_config,
            period=128, period_unit=Order.PeriodUnit.DAY.value, start_time=None, end_time=None,
            user_id=snapshot1.user_id, username=snapshot1.user.username,
            vo_id=snapshot1.vo_id, vo_name=snapshot1.vo.name, owner_type=OwnerType.VO.value
        )
        or_dlver = OrderResourceDeliverer()

        # order unpaid
        with self.assertRaises(errors.OrderUnpaid):
            or_dlver.deliver_order(order1, resource=None)

        order1.set_paid(
            pay_amount=Decimal('0'), balance_amount=Decimal('0'), coupon_amount=Decimal('0'), payment_history_id='')

        od1_res1 = resource1
        od1_res1.refresh_from_db()
        self.assertIsNone(od1_res1.last_deliver_time)
        self.assertEqual(order1.trading_status, order1.TradingStatus.OPENING.value)
        self.assertEqual(od1_res1.instance_status, od1_res1.InstanceStatus.WAIT.value)

        # 请求success
        or_dlver.deliver_order(order1, resource=None)
        order1.refresh_from_db()
        self.assertEqual(order1.trading_status, order1.TradingStatus.COMPLETED.value)
        od1_res1.refresh_from_db()
        self.assertLess(od1_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od1_res1.instance_status, od1_res1.InstanceStatus.SUCCESS.value)
        # snapshot 过期时间
        snapshot1.refresh_from_db()
        self.assertTrue((snapshot1.expiration_time - expiration_time) >= timedelta(days=128))
        self.assertTrue((snapshot1.expiration_time - expiration_time) < timedelta(days=129))

        with self.assertRaises(errors.OrderTradingCompleted):
            or_dlver.deliver_order(order1, resource=None)

        # 创建订单2
        expiration_time = snapshot1.expiration_time
        instance_config2 = ServerSnapshotConfig(
            server_id=vo_server.id, systemdisk_size=200, azone_id='',
            snapshot_name='snapshot_name2', snapshot_desc='snapshot_desc2'
        )
        order2, resource2 = OrderManager().create_renew_order(
            service_id=service.id, service_name=service.name, pay_app_service_id=service.pay_app_service_id,
            resource_type=ResourceType.VM_SNAPSHOT.value, instance_id=snapshot1.id,
            instance_config=instance_config2,
            period=8, period_unit=Order.PeriodUnit.MONTH.value, start_time=None, end_time=None,
            user_id=snapshot1.user_id, username=snapshot1.user.username,
            vo_id=snapshot1.vo_id, vo_name=snapshot1.vo.name, owner_type=OwnerType.VO.value
        )
        od2_res1 = resource2
        order2.set_paid(
            pay_amount=Decimal('0'), balance_amount=Decimal('0'), coupon_amount=Decimal('0'), payment_history_id='')
        or_dlver = OrderResourceDeliverer()

        # 系统盘大小不一致
        with self.assertRaises(errors.Error) as cm:
            or_dlver.deliver_order(order2, resource=None)
        self.assertEqual(cm.exception.code, 'InternalError')
        self.assertEqual(cm.exception.status_code, 500)
        order2.refresh_from_db()
        self.assertEqual(order2.trading_status, order2.TradingStatus.UNDELIVERED.value)
        od2_res1.refresh_from_db()
        self.assertLess(od2_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od2_res1.instance_status, od2_res1.InstanceStatus.FAILED.value)
        snapshot1.refresh_from_db()
        self.assertEqual(snapshot1.expiration_time, expiration_time)

        # 请求太频繁
        with self.assertRaises(errors.TryAgainLater) as cm:
            or_dlver.deliver_order(order2, resource=None)
        self.assertEqual(cm.exception.code, 'TryAgainLater')
        self.assertEqual(cm.exception.status_code, 409)

        # 请求success
        now_time = dj_timezone.now()
        od2_res1.last_deliver_time = dj_timezone.now() - timedelta(seconds=60)
        od2_res1.save(update_fields=['last_deliver_time'])
        cfg = ServerSnapshotConfig.from_dict(order2.instance_config)
        cfg.systemdisk_size = snapshot1.size
        order2.instance_config = cfg.to_dict()
        order2.save(update_fields=['instance_config'])

        or_dlver.deliver_order(order2, resource=None)
        order2.refresh_from_db()
        self.assertEqual(order2.trading_status, order2.TradingStatus.COMPLETED.value)
        od2_res1.refresh_from_db()
        self.assertLess(od2_res1.last_deliver_time - dj_timezone.now(), timedelta(seconds=30))
        self.assertEqual(od2_res1.instance_status, od2_res1.InstanceStatus.SUCCESS.value)
        # snapshot 过期时间
        snapshot1.refresh_from_db()
        self.assertTrue((snapshot1.expiration_time - expiration_time) >= timedelta(days=30 * 8))
        self.assertTrue((snapshot1.expiration_time - expiration_time) < timedelta(days=30 * 8 + 1))
        with self.assertRaises(errors.OrderTradingCompleted):
            or_dlver.deliver_order(order1, resource=None)
