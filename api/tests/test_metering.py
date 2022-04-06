from decimal import Decimal
from urllib import parse
from datetime import date

from django.urls import reverse

from utils.model import PayType, OwnerType
from utils.test import get_or_create_service
from service.models import ServiceConfig
from vo.models import VirtualOrganization
from metering.models import MeteringServer, PaymentStatus
from . import set_auth_header, MyAPITestCase


class MeteringServerTests(MyAPITestCase):
    def setUp(self):
        self.user = set_auth_header(self)
        self.service = get_or_create_service()
        self.service2 = ServiceConfig(
            name='test2', data_center_id=self.service.data_center_id, endpoint_url='test2', username='', password='',
            need_vpn=False
        )
        self.service2.save(force_insert=True)
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user
        )
        self.vo.save()

    def test_list_metering(self):
        metering1 = MeteringServer(
            original_amount=Decimal('1.11'),
            trade_amount=Decimal('1.11'),
            payment_status=PaymentStatus.PAID.value,
            payment_history_id=None,
            service_id=self.service.id,
            server_id='server1',
            date=date(year=2022, month=2, day=16),
            user_id=self.user.id,
            vo_id='',
            owner_type=OwnerType.USER.value,
            pay_type=PayType.POSTPAID.value
        )
        metering1.save(force_insert=True)

        metering2 = MeteringServer(
            original_amount=Decimal('2.22'),
            trade_amount=Decimal('0'),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=None,
            service_id=self.service.id,
            server_id='server1',
            date=date(year=2022, month=3, day=16),
            user_id=self.user.id,
            vo_id='',
            owner_type=OwnerType.USER.value,
            pay_type=PayType.POSTPAID.value
        )
        metering2.save(force_insert=True)

        metering3 = MeteringServer(
            original_amount=Decimal('3.33'),
            trade_amount=Decimal('0'),
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id=None,
            service_id=self.service.id,
            server_id='server2',
            date=date(year=2022, month=2, day=8),
            user_id='',
            vo_id=self.vo.id,
            owner_type=OwnerType.VO.value,
            pay_type=PayType.POSTPAID.value
        )
        metering3.save(force_insert=True)

        metering4 = MeteringServer(
            original_amount=Decimal('4.44'),
            trade_amount=Decimal('4.44'),
            payment_status=PaymentStatus.PAID.value,
            payment_history_id=None,
            service_id=self.service.id,
            server_id='server2',
            date=date(year=2022, month=3, day=8),
            user_id='',
            vo_id='vo1',
            owner_type=OwnerType.VO.value,
            pay_type=PayType.PREPAID.value
        )
        metering4.save(force_insert=True)

        metering5 = MeteringServer(
            original_amount=Decimal('5.55'),
            trade_amount=Decimal('5.55'),
            payment_status=PaymentStatus.PAID.value,
            payment_history_id=None,
            service_id=self.service2.id,
            server_id='server2',
            date=date(year=2022, month=3, day=18),
            user_id=self.user.id,
            vo_id='',
            owner_type=OwnerType.USER.value,
            pay_type=PayType.PREPAID.value
        )
        metering5.save(force_insert=True)

        metering6 = MeteringServer(
            original_amount=Decimal('6.66'),
            trade_amount=Decimal('6.66'),
            payment_status=PaymentStatus.PAID.value,
            payment_history_id=None,
            service_id=self.service2.id,
            server_id='server6',
            date=date(year=2022, month=3, day=9),
            user_id='',
            vo_id=self.vo.id,
            owner_type=OwnerType.VO.value,
            pay_type=PayType.PREPAID.value
        )
        metering6.save(force_insert=True)

        # list user metering, default current month
        base_url = reverse('api:metering-server-list')
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", "results"], r.data)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0)

        # list user metering, date_start - date_end
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", "results"], r.data)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertKeysIn([
            "id", "original_amount", "trade_amount", "payment_status",
            "payment_history_id", "service_id", "server_id", "date",
            "creation_time", "user_id", "vo_id", "owner_type",
            "cpu_hours", "ram_hours", "disk_hours", "public_ip_hours",
            "snapshot_hours", "upstream", "downstream", "pay_type"
        ], r.data['results'][0])

        # list user metering, invalid date_start
        query = parse.urlencode(query={
            'date_start': '2022-02-30'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # list user metering, invalid date_end
        query = parse.urlencode(query={
            'date_end': '2022-2-01'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # list user metering, date_start date_end timedelta less than one year
        query = parse.urlencode(query={
            'date_start': '2021-02-01', 'date_end': '2022-02-02'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # list user metering, query page_size
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'page_size': 1
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(r.data["page_size"], 1)
        self.assertEqual(len(r.data['results']), 1)

        # list vo metering
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'vo_id': self.vo.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)

        # service admin
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0)

        # service admin, no permission service
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 403)

        # service admin, has permission service
        self.service.users.add(self.user)
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 4)
        self.assertEqual(len(r.data['results']), 4)

        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 4)
        self.assertEqual(len(r.data['results']), 4)

        # service admin, list user metering
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'service_id': self.service.id,
            'user_id': self.user.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['user_id'], self.user.id)
        self.assertEqual(r.data['results'][0]['owner_type'], OwnerType.USER.value)

        # service admin, list vo metering
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'service_id': self.service.id,
            'vo_id': self.vo.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['vo_id'], self.vo.id)
        self.assertEqual(r.data['results'][0]['owner_type'], OwnerType.VO.value)

        # service admin, list vo metering, param "vo_id" and "user_id" togethor
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'service_id': self.service.id,
            'vo_id': self.vo.id, 'user_id': self.user.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # service admin, no permission service2
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 403)

        # federal admin， list all
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 6)
        self.assertEqual(len(r.data['results']), 6)

        # federal admin, service_id
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 4)
        self.assertEqual(len(r.data['results']), 4)

        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)

        # federal admin, user_id
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'user_id': self.user.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)

        # federal admin, user_id, service_id
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'user_id': self.user.id,
            'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)

        # federal admin, vo_id, service_id
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'vo_id': self.vo.id,
            'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
