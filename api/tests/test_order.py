from decimal import Decimal
from urllib import parse
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from servers.models import Flavor
from utils.model import PayType, OwnerType
from order.models import Price, Order, ResourceType
from order.managers import OrderManager
from order.managers.instance_configs import ServerConfig, DiskConfig
from utils.decimal_utils import quantize_10_2
from vo.models import VirtualOrganization
from . import set_auth_header, MyAPITestCase


class OrderTests(MyAPITestCase):
    def setUp(self):
        self.user = set_auth_header(self)
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
        price.save()
        self.price = price
        self.flavor = Flavor(vcpus=2, ram=4 * 1024)
        self.flavor.save()
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user
        )
        self.vo.save()

    def test_list_order(self):
        omgr = OrderManager()
        base_url = reverse('api:order-list')

        # list user order
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'orders'], response.data)
        self.assertIsInstance(response.data['orders'], list)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        # list vo order
        query = parse.urlencode(query={
            'vo_id': self.vo.id
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'orders'], response.data)
        self.assertIsInstance(response.data['orders'], list)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        order, resource = omgr.create_order(
            order_type=Order.OrderType.NEW.value,
            service_id='test',
            service_name='test',
            resource_type=ResourceType.VM.value,
            instance_config=ServerConfig(
                vm_cpu=2, vm_ram=2048, systemdisk_size=100, public_ip=True
            ),
            period=2,
            pay_type=PayType.PREPAID.value,
            user_id=self.user.id,
            username=self.user.username,
            vo_id='', vo_name='',
            owner_type=OwnerType.USER.value
        )

        # list user order
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['orders']), 1)
        self.assertKeysIn(["id", "order_type", "status", "total_amount", "pay_amount",
                           "service_id", "service_name", "resource_type", "instance_config", "period",
                           "payment_time", "pay_type", "creation_time", "user_id", "username",
                           "vo_id", "vo_name", "owner_type"], response.data['orders'][0])
        self.assert_is_subdict_of({
            "id": order.id,
            "order_type": order.order_type,
            "status": order.status,
            "total_amount": str(quantize_10_2(order.total_amount)),
            "pay_amount": str(quantize_10_2(order.pay_amount)),
            "service_id": order.service_id,
            "service_name": order.service_name,
            "resource_type": ResourceType.VM.value,
            "instance_config": order.instance_config,
            "period": order.period,
            "pay_type": PayType.PREPAID.value,
            "user_id": self.user.id,
            "username": self.user.username,
            "vo_id": order.vo_id,
            "vo_name": order.vo_name,
            "owner_type": OwnerType.USER.value
        }, response.data['orders'][0])

        # list vo order
        query = parse.urlencode(query={
            'vo_id': self.vo.id
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        order2, resource2 = omgr.create_order(
            order_type=Order.OrderType.UPGRADE.value,
            service_id='test',
            service_name='test',
            resource_type=ResourceType.DISK.value,
            instance_config=DiskConfig(disk_size=166),
            period=2,
            pay_type=PayType.POSTPAID.value,
            user_id='',
            username='',
            vo_id=self.vo.id, vo_name=self.vo.name,
            owner_type=OwnerType.VO.value
        )

        # list user order
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['orders']), 1)

        # list vo order
        query = parse.urlencode(query={
            'vo_id': self.vo.id
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['orders']), 1)
        self.assert_is_subdict_of({
            "id": order2.id,
            "order_type": order2.order_type,
            "status": order2.status,
            "total_amount": str(quantize_10_2(order2.total_amount)),
            "pay_amount": str(quantize_10_2(order2.pay_amount)),
            "service_id": order2.service_id,
            "service_name": order2.service_name,
            "resource_type": ResourceType.DISK.value,
            "instance_config": order2.instance_config,
            "period": order2.period,
            "pay_type": PayType.POSTPAID.value,
            "user_id": order2.user_id,
            "username": order2.username,
            "vo_id": self.vo.id,
            "vo_name": self.vo.name,
            "owner_type": OwnerType.VO.value
        }, response.data['orders'][0])

        self.list_user_order_query_test()
        self.list_vo_order_query_test()

    def list_user_order_query_test(self):
        base_url = reverse('api:order-list')

        # list user order, filter query "resource_type"
        query = parse.urlencode(query={
            'resource_type': ResourceType.DISK.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        query = parse.urlencode(query={
            'resource_type': ResourceType.VM.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['orders']), 1)
        self.assertEqual(response.data['orders'][0]['resource_type'], ResourceType.VM.value)

        # list user order, filter query "resource_type, order_type"
        query = parse.urlencode(query={
            'resource_type': ResourceType.VM.value, 'order_type': Order.OrderType.UPGRADE.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        query = parse.urlencode(query={
            'resource_type': ResourceType.VM.value, 'order_type': Order.OrderType.NEW.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['orders']), 1)
        self.assertEqual(response.data['orders'][0]['resource_type'], ResourceType.VM.value)
        self.assertEqual(response.data['orders'][0]['order_type'], Order.OrderType.NEW.value)

        def check_user_order_response(_self, _url: str):
            _response = _self.client.get(_url)
            _self.assertEqual(_response.status_code, 200)
            _self.assertEqual(_response.data['count'], 1)
            _self.assertEqual(len(_response.data['orders']), 1)
            _self.assertEqual(_response.data['orders'][0]['order_type'], Order.OrderType.NEW.value)
            _self.assertEqual(_response.data['orders'][0]['status'], Order.Status.UPPAID.value)
            _self.assertEqual(_response.data['orders'][0]['resource_type'], ResourceType.VM.value)

        # list user order, filter query "resource_type, order_type, status"
        query = parse.urlencode(query={
            'resource_type': ResourceType.VM.value, 'order_type': Order.OrderType.NEW.value,
            'status': Order.Status.PAID.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        query = parse.urlencode(query={
            'resource_type': ResourceType.VM.value, 'order_type': Order.OrderType.NEW.value,
            'status': Order.Status.UPPAID.value
        })
        check_user_order_response(self, f'{base_url}?{query}')

        # list user order, filter query "resource_type, order_type, status, time_start"
        query = parse.urlencode(query={
            'resource_type': ResourceType.VM.value, 'order_type': Order.OrderType.NEW.value,
            'status': Order.Status.UPPAID.value, 'time_start': timezone.now()
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        query = parse.urlencode(query={
            'resource_type': ResourceType.VM.value, 'order_type': Order.OrderType.NEW.value,
            'status': Order.Status.UPPAID.value, 'time_start': timezone.now() - timedelta(hours=1)
        })
        check_user_order_response(self, f'{base_url}?{query}')

        # list user order, filter query "resource_type, order_type, status, time_end"
        query = parse.urlencode(query={
            'resource_type': ResourceType.VM.value, 'order_type': Order.OrderType.NEW.value,
            'status': Order.Status.UPPAID.value, 'time_end': timezone.now()
        })
        check_user_order_response(self, f'{base_url}?{query}')

        query = parse.urlencode(query={
            'resource_type': ResourceType.VM.value, 'order_type': Order.OrderType.NEW.value,
            'status': Order.Status.UPPAID.value, 'time_end': timezone.now() - timedelta(hours=1)
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        # list user order, filter query "resource_type, order_type, status, time_start, time_end"
        query = parse.urlencode(query={
            'resource_type': ResourceType.VM.value, 'order_type': Order.OrderType.NEW.value,
            'status': Order.Status.UPPAID.value,
            'time_start': timezone.now() - timedelta(hours=1), 'time_end': timezone.now()
        })
        check_user_order_response(self, f'{base_url}?{query}')

        query = parse.urlencode(query={
            'resource_type': ResourceType.VM.value, 'order_type': Order.OrderType.NEW.value,
            'status': Order.Status.UPPAID.value,
            'time_start': timezone.now(), 'time_end': timezone.now()
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

    def list_vo_order_query_test(self):
        base_url = reverse('api:order-list')

        # list vo order, filter query "resource_type"
        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.VM.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['orders']), 1)
        self.assertEqual(response.data['orders'][0]['resource_type'], ResourceType.DISK.value)

        # list vo order, filter query "resource_type, order_type"
        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value, 'order_type': Order.OrderType.RENEWAL.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value, 'order_type': Order.OrderType.UPGRADE.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['orders']), 1)
        self.assertEqual(response.data['orders'][0]['resource_type'], ResourceType.DISK.value)
        self.assertEqual(response.data['orders'][0]['order_type'], Order.OrderType.UPGRADE.value)

        def check_vo_order_response(_self, _url: str):
            _r = _self.client.get(_url)
            _self.assertEqual(_r.status_code, 200)
            _self.assertEqual(_r.data['count'], 1)
            _self.assertEqual(len(_r.data['orders']), 1)
            _self.assertEqual(_r.data['orders'][0]['resource_type'], ResourceType.DISK.value)
            _self.assertEqual(_r.data['orders'][0]['order_type'], Order.OrderType.UPGRADE.value)
            _self.assertEqual(_r.data['orders'][0]['status'], Order.Status.UPPAID.value)

        # list vo order, filter query "resource_type, order_type, status"
        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value, 'order_type': Order.OrderType.UPGRADE.value,
            'status': Order.Status.PAID.value
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value, 'order_type': Order.OrderType.UPGRADE.value,
            'status': Order.Status.UPPAID.value
        })
        check_vo_order_response(self, f'{base_url}?{query}')

        # list vo order, filter query "resource_type, order_type, status, time_start"
        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value, 'order_type': Order.OrderType.UPGRADE.value,
            'status': Order.Status.UPPAID.value, 'time_start': timezone.now()
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value, 'order_type': Order.OrderType.UPGRADE.value,
            'status': Order.Status.UPPAID.value, 'time_start': timezone.now() - timedelta(hours=1)
        })
        check_vo_order_response(self, f'{base_url}?{query}')

        # list vo order, filter query "resource_type, order_type, status, time_end"
        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value, 'order_type': Order.OrderType.UPGRADE.value,
            'status': Order.Status.UPPAID.value, 'time_end': timezone.now()
        })
        check_vo_order_response(self, f'{base_url}?{query}')

        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value, 'order_type': Order.OrderType.UPGRADE.value,
            'status': Order.Status.UPPAID.value, 'time_end': timezone.now() - timedelta(hours=1)
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)

        # list vo order, filter query "resource_type, order_type, status, time_start, time_end"
        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value, 'order_type': Order.OrderType.UPGRADE.value,
            'status': Order.Status.UPPAID.value,
            'time_start': timezone.now() - timedelta(hours=1), 'time_end': timezone.now()
        })
        check_vo_order_response(self, f'{base_url}?{query}')

        query = parse.urlencode(query={
            'vo_id': self.vo.id, 'resource_type': ResourceType.DISK.value, 'order_type': Order.OrderType.UPGRADE.value,
            'status': Order.Status.UPPAID.value,
            'time_start': timezone.now(), 'time_end': timezone.now()
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['orders']), 0)
