from decimal import Decimal
from urllib import parse
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from core import errors
from utils.model import PayType, OwnerType, ResourceType
from order.models import Price, Order, Resource, OrderRefund
from order.managers import OrderManager, OrderPaymentManager
from order.managers.instance_configs import ServerConfig
from utils.test import get_or_create_user, get_or_create_service, get_or_create_organization, MyAPITestCase
from vo.models import VirtualOrganization
from bill.managers import PaymentManager
from bill.models import CashCoupon, PayAppService, PayApp
from servers.models import ServiceConfig, Flavor


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
        self.app = PayApp(name='app', id=settings.PAYMENT_BALANCE['app_id'])
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
        settings.PAYMENT_BALANCE['app_id'] = self.app.id

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

        now_time = timezone.now()
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
