from time import sleep as time_sleep
from urllib import parse
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone as dj_timezone
from django.conf import settings

from apps.servers.managers import ServicePrivateQuotaManager
from apps.servers.models import ServiceConfig
from apps.servers.models import Flavor, Server
from utils.test import (
    get_or_create_user, get_or_create_service, get_or_create_organization,
    MyAPITransactionTestCase
)
from utils.model import PayType, OwnerType, ResourceType
from apps.vo.models import VirtualOrganization
from apps.order.managers import OrderManager
from apps.order.models import Order
from apps.order.managers import ServerConfig
from apps.order.tests import create_price
from apps.app_wallet.models import PayApp, PayAppService, CashCoupon, PaymentHistory
from core import site_configs_manager
from apps.servers.apiviews.res_order_deliver_task_views import ResTaskManager
from apps.servers.models import ResourceOrderDeliverTask


PAY_APP_ID = site_configs_manager.get_pay_app_id(settings)


# 替换任务订单资源交付处理方法，防止测试用例真实去创建资源
def new_deliver_task_order(*args, **kwargs):
    print('模拟的资源交付')
    pass


class ResOrderTaskTests(MyAPITransactionTestCase):
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

        # 余额支付有关配置
        self.app = PayApp(name='app', id=PAY_APP_ID)
        self.app.save(force_insert=True)
        self.po = get_or_create_organization(name='机构')
        self.po.save()
        app_service1 = PayAppService(
            id='123', name='service1', app=self.app, orgnazition=self.po,
            category=PayAppService.Category.VMS_SERVER.value
        )
        app_service1.save()
        self.app_service1 = app_service1

    def test_task_create_bad_request(self):
        url = reverse('servers-api:res-order-deliver-task-server-create')
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
            'image_id': 'ss', 'period': 12, 'flavor_id': '1', 'username': self.user2.username})
        self.assertErrorResponse(status_code=400, code='InvalidFlavorId', response=response)

        # param "service_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': 'test', 'network_id': 'test',
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'username': self.user2.username})
        self.assertErrorResponse(status_code=400, code='InvalidServiceId', response=response)

        # param "vo_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'vo_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidVoId', response=response)

        # param "username"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'username': 'notfound'
        })
        self.assertErrorResponse(status_code=400, code='InvalidUsername', response=response)

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

        # admin permission test
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.user.set_fed_admin(is_fed=True)
        # param "network_id"
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id,
            'vo_id': self.vo.id, 'network_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidNetworkId', response=response)

        self.user.set_fed_admin(is_fed=False)
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'network_id': 'test',
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'vo_id': self.vo.id
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        self.service.org_data_center.add_admin_user(user=self.user, is_ops_user=False)
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
        url = reverse('servers-api:res-order-deliver-task-server-create')
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'vo_id': self.vo.id, 'network_id': network_id, 'azone_id': 'test'
        })
        self.assertErrorResponse(status_code=400, code='InvalidAzoneId', response=response)

        # username and vo_id
        response = self.client.post(url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id,
            'vo_id': self.vo.id, 'network_id': network_id, 'azone_id': 'test',
            'username': self.user2.username
        })
        self.assertErrorResponse(status_code=400, code='ArgumentConflict', response=response)

    def test_task_create(self):
        # 替换资源交付方法，模拟资源交付，避免真实去交付资源
        ResTaskManager.deliver_task_order = new_deliver_task_order

        self.client.force_login(self.user)
        # get network id
        base_url = reverse('servers-api:networks-list')
        response = self.client.get(f'{base_url}?service_id={self.service.id}')
        self.assertEqual(response.status_code, 200)
        network_id = response.data[0]['id']
        is_public_network = response.data[0]['public']

        # service not set pay_app_service_id
        task_base_url = reverse('servers-api:res-order-deliver-task-server-create')
        response = self.client.post(task_base_url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': 'ss', 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'username': self.user2.username
        })
        self.assertErrorResponse(status_code=409, code='ServiceNoPayAppServiceId', response=response)

        self.service.pay_app_service_id = 'app_service_id'  # 无效的结算单元id
        self.service.save(update_fields=['pay_app_service_id'])

        # get image_id
        url = reverse('servers-api:images-paginate-list')
        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{url}?{query}')
        self.assertEqual(response.status_code, 200)
        image_id = response.data['results'][0]['id']
        min_sys_disk_gb = response.data['results'][0]['min_sys_disk_gb']

        # service admin
        response = self.client.post(task_base_url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'period_unit': Order.PeriodUnit.MONTH.value,
            'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'number': 2, 'username': self.user2.username
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)
        self.service.org_data_center.add_admin_user(user=self.user, is_ops_user=False)

        # service quota set
        ServicePrivateQuotaManager().update(
            service=self.service, vcpus=2, ram_gib=3, public_ip=2, private_ip=2
        )

        # service privete quota not enough
        response = self.client.post(task_base_url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'period_unit': Order.PeriodUnit.MONTH.value,
            'flavor_id': self.flavor.id, 'network_id': network_id, 'task_desc': 'test task desc',
            'remarks': 'testcase创建，可删除', 'number': 2, 'username': self.user2.username
        })
        self.assertErrorResponse(status_code=409, code='QuotaShortage', response=response)

        # service quota set
        ServicePrivateQuotaManager().update(
            service=self.service, vcpus=6, ram_gib=6, public_ip=2, private_ip=2
        )

        self.assertEqual(ResourceOrderDeliverTask.objects.count(), 0)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(CashCoupon.objects.count(), 0)
        self.assertEqual(PaymentHistory.objects.count(), 0)
        self.assertEqual(Server.objects.count(), 0)

        # create user2 server prepaid mode
        response = self.client.post(task_base_url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id, 'task_desc': 'test task desc',
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'number': 2, 'username': self.user2.username
        })
        self.assertEqual(response.status_code, 202)
        self.assertKeysIn(['task_id'], response.data)

        # 等待异步任务处理完
        time_sleep(2)
        # 无效的结算单元id，发券失败
        self.assertEqual(ResourceOrderDeliverTask.objects.count(), 1)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(CashCoupon.objects.count(), 0)
        self.assertEqual(PaymentHistory.objects.count(), 0)
        self.assertEqual(Server.objects.count(), 0)

        order1 = Order.objects.first()
        self.assertEqual(order1.status, Order.Status.UNPAID.value)
        self.assertEqual(order1.order_type, Order.OrderType.NEW.value)
        self.assertEqual(order1.resource_type, ResourceType.VM.value)
        self.assertEqual(order1.pay_type, PayType.PREPAID.value)
        self.assertEqual(order1.owner_type, OwnerType.USER.value)
        self.assertEqual(order1.user_id, self.user2.id)
        self.assertEqual(order1.number, 2)
        self.assertEqual(order1.service_id, self.service.id)

        task1 = ResourceOrderDeliverTask.objects.first()
        self.assertEqual(task1.service_id, self.service.id)
        self.assertEqual(task1.order_id, order1.id)
        self.assertEqual(task1.status, ResourceOrderDeliverTask.Status.FAILED.value)
        self.assertEqual(task1.progress, ResourceOrderDeliverTask.Progress.ORDERAED.value)
        self.assertEqual(task1.submitter_id, self.user.id)
        self.assertEqual(task1.submitter, self.user.username)
        self.assertEqual(task1.task_desc, 'test task desc')

        # 修改订单的结算单元id
        order1.app_service_id = self.app_service1.id
        order1.save(update_fields=['app_service_id'])

        # 尝试处理任务
        # 替换资源交付方法，模拟资源交付失败，避免真实去交付资源
        ResTaskManager.deliver_task_order = print
        with self.assertRaises(Exception):
            ResTaskManager().res_task_handler(task=task1, auth_user=self.user)

        # 发券和订单支付成功
        self.assertEqual(ResourceOrderDeliverTask.objects.count(), 1)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(CashCoupon.objects.count(), 1)
        self.assertEqual(PaymentHistory.objects.count(), 1)
        self.assertEqual(Server.objects.count(), 0)

        order1.refresh_from_db()
        self.assertEqual(order1.status, Order.Status.PAID.value)
        self.assertEqual(order1.trading_status, Order.TradingStatus.OPENING.value)  # 未执行交付资源业务

        task1.refresh_from_db()
        self.assertEqual(task1.service_id, self.service.id)
        self.assertEqual(task1.order_id, order1.id)
        self.assertEqual(task1.status, ResourceOrderDeliverTask.Status.FAILED.value)
        self.assertEqual(task1.progress, ResourceOrderDeliverTask.Progress.PAID.value)

        # --- 测试vo, 一次成功 ---
        # 替换资源交付方法，模拟资源交付，避免真实去交付资源
        ResTaskManager.deliver_task_order = new_deliver_task_order
        # 修改服务单元的结算单元id
        self.service.pay_app_service_id = self.app_service1.id
        self.service.save(update_fields=['pay_app_service_id'])

        # create user2 server prepaid mode
        response = self.client.post(task_base_url, data={
            'pay_type': PayType.PREPAID.value, 'service_id': self.service.id,
            'image_id': image_id, 'period': 12, 'flavor_id': self.flavor.id, 'network_id': network_id,
            'remarks': 'testcase创建，可删除', 'number': 1, 'vo_id': self.vo.id
        })
        self.assertEqual(response.status_code, 202)
        self.assertKeysIn(['task_id'], response.data)

        # 等待异步任务处理完
        time_sleep(2)

        # 无效的结算单元id，发券失败
        self.assertEqual(ResourceOrderDeliverTask.objects.count(), 2)
        self.assertEqual(Order.objects.count(), 2)
        self.assertEqual(CashCoupon.objects.count(), 2)
        self.assertEqual(PaymentHistory.objects.count(), 2)
        self.assertEqual(Server.objects.count(), 0)

        order2 = Order.objects.order_by('-creation_time').first()
        self.assertEqual(order2.status, Order.Status.PAID.value)
        self.assertEqual(order2.order_type, Order.OrderType.NEW.value)
        self.assertEqual(order2.resource_type, ResourceType.VM.value)
        self.assertEqual(order2.pay_type, PayType.PREPAID.value)
        self.assertEqual(order2.owner_type, OwnerType.VO.value)
        self.assertEqual(order2.user_id, self.user.id) # 提交订单的用户
        self.assertEqual(order2.vo_id, self.vo.id)
        self.assertEqual(order2.number, 1)
        self.assertEqual(order2.service_id, self.service.id)
        self.assertEqual(order2.payment_method, Order.PaymentMethod.CASH_COUPON.value)
        self.assertEqual(order2.trading_status, Order.TradingStatus.OPENING.value)  # 模拟交付，未真实去交付

        task2 = ResourceOrderDeliverTask.objects.order_by('-creation_time').first()
        self.assertEqual(task2.service_id, self.service.id)
        self.assertEqual(task2.order_id, order2.id)
        self.assertEqual(task2.status, ResourceOrderDeliverTask.Status.COMPLETED.value)
        self.assertEqual(task2.progress, ResourceOrderDeliverTask.Progress.DELIVERED.value)
        self.assertEqual(task2.submitter_id, self.user.id)
        self.assertEqual(task2.submitter, self.user.username)
        self.assertEqual(task2.task_desc, '')

    def test_list(self):
        service2 = ServiceConfig(
            name='test2', name_en='test2_en', org_data_center=None,
        )
        service2.save(force_insert=True)

        coupon1 = CashCoupon(
            face_value=Decimal('66.6'),
            balance=Decimal('66.6'),
            effective_time=dj_timezone.now(),
            expiration_time=dj_timezone.now(),
            status=CashCoupon.Status.WAIT.value
        )
        coupon1.save(force_insert=True)

        order_instance_config = ServerConfig(
            vm_cpu=2, vm_ram=2, systemdisk_size=100, public_ip=True,
            image_id='image_id', image_name='', network_id='network_id', network_name='',
            azone_id='azone_id', azone_name='azone_name', flavor_id=''
        )
        order1, resource_list = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id='test',
            service_id='test',
            service_name='test',
            resource_type=ResourceType.VM.value,
            instance_config=order_instance_config,
            period=2,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.PREPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='', vo_name='',
            owner_type=OwnerType.USER.value
        )

        task1 = ResTaskManager.create_task(
            status=ResourceOrderDeliverTask.Status.WAIT.value,
            status_desc='', progress=ResourceOrderDeliverTask.Progress.ORDERAED.value,
            order=order1, submitter_id=self.user.id, submitter=self.user.username,
            service=self.service, task_desc='test task1 desc'
        )
        task2 = ResTaskManager.create_task(
            status=ResourceOrderDeliverTask.Status.FAILED.value,
            status_desc='', progress=ResourceOrderDeliverTask.Progress.COUPON.value,
            order=order1, submitter_id=self.user.id, submitter=self.user.username,
            service=self.service, task_desc='test task2 desc', coupon=coupon1
        )
        task3 = ResTaskManager.create_task(
            status=ResourceOrderDeliverTask.Status.COMPLETED.value,
            status_desc='', progress=ResourceOrderDeliverTask.Progress.DELIVERED.value,
            order=order1, submitter_id=self.user2.id, submitter=self.user2.username,
            service=service2, task_desc='test task3 desc', coupon=coupon1
        )

        base_url = reverse('servers-api:res-order-deliver-task-list')
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'results'], response.data)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 0)

        # -- test fed admin --
        self.user.set_fed_admin(is_fed=True)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 3)
        self.assertEqual(response.data['results'][0]['id'], task3.id)
        self.assertEqual(response.data['results'][1]['id'], task2.id)
        self.assertEqual(response.data['results'][2]['id'], task1.id)

        # page，page_size
        query = parse.urlencode(query={'page': 2, 'page_size': 1})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page_num'], 2)
        self.assertEqual(response.data['page_size'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], task2.id)

        # query "status"
        query = parse.urlencode(query={'status': 'test'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidArgument', response=response)

        query = parse.urlencode(query={'status': ResourceOrderDeliverTask.Status.FAILED.value})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], task2.id)

        # query "search"
        query = parse.urlencode(query={'search': 'task'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)

        query = parse.urlencode(query={'search': 'task3'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], task3.id)

        # service_id
        query = parse.urlencode(query={'service_id': 'task'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['results']), 0)

        query = parse.urlencode(query={'service_id': service2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], task3.id)

        # -- test service admin ---
        self.user.set_fed_admin(is_fed=False)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(response.data['page_num'], 1)
        self.assertEqual(response.data['page_size'], 100)
        self.assertEqual(len(response.data['results']), 0)

        # 运维管理员
        self.service.org_data_center.add_admin_user(self.user, is_ops_user=True)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['id'], task2.id)
        self.assertEqual(response.data['results'][1]['id'], task1.id)

        # service_id
        query = parse.urlencode(query={'service_id': 'task'})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        query = parse.urlencode(query={'service_id': service2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=response)

        query = parse.urlencode(query={'service_id': self.service.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

        service2.users.add(self.user)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['results']), 3)

        query = parse.urlencode(query={'service_id': service2.id})
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], task3.id)

        self.assertKeysIn([
            'id', 'status', 'status_desc', 'progress', 'submitter_id', 'submitter', 'creation_time',
            'update_time', 'task_desc', 'service', 'order', 'coupon_id'
        ], response.data['results'][0])
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['results'][0]['service'])
        self.assertKeysIn([
            'id', 'resource_type', 'number', 'order_type', 'total_amount'
        ], response.data['results'][0]['order'])

    def test_detail(self):
        order_instance_config = ServerConfig(
            vm_cpu=2, vm_ram=2, systemdisk_size=100, public_ip=True,
            image_id='image_id', image_name='', network_id='network_id', network_name='',
            azone_id='azone_id', azone_name='azone_name', flavor_id=''
        )
        order1, resource_list = OrderManager().create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=self.app_service1.id,
            service_id=self.service.id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config=order_instance_config,
            period=2,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.PREPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id=self.vo.id, vo_name=self.vo.name,
            owner_type=OwnerType.VO.value
        )

        task1 = ResTaskManager.create_task(
            status=ResourceOrderDeliverTask.Status.COMPLETED.value,
            status_desc='', progress=ResourceOrderDeliverTask.Progress.DELIVERED.value,
            order=order1, submitter_id=self.user2.id, submitter=self.user2.username,
            service=self.service, task_desc='test task3 desc', coupon=None
        )

        task_url = reverse('servers-api:res-order-deliver-task-detail', kwargs={'id': task1.id})
        response = self.client.get(task_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

        task_url = reverse('servers-api:res-order-deliver-task-detail', kwargs={'id': 'test'})
        response = self.client.get(task_url)
        self.assertEqual(response.status_code, 404)

        task_url = reverse('servers-api:res-order-deliver-task-detail', kwargs={'id': task1.id})
        response = self.client.get(task_url)
        self.assertEqual(response.status_code, 403)

        # -- test fed admin --
        self.user.set_fed_admin(is_fed=True)
        response = self.client.get(task_url)
        self.assertEqual(response.status_code, 200)

        self.user.set_fed_admin(is_fed=False)
        response = self.client.get(task_url)
        self.assertEqual(response.status_code, 403)

        # --- admin ---
        coupon1 = ResTaskManager.create_coupon_for_order(order=order1, issuer=self.user.username)
        task1.coupon = coupon1
        task1.save(update_fields=['coupon'])

        self.service.org_data_center.add_admin_user(self.user, is_ops_user=True)
        response = self.client.get(task_url)
        self.assertEqual(response.status_code, 200)

        self.assertKeysIn(['id'], response.data)
        self.assertKeysIn([
            'id', 'status', 'status_desc', 'progress', 'submitter_id', 'submitter', 'creation_time',
            'update_time', 'task_desc', 'service', 'order', 'coupon_id', 'coupon'
        ], response.data)
        self.assertKeysIn(['id', 'name', 'name_en'], response.data['service'])
        self.assertKeysIn([
            "id", "order_type", "status", "total_amount", "pay_amount",
            "service_id", "service_name", "resource_type", "instance_config",
            "period", "period_unit", "start_time", "end_time",
            "payment_time", "pay_type", "creation_time", "user_id", "username", 'number',
            "vo_id", "vo_name", "owner_type", "cancelled_time", "app_service_id", 'trading_status'
        ], response.data['order'])
        self.assertKeysIn([
            "id", "face_value", "creation_time", "effective_time", "expiration_time",
            "balance", "status", "granted_time", "issuer", 'use_scope', 'order_id',
            "owner_type", "app_service", "user", "vo", "activity", 'remark'], response.data['coupon']
        )
        self.assertKeysIn([
            "id", "name", "name_en", "service_id", "category"], response.data['coupon']['app_service']
        )

    def test_retry(self):
        # 替换资源交付方法，模拟资源交付，避免真实去交付资源
        ResTaskManager.deliver_task_order = new_deliver_task_order

        # 配置无效，兜底 避免成功创建资源
        order_instance_config = ServerConfig(
            vm_cpu=2, vm_ram=2, systemdisk_size=100, public_ip=True,
            image_id='image_id', image_name='', network_id='network_id', network_name='',
            azone_id='azone_id', azone_name='azone_name', flavor_id=''
        )
        order1, resource_list = OrderManager().create_order(
            order_type=Order.OrderType.RENEWAL.value,
            pay_app_service_id=self.app_service1.id,
            service_id=self.service.id,
            service_name=self.service.name,
            resource_type=ResourceType.VM.value,
            instance_config=order_instance_config,
            period=1,
            period_unit=Order.PeriodUnit.MONTH.value,
            pay_type=PayType.PREPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id=self.vo.id, vo_name=self.vo.name,
            owner_type=OwnerType.VO.value
        )

        task1 = ResTaskManager.create_task(
            status=ResourceOrderDeliverTask.Status.COMPLETED.value,
            status_desc='', progress=ResourceOrderDeliverTask.Progress.ORDERAED.value,
            order=order1, submitter_id=self.user2.id, submitter=self.user2.username,
            service=self.service, task_desc='test task3 desc', coupon=None
        )

        task_url = reverse('servers-api:res-order-deliver-task-retry', kwargs={'id': task1.id})
        response = self.client.post(task_url)
        self.assertEqual(response.status_code, 401)
        self.client.force_login(self.user)

        task_url = reverse('servers-api:res-order-deliver-task-retry', kwargs={'id': 'test'})
        response = self.client.post(task_url)
        self.assertEqual(response.status_code, 404)

        task_url = reverse('servers-api:res-order-deliver-task-retry', kwargs={'id': task1.id})
        response = self.client.post(task_url)
        self.assertEqual(response.status_code, 403)

        # -- test fed admin --
        self.user.set_fed_admin(is_fed=True)
        response = self.client.post(task_url)
        self.assertErrorResponse(status_code=409, code='ConflictStatus', response=response)

        task1.status = ResourceOrderDeliverTask.Status.CANCELLED.value
        task1.save(update_fields=['status'])
        response = self.client.post(task_url)
        self.assertErrorResponse(status_code=409, code='ConflictStatus', response=response)

        task1.status = ResourceOrderDeliverTask.Status.IN_PROGRESS.value
        task1.save(update_fields=['status'])
        response = self.client.post(task_url)
        self.assertErrorResponse(status_code=409, code='ConflictStatus', response=response)

        self.user.set_fed_admin(is_fed=False)
        response = self.client.post(task_url)
        self.assertEqual(response.status_code, 403)

        # --- admin ---
        self.service.org_data_center.add_admin_user(self.user, is_ops_user=True)

        task1.status = ResourceOrderDeliverTask.Status.WAIT.value
        task1.save(update_fields=['status'])

        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(CashCoupon.objects.count(), 0)
        self.assertEqual(PaymentHistory.objects.count(), 0)
        order1.refresh_from_db()
        self.assertEqual(order1.status, Order.Status.UNPAID.value)
        task1.refresh_from_db()
        self.assertEqual(task1.status, ResourceOrderDeliverTask.Status.WAIT.value)

        # ok
        response = self.client.post(task_url)
        self.assertEqual(response.status_code, 202)

        # 发券、支付
        time_sleep(2)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(CashCoupon.objects.count(), 1)
        self.assertEqual(PaymentHistory.objects.count(), 1)
        order1.refresh_from_db()
        self.assertEqual(order1.status, Order.Status.PAID.value)
        task1.refresh_from_db()
        self.assertEqual(task1.status, ResourceOrderDeliverTask.Status.COMPLETED.value)
        self.assertEqual(task1.progress, ResourceOrderDeliverTask.Progress.DELIVERED.value)
        self.assertEqual(task1.coupon_id, CashCoupon.objects.first().id)
