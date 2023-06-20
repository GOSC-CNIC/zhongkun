from urllib import parse
from decimal import Decimal

from django.urls import reverse

from service.managers import ServicePrivateQuotaManager
from utils.test import get_or_create_user, get_or_create_service
from utils.model import PayType, OwnerType, ResourceType
from utils.decimal_utils import quantize_10_2
from vo.models import VirtualOrganization, VoMember
from order.managers import OrderManager, PriceManager
from order.models import Price, Order
from order.managers import DiskConfig
from bill.managers import PaymentManager
from . import MyAPITransactionTestCase


class DiskOrderTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.user2 = get_or_create_user(username='user2')
        self.service = get_or_create_service()
        self.vo = VirtualOrganization(name='test vo', owner=self.user2)
        self.vo.save(force_insert=True)
        self.price = Price(
            vm_ram=Decimal('0.012'),
            vm_cpu=Decimal('0.066'),
            vm_disk=Decimal('0.122'),
            vm_pub_ip=Decimal('0.66'),
            vm_upstream=Decimal('0.33'),
            vm_downstream=Decimal('1.44'),
            vm_disk_snap=Decimal('0.65'),
            disk_size=Decimal('0.12'),
            disk_snap=Decimal('0.77'),
            obj_size=Decimal('0'),
            obj_upstream=Decimal('0'),
            obj_downstream=Decimal('0'),
            obj_replication=Decimal('0'),
            obj_get_request=Decimal('0'),
            obj_put_request=Decimal('0'),
            prepaid_discount=66
        )
        self.price.save(force_insert=True)

    def test_disk_create_bad_request(self):
        url = reverse('api:disks-list')
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 401)

        self.client.force_login(self.user)
        response = self.client.post(url, data={})
        self.assertErrorResponse(status_code=400, code='InvalidPayType', response=response)

        # param "size"
        response = self.client.post(url, data={
            'pay_type': 'test', 'service_id': self.service.id, 'azone_id': 'test', 'size': -1, 'remarks': 'shun开发测试'})
        self.assertErrorResponse(status_code=400, code='InvalidSize', response=response)

        # param "pay_type"
        response = self.client.post(url, data={
            'pay_type': 'test', 'service_id': self.service.id, 'azone_id': 'test', 'size': 1, 'remarks': 'shun开发测试'})
        self.assertErrorResponse(status_code=400, code='InvalidPayType', response=response)

        # param "period"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': 'test', 'size': 1,
            'remarks': 'shun开发测试'})
        self.assertErrorResponse(status_code=400, code='MissingPeriod', response=response)
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': 'test', 'size': 1,
            'period': 0})
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': 'test', 'size': 1,
            'period': 12 * 5 + 1})
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)

        # param "service_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'azone_id': 'test', 'size': 1, 'period': 2})
        self.assertErrorResponse(status_code=400, code='InvalidServiceId', response=response)

        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': 'test', 'azone_id': 'test', 'size': 1,
            'period': 2})
        self.assertErrorResponse(status_code=400, code='InvalidServiceId', response=response)

        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': 'test', 'size': 1,
            'period': 2})
        self.assertErrorResponse(status_code=409, code='ServiceNoPayAppServiceId', response=response)

        self.service.pay_app_service_id = 'app_service_id'
        self.service.save(update_fields=['pay_app_service_id'])

        # param "azone_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'size': 1,
            'period': 2})
        self.assertErrorResponse(status_code=400, code='InvalidAzoneId', response=response)

        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': 'test', 'size': 1,
            'period': 2})
        self.assertErrorResponse(status_code=400, code='InvalidAzoneId', response=response)

        # param "vo_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': 'test', 'size': 1,
            'period': 2, 'vo_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidVoId', response=response)
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': 'test', 'size': 1,
            'period': 2, 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo permission
        member = VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER,
                          inviter=self.user2.username, inviter_id=self.user2.id)
        member.save(force_insert=True)

    def test_disk_create(self):
        url = reverse('api:disks-list')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

        # get azone id
        base_url = reverse('api:availability-zone-list')
        response = self.client.get(f'{base_url}?service_id={self.service.id}')
        self.assertEqual(response.status_code, 200)
        azone_id = response.data['zones'][0]['id']

        # service not set pay_app_service_id
        url = reverse('api:disks-list')
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': azone_id,
            'size': 2, 'period': 12, 'remarks': 'testcase创建，可删除'
        })
        self.assertErrorResponse(status_code=409, code='ServiceNoPayAppServiceId', response=response)

        self.service.pay_app_service_id = 'app_service_id'
        self.service.save(update_fields=['pay_app_service_id'])

        # service privete quota not enough
        disk_url = reverse('api:disks-list')
        response = self.client.post(disk_url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': azone_id,
            'size': 2, 'period': 12, 'remarks': 'testcase创建，可删除'
        })
        self.assertErrorResponse(status_code=409, code='QuotaShortage', response=response)

        # service quota set
        ServicePrivateQuotaManager().increase(service=self.service, disk_size=6)

        # create user disk prepaid mode
        response = self.client.post(disk_url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': azone_id,
            'size': 2, 'period': 12, 'remarks': 'testcase创建，可删除'
        })
        self.assertEqual(response.status_code, 200)
        try:
            self.assertKeysIn(['order_id'], response.data)
            order_id = response.data['order_id']
            order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user)
            self.try_delete_disk(disk_id=resources[0].instance_id)
        except Exception as e:
            raise e

        self.assertEqual(order.service_id, self.service.id)
        self.assertEqual(order.resource_type, ResourceType.DISK.value)
        self.assertEqual(order.status, Order.Status.UNPAID.value)
        self.assertEqual(order.order_type, Order.OrderType.NEW.value)
        self.assertEqual(order.period, 12)
        self.assertEqual(order.owner_type, OwnerType.USER.value)
        self.assertEqual(order.user_id, self.user.id)
        self.assertEqual(order.vo_id, '')
        disk_config = DiskConfig.from_dict(order.instance_config)
        self.assertEqual(disk_config.disk_azone_id, azone_id)

        # create user disk postpaid mode, no balance
        response = self.client.post(disk_url, data={
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id, 'azone_id': azone_id,
            'size': 2, 'period': 12, 'remarks': 'testcase创建，可删除'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=response)

        # create user server prepaid mode
        user_account = PaymentManager().get_user_point_account(user_id=self.user.id)
        user_account.balance = Decimal('10000')
        user_account.save()
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': azone_id,
            'size': 2, 'period': 13, 'remarks': 'testcase创建，可删除'
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['order_id'], response.data)
        order_id = response.data['order_id']
        order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user)
        self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.WAIT.value)
        self.assertEqual(order.resource_type, ResourceType.DISK.value)
        self.assertEqual(order.status, Order.Status.UNPAID.value)
        self.assertEqual(order.order_type, Order.OrderType.NEW.value)
        self.assertEqual(order.period, 13)
        self.assertEqual(order.trading_status, order.TradingStatus.OPENING.value)
        self.assertEqual(order.owner_type, OwnerType.USER.value)
        self.assertEqual(order.user_id, self.user.id)

        original_price, trade_price = PriceManager().describe_disk_price(
            size_gib=2, is_prepaid=True, period=13, days=0)
        self.assertEqual(order.total_amount, quantize_10_2(original_price))
        self.assertEqual(order.payable_amount, quantize_10_2(trade_price))

        # 修改azone_id，让订单交付资源失败
        d_config = DiskConfig.from_dict(order.instance_config)
        d_config.disk_azone_id = 'test'
        order.instance_config = d_config.to_dict()
        order.save(update_fields=['instance_config'])

        # 订单交付资源
        order.payable_amount = Decimal(0)
        order.save(update_fields=['payable_amount'])
        pay_url = reverse('api:order-pay-order', kwargs={'id': order_id})
        query = parse.urlencode(query={
            'payment_method': Order.PaymentMethod.BALANCE.value
        })
        response = self.client.post(f'{pay_url}?{query}')
        self.assertEqual(response.status_code, 200)
        try:
            order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user)
            self.try_delete_disk(disk_id=resources[0].instance_id)
            self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.FAILED.value)
            self.assertEqual(order.trading_status, order.TradingStatus.UNDELIVERED.value)
            self.assertEqual(order.owner_type, OwnerType.USER.value)
            self.assertEqual(order.user_id, self.user.id)
            self.assertEqual(order.resource_type, ResourceType.DISK.value)
            self.assertEqual(order.status, Order.Status.PAID.value)
            self.assertEqual(order.order_type, Order.OrderType.NEW.value)
            self.assertEqual(order.period, 13)
        except Exception as e:
            raise e

        # --------vo-------------
        # create vo server postpaid mode, no vo permission
        disk_url = reverse('api:disks-list')
        response = self.client.post(disk_url, data={
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id, 'azone_id': azone_id,
            'size': 2, 'period': 12, 'remarks': 'testcase创建，可删除', 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo permisson
        member = VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER,
                          inviter=self.user2.username, inviter_id=self.user2.id)
        member.save(force_insert=True)

        # create vo server postpaid mode, no balance
        response = self.client.post(url, data={
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id, 'azone_id': azone_id,
            'size': 3, 'period': 12, 'remarks': 'testcase创建，可删除', 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=409, code='VoBalanceNotEnough', response=response)

        # create order
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'azone_id': azone_id,
            'size': 3, 'period': 12, 'remarks': 'testcase创建，可删除', 'vo_id': self.vo.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['order_id'], response.data)
        order_id = response.data['order_id']
        order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user)
        self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.WAIT.value)
        self.assertEqual(order.resource_type, ResourceType.DISK.value)
        self.assertEqual(order.status, Order.Status.UNPAID.value)
        self.assertEqual(order.order_type, Order.OrderType.NEW.value)
        self.assertEqual(order.period, 12)
        self.assertEqual(order.trading_status, order.TradingStatus.OPENING.value)
        self.assertEqual(order.owner_type, OwnerType.VO.value)
        self.assertEqual(order.vo_id, self.vo.id)
        self.assertEqual(order.user_id, self.user.id)

        # 修改azone_id，让订单交付资源失败
        d_config = DiskConfig.from_dict(order.instance_config)
        d_config.disk_azone_id = 'test'
        order.instance_config = d_config.to_dict()
        order.save(update_fields=['instance_config'])

        # 支付订单交付资源
        order.payable_amount = Decimal(0)
        order.save(update_fields=['payable_amount'])
        pay_url = reverse('api:order-pay-order', kwargs={'id': order_id})
        query = parse.urlencode(query={
            'payment_method': Order.PaymentMethod.BALANCE.value
        })
        response = self.client.post(f'{pay_url}?{query}')
        self.assertEqual(response.status_code, 200)
        try:
            order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user)
            self.try_delete_disk(disk_id=resources[0].instance_id)
            self.assertEqual(order.trading_status, order.TradingStatus.UNDELIVERED.value)
            self.assertEqual(order.owner_type, OwnerType.VO.value)
            self.assertEqual(order.vo_id, self.vo.id)
            self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.FAILED.value)
            self.assertEqual(order.resource_type, ResourceType.DISK.value)
            self.assertEqual(order.status, Order.Status.PAID.value)
        except Exception as e:
            raise e

    def try_delete_disk(self, disk_id: str):
        try:
            url = reverse('api:disks-detail', kwargs={'id': disk_id})
        except Exception as exc:
            print(str(exc))
            return

        response = self.client.delete(url)
        if response.status_code == 204:
            print(f'Delete disk({disk_id}) OK.')
        elif response.status_code == 404:
            print(f'Delete Ok, disk({disk_id}) not found.')
        else:
            print(f'Delete disk({disk_id}) Failed.')
