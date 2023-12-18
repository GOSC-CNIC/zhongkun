from urllib import parse
from decimal import Decimal
from datetime import timedelta, timezone

from django.urls import reverse
from django.utils import timezone as dj_timezone
from django.conf import settings

from service.managers import ServicePrivateQuotaManager
from service.models import ServiceConfig
from servers.models import Flavor, Server, ServerArchive
from utils.test import get_or_create_user, get_or_create_service, get_or_create_organization
from utils.model import PayType, OwnerType, ResourceType
from utils.time import iso_utc_to_datetime
from utils.decimal_utils import quantize_10_2
from vo.models import VirtualOrganization, VoMember
from order.managers import OrderManager, PriceManager
from order.models import Price, Order, Resource
from order.managers import ServerConfig
from bill.managers import PaymentManager
from bill.models import PayApp, PayAppService
from metering.measurers import ServerMeasurer
from metering.models import MeteringServer
from adapters.evcloud import EVCloudAdapter
from . import MyAPITransactionTestCase, set_auth_header

utc = timezone.utc


class ServerOrderTests(MyAPITransactionTestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.user2 = get_or_create_user(username='user2')
        self.service = get_or_create_service()
        self.default_user = 'root'
        self.default_password = 'password'
        self.flavor = Flavor(vcpus=2, ram=3, enable=True)
        self.flavor.save(force_insert=True)
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user2
        )
        self.vo.save(force_insert=True)
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
        self.price.save(force_insert=True)

    def test_server_create_bad_request(self):
        url = reverse('api:servers-list')
        response = self.client.post(url, data={})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)
        response = self.client.post(url, data={
            'service_id': 'sss', 'image_id': 'aaa', 'flavor_id': 'xxx'})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # param "pay_type"
        response = self.client.post(url, data={
            'pay_type': 'test', 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'flavor_id': '1'})
        self.assertErrorResponse(status_code=400, code='InvalidPayType', response=response)

        # param "period"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'flavor_id': '1'})
        self.assertErrorResponse(status_code=400, code='MissingPeriod', response=response)
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'flavor_id': '1', 'period': -1})
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'flavor_id': '1', 'period': 12 * 5 + 1})
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)

        # param "flavor_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'period': 12, 'flavor_id': '1'})
        self.assertErrorResponse(status_code=400, code='InvalidFlavorId', response=response)

        # param "service_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': 'test', 'network_id': 'test',
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id})
        self.assertErrorResponse(status_code=400, code='InvalidServiceId', response=response)

        # param "vo_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'vo_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidVoId', response=response)
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo permission
        member = VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER,
                          inviter=self.user2.username, inviter_id=self.user2.id)
        member.save(force_insert=True)

        # service not set pay_app_service_id
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id,
            'vo_id': self.vo.id, 'network_id': 'test'
        })
        self.assertErrorResponse(status_code=409, code='ServiceNoPayAppServiceId', response=response)

        self.service.pay_app_service_id = 'app_service_id'
        self.service.save(update_fields=['pay_app_service_id'])

        # flavor2 of service2
        service2 = ServiceConfig(
            name='test2', org_data_center_id=self.service.org_data_center_id, endpoint_url='test2',
            username='', password='', need_vpn=False
        )
        service2.save(force_insert=True)
        flavor2 = Flavor(vcpus=1, ram=2, enable=True, service_id=service2.id)
        flavor2.save(force_insert=True)
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': 'ss', 'period': 12, 'flavor_id': flavor2.id,
            'vo_id': self.vo.id, 'network_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='FlavorServiceMismatch', response=response)

        # param "network_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id,
            'vo_id': self.vo.id, 'network_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidNetworkId', response=response)

        # get network id
        base_url = reverse('api:networks-list')
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        network_id = response.data[0]['id']

        # param "image_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id,
            'vo_id': self.vo.id, 'network_id': network_id, 'azone_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidImageId', response=response)

        # get image_id
        url = reverse('api:images-paginate-list')
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        image_id = response.data['results'][0]['id']

        # param "azone_id"
        url = reverse('api:servers-list')
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'vo_id': self.vo.id, 'network_id': network_id, 'azone_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidAzoneId', response=response)

    def test_server_create(self):
        # get network id
        base_url = reverse('api:networks-list')
        response = self.client.get(f'{base_url}?service_id={self.service.id}')
        self.assertEqual(response.status_code, 200)
        network_id = response.data[0]['id']
        is_public_network = response.data[0]['public']

        # service not set pay_app_service_id
        url = reverse('api:servers-list')
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除'
        })
        self.assertErrorResponse(status_code=409, code='ServiceNoPayAppServiceId', response=response)

        self.service.pay_app_service_id = 'app_service_id'
        self.service.save(update_fields=['pay_app_service_id'])

        # get image_id
        url = reverse('api:images-paginate-list')
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        image_id = response.data['results'][0]['id']
        min_sys_disk_gb = response.data['results'][0]['min_sys_disk_gb']

        # service quota set
        ServicePrivateQuotaManager().update(
            service=self.service, vcpus=1, ram_gib=1, public_ip=1, private_ip=1
        )

        # service privete quota not enough
        url = reverse('api:servers-list')
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除'
        })
        self.assertErrorResponse(status_code=409, code='QuotaShortage', response=response)

        # service quota set
        ServicePrivateQuotaManager().update(
            service=self.service, vcpus=6, ram_gib=4, public_ip=1, private_ip=1
        )
        # create user server prepaid mode
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除'
        })
        self.assertEqual(response.status_code, 200)
        try:
            self.assertKeysIn(['order_id'], response.data)
            order_id = response.data['order_id']
            order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user)
            self.try_delete_server(server_id=resources[0].instance_id)
        except Exception as e:
            raise e

        # create user server postpaid mode, no balance
        response = self.client.post(url, data={
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除'
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=response)

        # create user server postpaid mode, test "systemdisk_size"
        response = self.client.post(url, data={
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'systemdisk_size': 51
        })
        self.assertErrorResponse(status_code=400, code='InvalidSystemDiskSize', response=response)
        response = self.client.post(url, data={
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'systemdisk_size': 'a'
        })
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        if min_sys_disk_gb > 50:
            response = self.client.post(url, data={
                'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id,
                'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
                'remarks': 'testcase创建，可删除', 'systemdisk_size': 50
            })
            self.assertErrorResponse(status_code=400, code='MinSystemDiskSize', response=response)

        # create user server postpaid mode
        user_account = PaymentManager().get_user_point_account(user_id=self.user.id)
        user_account.balance = Decimal('10000')
        user_account.save()
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'systemdisk_size': 500
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['order_id'], response.data)
        order_id = response.data['order_id']
        order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user)
        self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.WAIT.value)
        self.assertEqual(order.trading_status, order.TradingStatus.OPENING.value)
        self.assertEqual(order.owner_type, OwnerType.USER.value)
        self.assertEqual(order.user_id, self.user.id)

        original_price, trade_price = PriceManager().describe_server_price(
            ram_mib=1024*3, cpu=2, disk_gib=500, public_ip=is_public_network, is_prepaid=True, period=12, days=0)
        self.assertEqual(order.total_amount, quantize_10_2(original_price))
        self.assertEqual(order.payable_amount, quantize_10_2(trade_price))

        # 修改镜像id，让订单交付资源失败
        s_config = ServerConfig.from_dict(order.instance_config)
        self.assertEqual(s_config.vm_systemdisk_size, 500)
        s_config.vm_image_id = 'test'
        order.instance_config = s_config.to_dict()
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
            self.try_delete_server(server_id=resources[0].instance_id)
            self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.FAILED.value)
            self.assertEqual(order.trading_status, order.TradingStatus.UNDELIVERED.value)
            self.assertEqual(order.owner_type, OwnerType.USER.value)
            self.assertEqual(order.user_id, self.user.id)
        except Exception as e:
            raise e

        # --------vo-------------
        # create vo server postpaid mode, no vo permission
        url = reverse('api:servers-list')
        response = self.client.post(url, data={
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id,
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo permisson
        member = VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER,
                          inviter=self.user2.username, inviter_id=self.user2.id)
        member.save(force_insert=True)

        # create vo server postpaid mode, no balance
        response = self.client.post(url, data={
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=409, code='VoBalanceNotEnough', response=response)

        # create vo server postpaid mode, invalid image_id
        # vo_account = PaymentManager().get_vo_point_account(vo_id=self.vo.id)
        # vo_account.balance = Decimal('10000')
        # vo_account.save()

        # create order
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'vo_id': self.vo.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['order_id'], response.data)
        order_id = response.data['order_id']
        order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user)
        self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.WAIT.value)
        self.assertEqual(order.trading_status, order.TradingStatus.OPENING.value)
        self.assertEqual(order.owner_type, OwnerType.VO.value)
        self.assertEqual(order.vo_id, self.vo.id)
        self.assertEqual(order.user_id, self.user.id)

        # 修改镜像id，让订单交付资源失败
        s_config = ServerConfig.from_dict(order.instance_config)
        self.assertEqual(s_config.vm_systemdisk_size, min_sys_disk_gb)
        self.assertGreaterEqual(s_config.vm_systemdisk_size, EVCloudAdapter.SYSTEM_DISK_MIN_SIZE_GB)
        s_config.vm_image_id = 'test'
        order.instance_config = s_config.to_dict()
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
            self.try_delete_server(server_id=resources[0].instance_id)
            self.assertEqual(order.trading_status, order.TradingStatus.UNDELIVERED.value)
            self.assertEqual(order.owner_type, OwnerType.VO.value)
            self.assertEqual(order.vo_id, self.vo.id)
            self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.FAILED.value)
        except Exception as e:
            raise e

    def test_renew_server(self):
        # 余额支付有关配置
        app = PayApp(name='app', id=settings.PAYMENT_BALANCE['app_id'])
        app.save()
        po = get_or_create_organization(name='机构')
        po.save()
        app_service1 = PayAppService(
            name='service1', app=app, orgnazition=po, service_id=self.service.id
        )
        app_service1.save(force_insert=True)

        now_time = dj_timezone.now()
        user_server_expiration_time = now_time + timedelta(days=100)
        user_server = Server(
            service_id=self.service.id,
            name='user_server',
            instance_id='user_server_id',
            instance_name='instance_user',
            vcpus=2,
            ram=2,
            ipv4='127.0.0.1',
            public_ip=True,
            image='',
            image_id='image_id',
            task_status=Server.TASK_CREATE_FAILED,
            expiration_time=None,
            classification=Server.Classification.PERSONAL.value,
            user_id=self.user.id,
            vo_id=None,
            creation_time=now_time,
            start_time=now_time,
            pay_type=PayType.POSTPAID.value,
            lock=Server.Lock.OPERATION.value,
            azone_id='',
            disk_size=0
        )
        user_server.save(force_insert=True)

        # renew user server
        renew_to_time = (now_time + timedelta(200)).isoformat()
        renew_to_time = renew_to_time.split('.')[0] + 'Z'
        url = reverse('api:servers-renew-server', kwargs={'id': user_server.id})
        response = self.client.post(url)
        self.assertErrorResponse(status_code=400, code='MissingPeriod', response=response)

        query = parse.urlencode(query={'period': 10, 'renew_to_time': renew_to_time})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        query = parse.urlencode(query={'period': 0})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)

        query = parse.urlencode(query={'renew_to_time': '2022-02-30T08:08:08Z'})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidRenewToTime', response=response)

        query = parse.urlencode(query={'period': 10})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='UnknownExpirationTime', response=response)

        user_server.expiration_time = user_server_expiration_time
        user_server.save(update_fields=['expiration_time'])

        query = parse.urlencode(query={'renew_to_time': '2022-02-20T08:08:08Z'})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='InvalidRenewToTime', response=response)

        query = parse.urlencode(query={'period': 10})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        user_server.lock = Server.Lock.FREE.value
        user_server.save(update_fields=['lock'])

        query = parse.urlencode(query={'period': 10})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='RenewPrepostOnly', response=response)

        user_server.pay_type = PayType.PREPAID.value
        user_server.save(update_fields=['pay_type'])

        query = parse.urlencode(query={'period': 10})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='RenewDeliveredOkOnly', response=response)

        user_server.task_status = Server.TASK_CREATED_OK
        user_server.save(update_fields=['task_status'])

        # service not set pay_app_service_id
        period = 10
        query = parse.urlencode(query={'period': period})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='ServiceNoPayAppServiceId', response=response)

        self.service.pay_app_service_id = app_service1.id
        self.service.save(update_fields=['pay_app_service_id'])

        # renew user server ok
        period = 10
        query = parse.urlencode(query={'period': period})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        order_id = response.data['order_id']
        order = Order.objects.get(id=order_id)
        resource = Resource.objects.get(order_id=order_id)
        self.assertEqual(resource.instance_id, user_server.id)
        config = ServerConfig.from_dict(order.instance_config)
        self.assertEqual(config.vm_ram, user_server.ram_gib)
        self.assertEqual(config.vm_cpu, user_server.vcpus)
        self.assertEqual(order.period, period)
        self.assertIsNone(order.start_time)
        self.assertIsNone(order.end_time)

        # renew user server again
        period = 10
        query = parse.urlencode(query={'period': period})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='SomeOrderNeetToTrade', response=response)

        # pay renewal order
        user_account = PaymentManager.get_user_point_account(user_id=self.user.id)
        user_account.balance = Decimal(10000)
        user_account.save(update_fields=['balance'])
        url = reverse('api:order-pay-order', kwargs={'id': order_id})
        query = parse.urlencode(query={'payment_method': Order.PaymentMethod.BALANCE.value})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['order_id'], order.id)

        order.refresh_from_db()
        self.assertEqual(order.trading_status, order.TradingStatus.COMPLETED.value)
        self.assertEqual(order.start_time, user_server_expiration_time)
        self.assertEqual(order.end_time, user_server_expiration_time + timedelta(days=period * 30))

        user_server.refresh_from_db()
        self.assertEqual(user_server.expiration_time, user_server_expiration_time + timedelta(days=period * 30))

        # renew user server "renew_to_time" 续费到指定日期
        expiration_time = user_server.expiration_time
        renew_to_time = expiration_time.replace(microsecond=0) + timedelta(days=2)
        renew_to_time_utc = renew_to_time.astimezone(tz=utc)
        self.assertEqual(renew_to_time, renew_to_time_utc)
        renew_to_time_utc_str = renew_to_time_utc.isoformat()
        renew_to_time_utc_str = renew_to_time_utc_str[0:19] + 'Z'

        url = reverse('api:servers-renew-server', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'renew_to_time': renew_to_time_utc_str})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        order_id = response.data['order_id']
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.period, 0)
        self.assertEqual(order.start_time, expiration_time)
        self.assertEqual(order.end_time, renew_to_time_utc)

        # pay renewal order
        url = reverse('api:order-pay-order', kwargs={'id': order_id})
        query = parse.urlencode(query={'payment_method': Order.PaymentMethod.BALANCE.value})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['order_id'], order.id)

        order.refresh_from_db()
        self.assertEqual(order.trading_status, order.TradingStatus.COMPLETED.value)
        self.assertEqual(order.start_time, expiration_time)
        self.assertEqual(order.end_time, renew_to_time_utc)

        user_server.refresh_from_db()
        self.assertEqual(user_server.expiration_time, renew_to_time_utc)

        # ----------renew vo server-----------
        now_time = dj_timezone.now()
        vo_server_expiration_time = now_time + timedelta(days=100)
        vo_server = Server(
            service_id=self.service.id,
            name='vo_server',
            instance_id='vo_server_id',
            instance_name='instance_vo',
            vcpus=4,
            ram=4,
            ipv4='127.0.0.1',
            public_ip=False,
            image='',
            image_id='image_id',
            task_status=Server.TASK_CREATED_OK,
            expiration_time=vo_server_expiration_time,
            classification=Server.Classification.VO.value,
            user_id=self.user.id,
            vo_id=self.vo.id,
            creation_time=now_time,
            start_time=now_time,
            pay_type=PayType.PREPAID.value,
            lock=Server.Lock.FREE.value,
            azone_id='',
            disk_size=0
        )
        vo_server.save(force_insert=True)
        renew_to_time = (vo_server_expiration_time + timedelta(days=200)).astimezone(utc).isoformat()
        renew_to_time = renew_to_time.split('.')[0] + 'Z'
        renew_to_datetime = iso_utc_to_datetime(renew_to_time)

        # renew vo server, no vo permission
        url = reverse('api:servers-renew-server', kwargs={'id': vo_server.id})
        query = parse.urlencode(query={'renew_to_time': renew_to_time})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER.value).save()

        # renew vo server
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        order_id = response.data['order_id']
        order = Order.objects.get(id=order_id)
        resource = Resource.objects.get(order_id=order_id)
        self.assertEqual(resource.instance_id, vo_server.id)
        config = ServerConfig.from_dict(order.instance_config)
        self.assertEqual(config.vm_ram, vo_server.ram_gib)
        self.assertEqual(config.vm_cpu, vo_server.vcpus)
        self.assertEqual(order.period, 0)
        self.assertEqual(order.start_time, vo_server_expiration_time)
        self.assertEqual(order.end_time, renew_to_datetime)

        # pay renewal order
        vo_account = PaymentManager.get_vo_point_account(vo_id=self.vo.id)
        vo_account.balance = Decimal(10000)
        vo_account.save(update_fields=['balance'])
        url = reverse('api:order-pay-order', kwargs={'id': order_id})
        query = parse.urlencode(query={'payment_method': Order.PaymentMethod.BALANCE.value})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['order_id'], order.id)

        order.refresh_from_db()
        self.assertEqual(order.trading_status, order.TradingStatus.COMPLETED.value)
        self.assertEqual(order.start_time, vo_server_expiration_time)
        self.assertEqual(order.end_time, renew_to_datetime)

        vo_server.refresh_from_db()
        self.assertEqual(vo_server.expiration_time, renew_to_datetime)

    def test_modify_pay_type(self):
        # 余额支付有关配置
        app = PayApp(name='app', id=settings.PAYMENT_BALANCE['app_id'])
        app.save()
        po = get_or_create_organization(name='机构')
        po.save()
        app_service1 = PayAppService(
            name='service1', app=app, orgnazition=po, service_id=self.service.id
        )
        app_service1.save(force_insert=True)

        now_time = dj_timezone.now()
        user_server = Server(
            service_id=self.service.id,
            name='user_server',
            instance_id='user_server_id',
            instance_name='instance_user',
            vcpus=6,
            ram=2,
            ipv4='127.0.0.1',
            public_ip=True,
            image='',
            image_id='image_id',
            task_status=Server.TASK_CREATE_FAILED,
            expiration_time=None,
            classification=Server.Classification.PERSONAL.value,
            user_id=self.user.id,
            vo_id=None,
            creation_time=now_time - timedelta(days=1),
            start_time=now_time - timedelta(days=1),
            pay_type=PayType.PREPAID.value,
            lock=Server.Lock.OPERATION.value,
            azone_id='',
            disk_size=100
        )
        user_server.save(force_insert=True)

        # --- user server ----
        # pay_type
        url = reverse('api:servers-modify-pay-type', kwargs={'id': user_server.id})
        response = self.client.post(url)
        self.assertErrorResponse(status_code=400, code='MissingPayType', response=response)
        query = parse.urlencode(query={'pay_type': PayType.POSTPAID.value})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidPayType', response=response)
        query = parse.urlencode(query={'pay_type': PayType.PREPAID.value})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='MissingPeriod', response=response)

        # period
        query = parse.urlencode(query={'pay_type': PayType.PREPAID.value})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='MissingPeriod', response=response)

        query = parse.urlencode(query={'pay_type': PayType.PREPAID.value, 'period': 0})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)

        query = parse.urlencode(query={'pay_type': PayType.PREPAID.value, 'period': 10})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        user_server.lock = Server.Lock.FREE.value
        user_server.save(update_fields=['lock'])

        # Delivered Ok Only
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        user_server.task_status = Server.TASK_CREATED_OK
        user_server.save(update_fields=['task_status'])

        # service not set pay_app_service_id
        query = parse.urlencode(query={'pay_type': PayType.PREPAID.value, 'period': 10})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='ServiceNoPayAppServiceId', response=response)

        self.service.pay_app_service_id = app_service1.id
        self.service.save(update_fields=['pay_app_service_id'])

        # only postpaid can to prepaid
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        user_server.pay_type = PayType.POSTPAID.value
        user_server.save(update_fields=['pay_type'])

        # renew user server ok
        period = 10
        query = parse.urlencode(query={'pay_type': PayType.PREPAID.value, 'period': period})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        order_id = response.data['order_id']
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.order_type, Order.OrderType.POST2PRE.value)
        self.assertEqual(order.status, Order.Status.UNPAID.value)
        original_price, trade_price = PriceManager().describe_server_price(
            ram_mib=2048, cpu=6, disk_gib=100, public_ip=True, is_prepaid=True, period=period, days=0)
        self.assertEqual(order.total_amount, quantize_10_2(original_price))
        self.assertEqual(order.payable_amount, quantize_10_2(trade_price))
        self.assertEqual(order.period, period)
        self.assertIsNone(order.start_time)
        self.assertIsNone(order.end_time)
        self.assertEqual(order.resource_type, ResourceType.VM.value)

        resource = Resource.objects.get(order_id=order_id)
        self.assertEqual(resource.instance_id, user_server.id)
        config = ServerConfig.from_dict(order.instance_config)
        self.assertEqual(config.vm_ram, user_server.ram_gib)
        self.assertEqual(config.vm_cpu, user_server.vcpus)

        # post user server again
        query = parse.urlencode(query={'pay_type': PayType.PREPAID.value, 'period': period})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='SomeOrderNeetToTrade', response=response)

        # pay order
        user_account = PaymentManager.get_user_point_account(user_id=self.user.id)
        user_account.balance = Decimal(70000)
        user_account.save(update_fields=['balance'])
        url = reverse('api:order-pay-order', kwargs={'id': order_id})
        query = parse.urlencode(query={'payment_method': Order.PaymentMethod.BALANCE.value})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['order_id'], order.id)

        order.refresh_from_db()
        user_server.refresh_from_db()
        resource = Resource.objects.get(order_id=order_id)
        self.assertEqual(resource.instance_status, Resource.InstanceStatus.SUCCESS.value)
        self.assertEqual(order.trading_status, order.TradingStatus.COMPLETED.value)
        self.assertEqual(order.start_time, user_server.start_time)
        self.assertEqual(order.end_time, user_server.expiration_time)
        self.assertEqual(order.end_time, user_server.start_time + timedelta(days=period * 30))
        self.assertEqual(user_server.pay_type, PayType.PREPAID.value)

        # log
        sa_logs = ServerArchive.objects.filter(archive_type=ServerArchive.ArchiveType.POST2PRE.value).all()
        self.assertEqual(len(sa_logs), 1)
        log: ServerArchive = sa_logs[0]
        self.assertEqual(log.deleted_time, user_server.start_time)

        # ----------renew vo server-----------
        now_time = dj_timezone.now()
        vo_server = Server(
            service_id=self.service.id,
            name='vo_server',
            instance_id='vo_server_id',
            instance_name='instance_vo',
            vcpus=4,
            ram=4,
            ipv4='127.0.0.1',
            public_ip=False,
            image='',
            image_id='image_id',
            task_status=Server.TASK_CREATED_OK,
            expiration_time=None,
            classification=Server.Classification.VO.value,
            user_id=self.user.id,
            vo_id=self.vo.id,
            creation_time=now_time - timedelta(days=1),
            start_time=now_time - timedelta(days=1),
            pay_type=PayType.POSTPAID.value,
            lock=Server.Lock.FREE.value,
            azone_id='',
            disk_size=0
        )
        vo_server.save(force_insert=True)

        # post vo server, no vo permission
        url = reverse('api:servers-modify-pay-type', kwargs={'id': vo_server.id})
        query = parse.urlencode(query={'pay_type': PayType.PREPAID.value, 'period': 6})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo member
        VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER.value).save()

        # post vo server
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        order_id = response.data['order_id']
        vo_order = Order.objects.get(id=order_id)
        self.assertEqual(vo_order.order_type, Order.OrderType.POST2PRE.value)
        self.assertEqual(vo_order.status, Order.Status.UNPAID.value)
        original_price, trade_price = PriceManager().describe_server_price(
            ram_mib=4096, cpu=4, disk_gib=0, public_ip=False, is_prepaid=True, period=6, days=0)
        self.assertEqual(vo_order.total_amount, quantize_10_2(original_price))
        self.assertEqual(vo_order.payable_amount, quantize_10_2(trade_price))
        self.assertEqual(vo_order.period, 6)
        self.assertIsNone(vo_order.start_time)
        self.assertIsNone(vo_order.end_time)
        self.assertEqual(vo_order.resource_type, ResourceType.VM.value)

        resource = Resource.objects.get(order_id=order_id)
        self.assertEqual(resource.instance_id, vo_server.id)
        config = ServerConfig.from_dict(vo_order.instance_config)
        self.assertEqual(config.vm_ram, vo_server.ram_gib)
        self.assertEqual(config.vm_cpu, vo_server.vcpus)

        # pay renewal order
        vo_account = PaymentManager.get_vo_point_account(vo_id=self.vo.id)
        vo_account.balance = Decimal(2000)
        vo_account.save(update_fields=['balance'])
        url = reverse('api:order-pay-order', kwargs={'id': order_id})
        query = parse.urlencode(query={'payment_method': Order.PaymentMethod.BALANCE.value})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['order_id'], vo_order.id)

        vo_order.refresh_from_db()
        vo_server.refresh_from_db()
        self.assertEqual(vo_order.trading_status, vo_order.TradingStatus.COMPLETED.value)
        self.assertEqual(vo_order.start_time, vo_server.start_time)
        self.assertEqual(vo_order.end_time, vo_server.expiration_time)
        self.assertEqual(vo_order.end_time, vo_server.start_time + timedelta(days=6 * 30))
        self.assertEqual(vo_server.pay_type, PayType.PREPAID.value)
        resource = Resource.objects.get(order_id=order_id)
        self.assertEqual(resource.instance_status, Resource.InstanceStatus.SUCCESS.value)

        # log
        count = ServerArchive.objects.filter(archive_type=ServerArchive.ArchiveType.POST2PRE.value).count()
        self.assertEqual(count, 2)

        # 计量
        today_start_time = dj_timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        metering_date = dj_timezone.now().date()
        measurer = ServerMeasurer(metering_date=metering_date)
        # 顺序先server后archive，因为数据库数据流向从server到archive
        measurer.metering_loop(loop_server=True)
        measurer.metering_loop(loop_server=False)
        self.assertEqual(MeteringServer.objects.count(), 2)
        u_mt = MeteringServer.objects.filter(date=metering_date, server_id=user_server.id).first()
        self.assertEqual(round(u_mt.cpu_hours), user_server.vcpus * 24)
        self.assertEqual(round(u_mt.ram_hours), user_server.ram_gib * 24)
        self.assertLess(u_mt.trade_amount, u_mt.original_amount)
        # 按量付费金额占比
        u_zb = (user_server.start_time - today_start_time).total_seconds() / (3600 * 24)
        u_m_zb = u_mt.trade_amount / u_mt.original_amount
        delta = Decimal.from_float(u_zb) - u_m_zb
        self.assertEqual(int(delta * 1000), 0)

        vo_mt = MeteringServer.objects.filter(date=metering_date, server_id=vo_server.id).first()
        self.assertEqual(round(vo_mt.cpu_hours), vo_server.vcpus * 24)
        self.assertEqual(round(vo_mt.ram_hours), vo_server.ram_gib * 24)
        self.assertLess(vo_mt.trade_amount, vo_mt.original_amount)
        # 按量付费金额占比
        u_zb = (vo_server.start_time - today_start_time).total_seconds() / (3600 * 24)
        u_m_zb = vo_mt.trade_amount / vo_mt.original_amount
        delta = Decimal.from_float(u_zb) - u_m_zb
        self.assertEqual(int(delta * 1000), 0)

    def try_delete_server(self, server_id: str):
        url = reverse('api:servers-detail', kwargs={'id': server_id})
        response = self.client.delete(url)
        if response.status_code == 204:
            print(f'Delete server({server_id}) OK.')
        elif response.status_code == 404:
            print(f'Delete Ok, server({server_id}) not found.')
        else:
            print(f'Delete server({server_id}) Failed.')

    def test_suspend_server(self):
        now_time = dj_timezone.now()
        user_server = Server(
            service_id=self.service.id,
            name='user_server',
            instance_id='000000',
            instance_name='instance_user',
            vcpus=2,
            ram=2,
            ipv4='127.0.0.1',
            public_ip=True,
            image='',
            image_id='image_id',
            task_status=Server.TASK_CREATE_FAILED,
            expiration_time=None,
            classification=Server.Classification.PERSONAL.value,
            user_id=self.user.id,
            vo_id=None,
            creation_time=now_time,
            start_time=now_time,
            pay_type=PayType.POSTPAID.value,
            lock=Server.Lock.OPERATION.value,
            situation=Server.Situation.ARREARAGE.value,
            azone_id='',
            disk_size=0
        )
        user_server.save(force_insert=True)

        url = reverse('api:servers-server-suspend', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'act': 'act'})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        url = reverse('api:servers-server-suspend', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'act': Server.Situation.EXPIRED.value})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # service admin
        self.service.users.add(self.user)
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        url = reverse('api:servers-server-suspend', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'act': Server.Situation.NORMAL.value})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.NORMAL.value)

        self.service.users.remove(self.user)
        url = reverse('api:servers-server-suspend', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'act': Server.Situation.EXPIRED.value})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin
        self.user.set_federal_admin()
        url = reverse('api:servers-server-suspend', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'act': Server.Situation.NORMAL.value})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)

        url = reverse('api:servers-server-suspend', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'act': Server.Situation.ARREARAGE.value})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)
