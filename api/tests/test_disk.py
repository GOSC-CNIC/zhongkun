from urllib import parse
from decimal import Decimal
from urllib.parse import urlencode

from django.urls import reverse
from django.utils import timezone

from service.managers import ServicePrivateQuotaManager
from service.models import ServiceConfig
from servers.models import Disk, Server
from utils.test import get_or_create_user, get_or_create_service
from utils.model import PayType, OwnerType, ResourceType
from utils.decimal_utils import quantize_10_2
from utils import rand_utils
from vo.models import VirtualOrganization, VoMember
from order.managers import OrderManager, PriceManager
from order.models import Price, Order
from order.managers import DiskConfig
from bill.managers import PaymentManager
from . import MyAPITransactionTestCase
from .tests import create_server_metadata


def create_disk_metadata(
        service_id: str, azone_id: str, disk_size: int,
        pay_type: str, classification: str, user_id, vo_id,
        creation_time, expiration_time=None, remarks: str = '',
        server_id=None, disk_id: str = None, instance_id: str = None,
        lock: str = None
):
    disk = Disk(
        id=disk_id,
        name='',
        instance_id=instance_id if instance_id else rand_utils.short_uuid1_25(),
        instance_name=rand_utils.short_uuid1_25(),
        size=disk_size,
        service_id=service_id,
        azone_id=azone_id,
        azone_name='azone_name',
        quota_type=Disk.QuotaType.PRIVATE.value,
        creation_time=creation_time,
        remarks=remarks,
        task_status=Disk.TaskStatus.CREATING.value,
        expiration_time=expiration_time,
        start_time=creation_time,
        pay_type=pay_type,
        classification=classification,
        user_id=user_id,
        vo_id=vo_id,
        lock=lock if lock else Disk.Lock.FREE.value,
        deleted=False,
        server_id=server_id,
        mountpoint='',
    )
    disk.save(force_insert=True)
    return disk


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
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id,
            'size': 2, 'period': 12, 'remarks': 'testcase创建，可删除', 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo permisson
        member = VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER,
                          inviter=self.user2.username, inviter_id=self.user2.id)
        member.save(force_insert=True)

        # create vo server postpaid mode, no balance
        response = self.client.post(url, data={
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id,
            'size': 3, 'period': 12, 'remarks': 'testcase创建，可删除', 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=409, code='VoBalanceNotEnough', response=response)

        # create order, no "azone_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
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
        self.assertEqual(d_config.disk_azone_id, '')
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

    def test_list_disk(self):
        service2 = ServiceConfig(
            name='test2', name_en='test2_en', data_center=self.service.data_center
        )
        service2.save(force_insert=True)

        server1 = create_server_metadata(
            service=self.service, user=self.user, ram=8, vcpus=6,
            default_user='user', default_password='password',
            ipv4='127.0.0.1', remarks='test server', pay_type=PayType.PREPAID.value
        )
        disk1 = create_disk_metadata(
            service_id=self.service.id, azone_id='1', disk_size=66, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=server1.id
        )
        disk2 = create_disk_metadata(
            service_id=service2.id, azone_id='2', disk_size=88, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=None
        )
        disk3_vo = create_disk_metadata(
            service_id=self.service.id, azone_id='1', disk_size=886, pay_type=PayType.POSTPAID.value,
            classification=Disk.Classification.VO.value, user_id=self.user2.id, vo_id=self.vo.id,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=None
        )

        base_url = reverse('api:disks-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

        # list user disk
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 20)
        self.assertEqual(len(response.data['results']), 2)
        self.assertKeysIn(['id', 'name', 'size', 'service', 'azone_id', 'azone_name', 'creation_time',
                           'remarks', 'task_status', 'expiration_time', 'pay_type', 'classification',
                           'user', 'vo', 'lock', 'deleted', 'server', 'mountpoint', 'attached_time',
                           'detached_time'], response.data['results'][0])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['results'][0]['service'])
        self.assertKeysIn(['id', 'username'], response.data['results'][0]['user'])
        self.assertEqual(response.data['results'][0]['id'], disk2.id)
        self.assertEqual(response.data['results'][1]['id'], disk1.id)
        self.assertKeysIn(['id', 'ipv4', 'vcpus', 'ram', 'image'], response.data['results'][1]['server'])

        # service_id
        query = urlencode(query={'service_id': self.service.id, 'page_size': 10})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 10)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], disk1.id)

        # page, page_size
        query = urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], disk1.id)
        self.assertEqual(response.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(response.data['results'][0]['user']['username'], self.user.username)

        # list vo disk
        query = urlencode(query={'vo_id': 2, 'page_size': 100})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        query = urlencode(query={'vo_id': self.vo.id, 'page_size': 100})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER.value).save()

        query = urlencode(query={'vo_id': self.vo.id, 'page_size': 100})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], disk3_vo.id)
        self.assertEqual(response.data['results'][0]['user']['id'], self.user2.id)
        self.assertEqual(response.data['results'][0]['user']['username'], self.user2.username)
        self.assertEqual(response.data['results'][0]['vo']['id'], self.vo.id)
        self.assertEqual(response.data['results'][0]['vo']['name'], self.vo.name)

        # service_id
        query = urlencode(query={'vo_id': self.vo.id, 'service_id': self.service.id, 'page_size': 10})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 10)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], disk3_vo.id)

        query = urlencode(query={'vo_id': self.vo.id, 'service_id': service2.id, 'page_size': 10})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 10)
        self.assertEqual(len(response.data['results']), 0)

    def test_delete_disk(self):
        service2 = ServiceConfig(
            name='test2', name_en='test2_en', data_center=self.service.data_center
        )
        service2.save(force_insert=True)

        server1 = create_server_metadata(
            service=self.service, user=self.user, ram=8, vcpus=6,
            default_user='user', default_password='password',
            ipv4='127.0.0.1', remarks='test server', pay_type=PayType.PREPAID.value
        )
        disk1 = create_disk_metadata(
            instance_id='testdev',
            service_id=self.service.id, azone_id='1', disk_size=66, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=server1.id,
            lock=Disk.Lock.OPERATION.value
        )

        disk2_vo = create_disk_metadata(
            instance_id='testdev',
            service_id=self.service.id, azone_id='2', disk_size=88, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.VO.value, user_id=self.user.id, vo_id=self.vo.id,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=server1.id,
            lock=Disk.Lock.FREE.value
        )

        base_url = reverse('api:disks-detail', kwargs={'id': 'test'})
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user2)

        # DiskNotExist
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=404, code='DiskNotExist', response=response)

        # AccessDenied
        base_url = reverse('api:disks-detail', kwargs={'id': disk1.id})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # DiskAttached
        self.client.logout()
        self.client.force_login(self.user)
        base_url = reverse('api:disks-detail', kwargs={'id': disk1.id})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=409, code='DiskAttached', response=response)

        # ResourceLocked
        disk1.server_id = None
        disk1.save(update_fields=['server_id'])
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        disk1.lock = Disk.Lock.FREE.value
        disk1.save(update_fields=['lock'])

        # ok
        disk1.refresh_from_db()
        self.assertEqual(disk1.deleted, False)
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        disk1.refresh_from_db()
        self.assertEqual(disk1.deleted, True)

        # ----- vo -----
        # AccessDenied
        base_url = reverse('api:disks-detail', kwargs={'id': disk2_vo.id})
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo permisson
        member = VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER.value,
                          inviter=self.user2.username, inviter_id=self.user2.id)
        member.save(force_insert=True)

        self.assertEqual(disk2_vo.deleted, False)
        response = self.client.delete(base_url)
        self.assertErrorResponse(status_code=409, code='DiskAttached', response=response)

        disk2_vo.server_id = None
        disk2_vo.save(update_fields=['server_id'])
        response = self.client.delete(base_url)
        self.assertEqual(response.status_code, 204)
        disk2_vo.refresh_from_db()
        self.assertEqual(disk2_vo.deleted, True)

    def test_attach_disk(self):
        service2 = ServiceConfig(
            name='test2', name_en='test2_en', data_center=self.service.data_center
        )
        service2.save(force_insert=True)
        server1 = create_server_metadata(
            service=service2, user=self.user, vo_id=self.vo.id, classification=Server.Classification.VO.value,
            ram=8, vcpus=6,
            default_user='user', default_password='password',
            ipv4='127.0.0.1', remarks='test server', pay_type=PayType.PREPAID.value
        )
        disk1 = create_disk_metadata(
            instance_id='testdev',
            service_id=self.service.id, azone_id='1', disk_size=66, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=server1.id,
            lock=Disk.Lock.OPERATION.value
        )

        base_url = reverse('api:disks-attach', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user2)

        # DiskNotExist
        base_url = reverse('api:disks-attach', kwargs={'id': 'test'})
        query = parse.urlencode(query={'server_id': server1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='DiskNotExist', response=response)

        # AccessDenied
        base_url = reverse('api:disks-attach', kwargs={'id': disk1.id})
        query = parse.urlencode(query={'server_id': server1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # DiskAttached
        self.client.logout()
        self.client.force_login(self.user)
        base_url = reverse('api:disks-attach', kwargs={'id': disk1.id})
        query = parse.urlencode(query={'server_id': server1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='DiskAttached', response=response)

        # ResourceLocked
        disk1.server_id = None
        disk1.save(update_fields=['server_id'])
        base_url = reverse('api:disks-attach', kwargs={'id': disk1.id})
        query = parse.urlencode(query={'server_id': server1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        disk1.lock = Disk.Lock.FREE.value
        disk1.save(update_fields=['lock'])

        # NotFound server
        base_url = reverse('api:disks-attach', kwargs={'id': disk1.id})
        query = parse.urlencode(query={'server_id': 'dddd'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        # AccessDenied
        base_url = reverse('api:disks-attach', kwargs={'id': disk1.id})
        query = parse.urlencode(query={'server_id': server1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo permisson
        member = VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER.value,
                          inviter=self.user2.username, inviter_id=self.user2.id)
        member.save(force_insert=True)

        # ResourcesNotSameOwner
        base_url = reverse('api:disks-attach', kwargs={'id': disk1.id})
        query = parse.urlencode(query={'server_id': server1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='ResourcesNotSameOwner', response=response)

        # server1 service2 no match disk1 service1
        server1.classification = Server.Classification.PERSONAL.value
        server1.user_id = self.user.id
        server1.save(update_fields=['classification', 'user_id'])
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='ResourcesNotInSameService', response=response)

        server1.service_id = self.service.id
        server1.save(update_fields=['service_id'])

        # server1 azone_id != disk1 azone_id
        # response = self.client.post(f'{base_url}?{query}')
        # self.assertErrorResponse(status_code=409, code='ResourcesNotInSameZone', response=response)
        #
        # server1.azone_id = disk1.azone_id
        # server1.save(update_fields=['azone_id'])

        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 500)
        message = response.data['message']
        self.assertIn('adapter', message)
        self.assertIn('不存在', message)

    def test_detach_disk(self):
        server1 = create_server_metadata(
            service=self.service, user=self.user, vo_id=self.vo.id, classification=Server.Classification.VO.value,
            ram=8, vcpus=6,
            default_user='user', default_password='password',
            ipv4='127.0.0.1', remarks='test server', pay_type=PayType.PREPAID.value
        )
        disk1 = create_disk_metadata(
            instance_id='testdev',
            service_id=self.service.id, azone_id='1', disk_size=66, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=None,
            lock=Disk.Lock.OPERATION.value
        )

        base_url = reverse('api:disks-detach', kwargs={'id': 'test'})
        response = self.client.post(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user2)

        # DiskNotExist
        base_url = reverse('api:disks-detach', kwargs={'id': 'test'})
        query = parse.urlencode(query={'server_id': server1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='DiskNotExist', response=response)

        # AccessDenied
        base_url = reverse('api:disks-detach', kwargs={'id': disk1.id})
        query = parse.urlencode(query={'server_id': server1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # DiskNotAttached
        self.client.logout()
        self.client.force_login(self.user)
        base_url = reverse('api:disks-detach', kwargs={'id': disk1.id})
        query = parse.urlencode(query={'server_id': server1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='DiskNotAttached', response=response)

        disk1.server_id = server1.id
        disk1.save(update_fields=['server_id'])

        base_url = reverse('api:disks-detach', kwargs={'id': disk1.id})
        query = parse.urlencode(query={'server_id': 'ffddd'})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='DiskNotOnServer', response=response)

        # ResourceLocked
        base_url = reverse('api:disks-detach', kwargs={'id': disk1.id})
        query = parse.urlencode(query={'server_id': server1.id})
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        disk1.lock = Disk.Lock.FREE.value
        disk1.save(update_fields=['lock'])

        # no permission of vo server1
        response = self.client.post(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        server1.classification = Server.Classification.PERSONAL.value
        server1.user_id = self.user.id
        server1.save(update_fields=['classification', 'user_id'])

        response = self.client.post(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 500)
        message = response.data['message']
        self.assertIn('adapter', message)
        self.assertIn('不存在', message)

    def test_detail_disk(self):
        server1 = create_server_metadata(
            service=self.service, user=self.user, ram=8, vcpus=6,
            default_user='user', default_password='password',
            ipv4='127.0.0.1', remarks='test server', pay_type=PayType.PREPAID.value
        )
        disk1 = create_disk_metadata(
            service_id=self.service.id, azone_id='1', disk_size=66, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=server1.id
        )
        disk3_vo = create_disk_metadata(
            service_id=self.service.id, azone_id='1', disk_size=886, pay_type=PayType.POSTPAID.value,
            classification=Disk.Classification.VO.value, user_id=self.user2.id, vo_id=self.vo.id,
            creation_time=timezone.now(), expiration_time=None, remarks='test', server_id=None
        )

        base_url = reverse('api:disks-detail', kwargs={'id': 'test'})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

        base_url = reverse('api:disks-detail', kwargs={'id': 'test'})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=404, code='DiskNotExist', response=response)

        # detail user disk
        base_url = reverse('api:disks-detail', kwargs={'id': disk1.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'size', 'service', 'azone_id', 'azone_name', 'creation_time',
                           'remarks', 'task_status', 'expiration_time', 'pay_type', 'classification',
                           'user', 'vo', 'lock', 'deleted', 'server', 'mountpoint', 'attached_time',
                           'detached_time'], response.data)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['service'])
        self.assertKeysIn(['id', 'username'], response.data['user'])
        self.assertEqual(response.data['id'], disk1.id)
        self.assertKeysIn(['id', 'ipv4', 'vcpus', 'ram', 'image'], response.data['server'])

        # detail vo disk
        base_url = reverse('api:disks-detail', kwargs={'id': disk3_vo.id})
        response = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER.value).save()

        base_url = reverse('api:disks-detail', kwargs={'id': disk3_vo.id})
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['id', 'name', 'size', 'service', 'azone_id', 'azone_name', 'creation_time',
                           'remarks', 'task_status', 'expiration_time', 'pay_type', 'classification',
                           'user', 'vo', 'lock', 'deleted', 'server', 'mountpoint', 'attached_time',
                           'detached_time'], response.data)
        self.assertEqual(response.data['id'], disk3_vo.id)
        self.assertIsNone(response.data['server'])
