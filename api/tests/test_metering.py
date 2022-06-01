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
from servers.models import Server, ServerArchive 
from django.utils import timezone
from users.models import UserProfile


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
            username=self.user.username,
            vo_id='',
            vo_name='',
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
            username=self.user.username,
            vo_id='',
            vo_name='',
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
            username='',
            vo_id=self.vo.id,
            vo_name=self.vo.name,
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
            username='',
            vo_id='vo1',
            vo_name='vo1 test',
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
            username=self.user.username,
            vo_id='',
            vo_name='',
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
            vo_name=self.vo.name,
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
            "snapshot_hours", "upstream", "downstream", "pay_type",
            "username", "vo_name"
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

    def test_aggregate_metering_by_uuid(self):
        server = Server(
            id='server', ipv4='1.1.1.1', vcpus=1, ram=11, service_id=self.service.id, creation_time=timezone.now())
        server.save(force_insert=True)
        server2 = ServerArchive(
            server_id='server2', ipv4='2.2.2.2', vcpus=2, ram=22, service_id=self.service2.id,
            creation_time=timezone.now(), deleted_time=timezone.now(),
            archive_type=ServerArchive.ArchiveType.ARCHIVE.value
        )
        server2.save(force_insert=True)
        server3 = Server(id='server3', ipv4='3.3.3.3', vcpus=3, ram=33, creation_time=timezone.now())
        server3.save(force_insert=True)

        metering1 = MeteringServer(
            cpu_hours=float(5.1),
            service_id=self.service.id,
            server_id=server.id,
            date=date(year=2022, month=3, day=29),
            user_id=self.user.id,
            vo_id='',
            owner_type=OwnerType.USER.value,
        )
        metering1.save(force_insert=True)

        metering2 = MeteringServer(
            cpu_hours=float(6),
            service_id=self.service.id,
            server_id=server.id,
            date=date(year=2022, month=4, day=1),
            user_id=self.user.id,
            vo_id='',
            owner_type=OwnerType.USER.value,
        )
        metering2.save(force_insert=True)

        metering3 = MeteringServer(
            cpu_hours=float(6.1),
            service_id=self.service.id,
            server_id=server.id,
            date=date(year=2022, month=4, day=30),
            user_id=self.user.id,
            vo_id='',
            owner_type=OwnerType.USER.value,
        )
        metering3.save(force_insert=True)

        metering4 = MeteringServer(
            cpu_hours=float(7),
            service_id=self.service2.id,
            server_id=server2.server_id,
            date=date(year=2022, month=3, day=20),
            user_id=self.user.id,
            vo_id='',
            owner_type=OwnerType.USER.value,
        )
        metering4.save(force_insert=True)

        metering5 = MeteringServer(
            cpu_hours=float(8),
            service_id=self.service2.id,
            server_id=server2.server_id,
            date=date(year=2022, month=3, day=29),
            user_id='',
            vo_id=self.vo.id,
            owner_type=OwnerType.VO.value,
        )
        metering5.save(force_insert=True)

        metering6 = MeteringServer(
            cpu_hours=float(9),
            service_id=self.service2.id,
            server_id=server2.server_id,
            date=date(year=2022, month=4, day=1),
            user_id='',
            vo_id='vo1',
            owner_type=OwnerType.VO.value,
        )
        metering6.save(force_insert=True)        

        metering7 = MeteringServer(
            cpu_hours=float(10),
            service_id=self.service.id,
            server_id=server3.id,
            date=date(year=2022, month=4, day=1),
            user_id='user2',
            vo_id='',
            owner_type=OwnerType.USER.value,
        )
        metering7.save(force_insert=True)   

        metering8 = MeteringServer(
            cpu_hours=float(10.1),
            service_id=self.service2.id,
            server_id=server3.id,
            date=date(year=2022, month=4, day=2),
            user_id='',
            vo_id='vo1',
            owner_type=OwnerType.VO.value,
        )
        metering8.save(force_insert=True)  

        base_url = reverse('api:metering-server-aggregation-by-server')
        
        # list user aggregate metering, default current month
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", "results"], r.data)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0) 
        
        # list user aggregate metering, date_start - date_end
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-03-31',
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2) 
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 5.1)
        self.assertEqual(r.data['results'][0]['server']['ipv4'], '1.1.1.1')
        self.assertEqual(r.data['results'][1]['total_cpu_hours'], 7)
        self.assertEqual(r.data['results'][1]['server']['ipv4'], '2.2.2.2')
        self.assertEqual(r.data['results'][1]['server']['vcpus'], 2)
        
        # list user aggregate metering, invalid date_start
        query = parse.urlencode(query={
            'date_start': '2022-02-31'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # list user aggregate metering, invalid date_end
        query = parse.urlencode(query={
            'date_end': '2022-2-1'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)        

        # list user aggregate metering, query page_size
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-01', 'page_size': 1
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(r.data["page_size"], 1)
        self.assertEqual(len(r.data['results']), 1)
        
        # list vo aggregate metering
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'vo_id': self.vo.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)   
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 8)  
        self.assertEqual(r.data['results'][0]['server']['vcpus'], 2)
        self.assertEqual(r.data['results'][0]['service_name'], 'test2')     

        # service admin
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': ''
        })       
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0)
        
        # service admin, no permission service
        query = parse.urlencode(query={
            'date_start': '2022-04-01', 'date_end': '2022-05-01', 'as-admin': '', 'service_id': self.service.id
        })           
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 403)
        
        # service admin, has permission service
        self.service.users.add(self.user)
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-03-31', 'as-admin': ''
        })    
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)       
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 5.1)
        
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': ''
        })    
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)       
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 11.1)
        self.assertEqual(r.data['results'][1]['total_cpu_hours'], 10)
        
        # service admin, no permission service2
        query = parse.urlencode(query={
            'date_start': '2022-04-01', 'date_end': '2022-04-30', 'as-admin': '', 'service_id': self.service2.id
        })    
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 403)  

        # service admin, list user aggregate metering
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '',
            'service_id': self.service.id, 'user_id': 'user2'
        })    
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)       
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 10)
        self.assertEqual(r.data['results'][0]['server']['ipv4'], '3.3.3.3')
        
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '',
            'user_id': self.user.id
        })    
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)       
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 11.1)
        self.assertEqual(r.data['results'][0]['server']['ipv4'], '1.1.1.1')
        
        # service admin, list vo aggregate metering
        self.service2.users.add(self.user)
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '',
            'vo_id': self.vo.id
        })    
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)       
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 8)
        
        # service admin, list vo aggregate metering, param "vo_id" and "user_id" togethor
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '',
            'vo_id': self.vo.id, 'user_id': self.user.id 
        })    
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)
        
        # federal admin, list all
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)  
        
        # federal admin, vo_id
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '', 'vo_id': self.vo.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)  
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 8)
        self.assertEqual(r.data['results'][0]['server']['ipv4'], '2.2.2.2')

        # federal admin, service_id
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)  
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 11.1)
        self.assertEqual(r.data['results'][1]['total_cpu_hours'], 10)
                
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)  
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 24)
        self.assertEqual(r.data['results'][0]['server']['ipv4'], '2.2.2.2')
        self.assertEqual(r.data['results'][1]['total_cpu_hours'], 10.1)
        self.assertEqual(r.data['results'][1]['server']['ipv4'], '3.3.3.3')
        
        # federal admin, user_id
        query = parse.urlencode(query={
            'date_start': '2022-04-01', 'date_end': '2022-04-30', 'as-admin': '', 'user_id': 'user2'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)  
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 10)
        
        # federal admin, user_id, service_id
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '', 'user_id': self.user.id,
            'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 11.1)

        # federal admin, vo_id, service_id
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '', 'vo_id': 'vo1',
            'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)       
        self.assertEqual(r.data['results'][0]['total_cpu_hours'], 9)
        self.assertEqual(r.data['results'][1]['total_cpu_hours'], 10.1)

        # param 'download'
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '', 'download': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertIs(r.streaming, True)
        self.assertEqual(r.status_code, 200)

    def test_aggregate_metering_by_user(self):
        user2 = UserProfile(id='user2', username='username2', company='c2')
        user2.save(force_insert=True)
        user3 = UserProfile(id='user3', username='username3', company='c3')
        user3.save(force_insert=True)

        metering1 = MeteringServer(
            user_id=self.user.id,
            server_id='server1',
            owner_type=OwnerType.USER.value,
            service_id=self.service.id,
            original_amount=Decimal('1.11'),
            trade_amount=Decimal('1'),
            date=date(year=2022, month=3, day=1),      
        )
        metering1.save(force_insert=True)

        metering2 = MeteringServer(
            user_id=self.user.id,
            server_id='server1',
            owner_type=OwnerType.USER.value,
            service_id=self.service.id,
            original_amount=Decimal('2.22'),
            trade_amount=Decimal('2'),
            date=date(year=2022, month=3, day=2),      
        )
        metering2.save(force_insert=True)

        metering3 = MeteringServer(
            user_id=self.user.id,
            server_id='server1',
            owner_type=OwnerType.USER.value,
            service_id=self.service2.id,
            original_amount=Decimal('3.33'),
            trade_amount=Decimal('3'),
            date=date(year=2022, month=3, day=3),      
        )
        metering3.save(force_insert=True)

        metering4 = MeteringServer(
            user_id=self.user.id,
            server_id='server2',
            owner_type=OwnerType.USER.value,
            service_id=self.service2.id,
            original_amount=Decimal('4.44'),
            trade_amount=Decimal('4'),
            date=date(year=2022, month=4, day=1),      
        )
        metering4.save(force_insert=True)

        metering5 = MeteringServer(
            user_id=user2.id,
            server_id='server3',
            owner_type=OwnerType.USER.value,
            service_id=self.service.id,
            original_amount=Decimal('5.55'),
            trade_amount=Decimal('5'),
            date=date(year=2022, month=4, day=1),      
        )
        metering5.save(force_insert=True)

        metering6 = MeteringServer(
            user_id=user3.id,
            server_id='server4',
            owner_type=OwnerType.USER.value,
            service_id=self.service2.id,
            original_amount=Decimal('6.66'),
            trade_amount=Decimal('6'),
            date=date(year=2022, month=4, day=1),      
        )
        metering6.save(force_insert=True)

        metering7 = MeteringServer(
            vo_id='vo1',
            server_id='server5',
            owner_type=OwnerType.VO.value,
            service_id=self.service2.id,
            original_amount=Decimal('7.77'),
            trade_amount=Decimal('7'),
            date=date(year=2022, month=4, day=1),      
        )
        metering7.save(force_insert=True)

        base_url = reverse('api:metering-server-aggregation-by-user')

        # no param 'as-admin'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # invalid date_start
        query = parse.urlencode(query={
            'date_start': '2022-02-1', 'date_end': '2022-04-01', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # invalid date_end
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-32', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # service admin
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0)

        # service admin, no permission service
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 403)        

        # service admin, has permission service
        self.service2.users.add(self.user)
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)        
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)       
        self.assertEqual(r.data['results'][0]['total_server'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('7.77'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('7'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)    
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['total_trade_amount'], Decimal('6'))
        self.assertEqual(r.data['results'][1]['user']['id'], user3.id)  

        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)        
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)       
        self.assertEqual(r.data['results'][0]['total_server'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('7.77'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('7'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)    
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['total_trade_amount'], Decimal('6'))
        self.assertEqual(r.data['results'][1]['user']['id'], user3.id)  

        # service admin, default current month
        query = parse.urlencode(query={
            'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)        
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0) 

        # service admin, no permission service
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 403)

        # federal admin, list all
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['total_server'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('11.10'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)    
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][1]['user']['id'], user2.id)  
        self.assertEqual(r.data['results'][2]['total_server'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][2]['user']['id'], user3.id)  

        # federal admin, service_id
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['total_server'], 1)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('3.33'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)  
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][1]['user']['id'], user2.id) 

        query = parse.urlencode(query={
            'date_start': '2022-04-01', 'as-admin': '', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['total_server'], 1)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('4.44'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)  
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['user']['id'], user3.id) 

    def test_aggregate_metering_by_vo(self):
        vo1 = VirtualOrganization(id='vo1', name='name1', company='company1', owner_id='owner1')
        vo1.save(force_insert=True)
        vo2 = VirtualOrganization(id='vo2', name='name2', company='company2', owner_id='owner2')
        vo2.save(force_insert=True)
        vo3 = VirtualOrganization(id='vo3', name='name3', company='company3', owner_id='owner3')
        vo3.save(force_insert=True)

        metering1 = MeteringServer(
            vo_id=vo1.id,
            server_id='server1',
            owner_type=OwnerType.VO.value,
            service_id=self.service.id,
            original_amount=Decimal('1.11'),
            trade_amount=Decimal('1'),
            date=date(year=2022, month=3, day=1),      
        )
        metering1.save(force_insert=True)

        metering2 = MeteringServer(
            vo_id=vo1.id,
            server_id='server1',
            owner_type=OwnerType.VO.value,
            service_id=self.service.id,
            original_amount=Decimal('2.22'),
            trade_amount=Decimal('2'),
            date=date(year=2022, month=3, day=2),      
        )
        metering2.save(force_insert=True)

        metering3 = MeteringServer(
            vo_id=vo1.id,
            server_id='server1',
            owner_type=OwnerType.VO.value,
            service_id=self.service2.id,
            original_amount=Decimal('3.33'),
            trade_amount=Decimal('3'),
            date=date(year=2022, month=3, day=3),      
        )
        metering3.save(force_insert=True)

        metering4 = MeteringServer(
            vo_id=vo1.id,
            server_id='server2',
            owner_type=OwnerType.VO.value,
            service_id=self.service2.id,
            original_amount=Decimal('4.44'),
            trade_amount=Decimal('4'),
            date=date(year=2022, month=4, day=1),      
        )
        metering4.save(force_insert=True)

        metering5 = MeteringServer(
            vo_id=vo2.id,
            server_id='server3',
            owner_type=OwnerType.VO.value,
            service_id=self.service.id,
            original_amount=Decimal('5.55'),
            trade_amount=Decimal('5'),
            date=date(year=2022, month=4, day=1),      
        )
        metering5.save(force_insert=True)

        metering6 = MeteringServer(
            vo_id=vo3.id,
            server_id='server4',
            owner_type=OwnerType.VO.value,
            service_id=self.service2.id,
            original_amount=Decimal('6.66'),
            trade_amount=Decimal('6'),
            date=date(year=2022, month=4, day=1),      
        )
        metering6.save(force_insert=True)

        metering7 = MeteringServer(
            user_id=self.user.id,
            server_id='server5',
            owner_type=OwnerType.USER.value,
            service_id=self.service2.id,
            original_amount=Decimal('7.77'),
            trade_amount=Decimal('7'),
            date=date(year=2022, month=4, day=1),      
        )
        metering7.save(force_insert=True)

        base_url = reverse('api:metering-server-aggregation-by-vo')
        
        # no param 'as-admin'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)
        
        # invalid date_start
        query = parse.urlencode(query={
            'date_start': '2022-02-1', 'date_end': '2022-04-01', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # invalid date_end
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-32', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)
        
        # service admin
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0) 
        
        # service admin, no permission service
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 403)        
        
        # service admin, has permission service2
        self.service2.users.add(self.user)
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)        
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)       
        self.assertEqual(r.data['results'][0]['total_server'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('7.77'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('7'))
        self.assertEqual(r.data['results'][0]['vo']['id'], vo1.id)    
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['total_trade_amount'], Decimal('6'))
        self.assertEqual(r.data['results'][1]['vo']['id'], vo3.id)  
        
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)        
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)       
        self.assertEqual(r.data['results'][0]['total_server'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('7.77'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('7'))
        self.assertEqual(r.data['results'][0]['vo']['id'], vo1.id)    
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['total_trade_amount'], Decimal('6'))
        self.assertEqual(r.data['results'][1]['vo']['id'], vo3.id)  

        # service admin, default current month
        query = parse.urlencode(query={
            'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)        
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0) 

        # service admin, no permission service
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 403)   
        
        # federal admin, list all
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['total_server'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('11.10'))
        self.assertEqual(r.data['results'][0]['vo']['id'], vo1.id) 
        self.assertEqual(r.data['results'][0]['vo']['company'], vo1.company)      
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][1]['vo']['id'], vo2.id)  
        self.assertEqual(r.data['results'][1]['vo']['company'], vo2.company)      
        self.assertEqual(r.data['results'][2]['total_server'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][2]['vo']['id'], vo3.id)  
        self.assertEqual(r.data['results'][2]['vo']['company'], vo3.company)      
        
        # federal admin, service_id
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['total_server'], 1)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('3.33'))
        self.assertEqual(r.data['results'][0]['vo']['id'], vo1.id)  
        self.assertEqual(r.data['results'][0]['vo']['name'], vo1.name)
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][1]['vo']['id'], vo2.id) 
        self.assertEqual(r.data['results'][1]['vo']['name'], vo2.name) 
        
        query = parse.urlencode(query={
            'date_start': '2022-04-01', 'as-admin': '', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['total_server'], 1)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('4.44'))
        self.assertEqual(r.data['results'][0]['vo']['id'], vo1.id)  
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['vo']['id'], vo3.id) 

    def test_aggregate_metering_by_service(self):
        service3 = ServiceConfig(id='service3', name='name3')
        service3.save(force_insert=True)

        metering1 = MeteringServer(
            service_id=self.service.id,
            vo_id='vo1',
            server_id='server1',
            owner_type=OwnerType.VO.value,
            original_amount=Decimal('1.11'),
            trade_amount=Decimal('1'),
            date=date(year=2022, month=3, day=1),      
        )
        metering1.save(force_insert=True)

        metering2 = MeteringServer(
            service_id=self.service.id,
            user_id='user1',
            server_id='server1',
            owner_type=OwnerType.USER.value,
            original_amount=Decimal('2.22'),
            trade_amount=Decimal('2'),
            date=date(year=2022, month=3, day=2),      
        )
        metering2.save(force_insert=True)    

        metering3 = MeteringServer(
            service_id=self.service.id,
            user_id='user1',
            server_id='server2',
            owner_type=OwnerType.USER.value,
            original_amount=Decimal('3.33'),
            trade_amount=Decimal('3'),
            date=date(year=2022, month=3, day=1),      
        )
        metering3.save(force_insert=True) 

        metering4 = MeteringServer(
            service_id=self.service2.id,
            user_id='user2',
            server_id='server3',
            owner_type=OwnerType.USER.value,
            original_amount=Decimal('4.44'),
            trade_amount=Decimal('4'),
            date=date(year=2022, month=3, day=1),      
        )
        metering4.save(force_insert=True)     

        metering5 = MeteringServer(
            service_id=service3.id,
            user_id='user2',
            server_id='server3',
            owner_type=OwnerType.USER.value,
            original_amount=Decimal('5.55'),
            trade_amount=Decimal('5'),
            date=date(year=2022, month=4, day=1),      
        )
        metering5.save(force_insert=True)  

        base_url = reverse('api:metering-server-aggregation-by-service')

        # no param 'as-admin'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)
        
        # invalid date_start
        query = parse.urlencode(query={
            'date_start': '2022-02-1', 'date_end': '2022-04-01', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # invalid date_end
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-32', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)
        
        # service admin
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0) 
            
        # service admin, has permission service
        self.service.users.add(self.user)
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '',
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)        
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)       
        self.assertEqual(r.data['results'][0]['total_server'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('6'))
        
        # service admin, has permission service and service2
        self.service2.users.add(self.user)
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '',
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)         
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)  
        self.assertEqual(r.data['results'][0]['total_server'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('6'))   
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('4.44'))
        self.assertEqual(r.data['results'][1]['total_trade_amount'], Decimal('4'))            

        # service admin, default current month
        query = parse.urlencode(query={
            'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)        
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0) 
        
        # federal admin, list all
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['total_server'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][0]['service']['id'], self.service.id)
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('4.44'))
        self.assertEqual(r.data['results'][1]['service']['id'], self.service2.id)  
        self.assertEqual(r.data['results'][2]['total_server'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][2]['service']['id'], service3.id)  
        self.assertEqual(r.data['results'][2]['service']['name'], service3.name)      
  