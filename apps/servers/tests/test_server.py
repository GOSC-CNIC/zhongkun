from time import sleep as time_sleep
from urllib import parse
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from django.urls import reverse
from django.utils import timezone as dj_timezone
from django.conf import settings

from apps.servers.managers import ServicePrivateQuotaManager, ServerSnapshotManager
from apps.servers.models import ServiceConfig, EVCloudPermsLog
from apps.servers.models import Flavor, Server, ServerArchive, Disk, ResourceActionLog, ServerSnapshot
from utils.test import (
    get_or_create_user, get_or_create_service, get_or_create_organization,
    MyAPITransactionTestCase, MyAPITestCase
)
from utils.model import PayType, OwnerType, ResourceType
from utils.time import iso_utc_to_datetime
from utils.decimal_utils import quantize_10_2
from apps.vo.models import VirtualOrganization, VoMember
from apps.vo.tests import VoTests
from apps.app_order.managers import OrderManager, PriceManager
from apps.app_order.models import Order, Resource
from apps.app_order.managers import ServerConfig
from apps.app_order.tests import create_price
from apps.app_wallet.managers import PaymentManager
from apps.app_wallet.models import PayApp, PayAppService
from apps.app_metering.measurers import ServerMeasurer
from apps.app_metering.models import MeteringServer
from core.adapters.evcloud import EVCloudAdapter
from core.adapters import outputs
from core import site_configs_manager
from . import create_server_metadata


utc = timezone.utc
PAY_APP_ID = site_configs_manager.get_pay_app_id(settings)


