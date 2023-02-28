import pytz
from urllib import parse
from decimal import Decimal
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from service.managers import ServicePrivateQuotaManager
from servers.models import Flavor, Server
from utils.test import get_or_create_user, get_or_create_service
from utils.model import PayType, OwnerType
from utils.time import iso_utc_to_datetime
from vo.models import VirtualOrganization, VoMember
from order.managers import OrderManager
from order.models import Price, Order, Resource
from order.managers import ServerConfig
from bill.managers import PaymentManager
from bill.models import PayApp, PayAppService, PayOrgnazition
from adapters.evcloud import EVCloudAdapter
from . import MyAPITransactionTestCase, set_auth_header


class ServerOrderTests(MyAPITransactionTestCase):
    def setUp(self):
        set_auth_header(self)
        self.user = get_or_create_user()
        self.user2 = get_or_create_user(username='user2')
        self.service = get_or_create_service()
        self.default_user = 'root'
        self.default_password = 'password'
        self.flavor = Flavor(vcpus=1, ram=1024, enable=True)
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

        # service privete quota not enough
        url = reverse('api:servers-list')
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除'
        })
        self.assertErrorResponse(status_code=409, code='QuotaShortage', response=response)

        # service quota set
        ServicePrivateQuotaManager().increase(
            service=self.service, vcpus=6, ram=4096, public_ip=1, private_ip=1
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
            'remarks': 'testcase创建，可删除', 'systemdisk_size': 250
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['order_id'], response.data)
        order_id = response.data['order_id']
        order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user)
        self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.WAIT.value)
        self.assertEqual(order.trading_status, order.TradingStatus.OPENING.value)
        self.assertEqual(order.owner_type, OwnerType.USER.value)
        self.assertEqual(order.user_id, self.user.id)

        # 修改镜像id，让订单交付资源失败
        s_config = ServerConfig.from_dict(order.instance_config)
        self.assertEqual(s_config.vm_systemdisk_size, 250)
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
        po = PayOrgnazition(name='机构')
        po.save()
        app_service1 = PayAppService(
            name='service1', app=app, orgnazition=po, service_id=self.service.id
        )
        app_service1.save(force_insert=True)

        now_time = timezone.now()
        user_server_expiration_time = now_time + timedelta(days=100)
        user_server = Server(
            service_id=self.service.id,
            name='user_server',
            instance_id='user_server_id',
            instance_name='instance_user',
            vcpus=2,
            ram=2048,
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
        self.assertEqual(config.vm_ram, user_server.ram)
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
        renew_to_time_utc = renew_to_time.astimezone(tz=pytz.utc)
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
        now_time = timezone.now()
        vo_server_expiration_time = now_time + timedelta(days=100)
        vo_server = Server(
            service_id=self.service.id,
            name='vo_server',
            instance_id='vo_server_id',
            instance_name='instance_vo',
            vcpus=4,
            ram=4096,
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
        renew_to_time = (vo_server_expiration_time + timedelta(days=200)).astimezone(pytz.utc).isoformat()
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
        self.assertEqual(config.vm_ram, vo_server.ram)
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
        now_time = timezone.now()
        user_server = Server(
            service_id=self.service.id,
            name='user_server',
            instance_id='000000',
            instance_name='instance_user',
            vcpus=2,
            ram=2048,
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
