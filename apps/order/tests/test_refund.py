from decimal import Decimal
from urllib import parse
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone as dj_timezone
from django.conf import settings

from core import errors, site_configs_manager
from utils.model import PayType, OwnerType, ResourceType
from apps.order.models import Price, Order, Resource, OrderRefund
from apps.order.managers import OrderManager, OrderPaymentManager
from apps.order.managers.instance_configs import ServerConfig
from utils.test import get_or_create_user, get_or_create_service, get_or_create_organization, MyAPITestCase
from apps.vo.models import VirtualOrganization
from apps.app_wallet.managers import PaymentManager
from apps.app_wallet.models import CashCoupon, PayAppService, PayApp
from apps.servers.models import ServiceConfig, Flavor


class OrderRefundTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.user2 = get_or_create_user(username='user2')
        price = Price(
            vm_ram=Decimal('0.12'),
            vm_cpu=Decimal('0.066'),
            vm_disk=Decimal('0.122'),
            vm_pub_ip=Decimal('0.66'),
            vm_upstream=Decimal('0.33'),
            vm_downstream=Decimal('1.446'),
            vm_disk_snap=Decimal('0.65'),
            disk_size=Decimal('1.02'),
            disk_snap=Decimal('0.77'),
            obj_size=Decimal('0'),
            obj_upstream=Decimal('0'),
            obj_downstream=Decimal('0'),
            obj_replication=Decimal('0.2'),
            obj_get_request=Decimal('0'),
            obj_put_request=Decimal('0'),
            prepaid_discount=66
        )
        price.save(force_insert=True)
        self.price = price
        self.flavor = Flavor(vcpus=2, ram=4)
        self.flavor.save()
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user
        )
        self.vo.save()
        self.service = get_or_create_service()

        # 余额支付有关配置
        self.app = PayApp(name='app', id=site_configs_manager.get_pay_app_id(dj_settings=settings))
        self.app.save(force_insert=True)
        self.po = get_or_create_organization(name='机构')
        self.po.save()
        app_service1 = PayAppService(
            id='123', name='service1', app=self.app, orgnazition=self.po
        )
        app_service1.save()
        self.app_service1 = app_service1
        self.service.pay_app_service_id = app_service1.id
        self.service.save(update_fields=['pay_app_service_id'])

    def test_refund_order(self):
        self.app_service2 = PayAppService(
            name='service2', app=self.app, orgnazition=self.po
        )
        self.app_service2.save()

        service2 = ServiceConfig(
            name='test2', org_data_center_id=self.service.org_data_center_id, endpoint_url='test2',
            username='', password='', need_vpn=False, pay_app_service_id=self.app_service2.id
        )
        service2.save()

        now_time = dj_timezone.now()
        # 通用有效
        coupon1_user = CashCoupon(
            face_value=Decimal('10'),
            balance=Decimal('10'),
            effective_time=now_time - timedelta(days=1),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon1_user.save(force_insert=True)

        # 专用有效
        coupon2_user = CashCoupon(
            face_value=Decimal('20'),
            balance=Decimal('20'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=self.service.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon2_user.save(force_insert=True)

        # 通用有效，只适用于service2
        coupon3_user = CashCoupon(
            face_value=Decimal('30'),
            balance=Decimal('30'),
            effective_time=now_time - timedelta(days=2),
            expiration_time=now_time + timedelta(days=10),
            app_service_id=service2.pay_app_service_id,
            status=CashCoupon.Status.AVAILABLE.value,
            owner_type=OwnerType.USER.value,
            user_id=self.user.id, vo_id=None
        )
        coupon3_user.save(force_insert=True)

        # prepaid mode order
        instance_config = ServerConfig(
            vm_cpu=1, vm_ram=1, systemdisk_size=50, public_ip=True,
            image_id='test', image_name='', network_id='network_id', network_name='',
            azone_id='', azone_name='', flavor_id=''
        )
        # 创建订单
        order1, resource_list = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=self.service.pay_app_service_id,
            service_id=self.service.id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config=instance_config,
            period=8,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.PREPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
            remark='testcase创建，可删除',
            number=3
        )
        order1.payable_amount = Decimal('333.3')
        order1.save(update_fields=['payable_amount'])
        od1_res1, od1_res2, od1_res3 = resource_list

        # test param "payment_method"
        base_url = reverse('order-api:order-refund-list')
        query = parse.urlencode(query={'reason': '退款原因'}, doseq=True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)
        self.client.force_login(self.user2)

        query = parse.urlencode(query={'reason': '退款原因'}, doseq=True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'order_id': '', 'reason': '退款原因'}, doseq=True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'order_id': 'test', 'reason': '退款原因'}, doseq=True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        query = parse.urlencode(query={'order_id': order1.id, 'reason': '退款原因'}, doseq=True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.client.logout()
        self.client.force_login(self.user)

        query = parse.urlencode(query={'order_id': order1.id, 'reason': '退款原因'}, doseq=True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='OrderUnpaid', response=response)

        # pay order1 by balance, balance not enough
        with self.assertRaises(errors.BalanceNotEnough):
            OrderPaymentManager().pay_order(
                order=order1, app_id=self.app.id, subject='test', executor='testcase', remark='')

        user1_account = PaymentManager.get_user_point_account(user_id=self.user.id)
        user1_account.balance = Decimal('500')
        user1_account.save(update_fields=['balance'])
        OrderPaymentManager().pay_order(
            order=order1, app_id=self.app.id, subject='test', executor='testcase', remark='')
        order1.refresh_from_db()
        self.assertEqual(order1.balance_amount, Decimal('303.3'))
        self.assertEqual(order1.coupon_amount, Decimal('30'))
        coupon1_user.refresh_from_db()
        self.assertEqual(coupon1_user.balance, Decimal('0'))
        coupon2_user.refresh_from_db()
        self.assertEqual(coupon2_user.balance, Decimal('0'))
        user1_account.refresh_from_db()
        self.assertEqual(user1_account.balance, Decimal('500') - Decimal('303.3'))

        # 部分资源交付失败
        Resource.set_many_deliver_failed(res_ids=[od1_res1.id, od1_res2.id], failed_msg='test')
        od1_res3.set_deliver_success(instance_id='')
        OrderManager.set_order_deliver_failed(order=order1, trading_status=Order.TradingStatus.PART_DELIVER.value)
        order1.refresh_from_db()
        self.assertEqual(order1.trading_status, Order.TradingStatus.PART_DELIVER.value)

        self.assertEqual(OrderRefund.objects.count(), 0)
        query = parse.urlencode(query={'order_id': order1.id, 'reason': '退款原因'}, doseq=True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        refund1_id = response.data['refund_id']

        # 退订单
        self.assertEqual(OrderRefund.objects.count(), 1)
        refund1 = OrderRefund.objects.get(id=refund1_id)
        self.assertEqual(refund1.order_id, order1.id)
        self.assertEqual(refund1.status, OrderRefund.Status.REFUNDED.value)
        self.assertEqual(refund1.order_amount, Decimal('333.3'))
        self.assertEqual(refund1.refund_amount, Decimal('222.2'))
        self.assertEqual(refund1.balance_amount, Decimal('202.2'))
        self.assertEqual(refund1.coupon_amount, Decimal('20'))
        self.assertEqual(refund1.number, 2)
        self.assertEqual(refund1.reason, '退款原因')
        self.assertFalse(refund1.deleted)
        self.assertEqual(refund1.owner_type, OwnerType.USER.value)
        self.assertEqual(refund1.user_id, self.user.id)
        self.assertEqual(refund1.username, self.user.username)

        # 钱包退款记录
        coupon1_user.refresh_from_db()
        self.assertEqual(coupon1_user.balance, Decimal('6.67'))
        coupon2_user.refresh_from_db()
        self.assertEqual(coupon2_user.balance, Decimal('13.33'))
        user1_account.refresh_from_db()
        self.assertEqual(user1_account.balance, Decimal('500') - Decimal('303.3') + Decimal('202.2'))

        # --- test vo --
        order2, resource_list = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=self.service.pay_app_service_id,
            service_id=self.service.id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config=instance_config,
            period=18,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.POSTPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
            remark='testcase创建，可删除',
            number=1
        )
        order2.payable_amount = Decimal('100')
        order2.save(update_fields=['payable_amount'])
        od2_res1 = resource_list[0]

        vo_account = PaymentManager.get_vo_point_account(vo_id=self.vo.id)
        vo_account.balance = Decimal('200')
        vo_account.save(update_fields=['balance'])
        OrderPaymentManager().pay_order(
            order=order2, app_id=self.app.id, subject='test vo', executor='testcase2', remark='')
        order2.refresh_from_db()
        self.assertEqual(order2.balance_amount, Decimal('100'))
        self.assertEqual(order2.coupon_amount, Decimal('0'))
        vo_account.refresh_from_db()
        self.assertEqual(vo_account.balance, Decimal('200') - Decimal('100'))

        # permission
        self.client.logout()
        self.client.force_login(self.user2)
        query = parse.urlencode(query={'order_id': order2.id, 'reason': '退款原因'}, doseq=True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.client.logout()
        self.client.force_login(self.user)

        # 资源交付中
        order2.set_order_action(act=Order.OrderAction.DELIVERING.value)
        query = parse.urlencode(query={'order_id': order2.id, 'reason': '退款原因'}, doseq=True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='OrderDelivering', response=response)
        order2.set_order_action(act=Order.OrderAction.NONE.value)

        # 退订
        self.assertEqual(OrderRefund.objects.count(), 1)
        query = parse.urlencode(query={'order_id': order2.id, 'reason': '退款原因2'}, doseq=True)
        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        refund2_id = response.data['refund_id']

        # 退订单
        self.assertEqual(OrderRefund.objects.count(), 2)
        refund2 = OrderRefund.objects.get(id=refund2_id)
        self.assertEqual(refund2.order_id, order2.id)
        self.assertEqual(refund2.status, OrderRefund.Status.REFUNDED.value)
        self.assertEqual(refund2.order_amount, Decimal('100'))
        self.assertEqual(refund2.refund_amount, Decimal('100'))
        self.assertEqual(refund2.balance_amount, Decimal('100'))
        self.assertEqual(refund2.coupon_amount, Decimal('0'))
        self.assertEqual(refund2.number, 1)
        self.assertEqual(refund2.reason, '退款原因2')
        self.assertFalse(refund2.deleted)
        self.assertEqual(refund2.owner_type, OwnerType.VO.value)
        self.assertEqual(refund2.vo_id, self.vo.id)
        self.assertEqual(refund2.vo_name, self.vo.name)

        # 钱包退款记录
        vo_account.refresh_from_db()
        self.assertEqual(vo_account.balance, Decimal('200'))

    def test_list_refund(self):
        now_time = dj_timezone.now()

        # prepaid mode order
        instance_config = ServerConfig(
            vm_cpu=1, vm_ram=1, systemdisk_size=50, public_ip=True,
            image_id='test', image_name='', network_id='network_id', network_name='',
            azone_id='', azone_name='', flavor_id=''
        )
        # 创建订单
        order1 = Order(
            order_type=Order.OrderType.NEW.value,
            status=Order.Status.UNPAID.value,
            total_amount=Decimal('333.3'),
            payable_amount=Decimal('333.3'),
            pay_amount=Decimal('0'),
            balance_amount=Decimal('0'),
            coupon_amount=Decimal('0'),
            app_service_id=self.service.pay_app_service_id,
            service_id=self.service.id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config=instance_config.to_dict(),
            period=12,
            pay_type=PayType.PREPAID.value,
            payment_time=None,
            start_time=None,
            end_time=None,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
            deleted=False,
            trading_status=Order.TradingStatus.OPENING.value,
            completion_time=None,
            number=3
        )
        order1.save(force_insert=True)

        order2 = Order(
            order_type=Order.OrderType.NEW.value,
            status=Order.Status.PAID.value,
            total_amount=Decimal('200.0'),
            payable_amount=Decimal('200.0'),
            pay_amount=Decimal('200'),
            balance_amount=Decimal('150'),
            coupon_amount=Decimal('50'),
            app_service_id=self.service.pay_app_service_id,
            service_id=self.service.id,
            service_name=self.service.name,
            resource_type=ResourceType.DISK.value,
            instance_config={},
            period=12,
            pay_type=PayType.PREPAID.value,
            payment_time=None,
            start_time=None,
            end_time=None,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
            deleted=False,
            trading_status=Order.TradingStatus.OPENING.value,
            completion_time=None,
            number=1
        )
        order2.save(force_insert=True)

        refund1 = OrderRefund(
            order=order1,
            order_amount=Decimal('333.3'),
            payment_history_id=order1.payment_history_id,
            status=OrderRefund.Status.WAIT.value,
            status_desc='',
            creation_time=now_time,
            update_time=now_time,
            resource_type=order1.resource_type,
            number=2,
            reason='reason',
            refund_amount=Decimal('222.2'),
            balance_amount=Decimal('200'),
            coupon_amount=Decimal('22.2'),
            refund_history_id='xxx',
            refunded_time=None,
            user_id=order1.user_id,
            username=order1.username,
            vo_id=order1.vo_id,
            vo_name=order1.vo_name,
            owner_type=OwnerType.USER.value,
            deleted=False
        )
        refund1.save(force_insert=True)
        refund1.creation_time = now_time - timedelta(days=10)
        refund1.save(update_fields=['creation_time'])

        refund2 = OrderRefund(
            order=order2,
            order_amount=Decimal('123.4'),
            payment_history_id=order2.payment_history_id,
            status=OrderRefund.Status.REFUNDED.value,
            status_desc='',
            creation_time=now_time,
            update_time=now_time,
            resource_type=order2.resource_type,
            number=1,
            reason='reason',
            refund_amount=Decimal('123.4'),
            balance_amount=Decimal('100'),
            coupon_amount=Decimal('23.4'),
            refund_history_id='xxx',
            refunded_time=None,
            user_id=order2.user_id,
            username=order2.username,
            vo_id=order2.vo_id,
            vo_name=order2.vo_name,
            owner_type=OwnerType.USER.value,
            deleted=False
        )
        refund2.save(force_insert=True)

        refund3 = OrderRefund(
            order=order1,
            order_amount=Decimal('123.4'),
            payment_history_id=order1.payment_history_id,
            status=OrderRefund.Status.FAILED.value,
            status_desc='',
            creation_time=now_time,
            update_time=now_time,
            resource_type=order1.resource_type,
            number=1,
            reason='reason',
            refund_amount=Decimal('123.4'),
            balance_amount=Decimal('100'),
            coupon_amount=Decimal('23.4'),
            refund_history_id='xxx',
            refunded_time=None,
            user_id=order1.user_id,
            username=order1.username,
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
            deleted=False
        )
        refund3.save(force_insert=True)

        base_url = reverse('order-api:order-refund-list')
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)
        self.client.force_login(self.user)

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 2)
        self.assertKeysIn(['id', 'order', 'order_amount', 'status', 'status_desc', 'creation_time', 'update_time',
                           'resource_type', 'number', 'reason', 'refund_amount', 'balance_amount', 'coupon_amount',
                           'refunded_time', 'user_id', 'username', 'vo_id', 'vo_name', 'owner_type'
                           ], response.data['results'][0])
        self.assertKeysIn(["id", "order_type", "status", "total_amount", "pay_amount",
                           "service_id", "service_name", "resource_type", "instance_config", "period",
                           "payment_time", "pay_type", "creation_time", "user_id", "username", 'number',
                           "vo_id", "vo_name", "owner_type", "cancelled_time", "app_service_id", 'trading_status'
                           ], response.data['results'][0]['order'])

        # test param "order_id"
        query = parse.urlencode(query={'order_id': ''}, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'order_id': order1.id}, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], refund1.id)
        self.assertEqual(response.data['results'][0]['order']['id'], order1.id)

        # test param "status"
        query = parse.urlencode(query={'status': 'xx'}, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'status': OrderRefund.Status.REFUNDED.value}, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], refund2.id)
        self.assertEqual(response.data['results'][0]['order']['id'], order2.id)

        # test param "time_start"、"time_end"
        query = parse.urlencode(query={'time_start': '2024-03-04T08:33:'}, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={'time_start': '2024-03-0T08:33:56Z'}, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query = parse.urlencode(query={'time_start': '2024-03-04T08:33:66Z'}, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={
            'time_start': (now_time - timedelta(days=30)).isoformat(timespec='seconds')
        }, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], refund2.id)
        self.assertEqual(response.data['results'][1]['id'], refund1.id)

        query = parse.urlencode(query={
            'time_start': (now_time - timedelta(days=9)).isoformat(timespec='seconds')
        }, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], refund2.id)

        query = parse.urlencode(query={
            'time_start': (dj_timezone.now() + timedelta(seconds=1)).isoformat(timespec='seconds')
        }, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.data['count'], 0)

        query = parse.urlencode(query={
            'time_start': (now_time - timedelta(days=30)).isoformat(timespec='seconds'),
            'time_end': (now_time + timedelta(days=1)).isoformat(timespec='seconds')
        }, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], refund2.id)
        self.assertEqual(response.data['results'][1]['id'], refund1.id)

        query = parse.urlencode(query={
            'time_start': (now_time - timedelta(days=30)).isoformat(timespec='seconds'),
            'time_end': (now_time - timedelta(days=1)).isoformat(timespec='seconds')
        }, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], refund1.id)

        query = parse.urlencode(query={
            'time_start': (now_time - timedelta(days=30)).isoformat(timespec='seconds'),
            'time_end': (now_time - timedelta(days=10, minutes=6)).isoformat(timespec='seconds')
        }, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.data['count'], 0)

        # test param "vo_id"
        self.client.logout()
        self.client.force_login(self.user2)

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        query = parse.urlencode(query={'vo_id': ''}, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'vo_id': 'xxx'}, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        query = parse.urlencode(query={'vo_id': self.vo.id}, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.client.logout()
        self.client.force_login(self.user)

        query = parse.urlencode(query={'vo_id': self.vo.id}, doseq=True)
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(['id', 'order', 'order_amount', 'status', 'status_desc', 'creation_time', 'update_time',
                           'resource_type', 'number', 'reason', 'refund_amount', 'balance_amount', 'coupon_amount',
                           'refunded_time', 'user_id', 'username', 'vo_id', 'vo_name', 'owner_type'
                           ], response.data['results'][0])
        self.assertKeysIn(["id", "order_type", "status", "total_amount", "pay_amount",
                           "service_id", "service_name", "resource_type", "instance_config", "period",
                           "payment_time", "pay_type", "creation_time", "user_id", "username", 'number',
                           "vo_id", "vo_name", "owner_type", "cancelled_time", "app_service_id", 'trading_status'
                           ], response.data['results'][0]['order'])
        self.assertEqual(response.data['results'][0]['id'], refund3.id)

    def test_delete_refund(self):
        now_time = dj_timezone.now()

        # prepaid mode order
        instance_config = ServerConfig(
            vm_cpu=1, vm_ram=1, systemdisk_size=50, public_ip=True,
            image_id='test', image_name='', network_id='network_id', network_name='',
            azone_id='', azone_name='', flavor_id=''
        )
        # 创建订单
        order1 = Order(
            order_type=Order.OrderType.NEW.value,
            status=Order.Status.PAID.value,
            total_amount=Decimal('333.3'),
            payable_amount=Decimal('333.3'),
            pay_amount=Decimal('333.3'),
            balance_amount=Decimal('300'),
            coupon_amount=Decimal('33.3'),
            app_service_id=self.service.pay_app_service_id,
            service_id=self.service.id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config=instance_config.to_dict(),
            period=12,
            pay_type=PayType.PREPAID.value,
            payment_time=None,
            start_time=None,
            end_time=None,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
            deleted=False,
            trading_status=Order.TradingStatus.OPENING.value,
            completion_time=None,
            number=3
        )
        order1.save(force_insert=True)

        refund1 = OrderRefund(
            order=order1,
            order_amount=Decimal('333.3'),
            payment_history_id=order1.payment_history_id,
            status=OrderRefund.Status.WAIT.value,
            status_desc='',
            creation_time=now_time,
            update_time=now_time,
            resource_type=order1.resource_type,
            number=2,
            reason='reason test',
            refund_amount=Decimal('222.2'),
            balance_amount=Decimal('200'),
            coupon_amount=Decimal('22.2'),
            refund_history_id='xxx',
            refunded_time=None,
            user_id=order1.user_id,
            username=order1.username,
            vo_id=order1.vo_id,
            vo_name=order1.vo_name,
            owner_type=OwnerType.USER.value,
            deleted=False
        )
        refund1.save(force_insert=True)

        base_url = reverse('order-api:order-refund-detail', kwargs={'id': 'test'})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)
        self.client.force_login(self.user2)

        base_url = reverse('order-api:order-refund-detail', kwargs={'id': 'test'})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        base_url = reverse('order-api:order-refund-detail', kwargs={'id': refund1.id})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.client.logout()
        self.client.force_login(self.user)
        base_url = reverse('order-api:order-refund-detail', kwargs={'id': refund1.id})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=409, code='ConflictStatus', response=response)

        refund1.refresh_from_db()
        self.assertFalse(refund1.deleted)
        refund1.status = OrderRefund.Status.REFUNDED.value
        refund1.save(update_fields=['status'])
        base_url = reverse('order-api:order-refund-detail', kwargs={'id': refund1.id})
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        refund1.refresh_from_db()
        self.assertTrue(refund1.deleted)

        base_url = reverse('order-api:order-refund-detail', kwargs={'id': refund1.id})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

    def test_cancel_refund(self):
        now_time = dj_timezone.now()

        # prepaid mode order
        instance_config = ServerConfig(
            vm_cpu=1, vm_ram=1, systemdisk_size=50, public_ip=True,
            image_id='test', image_name='', network_id='network_id', network_name='',
            azone_id='', azone_name='', flavor_id=''
        )
        # 创建订单
        order1 = Order(
            order_type=Order.OrderType.NEW.value,
            status=Order.Status.REFUNDING.value,
            total_amount=Decimal('433.3'),
            payable_amount=Decimal('433.3'),
            pay_amount=Decimal('433.3'),
            balance_amount=Decimal('400'),
            coupon_amount=Decimal('33.3'),
            app_service_id=self.service.pay_app_service_id,
            service_id=self.service.id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config=instance_config.to_dict(),
            period=6,
            pay_type=PayType.PREPAID.value,
            payment_time=None,
            start_time=None,
            end_time=None,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
            deleted=False,
            trading_status=Order.TradingStatus.OPENING.value,
            completion_time=None,
            number=1
        )
        order1.save(force_insert=True)

        refund1 = OrderRefund(
            order=order1,
            order_amount=Decimal('433.3'),
            payment_history_id=order1.payment_history_id,
            status=OrderRefund.Status.REFUNDED.value,
            status_desc='',
            creation_time=now_time,
            update_time=now_time,
            resource_type=order1.resource_type,
            number=1,
            reason='reason test',
            refund_amount=Decimal('422.2'),
            balance_amount=Decimal('400'),
            coupon_amount=Decimal('22.2'),
            refund_history_id='xxx',
            refunded_time=None,
            user_id=self.user2.id,
            username=self.user2.username,
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
            deleted=False
        )
        refund1.save(force_insert=True)

        base_url = reverse('order-api:order-refund-cancel', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=response)
        self.client.force_login(self.user2)

        base_url = reverse('order-api:order-refund-cancel', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        base_url = reverse('order-api:order-refund-cancel', kwargs={'id': refund1.id})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.client.logout()
        self.client.force_login(self.user)
        base_url = reverse('order-api:order-refund-cancel', kwargs={'id': refund1.id})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=409, code='ConflictStatus', response=response)

        refund1.refresh_from_db()
        self.assertEqual(refund1.status, OrderRefund.Status.REFUNDED.value)
        self.assertEqual(refund1.order.status, Order.Status.REFUNDING.value)
        refund1.status = OrderRefund.Status.FAILED.value
        refund1.save(update_fields=['status'])
        base_url = reverse('order-api:order-refund-cancel', kwargs={'id': refund1.id})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 200)
        refund1.refresh_from_db()
        self.assertEqual(refund1.status, OrderRefund.Status.CANCELLED.value)
        self.assertEqual(refund1.order.status, Order.Status.PAID.value)

        base_url = reverse('order-api:order-refund-cancel', kwargs={'id': refund1.id})
        response = self.client.post(base_url)
        self.assertErrorResponse(status_code=409, code='ConflictStatus', response=response)