class ServerOrderTests(MyAPITransactionTestCase):
    def setUp(self):
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
        self.price = create_price()

    def test_server_create_bad_request(self):
        url = reverse('servers-api:servers-list')
        response = self.client.post(url, data={})
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)
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
            'image_id': 'ss', 'flavor_id': '1', 'period': 12*5 + 1})
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)

        # param "period_unit"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'flavor_id': '1', 'period': 6, 'period_unit': 'ss'})
        self.assertErrorResponse(status_code=400, code='InvalidPeriodUnit', response=response)
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'flavor_id': '1', 'period': 12*5 + 1, 'period_unit': Order.PeriodUnit.MONTH.value})
        self.assertErrorResponse(status_code=400, code='InvalidPeriod', response=response)
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'flavor_id': '1', 'period': 30*12*5 + 1, 'period_unit': Order.PeriodUnit.DAY.value})
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

        # vo
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # set vo permission
        member = VoMember(user_id=self.user.id, vo_id=self.vo.id, role=VoMember.Role.LEADER,
                          inviter=self.user2.username, inviter_id=self.user2.id)
        member.save(force_insert=True)

        # param "network_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id,
            'vo_id': self.vo.id, 'network_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidNetworkId', response=response)

        # get network id
        base_url = reverse('servers-api:networks-list')
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
        url = reverse('servers-api:images-paginate-list')
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        image_id = response.data['results'][0]['id']

        # param "azone_id"
        url = reverse('servers-api:servers-list')
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'vo_id': self.vo.id, 'network_id': network_id, 'azone_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidAzoneId', response=response)

        # --- as-admin test ---
        # "username" only when as-admin
        base_url = reverse('servers-api:servers-list')
        response = self.client.post(base_url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'network_id': network_id, 'azone_id': 'test',
            'username': 'user11'
        })
        self.assertErrorResponse(status_code=400, code='ArgumentConflict', response=response)

        # username not exists
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'network_id': network_id, 'azone_id': 'test',
            'username': 'user11'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUsername', response=response)

        # username and vo_id
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'vo_id': self.vo.id, 'network_id': network_id, 'azone_id': 'test',
            'username': self.user2.username
        })
        self.assertErrorResponse(status_code=400, code='ArgumentConflict', response=response)

        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'network_id': network_id, 'azone_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='MissingArgument', response=response)

        # admin permission test
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'network_id': network_id, 'azone_id': 'test',
            'username': self.user2.username
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user.set_fed_admin(is_fed=True)
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'network_id': network_id, 'azone_id': 'test',
            'username': self.user2.username
        })
        self.assertErrorResponse(status_code=400, code='InvalidAzoneId', response=response)

        self.user.set_fed_admin(is_fed=False)
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'network_id': network_id, 'azone_id': 'test',
            'username': self.user2.username
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.service.org_data_center.add_admin_user(user=self.user, is_ops_user=False)
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'network_id': network_id, 'azone_id': 'test',
            'username': self.user2.username
        })
        self.assertErrorResponse(status_code=400, code='InvalidAzoneId', response=response)

    def test_server_create(self):
        self.client.force_login(self.user)
        # get network id
        base_url = reverse('servers-api:networks-list')
        response = self.client.get(f'{base_url}?service_id={self.service.id}')
        self.assertEqual(response.status_code, 200)
        network_id = response.data[0]['id']
        is_public_network = response.data[0]['public']

        # service not set pay_app_service_id
        url = reverse('servers-api:servers-list')
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除'
        })
        self.assertErrorResponse(status_code=409, code='ServiceNoPayAppServiceId', response=response)

        self.service.pay_app_service_id = 'app_service_id'
        self.service.save(update_fields=['pay_app_service_id'])

        # get image_id
        url = reverse('servers-api:images-paginate-list')
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
        url = reverse('servers-api:servers-list')
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

        # create user server prepaid mode
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
            ram_mib=1024*3, cpu=2, disk_gib=500, public_ip=is_public_network, is_prepaid=True,
            period=12, period_unit=Order.PeriodUnit.MONTH.value, days=0)
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
        pay_url = reverse('order-api:order-pay-order', kwargs={'id': order_id})
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

        # ----- 一次订购多个资源 test ---
        url = reverse('servers-api:servers-list')
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'number': 0
        })
        self.assertErrorResponse(status_code=400, code='InvalidNumber', response=response)
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'number': 4
        })
        self.assertErrorResponse(status_code=400, code='InvalidNumber', response=response)

        # service privete quota not enough
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'number': 3
        })
        self.assertErrorResponse(status_code=409, code='QuotaShortage', response=response)

        # service quota set
        ServicePrivateQuotaManager().update(
            service=self.service, vcpus=6 + 2 * 3, ram_gib=4 + 3 * 3, public_ip=1 + 3, private_ip=1 + 3
        )
        # create user server prepaid mode
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'period_unit': Order.PeriodUnit.MONTH.value,
            'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'systemdisk_size': 500, 'number': 3
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['order_id'], response.data)
        order_id = response.data['order_id']
        order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user)
        self.assertEqual(order.number, 3)
        self.assertEqual(len(resources), 3)

        original_price, trade_price = PriceManager().describe_server_price(
            ram_mib=1024 * 3, cpu=2, disk_gib=500, public_ip=is_public_network, is_prepaid=True,
            period=12, period_unit=Order.PeriodUnit.MONTH.value, days=0)
        self.assertEqual(order.total_amount, quantize_10_2(original_price) * 3)
        self.assertEqual(int(order.payable_amount), int(quantize_10_2(trade_price) * 3))

        # --------vo-------------
        # create vo server postpaid mode, no vo permission
        url = reverse('servers-api:servers-list')
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
            'image_id': image_id, 'period': 120, 'period_unit': Order.PeriodUnit.DAY.value,
            'flavor_id': self.flavor.id, 'network_id': network_id,
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
            'image_id': image_id, 'period': 120, 'period_unit': Order.PeriodUnit.DAY.value,
            'flavor_id': self.flavor.id, 'network_id': network_id,
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
        original_price, trade_price = PriceManager().describe_server_price(
            ram_mib=1024 * 3, cpu=2, disk_gib=min_sys_disk_gb, public_ip=is_public_network, is_prepaid=True,
            period=120, period_unit=Order.PeriodUnit.DAY.value, days=0)
        self.assertEqual(order.total_amount, quantize_10_2(original_price))
        self.assertEqual(int(order.payable_amount), int(quantize_10_2(trade_price)))

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
        pay_url = reverse('order-api:order-pay-order', kwargs={'id': order_id})
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

    def test_admin_server_create(self):
        self.client.force_login(self.user)
        # get network id
        base_url = reverse('servers-api:networks-list')
        response = self.client.get(f'{base_url}?service_id={self.service.id}')
        self.assertEqual(response.status_code, 200)
        network_id = response.data[0]['id']
        is_public_network = response.data[0]['public']

        # service set pay_app_service_id
        self.service.pay_app_service_id = 'app_service_id'
        self.service.save(update_fields=['pay_app_service_id'])

        # get image_id
        url = reverse('servers-api:images-paginate-list')
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        image_id = response.data['results'][0]['id']
        min_sys_disk_gb = response.data['results'][0]['min_sys_disk_gb']

        # service quota set
        ServicePrivateQuotaManager().update(
            service=self.service, vcpus=6, ram_gib=4, public_ip=1, private_ip=1
        )

        # admin create user server prepaid mode
        url = reverse('servers-api:servers-list')
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'username': self.user2.username
        })
        self.assertEqual(response.status_code, 403)
        self.service.org_data_center.add_admin_user(user=self.user, is_ops_user=True)

        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'username': self.user2.username
        })
        self.assertEqual(response.status_code, 200)
        try:
            self.assertKeysIn(['order_id'], response.data)
            order_id = response.data['order_id']
            order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user2)
            self.assertEqual(order.owner_type, OwnerType.USER.value)
            self.assertEqual(order.user_id, self.user2.id)
            self.assertEqual(order.username, self.user2.username)
            self.assertEqual(order.vo_id, '')
            self.assertEqual(order.vo_name, '')
            self.try_delete_server(server_id=resources[0].instance_id)
        except Exception as e:
            raise e

        # create user2 server postpaid mode, no balance
        user_account = PaymentManager().get_user_point_account(user_id=self.user.id)
        user_account.balance = Decimal('20000')
        user_account.save(update_fields=['balance'])
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'username': self.user2.username
        })
        self.assertErrorResponse(status_code=409, code='BalanceNotEnough', response=response)

        # create user2 server prepaid mode
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'systemdisk_size': 500, 'username': self.user2.username
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['order_id'], response.data)
        order_id = response.data['order_id']
        order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user2)
        self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.WAIT.value)
        self.assertEqual(order.trading_status, order.TradingStatus.OPENING.value)
        self.assertEqual(order.owner_type, OwnerType.USER.value)
        self.assertEqual(order.user_id, self.user2.id)
        self.assertEqual(order.username, self.user2.username)
        self.assertEqual(order.vo_id, '')
        self.assertEqual(order.vo_name, '')
        self.assertIn(self.user.username, order.description)

        original_price, trade_price = PriceManager().describe_server_price(
            ram_mib=1024*3, cpu=2, disk_gib=500, public_ip=is_public_network, is_prepaid=True,
            period=12, period_unit=Order.PeriodUnit.MONTH.value, days=0)
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
        pay_url = reverse('order-api:order-pay-order', kwargs={'id': order_id})
        pay_query = parse.urlencode(query={
            'payment_method': Order.PaymentMethod.BALANCE.value, 'as-admin': ''
        })
        response = self.client.post(f'{pay_url}?{pay_query}')
        self.assertEqual(response.status_code, 200)
        try:
            order, resources = OrderManager().get_order_detail(order_id=order_id, user=self.user2)
            self.try_delete_server(server_id=resources[0].instance_id)
            self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.FAILED.value)
            self.assertEqual(order.trading_status, order.TradingStatus.UNDELIVERED.value)
            self.assertEqual(order.owner_type, OwnerType.USER.value)
            self.assertEqual(order.user_id, self.user2.id)
        except Exception as e:
            raise e

        # ----- 一次订购多个资源 test ---
        # --------vo-------------
        # create vo server postpaid mode, no balance
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.POSTPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 120, 'period_unit': Order.PeriodUnit.DAY.value,
            'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=409, code='VoBalanceNotEnough', response=response)

        # create order
        response = self.client.post(f'{url}?{query}', data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 120, 'period_unit': Order.PeriodUnit.DAY.value,
            'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'vo_id': self.vo.id
        })
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['order_id'], response.data)
        order_id = response.data['order_id']
        order, resources = OrderManager().get_order_detail(order_id=order_id, user=None, check_permission=False)
        self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.WAIT.value)
        self.assertEqual(order.trading_status, order.TradingStatus.OPENING.value)
        self.assertEqual(order.owner_type, OwnerType.VO.value)
        self.assertEqual(order.vo_id, self.vo.id)
        self.assertEqual(order.user_id, self.user.id)
        self.assertIn(self.user.username, order.description)
        original_price, trade_price = PriceManager().describe_server_price(
            ram_mib=1024 * 3, cpu=2, disk_gib=min_sys_disk_gb, public_ip=is_public_network, is_prepaid=True,
            period=120, period_unit=Order.PeriodUnit.DAY.value, days=0)
        self.assertEqual(order.total_amount, quantize_10_2(original_price))
        self.assertEqual(int(order.payable_amount), int(quantize_10_2(trade_price)))

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
        pay_url = reverse('order-api:order-pay-order', kwargs={'id': order_id})
        query = parse.urlencode(query={
            'payment_method': Order.PaymentMethod.BALANCE.value, 'as-admin': ''
        })
        response = self.client.post(f'{pay_url}?{query}')
        self.assertEqual(response.status_code, 200)
        try:
            order, resources = OrderManager().get_order_detail(order_id=order_id, user=None, check_permission=False)
            self.try_delete_server(server_id=resources[0].instance_id)
            self.assertEqual(order.trading_status, order.TradingStatus.UNDELIVERED.value)
            self.assertEqual(order.owner_type, OwnerType.VO.value)
            self.assertEqual(order.vo_id, self.vo.id)
            self.assertEqual(resources[0].instance_status, resources[0].InstanceStatus.FAILED.value)
        except Exception as e:
            raise e

    def test_renew_server(self):
        # 余额支付有关配置
        app = PayApp(name='app', id=PAY_APP_ID)
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
        url = reverse('servers-api:servers-renew-server', kwargs={'id': user_server.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

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
        self.assertEqual(order.period_unit, Order.PeriodUnit.MONTH.value)
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
        url = reverse('order-api:order-pay-order', kwargs={'id': order_id})
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

        url = reverse('servers-api:servers-renew-server', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'renew_to_time': renew_to_time_utc_str})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        order_id = response.data['order_id']
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.period, 0)
        self.assertEqual(order.start_time, expiration_time)
        self.assertEqual(order.end_time, renew_to_time_utc)

        # pay renewal order
        url = reverse('order-api:order-pay-order', kwargs={'id': order_id})
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

        # ----  as admin test----
        self.client.logout()
        self.client.force_login(self.user2)
        url = reverse('servers-api:servers-renew-server', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'period': 2, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.service.org_data_center.add_admin_user(self.user2)
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        order_id = response.data['order_id']
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.period, 2)
        self.assertEqual(order.period_unit, Order.PeriodUnit.MONTH.value)
        self.assertEqual(order.owner_type, OwnerType.USER.value)
        self.assertEqual(order.user_id, user_server.user.id)
        self.assertEqual(order.username, user_server.user.username)
        self.assertIn(self.user2.username, order.description)

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

        self.client.logout()
        self.client.force_login(self.user)

        # renew vo server, no vo permission
        url = reverse('servers-api:servers-renew-server', kwargs={'id': vo_server.id})
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
        url = reverse('order-api:order-pay-order', kwargs={'id': order_id})
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

        # 单次续费最长2年
        url = reverse('servers-api:servers-renew-server', kwargs={'id': vo_server.id})
        query = parse.urlencode(query={'period': 25})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='PeriodTooLong', response=response)

        url = reverse('servers-api:servers-renew-server', kwargs={'id': vo_server.id})
        renew_to_datetime += timedelta(days=365*2 + 1)
        renew_to_time = renew_to_datetime.astimezone(utc).isoformat()
        if '.' in renew_to_time:
            renew_to_time = renew_to_time.split('.')[0] + 'Z'
        elif '+' in renew_to_time:
            renew_to_time = renew_to_time.split('+')[0] + 'Z'
        else:
            renew_to_time = renew_to_time.split('-')[0] + 'Z'

        query = parse.urlencode(query={'renew_to_time': renew_to_time})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='PeriodTooLong', response=response)

        # ----  as admin test----
        self.service.org_data_center.remove_admin_user(self.user2)
        self.client.logout()
        self.client.force_login(self.user2)
        url = reverse('servers-api:servers-renew-server', kwargs={'id': vo_server.id})
        query = parse.urlencode(query={'period': 6, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user2.set_federal_admin()
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        order_id = response.data['order_id']
        order = Order.objects.get(id=order_id)
        self.assertEqual(order.period, 6)
        self.assertEqual(order.period_unit, Order.PeriodUnit.MONTH.value)
        self.assertEqual(order.owner_type, OwnerType.VO.value)
        self.assertEqual(order.user_id, self.user2.id)
        self.assertEqual(order.username, self.user2.username)
        self.assertIn(self.user2.username, order.description)

    def test_modify_pay_type(self):
        # 余额支付有关配置
        app = PayApp(name='app', id=PAY_APP_ID)
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
        url = reverse('servers-api:servers-modify-pay-type', kwargs={'id': user_server.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

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
            ram_mib=2048, cpu=6, disk_gib=100, public_ip=True, is_prepaid=True,
            period=period, period_unit=Order.PeriodUnit.MONTH.value, days=0)
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
        url = reverse('order-api:order-pay-order', kwargs={'id': order_id})
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
        url = reverse('servers-api:servers-modify-pay-type', kwargs={'id': vo_server.id})
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
            ram_mib=4096, cpu=4, disk_gib=0, public_ip=False, is_prepaid=True,
            period=6, period_unit=Order.PeriodUnit.MONTH.value, days=0)
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
        url = reverse('order-api:order-pay-order', kwargs={'id': order_id})
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
        url = reverse('servers-api:servers-detail', kwargs={'id': server_id})
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

        url = reverse('servers-api:servers-server-suspend', kwargs={'id': user_server.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

        query = parse.urlencode(query={'act': 'act'})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        url = reverse('servers-api:servers-server-suspend', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'act': Server.Situation.EXPIRED.value})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # service admin
        self.service.users.add(self.user)
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        url = reverse('servers-api:servers-server-suspend', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'act': Server.Situation.NORMAL.value})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.NORMAL.value)

        self.service.users.remove(self.user)
        url = reverse('servers-api:servers-server-suspend', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'act': Server.Situation.EXPIRED.value})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # federal admin
        self.user.set_federal_admin()
        url = reverse('servers-api:servers-server-suspend', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'act': Server.Situation.NORMAL.value})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)

        url = reverse('servers-api:servers-server-suspend', kwargs={'id': user_server.id})
        query = parse.urlencode(query={'act': Server.Situation.ARREARAGE.value})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)


class ServersTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.service = get_or_create_service()
        self.default_user = 'root'
        self.default_password = 'password'
        self.miss_server = create_server_metadata(
            service=self.service, user=self.user, ram=1,
            default_user=self.default_user, default_password=self.default_password,
            ipv4='127.0.0.1', remarks='test miss server', pay_type=PayType.PREPAID.value
        )
        self.vo1 = VirtualOrganization(name='test vo1', company='网络中心', description='unittest', owner=self.user)
        self.vo1.save(force_insert=True)
        self.vo_id = self.vo1.id
        self.vo_server = create_server_metadata(
            service=self.service, user=self.user, vo_id=self.vo_id, ram=2,
            classification=Server.Classification.VO, default_user=self.default_user,
            default_password=self.default_password,
            ipv4='127.0.0.12', remarks='test'
        )

    @staticmethod
    def server_detail_response(client, server_id, querys: dict = None):
        url = reverse('servers-api:servers-detail', kwargs={'id': server_id})
        if querys:
            query = parse.urlencode(query=querys)
            url = f'{url}?{query}'

        response = client.get(url)
        if response.status_code == 500:
            print(response.data)

        return response

    def test_server_remark(self):
        url = reverse('servers-api:servers-server-remark', kwargs={'id': self.miss_server.id})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, 400)

        url = reverse('servers-api:servers-server-remark', kwargs={'id': '00'})
        query = parse.urlencode(query={'remark': 'ss'})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 404)

        remark = 'test-remarks'
        url = reverse('servers-api:servers-server-remark', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.miss_server.refresh_from_db()
        self.assertEqual(remark, self.miss_server.remarks)

        # vo server when vo owner
        remark = 'test-vo-remarks'
        url = reverse('servers-api:servers-server-remark', kwargs={'id': self.vo_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.vo_server.refresh_from_db()
        self.assertEqual(remark, self.vo_server.remarks)

    def test_server_status(self):
        url = reverse('servers-api:servers-server_status', kwargs={'id': self.miss_server.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status']['status_code'], outputs.ServerStatus.MISS)

        # vo server
        url = reverse('servers-api:servers-server_status', kwargs={'id': self.vo_server.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status']['status_code'], outputs.ServerStatus.MISS)

        url = reverse('servers-api:servers-server_status', kwargs={'id': 'test'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.assertKeysIn(['code', 'message'], response.data)
        self.assertEqual(response.data['code'], 'NotFound')

        # ----------------admin get server status test -----------------------
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)

        # test when not admin
        url = reverse('servers-api:servers-server_status', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.client.logout()
        self.client.force_login(admin_user)

        # test when service admin
        self.service.users.add(admin_user)
        url = reverse('servers-api:servers-server_status', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query}')
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status']['status_code'], outputs.ServerStatus.MISS)

        # test when federal admin
        self.service.users.remove(admin_user)
        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        admin_user.set_federal_admin()
        url = reverse('servers-api:servers-server_status', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query}')
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status']['status_code'], outputs.ServerStatus.MISS)

    def test_server_detail(self):
        response = self.server_detail_response(client=self.client, server_id='motfound')
        self.assertEqual(response.status_code, 404)
        self.assertKeysIn(['code', 'message'], response.data)
        self.assertEqual(response.data['code'], 'NotFound')

        response = self.server_detail_response(client=self.client, server_id=self.miss_server.id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server'], response.data)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time", "remarks",
                           "service", 'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password", "pay_type",
                           "attached_disks"], response.data['server'])
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['server']['service'])
        self.assert_is_subdict_of(sub={
            "default_user": self.default_user, "default_password": self.default_password
        }, d=response.data['server'])
        self.assertIsInstance(response.data['server']['attached_disks'], list)
        self.assertEqual(len(response.data['server']['attached_disks']), 0)

        # ----------------admin get server detail test -----------------------
        from apps.servers.tests.test_disk import create_disk_metadata
        create_disk_metadata(
            service_id=self.service.id, azone_id='1', disk_size=6, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=dj_timezone.now(), server_id=self.miss_server.id
        )
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)

        # test when not admin
        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.client.logout()
        self.client.force_login(admin_user)

        # test when service admin
        self.service.users.add(admin_user)
        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server'], response.data)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time", "remarks",
                           "service", 'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password", "pay_type",
                           "attached_disks"], response.data['server'])
        self.assert_is_subdict_of(sub={
            "default_user": self.default_user, "default_password": self.default_password
        }, d=response.data['server'])
        self.assertIsInstance(response.data['server']['attached_disks'], list)
        self.assertEqual(len(response.data['server']['attached_disks']), 1)
        self.assertKeysIn(["id", "size", "creation_time", "remarks", "expiration_time", "mountpoint",
                           "attached_time", "detached_time", "pay_type"], response.data['server']['attached_disks'][0])

        # test when org date center admin
        self.service.users.remove(admin_user)
        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.service.org_data_center.add_admin_user(user=admin_user)
        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server'], response.data)

        # test when federal admin
        self.service.org_data_center.remove_admin_user(user=admin_user)
        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        admin_user.set_federal_admin()
        response = self.server_detail_response(
            client=self.client, server_id=self.miss_server.id, querys={'as-admin': ''})
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server'], response.data)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time", "remarks",
                           "service",
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password", "pay_type"
                           ], response.data['server'])

    def test_server_list(self):
        vo_server = self.vo_server
        vo_id = self.vo_id
        # list user servers
        url = reverse('servers-api:servers-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertIsInstance(response.data['servers'], list)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ram_gib", "ipv4",
                           "public_ip", "image", "creation_time",
                           "remarks", "service", 'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
                           "center_quota", "classification", "vo_id", "user", 'vo',
                           "image_id", "image_desc", "default_user", "default_password", 'instance_id',
                           "lock", "pay_type", 'created_user'], response.data['servers'][0])
        self.assertEqual(response.data['servers'][0]['ram_gib'], 1)
        self.assertEqual(response.data['servers'][0]['ram'], 1)
        self.assertKeysIn([
            "id", "name", "name_en", "service_type", 'endpoint_url'], response.data['servers'][0]['service'])
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.PERSONAL,
            'service': {
                'id': self.miss_server.service.id, 'name': self.miss_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': self.miss_server.service.name_en,
                'endpoint_url': self.miss_server.service.endpoint_url
            },
            'id': self.miss_server.id, 'vo_id': None
        }, d=response.data['servers'][0])

        # param ip-contain
        url = reverse('servers-api:servers-list')
        query = parse.urlencode({'ip-contain': self.miss_server.ipv4})
        url = f'{url}?{query}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.PERSONAL,
            'id': self.miss_server.id, 'ipv4': self.miss_server.ipv4
        }, d=response.data['servers'][0])

        url = reverse('servers-api:servers-list')
        query = parse.urlencode({'ip-contain': 'no-contain'})
        url = f'{url}?{query}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        # query 'status' invalid
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'status': 's'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # query status
        query_str = parse.urlencode(query={'status': 'expired'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        query_str = parse.urlencode(query={'status': 'prepaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)
        query_str = parse.urlencode(query={'status': 'postpaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        # query "public"
        query_str = parse.urlencode(query={'public': 'tr'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query_str = parse.urlencode(query={'public': 'true'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)
        query_str = parse.urlencode(query={'public': 'false'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)

        # param "remark
        url = reverse('servers-api:servers-list')
        query = parse.urlencode({'remark': 'miss'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.PERSONAL,
            'id': self.miss_server.id, 'ipv4': self.miss_server.ipv4
        }, d=response.data['servers'][0])
        query = parse.urlencode({'remark': 'ssmiss'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

        # query 'user-id' only as-admin
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'user-id': 'c'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # query 'username' only as-admin
        query_str = parse.urlencode(query={'username': 'c'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # query 'vo-id' only as-admin
        query_str = parse.urlencode(query={'vo-id': 'c'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # query 'vo-name' only as-admin
        query_str = parse.urlencode(query={'vo-name': 'c'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        # query 'exclude-vo' only as-admin
        query_str = parse.urlencode(query={'exclude-vo': None})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # list vo servers
        url = reverse('servers-api:servers-list-vo-servers', kwargs={'vo_id': self.vo_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertIsInstance(response.data['servers'], list)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['count'], 1)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4", "ram_gib",
                           "public_ip", "image", "creation_time",
                           "remarks", "service", 'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
                           "center_quota", "classification", "vo_id", "user", 'vo',
                           "image_id", "image_desc", "default_user", "default_password", 'instance_id',
                           "lock", "pay_type", 'created_user'], response.data['servers'][0])
        self.assertKeysIn(["id", "name"], response.data['servers'][0]['vo'])
        self.assertEqual(response.data['servers'][0]['ram_gib'], 2)
        self.assertEqual(response.data['servers'][0]['ram'], 2)
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.VO,
            'service': {
                'id': vo_server.service.id, 'name': vo_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': vo_server.service.name_en,
                'endpoint_url': vo_server.service.endpoint_url
            },
            'id': vo_server.id, 'vo_id': vo_id
        }, d=response.data['servers'][0])

        # query 'expired' invalid
        url = reverse('servers-api:servers-list-vo-servers', kwargs={'vo_id': self.vo_id})
        query_str = parse.urlencode(query={'expired': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # query expired
        query_str = parse.urlencode(query={'expired': 'true'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        # query not expired
        query_str = parse.urlencode(query={'expired': 'false'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(self.vo_server.ipv4, response.data['servers'][0]['ipv4'])

        # server vo detail
        response = self.server_detail_response(
            client=self.client, server_id=self.vo_server.id)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['server'], response.data)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4", "ram_gib",
                           "public_ip", "image", "creation_time", "remarks",
                           "service", 'created_user',
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password",
                           "lock", "pay_type"], response.data['server'])
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.VO,
            'service': {
                'id': vo_server.service.id, 'name': vo_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': vo_server.service.name_en,
                'endpoint_url': vo_server.service.endpoint_url
            },
            'id': vo_server.id, 'vo_id': vo_id
        }, d=response.data['server'])

        # ----------------admin list servers test -----------------------
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)
        service66 = ServiceConfig(
            name='test66', name_en='test66_en', org_data_center_id=None,
            endpoint_url='',
            username='',
            service_type=ServiceConfig.ServiceType.EVCLOUD,
            region_id='',
        )
        service66.save()
        admin_server66 = create_server_metadata(
            service=service66, user=admin_user, remarks='admin test',
            default_user=self.default_user, default_password=self.default_password,
            ipv4='159.226.235.66', expiration_time=dj_timezone.now(), public_ip=True
        )

        self.client.logout()
        self.client.force_login(admin_user)

        # list server when not admin user
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # -------------list server when service admin---------------
        self.service.users.add(admin_user)

        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertIsInstance(response.data['servers'], list)
        self.assertEqual(len(response.data['servers']), 2)
        self.assertKeysIn(["id", "name"], response.data['servers'][0]['vo'])

        # query 'status' invalid
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'dd'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # query status
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'expired'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        query_str = parse.urlencode(query={'as-admin': '', 'status': 'prepaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'postpaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.vo_server.id)

        # query "public"
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'tr'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'true'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'false'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # param "remark
        url = reverse('servers-api:servers-list')
        query = parse.urlencode(query={'as-admin': '', 'remark': 'miss'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)
        query = parse.urlencode(query={'as-admin': '', 'remark': 'admin'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        query = parse.urlencode(query={'as-admin': '', 'remark': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

        # list server when service admin bu query parameter 'service_id'
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # list server when service admin bu query parameter 'service_id' and 'user-id'
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id, 'user-id': admin_user.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)

        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id, 'user-id': self.user.id,
                                           'exclude-vo': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4", "ram_gib",
                           "public_ip", "image", "creation_time",
                           "remarks", "service", 'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password", 'instance_id',
                           "lock", "pay_type", 'created_user'], response.data['servers'][0])
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.PERSONAL,
            'service': {
                'id': self.miss_server.service.id, 'name': self.miss_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': self.miss_server.service.name_en,
                'endpoint_url': self.miss_server.service.endpoint_url
            },
            'id': self.miss_server.id, 'vo_id': None
        }, d=response.data['servers'][0])

        # list server when service admin bu query parameter 'service_id' and 'vo-id'
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id, 'vo-id': self.vo_id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.VO,
            'service': {
                'id': vo_server.service.id, 'name': vo_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': vo_server.service.name_en,
                'endpoint_url': vo_server.service.endpoint_url
            },
            'id': vo_server.id, 'vo_id': vo_id
        }, d=response.data['servers'][0])

        # list server when service admin by query parameter 'user-id' and 'username'
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'user-id': self.user.id, 'username': self.user.username})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # list server when service admin by query parameter 'vo-id' and 'vo-name'
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'vo-id': self.vo_id, 'vo-name': 'dd'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # list server when service admin by query parameter 'vo-id' and 'exclude-vo'
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'vo-id': self.vo_id, 'exclude-vo': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # list server when service admin by query parameter 'vo-name' and 'exclude-vo'
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': '', 'exclude-vo': '', 'vo-name': 'dd'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        # ----- org data center admin -------
        self.service.users.remove(admin_user)
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertIsInstance(response.data['servers'], list)
        self.assertEqual(len(response.data['servers']), 0)

        self.service.org_data_center.add_admin_user(user=admin_user)
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(response.data['count'], 2)
        self.assertIsInstance(response.data['servers'], list)
        self.assertEqual(len(response.data['servers']), 2)
        self.service.org_data_center.remove_admin_user(user=admin_user)

        # -------------list server when federal admin---------------
        admin_user.set_federal_admin()
        url = reverse('servers-api:servers-list')
        query_str = parse.urlencode(query={'as-admin': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['servers']), 3)

        # query "exclude-vo"
        query_str = parse.urlencode(query={'as-admin': '', 'exclude-vo': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # query "username"
        query_str = parse.urlencode(query={'as-admin': '', 'username': self.user.username})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # query "username" and "exclude-vo"
        query_str = parse.urlencode(query={'as-admin': '', 'username': self.user.username, 'exclude-vo': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)

        # query "user-id"
        query_str = parse.urlencode(query={'as-admin': '', 'user-id': self.user.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # query "user-id" and "exclude-vo"
        query_str = parse.urlencode(query={'as-admin': '', 'user-id': self.user.id, 'exclude-vo': ''})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)

        # query "user-id"
        query_str = parse.urlencode(query={'as-admin': '', 'user-id': admin_user.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], admin_server66.id)

        # query "vo-id"
        query_str = parse.urlencode(query={'as-admin': '', 'vo-id': self.vo_id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.vo_server.id)

        # query "vo-id" and "user-id"
        query_str = parse.urlencode(query={'as-admin': '', 'vo-id': self.vo_id, 'user-id': self.user.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.vo_server.id)

        # query "vo-name"
        query_str = parse.urlencode(query={'as-admin': '', 'vo-name': self.vo_server.vo.name})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.vo_server.id)

        # query 'status' invalid
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'ss'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # query "status"
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'expired'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['servers']), 0)
        # self.assertEqual(admin_server66.ipv4, response.data['servers'][0]['ipv4'])

        query_str = parse.urlencode(query={'as-admin': '', 'status': 'prepaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)
        query_str = parse.urlencode(query={'as-admin': '', 'status': 'postpaid'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # query "public"
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'tr'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'true'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], admin_server66.id)
        query_str = parse.urlencode(query={'as-admin': '', 'public': 'false'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        # param "remark
        url = reverse('servers-api:servers-list')
        query = parse.urlencode(query={'as-admin': '', 'remark': 'miss'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['servers'][0]['id'], self.miss_server.id)
        query = parse.urlencode(query={'as-admin': '', 'remark': 'admin'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['servers'][0]['id'], admin_server66.id)
        query = parse.urlencode(query={'as-admin': '', 'remark': 'test'})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)

        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        query_str = parse.urlencode(query={'as-admin': '', 'service_id': self.service.id, 'vo-id': self.vo_id})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)

        query_str = parse.urlencode(query={'as-admin': '', 'ip-contain': '0.0.1'})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['servers']), 2)

        query_str = parse.urlencode(query={'as-admin': '', 'ip-contain': admin_server66.ipv4})
        response = self.client.get(f'{url}?{query_str}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(admin_server66.ipv4, response.data['servers'][0]['ipv4'])

    def test_server_action(self):
        url = reverse('servers-api:servers-server-action', kwargs={'id': 'motfound'})
        response = self.client.post(url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(url, data={'action': 'test'})
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        url = reverse('servers-api:servers-server-action', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # ----------------admin action server test -----------------------
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)
        self.client.logout()
        self.client.force_login(admin_user)

        # test when not admin
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={'action': 'start'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # test when service admin
        self.service.users.add(admin_user)
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # test when org date center admin
        self.service.users.remove(admin_user)
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={'action': 'start'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.miss_server.service.org_data_center.add_admin_user(user=admin_user)
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)
        self.miss_server.service.org_data_center.remove_admin_user(user=admin_user)

        # test when federal admin
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={'action': 'start'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        admin_user.set_federal_admin()
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        response = self.client.post(f'{url}?{query}', data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # ------ 过期停服停机挂起的云主机测试 -----------
        self.client.logout()
        self.client.force_login(user=self.user)
        user_server = create_server_metadata(
            service=self.service, user=self.user,
            default_user=self.default_user, default_password=self.default_password,
            ipv4='127.0.0.1'
        )
        user_server.expiration_time = dj_timezone.now()
        user_server.situation = Server.Situation.EXPIRED.value
        user_server.save(update_fields=['situation', 'expiration_time'])
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.EXPIRED.value)

        url = reverse('servers-api:servers-server-action', kwargs={'id': user_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ExpiredSuspending', response=response)
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.EXPIRED.value)

        # 是否欠费查询时，no pay_app_service_id
        user_server.expiration_time = dj_timezone.now() + timedelta(days=1)
        user_server.save(update_fields=['expiration_time'])
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.NORMAL.value)

        # 未管控，按量计费云主机 欠费也不允许开机
        self.user.userpointaccount.balance = Decimal('-0.01')
        self.user.userpointaccount.save(update_fields=['balance'])
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ArrearageSuspending', response=response)

        # 未管控，预付费云主机 欠费也不允许开机
        user_server.expiration_time = dj_timezone.now() - timedelta(days=1)
        user_server.pay_type = PayType.PREPAID.value
        user_server.save(update_fields=['expiration_time', 'pay_type'])
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ExpiredSuspending', response=response)

        # ------ 欠费停服停机挂起的云主机测试 -----------
        service = self.vo_server.service
        service.pay_app_service_id = 'test'
        service.save(update_fields=['pay_app_service_id'])

        self.vo_server.situation = Server.Situation.ARREARAGE.value
        self.vo_server.save(update_fields=['situation'])
        self.vo_server.refresh_from_db()
        self.assertEqual(self.vo_server.situation, Server.Situation.ARREARAGE.value)

        url = reverse('servers-api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)
        self.vo_server.refresh_from_db()
        self.assertEqual(self.vo_server.situation, Server.Situation.NORMAL.value)

        vopointaccount = self.vo_server.vo.vopointaccount
        vopointaccount.balance = Decimal('-1')
        vopointaccount.save(update_fields=['balance'])
        self.vo_server.situation = Server.Situation.ARREARAGE.value
        self.vo_server.save(update_fields=['situation'])
        self.vo_server.refresh_from_db()
        self.assertEqual(self.vo_server.situation, Server.Situation.ARREARAGE.value)

        url = reverse('servers-api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ArrearageSuspending', response=response)
        self.vo_server.refresh_from_db()
        self.assertEqual(self.vo_server.situation, Server.Situation.ARREARAGE.value)

        # 未管控时，按量计费云主机 欠费 不允许开机
        self.vo_server.situation = Server.Situation.NORMAL.value
        self.vo_server.save(update_fields=['situation'])
        self.vo_server.refresh_from_db()
        self.assertEqual(self.vo_server.situation, Server.Situation.NORMAL.value)
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ArrearageSuspending', response=response)

    def test_vo_server_permission(self):
        member_user = get_or_create_user(username='vo-member')
        self.client.logout()
        self.client.force_login(member_user)

        # -------no permission------
        # vo server remark
        remark = 'test-vo-remarks'
        url = reverse('servers-api:servers-server-remark', kwargs={'id': self.vo_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # list vo servers
        url = reverse('servers-api:servers-list-vo-servers', kwargs={'vo_id': self.vo_id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # action server
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # vo server status
        url = reverse('servers-api:servers-server_status', kwargs={'id': self.vo_server.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # server vo detail
        response = self.server_detail_response(
            client=self.client, server_id=self.vo_server.id)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # server vnc
        url = reverse('servers-api:servers-server-vnc', kwargs={'id': self.vo_server.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # ----- add vo member ------
        self.client.logout()
        self.client.force_login(self.user)
        response = VoTests.add_members_response(client=self.client, vo_id=self.vo_id, usernames=[member_user.username])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['success']), 1)
        self.client.logout()
        self.client.force_login(member_user)

        # -------has permission-----

        # list vo servers
        url = reverse('servers-api:servers-list-vo-servers', kwargs={'vo_id': self.vo_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'next', 'previous', 'servers'], response.data)
        self.assertEqual(len(response.data['servers']), 1)
        self.assertEqual(response.data['count'], 1)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4",
                           "public_ip", "image", "creation_time", "remarks",
                           "service", 'instance_id',
                           "center_quota", "classification", "vo_id", "user",
                           "image_id", "image_desc", "default_user", "default_password",
                           "lock", "pay_type", 'created_user'], response.data['servers'][0])
        vo_server = self.vo_server
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.VO,
            'service': {
                'id': vo_server.service.id, 'name': vo_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': vo_server.service.name_en,
                'endpoint_url': vo_server.service.endpoint_url
            },
            'id': vo_server.id, 'vo_id': self.vo_id
        }, d=response.data['servers'][0])
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['servers'][0]['service'])

        # action server
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # vo server status
        url = reverse('servers-api:servers-server_status', kwargs={'id': self.vo_server.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('status', response.data)
        self.assertEqual(response.data['status']['status_code'], outputs.ServerStatus.MISS)

        # server vo detail
        response = self.server_detail_response(client=self.client, server_id=self.vo_server.id)
        self.assertEqual(response.status_code, 200)

        # server vnc
        url = reverse('servers-api:servers-server-vnc', kwargs={'id': self.vo_server.id})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # delete vo server need vo leader role
        url = reverse('servers-api:servers-detail', kwargs={'id': self.vo_server.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # action server
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'delete'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # vo server remark when not vo member leader
        remark = 'test-vo-remarks'
        url = reverse('servers-api:servers-server-remark', kwargs={'id': self.vo_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # vo server remark when vo member leader
        vo_member = VoMember.objects.filter(vo_id=self.vo_id, user_id=member_user.id).first()
        vo_member.role = VoMember.Role.LEADER
        vo_member.save(update_fields=['role'])

        remark = 'test-vo-remarks'
        url = reverse('servers-api:servers-server-remark', kwargs={'id': self.vo_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.vo_server.refresh_from_db()
        self.assertEqual(remark, self.vo_server.remarks)

    def test_delete_list_archive(self):
        od1_res1 = Resource(
            order=None, resource_type=ResourceType.VM.value,
            instance_id=Resource().generate_id(), instance_remark='remark', desc=''
        )
        od1_res1.save(force_insert=True)
        od1_res2 = Resource(
            order=None, resource_type=ResourceType.VM.value,
            instance_id=self.miss_server.id, instance_remark='remark', desc=''
        )
        od1_res2.save(force_insert=True)
        od1_res3 = Resource(
            order=None, resource_type=ResourceType.DISK.value,
            instance_id=self.miss_server.id, instance_remark='remark', desc=''
        )
        od1_res3.save(force_insert=True)

        od1_res4 = Resource(
            order=None, resource_type=ResourceType.VM.value,
            instance_id=self.miss_server.id, instance_remark='remark', desc=''
        )
        od1_res4.save(force_insert=True)

        self.client.logout()
        self.client.force_login(self.user)
        url = reverse('servers-api:servers-detail', kwargs={'id': 'motfound'})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        self.assertIsNone(od1_res1.instance_delete_time)
        self.assertIsNone(od1_res2.instance_delete_time)
        self.assertIsNone(od1_res3.instance_delete_time)
        self.assertIsNone(od1_res4.instance_delete_time)

        log_count = ResourceActionLog.objects.count()
        self.assertEqual(log_count, 0)
        url = reverse('servers-api:servers-detail', kwargs={'id': self.miss_server.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        log_count = ResourceActionLog.objects.count()
        self.assertEqual(log_count, 1)
        log: ResourceActionLog = ResourceActionLog.objects.order_by('-action_time').first()
        self.assertEqual(log.action_flag, ResourceActionLog.ActionFlag.DELETION.value)
        self.assertEqual(log.resource_id, self.miss_server.id)
        self.assertEqual(log.resource_type, ResourceActionLog.ResourceType.SERVER.value)
        self.assertEqual(log.owner_type, OwnerType.USER.value)

        od1_res1.refresh_from_db()
        od1_res2.refresh_from_db()
        od1_res3.refresh_from_db()
        od1_res4.refresh_from_db()
        self.assertIsNone(od1_res1.instance_delete_time)
        self.assertIsInstance(od1_res2.instance_delete_time, datetime)
        self.assertIsNone(od1_res3.instance_delete_time)
        self.assertIsInstance(od1_res4.instance_delete_time, datetime)

        url = reverse('servers-api:servers-detail', kwargs={'id': self.vo_server.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        log_count = ResourceActionLog.objects.count()
        self.assertEqual(log_count, 2)
        log: ResourceActionLog = ResourceActionLog.objects.order_by('-action_time').first()
        self.assertEqual(log.action_flag, ResourceActionLog.ActionFlag.DELETION.value)
        self.assertEqual(log.resource_id, self.vo_server.id)
        self.assertEqual(log.resource_type, ResourceActionLog.ResourceType.SERVER.value)
        self.assertEqual(log.owner_type, OwnerType.VO.value)

        # list user server archives
        url = reverse('servers-api:server-archive-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        obj = response.data['results'][0]
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4", "ram_gib",
                           "public_ip", "image", "creation_time",
                           "remarks", "service", 'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
                           "center_quota", "deleted_time", "classification", "vo_id", 'instance_id',
                           "pay_type", "server_id", 'created_user'], obj)
        self.assertEqual(obj['ram_gib'], 1)
        self.assertEqual(obj['ram'], 1)
        self.assertKeysIn(["id", "name", "name_en", "service_type"], obj['service'])
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.PERSONAL,
            'service': {
                'id': self.miss_server.service.id, 'name': self.miss_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': self.miss_server.service.name_en
            },
            'vo_id': None
        }, d=obj)

        self.assertEqual(datetime.strptime(obj['creation_time'], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp(),
                         self.miss_server.creation_time.timestamp())

        # list vo server archives
        url = reverse('servers-api:server-archive-list-vo-archives', kwargs={'vo_id': self.vo_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["count", "next", "previous", "results"], response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertKeysIn(["id", "name", "vcpus", "ram", "ipv4", "ram_gib",
                           "public_ip", "image", "creation_time",
                           "remarks", "service", 'img_sys_type', 'img_sys_arch', 'img_release', 'img_release_version',
                           "center_quota", "deleted_time", "classification", "vo_id",
                           "pay_type", "server_id"], response.data["results"][0])
        self.assertEqual(response.data['results'][0]['ram_gib'], 2)
        self.assertEqual(response.data['results'][0]['ram'], 2)
        self.assert_is_subdict_of(sub={
            'classification': Server.Classification.VO,
            'service': {
                'id': self.vo_server.service.id, 'name': self.vo_server.service.name,
                "service_type": ServiceConfig.ServiceType.EVCLOUD, 'name_en': self.vo_server.service.name_en
            },
            'vo_id': self.vo_id
        }, d=response.data['results'][0])

        # ----------------admin delete server test -----------------------
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)

        delete_server = create_server_metadata(
            service=self.service, user=self.user,
            default_user=self.default_user, default_password=self.default_password)

        self.client.logout()
        self.client.force_login(admin_user)

        # test when not admin
        base_url = reverse('servers-api:servers-detail', kwargs={'id': delete_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        delete_url = f'{base_url}?{query}'
        response = self.client.delete(delete_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # test when service admin
        self.service.users.add(admin_user)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 204)

        # test when org data center admin
        self.service.users.remove(admin_user)
        delete_server = create_server_metadata(
            service=self.service, user=self.user,
            default_user=self.default_user, default_password=self.default_password)

        base_url = reverse('servers-api:servers-detail', kwargs={'id': delete_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        delete_url = f'{base_url}?{query}'
        response = self.client.delete(delete_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.service.org_data_center.add_admin_user(user=admin_user)
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 204)

        # test when federal admin
        self.service.org_data_center.remove_admin_user(user=admin_user)
        delete_server = create_server_metadata(
            service=self.service, user=self.user,
            default_user=self.default_user, default_password=self.default_password)

        base_url = reverse('servers-api:servers-detail', kwargs={'id': delete_server.id})
        query = parse.urlencode(query={'as-admin': ''})
        delete_url = f'{base_url}?{query}'
        response = self.client.delete(delete_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        admin_user.set_federal_admin()
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, 204)

    def test_server_lock(self):
        # server remark
        remark = 'test-remarks'
        url = reverse('servers-api:servers-server-remark', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.miss_server.refresh_from_db()
        self.assertEqual(remark, self.miss_server.remarks)

        # server action
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        # ---- lock server delete ------
        url = reverse('servers-api:servers-server-lock', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.DELETE})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.DELETE)

        # server remark
        remark = 'test-remarks'
        url = reverse('servers-api:servers-server-remark', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.miss_server.refresh_from_db()
        self.assertEqual(remark, self.miss_server.remarks)

        # server action
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)

        url = reverse('servers-api:servers-detail', kwargs={'id': self.miss_server.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # ---- lock server all operation ------
        url = reverse('servers-api:servers-server-lock', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.OPERATION})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.OPERATION)

        # server remark
        remark = 'test-remarks'
        url = reverse('servers-api:servers-server-remark', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'remark': remark})
        response = self.client.patch(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # server action
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'action': 'start'})
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # server delete
        url = reverse('servers-api:servers-detail', kwargs={'id': self.miss_server.id})
        response = self.client.delete(url)
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # server action delete
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'action': 'delete'})
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # server rebuild
        url = reverse('servers-api:servers-rebuild', kwargs={'id': self.miss_server.id})
        response = self.client.post(url, data={'image_id': 'aaa'})
        self.assertErrorResponse(status_code=409, code='ResourceLocked', response=response)

        # ---- lock server free ------
        url = reverse('servers-api:servers-server-lock', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.FREE})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.FREE)

        # ----as admin------
        admin_username = 'admin-user'
        admin_password = 'admin-password'
        admin_user = get_or_create_user(username=admin_username, password=admin_password)

        self.client.logout()
        self.client.force_login(admin_user)

        url = reverse('servers-api:servers-server-lock', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.OPERATION.value, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # service admin
        self.service.users.add(admin_user)
        query = parse.urlencode(query={'lock': Server.Lock.OPERATION.value, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.OPERATION.value)

        url = reverse('servers-api:servers-server-lock', kwargs={'id': self.vo_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.FREE.value, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.FREE.value)

        # federal admin
        self.service.users.remove(admin_user)
        url = reverse('servers-api:servers-server-lock', kwargs={'id': self.miss_server.id})
        query = parse.urlencode(query={'lock': Server.Lock.FREE.value, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        admin_user.set_federal_admin()
        query = parse.urlencode(query={'lock': Server.Lock.FREE.value, 'as-admin': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['lock'], Server.Lock.FREE.value)

        # server delete
        self.client.logout()
        self.client.force_login(self.user)
        url = reverse('servers-api:servers-detail', kwargs={'id': self.miss_server.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

        # server action delete
        url = reverse('servers-api:servers-server-action', kwargs={'id': self.vo_server.id})
        response = self.client.post(url, data={'action': 'delete'})
        self.assertEqual(response.status_code, 200)

    def test_server_rebuild(self):
        from apps.servers.tests.test_disk import create_disk_metadata

        miss_server = self.miss_server
        url = reverse('servers-api:servers-rebuild', kwargs={'id': miss_server.id})

        # no body
        response = self.client.post(url, data={})
        self.assertErrorResponse(status_code=400, code='BadRequest', response=response)

        miss_server.task_status = miss_server.TASK_IN_CREATING
        miss_server.save(update_fields=['task_status'])
        response = self.client.post(url, data={'image_id': 'aaa'})
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        miss_server.task_status = miss_server.TASK_CREATED_OK
        miss_server.save(update_fields=['task_status'])
        response = self.client.post(url, data={'image_id': 'test'})
        self.assertEqual(response.status_code, 500)

        # ------ 过期停服停机挂起的云主机测试 -----------
        self.client.logout()
        self.client.force_login(user=self.user)
        user_server = create_server_metadata(
            service=self.service, user=self.user,
            default_user=self.default_user, default_password=self.default_password,
            ipv4='127.0.0.1'
        )
        user_server.expiration_time = dj_timezone.now()
        user_server.situation = Server.Situation.EXPIRED.value
        user_server.save(update_fields=['situation', 'expiration_time'])
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.EXPIRED.value)

        url = reverse('servers-api:servers-rebuild', kwargs={'id': user_server.id})
        response = self.client.post(url, data={'image_id': 'test'})
        self.assertErrorResponse(status_code=409, code='ExpiredSuspending', response=response)
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.EXPIRED.value)

        user_server.expiration_time = dj_timezone.now() + timedelta(days=1)
        user_server.save(update_fields=['expiration_time'])

        # 硬盘
        disk1 = create_disk_metadata(
            service_id=self.service.id, azone_id='1', disk_size=6, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=dj_timezone.now(), server_id=user_server.id
        )
        url = reverse('servers-api:servers-rebuild', kwargs={'id': user_server.id})
        response = self.client.post(url, data={'image_id': 'test'})
        self.assertErrorResponse(status_code=409, code='DiskAttached', response=response)
        disk1.set_detach()

        # 快照
        snapshot1 = ServerSnapshotManager.create_snapshot_metadata(
            name='name1', size_dib=66, remarks='snapshot1 test', instance_id='11',
            creation_time=dj_timezone.now(), expiration_time=dj_timezone.now() - timedelta(days=1),
            start_time=None, pay_type=PayType.PREPAID.value,
            classification=ServerSnapshot.Classification.PERSONAL.value, user=self.user, vo=None,
            server=user_server, service=user_server.service
        )
        url = reverse('servers-api:servers-rebuild', kwargs={'id': user_server.id})
        response = self.client.post(url, data={'image_id': 'test'})
        self.assertErrorResponse(status_code=409, code='SnapshotExists', response=response)
        snapshot1.do_soft_delete(deleted_user='')

        response = self.client.post(url, data={'image_id': 'test'})
        self.assertErrorResponse(status_code=500, code='InternalError', response=response)
        user_server.refresh_from_db()
        self.assertEqual(user_server.situation, Server.Situation.NORMAL.value)

    def test_server_handover_owner(self):
        user2 = get_or_create_user(username='zhangsan@cnic.cn')
        vo2 = VirtualOrganization(name='test vo2', company='网络中心', description='unittest', owner=user2)
        vo2.save(force_insert=True)

        server2 = create_server_metadata(
            service=self.service, user=user2, vo_id=vo2.id, ram=2,
            classification=Server.Classification.VO.value, default_user='', default_password='',
            ipv4='159.0.0.12', remarks='test'
        )

        self.client.logout()
        self.client.force_login(self.user)

        url = reverse('servers-api:servers-server-handover-owner', kwargs={'id': 'notfount'})
        # InvalidArgument
        response = self.client.post(url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'username': user2.username, 'vo_id': vo2.id})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'username': '', 'vo_id': ''})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # NotFound
        query = parse.urlencode(query={'username': user2.username})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        query = parse.urlencode(query={'vo_id': vo2.id})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)

        # --- server from vo handover to user ---
        # server2 of vo2，user no permission of vo2
        url = reverse('servers-api:servers-server-handover-owner', kwargs={'id': server2.id})
        query = parse.urlencode(query={'username': self.user.username})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        # 组员没有权限
        vo2_member_user = VoMember(user=self.user, vo=vo2, role=VoMember.Role.MEMBER.value, inviter='', inviter_id='')
        vo2_member_user.save(force_insert=True)
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.assertEqual(EVCloudPermsLog.objects.count(), 0)
        # 组admin有权限
        vo2_member_user.role = VoMember.Role.LEADER.value
        vo2_member_user.save(update_fields=['role'])
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        server2.refresh_from_db()
        self.assertEqual(server2.classification, Server.Classification.PERSONAL.value)
        self.assertEqual(server2.user_id, self.user.id)
        self.assertIsNone(server2.vo_id)
        time_sleep(1)
        self.assertEqual(EVCloudPermsLog.objects.count(), 1)

        # ---- server from user handover to user ----
        # user1's server2, to user2
        url = reverse('servers-api:servers-server-handover-owner', kwargs={'id': server2.id})
        query = parse.urlencode(query={'username': user2.username})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        server2.refresh_from_db()
        self.assertEqual(server2.classification, Server.Classification.PERSONAL.value)
        self.assertEqual(server2.user_id, user2.id)
        self.assertIsNone(server2.vo_id)
        time_sleep(1)
        self.assertEqual(EVCloudPermsLog.objects.count(), 2)

        # ---- server from user handover to vo ----
        # user2's server2, to vo1
        url = reverse('servers-api:servers-server-handover-owner', kwargs={'id': server2.id})
        query = parse.urlencode(query={'vo_id': self.vo1.id})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.client.logout()
        self.client.force_login(user2)

        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        server2.refresh_from_db()
        self.assertEqual(server2.classification, Server.Classification.VO.value)
        self.assertEqual(server2.user_id, self.vo1.owner.id)
        self.assertEqual(server2.vo_id, self.vo1.id)

        # ---- server from vo handover to vo ----
        # vo1's server2, to vo12
        url = reverse('servers-api:servers-server-handover-owner', kwargs={'id': server2.id})
        query = parse.urlencode(query={'vo_id': vo2.id})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.client.logout()
        self.client.force_login(self.user)

        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        server2.refresh_from_db()
        self.assertEqual(server2.classification, Server.Classification.VO.value)
        self.assertEqual(server2.user_id, vo2.owner.id)
        self.assertEqual(server2.vo_id, vo2.id)
        time_sleep(1)
        self.assertEqual(EVCloudPermsLog.objects.count(), 4)

    def test_server_handover_inside_vo(self):
        user2 = get_or_create_user(username='zhangsan@cnic.cn')
        user3 = get_or_create_user(username='lisi@cnic.cn')
        vo2 = VirtualOrganization(name='test vo2', company='网络中心', description='unittest', owner=user2)
        vo2.save(force_insert=True)
        vo2_member_user = VoMember(user=self.user, vo=vo2, role=VoMember.Role.MEMBER.value, inviter='', inviter_id='')
        vo2_member_user.save(force_insert=True)
        vo2_member_user3 = VoMember(user=user3, vo=vo2, role=VoMember.Role.MEMBER.value, inviter='', inviter_id='')
        vo2_member_user3.save(force_insert=True)

        server2 = create_server_metadata(
            service=self.service, user=user2, vo_id=vo2.id, ram=2,
            classification=Server.Classification.PERSONAL.value, default_user='', default_password='',
            ipv4='159.0.0.12', remarks='test'
        )

        self.client.logout()
        self.client.force_login(self.user)

        url = reverse('servers-api:servers-server-handover-inside-vo', kwargs={'id': 'notfount'})
        # InvalidArgument
        response = self.client.post(url)
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        # server NotFound
        query = parse.urlencode(query={'username': user2.username})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='NotFound', response=response)
        # not vo server
        url = reverse('servers-api:servers-server-handover-inside-vo', kwargs={'id': server2.id})
        query = parse.urlencode(query={'username': 'notexists'})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='Conflict', response=response)

        server2.classification = Server.Classification.VO.value
        server2.save(update_fields=['classification'])

        # user not found
        query = parse.urlencode(query={'username': 'notexists'})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # user1 no permission handover
        url = reverse('servers-api:servers-server-handover-inside-vo', kwargs={'id': server2.id})
        query = parse.urlencode(query={'username': user3.username})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # --- server from user2 to user3 ---
        # user2 no permission of (vo2 and server2)
        self.client.logout()
        self.client.force_login(user2)

        self.assertEqual(EVCloudPermsLog.objects.count(), 0)
        url = reverse('servers-api:servers-server-handover-inside-vo', kwargs={'id': server2.id})
        query = parse.urlencode(query={'username': user3.username})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        server2.refresh_from_db()
        self.assertEqual(server2.classification, Server.Classification.VO.value)
        self.assertEqual(server2.vo_id, vo2.id)
        self.assertEqual(server2.user_id, user3.id)
        time_sleep(1)
        self.assertEqual(EVCloudPermsLog.objects.count(), 1)

        # --- server from user3 to user1 --- vo admin handover
        # user2 is owner of vo2
        url = reverse('servers-api:servers-server-handover-inside-vo', kwargs={'id': server2.id})
        query = parse.urlencode(query={'username': self.user.username})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        server2.refresh_from_db()
        self.assertEqual(server2.classification, Server.Classification.VO.value)
        self.assertEqual(server2.vo_id, vo2.id)
        self.assertEqual(server2.user_id, self.user.id)

        # --- server from user1 to user3 --- member to member
        # user1 no permission of server2
        self.client.logout()
        self.client.force_login(self.user)
        url = reverse('servers-api:servers-server-handover-inside-vo', kwargs={'id': server2.id})
        query = parse.urlencode(query={'username': user3.username})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        server2.refresh_from_db()
        self.assertEqual(server2.classification, Server.Classification.VO.value)
        self.assertEqual(server2.vo_id, vo2.id)
        self.assertEqual(server2.user_id, user3.id)
        time_sleep(1)
        self.assertEqual(EVCloudPermsLog.objects.count(), 3)

        # --- server from user3 to user2 --- member to vo2 owner
        # user1 no permission of server2 now
        url = reverse('servers-api:servers-server-handover-inside-vo', kwargs={'id': server2.id})
        query = parse.urlencode(query={'username': user2.username})
        response = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        # vo admin
        vo2_member_user.role = VoMember.Role.LEADER.value
        vo2_member_user.save(update_fields=['role'])

        query = parse.urlencode(query={'username': user2.username})
        response = self.client.post(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        server2.refresh_from_db()
        self.assertEqual(server2.classification, Server.Classification.VO.value)
        self.assertEqual(server2.vo_id, vo2.id)
        self.assertEqual(server2.user_id, user2.id)
        time_sleep(1)
        self.assertEqual(EVCloudPermsLog.objects.count(), 4)
