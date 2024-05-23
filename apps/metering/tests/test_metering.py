from decimal import Decimal
from urllib import parse
from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone

from utils.model import PayType, OwnerType
from utils.test import get_or_create_service, get_or_create_user, get_or_create_storage_service, MyAPITestCase
from apps.storage.models import ObjectsService
from apps.vo.models import VirtualOrganization
from apps.metering.models import (
    MeteringServer, DailyStatementServer, PaymentStatus, MeteringObjectStorage, DailyStatementObjectStorage,
    MeteringDisk, DailyStatementDisk
)
from apps.servers.models import Server, ServerArchive, Disk, ServiceConfig
from apps.servers.tests.test_disk import create_disk_metadata
from apps.users.models import UserProfile


class MeteringServerTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.service = get_or_create_service()
        self.service2 = ServiceConfig(
            name='test2', org_data_center_id=self.service.org_data_center_id, endpoint_url='test2',
            username='', password='', need_vpn=False
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
            daily_statement_id='',
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
            daily_statement_id='',
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
            daily_statement_id='',
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
            daily_statement_id='',
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
            daily_statement_id='',
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
            daily_statement_id='',
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
        base_url = reverse('metering-api:metering-server-list')
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
            "id", "original_amount", "trade_amount",
            "daily_statement_id", "service_id", "server_id", "date",
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

        # param 'download'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'download': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertIs(r.streaming, True)
        self.assertEqual(r.status_code, 200)

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

        base_url = reverse('metering-api:metering-server-aggregation-by-server')
        
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

        base_url = reverse('metering-api:metering-server-aggregation-by-user')

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

        # federal admin, list all, order_by
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '',
            'order_by': '-total_original_amount'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['total_server'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('11.10'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['user']['id'], user3.id)
        self.assertEqual(r.data['results'][2]['total_server'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][2]['user']['id'], user2.id)

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

        # param 'download'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'download': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertIs(r.streaming, True)
        self.assertEqual(r.status_code, 200)

    def test_aggregate_metering_by_vo(self):
        owner1 = UserProfile(id='owner1', username='owner1')
        owner1.save(force_insert=True)
        owner2 = UserProfile(id='owner2', username='owner2')
        owner2.save(force_insert=True)
        owner3 = UserProfile(id='owner3', username='owner3')
        owner3.save(force_insert=True)

        vo1 = VirtualOrganization(id='vo1', name='name1', company='company1', owner_id=owner1.id)
        vo1.save(force_insert=True)
        vo2 = VirtualOrganization(id='vo2', name='name2', company='company2', owner_id=owner2.id)
        vo2.save(force_insert=True)
        vo3 = VirtualOrganization(id='vo3', name='name3', company='company3', owner_id=owner3.id)
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

        base_url = reverse('metering-api:metering-server-aggregation-by-vo')
        
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

        # federal admin, list all, order_by
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '',
            'order_by': '-total_original_amount'
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
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['vo']['id'], vo3.id)
        self.assertEqual(r.data['results'][1]['vo']['company'], vo3.company)
        self.assertEqual(r.data['results'][2]['total_server'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][2]['vo']['id'], vo2.id)
        self.assertEqual(r.data['results'][2]['vo']['company'], vo2.company)

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

        # param 'download'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'download': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertIs(r.streaming, True)
        self.assertEqual(r.status_code, 200)

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

        base_url = reverse('metering-api:metering-server-aggregation-by-service')

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

        # federal admin, list all, order_by
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '',
            'order_by': '-total_original_amount'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['total_server'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][0]['service']['id'], self.service.id)
        self.assertEqual(r.data['results'][1]['total_server'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][1]['service']['id'], service3.id)
        self.assertEqual(r.data['results'][1]['service']['name'], service3.name)
        self.assertEqual(r.data['results'][2]['total_server'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('4.44'))
        self.assertEqual(r.data['results'][2]['service']['id'], self.service2.id)

        # param 'download'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'download': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertIs(r.streaming, True)
        self.assertEqual(r.status_code, 200)


class StatementServerTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.user2 = get_or_create_user(username='user2')
        
        self.vo = VirtualOrganization(
            id='test vo id', name='test vo', owner=self.user
        )
        self.vo.save()

        self.service = get_or_create_service()
        self.service2 = ServiceConfig(
            name='test2', org_data_center_id=self.service.org_data_center_id, endpoint_url='test2',
            username='', password='', need_vpn=False
        )
        self.service2.save()

    def create_statement_server(self):
        # ## user
        # # user
        # 2022-1-1 service
        u_st0 = DailyStatementServer(
            original_amount='1.11',
            payable_amount='1.11',
            trade_amount='1.11',
            payment_status=PaymentStatus.PAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=1),
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
        )
        u_st0.save(force_insert=True)

        # 2022-1-1 service2
        u_st1 = DailyStatementServer(
            original_amount='2.22',
            payable_amount='2.22',
            trade_amount='0',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service2.id,
            date=date(year=2022, month=1, day=1),
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
        )
        u_st1.save(force_insert=True)

        # 2022-1-2 service1
        u_st2 = DailyStatementServer(
            original_amount='3.33',
            payable_amount='3.33',
            trade_amount='0',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=2),
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
        )
        u_st2.save(force_insert=True)

        # # user2
        u_st3 = DailyStatementServer(
            original_amount='4.44',
            payable_amount='4.44',
            trade_amount='0',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=2),
            user_id=self.user2.id,
            username=self.user2.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
        )
        u_st3.save(force_insert=True) 

        # ## vo
        # 2022-1-1 service
        v_st0 = DailyStatementServer(
            original_amount='5.55',
            payable_amount='5.55',
            trade_amount='5.55',
            payment_status=PaymentStatus.PAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=1),
            user_id='',
            username='',
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
        )
        v_st0.save(force_insert=True)

        # 2022-1-1 service2
        v_st1 = DailyStatementServer(
            original_amount='6.66',
            payable_amount='6.66',
            trade_amount='0',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service2.id,
            date=date(year=2022, month=1, day=1),
            user_id='',
            username='',
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
        )
        v_st1.save(force_insert=True)

        # 2022-1-2 service1
        v_st2 = DailyStatementServer(
            original_amount='7.77',
            payable_amount='7.77',
            trade_amount='0',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=2),
            user_id='',
            username='',
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
        )
        v_st2.save(force_insert=True)

        return u_st0, u_st1, u_st2, u_st3, v_st0, v_st1, v_st2

    def test_list_statement_server(self):
        base_url = reverse('metering-api:statement-server-list')

        # list user statement-server
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'statements'], response.data)
        self.assertIsInstance(response.data['statements'], list)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['statements']), 0)

        # list vo statement-server
        query = parse.urlencode(query={
            'vo_id': self.vo.id
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'statements'], response.data)
        self.assertIsInstance(response.data['statements'], list)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['statements']), 0)

        # create statement server
        u_st0, u_st1, u_st2, u_st3, v_st0, v_st1, v_st2 = self.create_statement_server()

        # ------ list user -------
        # no params
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['statements']), 3)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "service", "date", "creation_time",
                           "user_id", "username", "vo_id", "vo_name", "owner_type"], response.data['statements'][0])

        self.assertEqual(response.data['statements'][0]['original_amount'], u_st2.original_amount)
        self.assertEqual(response.data['statements'][1]['original_amount'], u_st1.original_amount)
        self.assertEqual(response.data['statements'][2]['original_amount'], u_st0.original_amount)

        # date_start - date_end
        query = parse.urlencode(query={
            'date_start': '2022-01-02', 'time_end': '2022-01-02'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['statements']), 1)
        self.assertEqual(response.data['statements'][0]['user_id'], self.user.id)
        self.assertEqual(response.data['statements'][0]['user_id'], u_st2.user_id)
        self.assertEqual(response.data['statements'][0]['original_amount'], u_st2.original_amount)

        query = parse.urlencode(query={
            'date_start': '2022-01-01', 'time_end': '2022-01-02'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['statements']), 3)

        # payment_status 
        query = parse.urlencode(query={
            'payment_status': PaymentStatus.PAID.value,
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['statements']), 1)
        self.assertEqual(response.data['statements'][0]['original_amount'], u_st0.original_amount)

        # date_start - date_end  && payment_status
        query = parse.urlencode(query={
            'date_start': '2022-01-01', 'time_end': '2022-01-02',
            'payment_status': PaymentStatus.UNPAID.value,

        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['statements']), 2)

        # ---- list vo ------
        query = parse.urlencode(query={
            'vo_id': self.vo.id
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['statements']), 3)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "service", "date", "creation_time",
                           "user_id", "username", "vo_id", "vo_name", "owner_type"], response.data['statements'][0])
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['statements'][0]['service'])
        self.assertEqual(response.data['statements'][0]['original_amount'], v_st2.original_amount)
        self.assertEqual(response.data['statements'][1]['original_amount'], v_st1.original_amount)
        self.assertEqual(response.data['statements'][2]['original_amount'], v_st0.original_amount)

        # date_start - date_end
        query = parse.urlencode(query={
            'vo_id': self.vo.id,
            'date_start': '2022-01-02', 'time_end': '2022-01-02',
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['statements']), 1)
        self.assertEqual(response.data['statements'][0]['vo_id'], self.vo.id)
        self.assertEqual(response.data['statements'][0]['vo_id'], v_st2.vo_id)
        self.assertEqual(response.data['statements'][0]['original_amount'], v_st2.original_amount)

        query = parse.urlencode(query={
            'vo_id': self.vo.id,
            'date_start': '2022-01-01', 'time_end': '2022-01-02'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['statements']), 3)

        # payment_status 
        query = parse.urlencode(query={
            'vo_id': self.vo.id,
            'payment_status': PaymentStatus.PAID.value,
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['statements']), 1)
        self.assertEqual(response.data['statements'][0]['original_amount'], v_st0.original_amount)

        # date_start - date_end  && payment_status
        query = parse.urlencode(query={
            'vo_id': self.vo.id,
            'date_start': '2022-01-01', 'time_end': '2022-01-02',
            'payment_status': PaymentStatus.UNPAID.value,

        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['statements']), 2)

    def test_detail_statement_server(self):

        # not found
        url = reverse('order-api:order-detail', kwargs={'id': '1234567891234567891234'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # create statement server
        u_st0, u_st1, u_st2, u_st3, v_st0, v_st1, v_st2 = self.create_statement_server()

        # user statement server detail
        url = reverse('metering-api:statement-server-detail', kwargs={'id': u_st0.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "service", "date", "creation_time",
                           "user_id", "username", "vo_id", "vo_name", "owner_type", "service"], response.data)
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['service'])

        self.assert_is_subdict_of(sub={
            "id": u_st0.id,
            "original_amount": u_st0.original_amount,
            "payable_amount": u_st0.payable_amount,
            "trade_amount": u_st0.trade_amount,
            "payment_status": u_st0.payment_status,
            "payment_history_id": u_st0.payment_history_id,
            "user_id": self.user.id,
            "username": self.user.username,
            "vo_id": '',
            "vo_name": '',
            "owner_type": OwnerType.USER.value,
        }, d=response.data)
        self.assert_is_subdict_of(sub={
            "id": self.service.id,
            "name": self.service.name,
            "name_en": self.service.name_en,
            "service_type": self.service.service_type,
        }, d=response.data['service'])

        # vo statement server detail
        url = reverse('metering-api:statement-server-detail', kwargs={'id': v_st0.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "service", "date", "creation_time",
                           "user_id", "username", "vo_id", "vo_name", "owner_type", "service",
                           'meterings'], response.data)
        self.assertIsInstance(response.data['meterings'], list)
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['service'])
        self.assertEqual(response.data['original_amount'], v_st0.original_amount)
        self.assertEqual(response.data['payable_amount'], v_st0.payable_amount)
        self.assertEqual(response.data['trade_amount'], v_st0.trade_amount)
        self.assertEqual(response.data['payment_status'], v_st0.payment_status)
        self.assertEqual(response.data['service_id'], v_st0.service_id)
        self.assertEqual(response.data['payment_history_id'], v_st0.payment_history_id)
        self.assertEqual(response.data['user_id'], '')
        self.assertEqual(response.data['username'], '')
        self.assertEqual(response.data['vo_id'], self.vo.id)
        self.assertEqual(response.data['vo_name'], self.vo.name)
        self.assertEqual(response.data['owner_type'], OwnerType.VO.value)

        # user2 no vo permission test
        self.client.logout()
        self.client.force_login(user=self.user2)
        url = reverse('metering-api:statement-server-detail', kwargs={'id': v_st0.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        url = reverse('metering-api:statement-server-detail', kwargs={'id': v_st1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


class MeteringObsTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.service = get_or_create_storage_service()
        self.service2 = ObjectsService(
            name='service2', org_data_center_id=self.service.org_data_center_id,
            endpoint_url='service2', username='', password=''
        )
        self.service2.save()

    def test_list_metering(self):
        user2 = get_or_create_user(username='lilei@cnic.cn')

        metering1 = MeteringObjectStorage(
            original_amount=Decimal('1.11'),
            trade_amount=Decimal('1.11'),
            daily_statement_id='',
            service_id=self.service.id,
            storage_bucket_id='bucket1',
            date=date(year=2022, month=10, day=1),
            user_id=self.user.id,
            username=self.user.username,
            storage=1.2345
        )
        metering1.save(force_insert=True)

        metering2 = MeteringObjectStorage(
            original_amount=Decimal('2.22'),
            trade_amount=Decimal('0'),
            daily_statement_id='',
            service_id=self.service2.id,
            storage_bucket_id='bucket2',
            date=date(year=2022, month=10, day=2),
            user_id=self.user.id,
            username=self.user.username,
            storage=2.2345
        )
        metering2.save(force_insert=True)

        metering3 = MeteringObjectStorage(
            original_amount=Decimal('2.22'),
            trade_amount=Decimal('0'),
            daily_statement_id='',
            service_id=self.service2.id,
            storage_bucket_id='bucket3',
            date=date(year=2022, month=10, day=3),
            user_id=user2.id,
            username=user2.username,
            storage=3.2345
        )
        metering3.save(force_insert=True)

        # list user metering
        base_url = reverse('metering-api:metering-storage-list')
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", "results"], r.data)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data["results"]), 0)

        # list user metering date_start->date_end
        query = parse.urlencode(query={
            'date_start': '2022-10-01', 'date_end': '2022-10-03'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", "results"], r.data)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data["results"]), 2)
        self.assertKeysIn([
            "id", "original_amount", "trade_amount", "daily_statement_id",
            "service_id", "storage_bucket_id", "date", "creation_time", "user_id",
            "username", "storage", 'service', 'billed_network_flow', 'unbilled_network_flow'
        ], r.data['results'][0])
        self.assertKeysIn(["id", "name", "name_en"], r.data['results'][0]['service'])

        # list user metering invalid date_start
        query = parse.urlencode(query={
            'date_start': '2022-02-30'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # list user metering invalid date end
        query = parse.urlencode(query={
            'date_end': '2022-2-01'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # list user metering timedelta more than one year
        query = parse.urlencode(query={
            'date_start': '2021-02-01', 'date_end': ' 2022-02-06'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # list user metering, query page_size
        query = parse.urlencode(query={
            'date_start': '2022-10-01', 'date_end': '2022-10-03', "page_size": 1
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", "results"], r.data)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data['page_size'], 1)

        # param 'download'
        query = parse.urlencode(query={
            'date_start': '2022-10-01', 'date_end': '2022-10-03', 'download': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertIs(r.streaming, True)
        self.assertEqual(r.status_code, 200)

        # param 'service_id'
        query = parse.urlencode(query={
            'date_start': '2022-10-01', 'date_end': '2022-10-10', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data['results'][0]['id'], metering1.id)

        query = parse.urlencode(query={
            'date_start': '2022-10-01', 'date_end': '2022-10-10', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data['results'][0]['id'], metering2.id)

        # param 'bucket_id'
        query = parse.urlencode(query={
            'date_start': '2022-10-01', 'date_end': '2022-10-10', 'bucket_id': 'bucket2'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data['results'][0]['id'], metering2.id)

        # param 'user_id'
        query = parse.urlencode(query={
            'date_start': '2022-10-01', 'date_end': '2022-10-10', 'user_id': user2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)

        # > 1 year
        query = parse.urlencode(query={
            'date_start': '2021-10-01', 'date_end': '2022-10-10'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='BadRequest', response=r)

        # param 'admin'
        query = parse.urlencode(query={
            'date_start': '2022-10-01', 'date_end': '2022-10-10', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(len(r.data["results"]), 0)

        self.user.set_federal_admin()
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 3)

        # param 'admin' 'user_id'
        query = parse.urlencode(query={
            'date_start': '2022-10-01', 'date_end': '2022-10-10', 'as-admin': '', 'user_id': user2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(len(r.data["results"]), 1)
        self.assertEqual(r.data['results'][0]['id'], metering3.id)

        # param odc 'admin'
        self.user.unset_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-10-01', 'date_end': '2022-10-10', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(len(r.data["results"]), 0)

        self.service2.users.add(self.user)
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 2)

        self.service2.org_data_center.add_admin_user(self.user)
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["results"]), 3)


class StatementStorageTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.user2 = get_or_create_user(username='user2')

        self.service = get_or_create_storage_service()
        self.service2 = ObjectsService(
            name='service2', org_data_center_id=self.service.org_data_center_id,
            endpoint_url='service2', username='', password=''
        )
        self.service2.save()

    def create_statement_storage(self):
        # user 2022-1-1 service
        u_st0 = DailyStatementObjectStorage(
            original_amount='1.11',
            trade_amount='1.11',
            payable_amount='1.11',
            payment_status=PaymentStatus.PAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=1),
            user_id=self.user.id,
            username=self.user.username
        )
        u_st0.save(force_insert=True)

        # user service2 2022-1-1
        u_st1 = DailyStatementObjectStorage(
            original_amount='2.22',
            trade_amount='0',
            payable_amount='2.22',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service2.id,
            date=date(year=2022, month=1, day=1),
            user_id=self.user.id,
            username=self.user.username
        )
        u_st1.save(force_insert=True)

        # user 2022-1-2 service
        u_st2 = DailyStatementObjectStorage(
            original_amount='3.33',
            trade_amount='0',
            payable_amount='3.33',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=2),
            user_id=self.user.id,
            username=self.user.username
        )
        u_st2.save(force_insert=True)

        # user2 service 2022-1-2
        u_st3 = DailyStatementObjectStorage(
            original_amount='4.44',
            trade_amount='0',
            payable_amount='4.44',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=2),
            user_id=self.user2.id,
            username=self.user2.username
        )
        u_st3.save(force_insert=True)

        return u_st0, u_st1, u_st2, u_st3

    def test_list_statement_storage(self):
        base_url = reverse('metering-api:statement-storage-list')
        # list user statement-storage
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'statements'], response.data)
        self.assertIsInstance(response.data['statements'], list)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['statements']), 0)
        # create statement server
        u_st0, u_st1, u_st2, u_st3 = self.create_statement_storage()
        # ------ list user -------
        # no params
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['statements']), 3)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "service", "date", "creation_time",
                           "user_id", "username"], response.data['statements'][0])
        self.assertEqual(response.data['statements'][0]['original_amount'], u_st2.original_amount)
        self.assertEqual(response.data['statements'][1]['original_amount'], u_st1.original_amount)
        self.assertEqual(response.data['statements'][2]['original_amount'], u_st0.original_amount)

        # date_start - date_end
        query = parse.urlencode(query={
            'date_start': '2022-01-02', 'date_end': '2022-01-02'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['statements']), 1)
        self.assertEqual(response.data['statements'][0]['user_id'], self.user.id)
        self.assertEqual(response.data['statements'][0]['user_id'], u_st2.user_id)
        self.assertEqual(response.data['statements'][0]['original_amount'], u_st2.original_amount)

        query = parse.urlencode(query={
            'date_start': '2022-01-01', 'date_end': '2022-01-02'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['statements']), 3)

        # payment_status
        query = parse.urlencode(query={
            'payment_status': PaymentStatus.PAID.value,
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['statements']), 1)
        self.assertEqual(response.data['statements'][0]['original_amount'], u_st0.original_amount)

        # date_start - date_end  && payment_status
        query = parse.urlencode(query={
            'date_start': '2022-01-01', 'date_end': '2022-01-02',
            'payment_status': PaymentStatus.UNPAID.value,

        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['statements']), 2)

    def test_detail_statement_storage(self):
        # not found
        url = reverse('metering-api:statement-storage-detail', kwargs={'id': '1234567891234567891234'})
        response = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=response)

        # create statement server
        u_st0, u_st1, u_st2, u_st3 = self.create_statement_storage()

        # user statement server detail
        metering1 = MeteringObjectStorage(
            original_amount=Decimal('2.22'),
            trade_amount=Decimal('0'),
            daily_statement_id=u_st0.id,
            service_id=self.service2.id,
            storage_bucket_id='bucket3',
            date=u_st0.date,
            user_id=self.user.id,
            username=self.user.username,
            storage=3.2345
        )
        metering1.save(force_insert=True)

        url = reverse('metering-api:statement-storage-detail', kwargs={'id': u_st0.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "service", "date", "creation_time",
                           "user_id", "username", "service", 'meterings'], response.data)
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['service'])
        self.assertIsInstance(response.data['meterings'], list)
        self.assertEqual(len(response.data['meterings']), 1)
        self.assertEqual(response.data['meterings'][0]['id'], metering1.id)

        self.assert_is_subdict_of(sub={
            "id": u_st0.id,
            "original_amount": u_st0.original_amount,
            "payable_amount": u_st0.payable_amount,
            "trade_amount": u_st0.trade_amount,
            "payment_status": u_st0.payment_status,
            "payment_history_id": u_st0.payment_history_id,
            "user_id": self.user.id,
            "username": self.user.username,
        }, d=response.data)
        self.assert_is_subdict_of(sub={
            "id": self.service.id,
            "name": self.service.name,
            "name_en": self.service.name_en,
            "service_type": self.service.service_type,
        }, d=response.data['service'])


class AdminMeteringServerTests(MyAPITestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='user1')
        self.user2 = get_or_create_user(username='user2')
        self.service1 = get_or_create_service()
        self.service2 = ServiceConfig(
            name='test2', org_data_center_id=self.service1.org_data_center_id, endpoint_url='test2',
            username='', password='', need_vpn=False
        )
        self.service2.save(force_insert=True)
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user1
        )
        self.vo.save(force_insert=True)

    def init_data(self):
        server1 = Server(
            id='server', ipv4='1.1.1.1', vcpus=1, ram=11, service_id=self.service1.id, creation_time=timezone.now(),
            user=self.user1, classification=Server.Classification.PERSONAL.value
        )
        server1.save(force_insert=True)
        server2 = ServerArchive(
            server_id='server2', ipv4='2.2.2.2', vcpus=2, ram=22, service_id=self.service2.id,
            user=self.user2, classification=Server.Classification.PERSONAL.value,
            creation_time=timezone.now(), deleted_time=timezone.now(),
            archive_type=ServerArchive.ArchiveType.ARCHIVE.value
        )
        server2.save(force_insert=True)
        server3 = Server(
            id='server3', ipv4='3.3.3.3', vcpus=3, ram=33, creation_time=timezone.now(), service_id=self.service1.id,
            user=self.user1, vo=self.vo, classification=Server.Classification.VO.value)
        server3.save(force_insert=True)

        # server1, 2023-02-10 - 2023-03-11
        start_date = date(year=2023, month=2, day=9)
        for i in range(30):
            start_date = start_date + timedelta(days=1)
            MeteringServer(
                service_id=server1.service_id, server_id=server1.id, date=start_date,
                user_id=server1.user_id, username=server1.user.username, owner_type=OwnerType.USER.value,
                original_amount=Decimal.from_float(i + 1), trade_amount=Decimal.from_float(i)
            ).save(force_insert=True)

        # server2, 2023-02-05 - 2023-03-06
        start_date = date(year=2023, month=2, day=4)
        for i in range(30):
            start_date = start_date + timedelta(days=1)
            MeteringServer(
                service_id=server2.service_id, server_id=server2.server_id, date=start_date,
                user_id=server2.user_id, username=server2.user.username, owner_type=OwnerType.USER.value,
                original_amount=Decimal.from_float(i + 6), trade_amount=Decimal.from_float(i + 1)
            ).save(force_insert=True)

        # server3, 2023-01-20 - 2023-02-18
        start_date = date(year=2023, month=1, day=19)
        for i in range(30):
            start_date = start_date + timedelta(days=1)
            MeteringServer(
                service_id=server3.service_id, server_id=server3.id, date=start_date,
                user_id=server3.user_id, username=server3.user.username,
                vo_id=server3.vo_id, owner_type=OwnerType.VO.value,
                original_amount=Decimal.from_float(3 * i + 6), trade_amount=Decimal.from_float(3 * i + 1)
            ).save(force_insert=True)

        return server1, server2, server3

    def test_metering_statistics(self):
        self.init_data()
        base_url = reverse('metering-api:admin-metering-server-statistics-list')

        # NotAuthenticated
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user1)

        # invalid date_start
        query = parse.urlencode(query={
            'date_start': '2022-02-31'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # invalid date_end
        query = parse.urlencode(query={
            'date_end': '2022-2-1'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # AccessDenied, user1 no permission of service1
        query = parse.urlencode(query={'service_id': self.service1.id})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user1.set_federal_admin()

        # --------- 2023-02-01 - 2023-02-28 ----------
        # service1(bucket1/3), date_start - date_end, order_by
        # server1 2023-02-10 - 02-28, 19 days
        total_original_amount1 = Decimal('0')  # 190
        total_trade_amount1 = Decimal('0')  # 171
        for i in range(19):
            total_original_amount1 += Decimal.from_float(i + 1)
            total_trade_amount1 += Decimal.from_float(i)

        # server3 2023-02-01 - 02-18, 18 days
        total_original_amount3 = Decimal('0')  # 1215
        total_trade_amount3 = Decimal('0')  # 1125
        for i in range(30 - 18, 30):
            total_original_amount3 += Decimal.from_float(3 * i + 6)
            total_trade_amount3 += Decimal.from_float(3 * i + 1)

        # server2 2023-02-05 - 02-28, 24 days
        total_original_amount2 = Decimal('0')  # 420
        total_trade_amount2 = Decimal('0')  # 300
        for i in range(0, 24):
            total_original_amount2 += Decimal.from_float(i + 6)
            total_trade_amount2 += Decimal.from_float(i + 1)

        query = parse.urlencode(query={
            'date_start': '2023-02-01', 'date_end': '2023-02-28',
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['total_original_amount'], Decimal.from_float(190 + 1215 + 420))
        self.assertEqual(r.data['total_postpaid_amount'], Decimal.from_float(171 + 1125 + 300))
        self.assertEqual(r.data["total_prepaid_amount"], Decimal('0.00'))
        self.assertEqual(r.data["total_server_count"], 3)
        self.assertEqual(r.data['user_original_amount'], Decimal.from_float(190 + 420))
        self.assertEqual(r.data['user_postpaid_amount'], Decimal.from_float(171 + 300))
        self.assertEqual(r.data['user_prepaid_amount'], Decimal('0.00'))
        self.assertEqual(r.data['user_server_count'], 2)
        self.assertEqual(r.data['vo_original_amount'], Decimal.from_float(1215))
        self.assertEqual(r.data['vo_postpaid_amount'], Decimal.from_float(1125))
        self.assertEqual(r.data['vo_prepaid_amount'], Decimal('0.00'))
        self.assertEqual(r.data['vo_server_count'], 1)

        query = parse.urlencode(query={
            'date_start': '2023-02-01', 'date_end': '2023-02-28', 'service_id': self.service1.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['total_original_amount'], Decimal.from_float(190 + 1215))
        self.assertEqual(r.data['total_postpaid_amount'], Decimal.from_float(171 + 1125))
        self.assertEqual(r.data["total_prepaid_amount"], Decimal('0.00'))
        self.assertEqual(r.data["total_server_count"], 2)
        self.assertEqual(r.data['user_original_amount'], Decimal.from_float(190))
        self.assertEqual(r.data['user_postpaid_amount'], Decimal.from_float(171))
        self.assertEqual(r.data["user_prepaid_amount"], Decimal('0.00'))
        self.assertEqual(r.data["user_server_count"], 1)
        self.assertEqual(r.data['vo_original_amount'], Decimal.from_float(1215))
        self.assertEqual(r.data['vo_postpaid_amount'], Decimal.from_float(1125))
        self.assertEqual(r.data["vo_prepaid_amount"], Decimal('0.00'))
        self.assertEqual(r.data["vo_server_count"], 1)

        query = parse.urlencode(query={
            'date_start': '2023-04-01',
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['total_original_amount'], Decimal.from_float(0))
        self.assertEqual(r.data['total_postpaid_amount'], Decimal.from_float(0))
        self.assertEqual(r.data["total_prepaid_amount"], Decimal('0.00'))
        self.assertEqual(r.data["total_server_count"], 0)
        self.assertEqual(r.data['user_original_amount'], Decimal('0.00'))
        self.assertEqual(r.data['user_postpaid_amount'], Decimal('0.00'))
        self.assertEqual(r.data["user_prepaid_amount"], Decimal('0.00'))
        self.assertEqual(r.data["user_server_count"], 0)
        self.assertEqual(r.data['vo_original_amount'], Decimal('0.00'))
        self.assertEqual(r.data['vo_postpaid_amount'], Decimal('0.00'))
        self.assertEqual(r.data["vo_prepaid_amount"], Decimal('0.00'))
        self.assertEqual(r.data["vo_server_count"], 0)


def create_disk_metering(
        service_id, disk_id, _date: date, pay_type,
        original_amount: Decimal, trade_amount: Decimal,
        owner_type: str, user_id, username: str, vo_id, vo_name, size_hours: float = 0
):
    metering = MeteringDisk(
        original_amount=original_amount,
        trade_amount=trade_amount,
        daily_statement_id='',
        service_id=service_id,
        disk_id=disk_id,
        date=_date,
        user_id=user_id,
        username=username,
        vo_id=vo_id,
        vo_name=vo_name,
        owner_type=owner_type,
        pay_type=pay_type,
        size_hours=size_hours
    )
    metering.save(force_insert=True)
    return metering


class MeteringDiskTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='lilei@cnic.cn')
        self.service = get_or_create_service()
        self.service2 = ServiceConfig(
            name='test2', org_data_center_id=self.service.org_data_center_id, endpoint_url='test2',
            username='', password='', need_vpn=False
        )
        self.service2.save(force_insert=True)
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user
        )
        self.vo.save()

    def test_list_metering(self):
        create_disk_metering(
            service_id=self.service.id, disk_id='disk1', _date=date(year=2022, month=2, day=16),
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('1.11'), trade_amount=Decimal('1.11'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service.id, disk_id='disk1', _date=date(year=2022, month=3, day=16),
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('2.22'), trade_amount=Decimal('0'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service.id, disk_id='disk2', _date=date(year=2022, month=2, day=8),
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('3.33'), trade_amount=Decimal('0'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id=self.vo.id, vo_name=self.vo.name
        )
        create_disk_metering(
            service_id=self.service.id, disk_id='disk2', _date=date(year=2022, month=3, day=8),
            pay_type=PayType.PREPAID.value,
            original_amount=Decimal('4.44'), trade_amount=Decimal('4.44'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id='vo1', vo_name='vo1 test'
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id='disk2', _date=date(year=2022, month=3, day=18),
            pay_type=PayType.PREPAID.value,
            original_amount=Decimal('5.55'), trade_amount=Decimal('5.55'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id='disk6', _date=date(year=2022, month=3, day=9),
            pay_type=PayType.PREPAID.value,
            original_amount=Decimal('6.66'), trade_amount=Decimal('6.66'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id=self.vo.id, vo_name=self.vo.name
        )

        # list user metering, default current month
        base_url = reverse('metering-api:metering-disk-list')
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 401)
        self.client.force_login(self.user)

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
            "id", "original_amount", "trade_amount",
            "daily_statement_id", "service_id", "disk_id", "date",
            "creation_time", "user_id", "vo_id", "owner_type",
            "size_hours", "pay_type", "username", "vo_name"
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

        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'disk_id': 'disk1'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0)

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

        # federal admin, 'disk1'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'disk_id': 'disk1'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)

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

    def test_detail_metering(self):
        user2 = get_or_create_user(username='tom@cnic.cn')
        disk1 = create_disk_metadata(
            service_id=self.service.id, azone_id='', disk_size=66, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.VO.value, user_id=None, vo_id=self.vo.id, creation_time=timezone.now()
        )
        m1_user = create_disk_metering(
            service_id=self.service.id, disk_id='disk1', _date=date(year=2022, month=2, day=16),
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('1.11'), trade_amount=Decimal('1.11'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        m2_vo1 = create_disk_metering(
            service_id=self.service.id, disk_id=disk1.id, _date=date(year=2022, month=2, day=8),
            pay_type=PayType.POSTPAID.value,
            original_amount=Decimal('3.33'), trade_amount=Decimal('0'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id=self.vo.id, vo_name=self.vo.name
        )

        self.client.logout()

        # detail user metering
        base_url = reverse('metering-api:metering-disk-detail', kwargs={'id': 'xxx'})
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 401)
        self.client.force_login(user2)

        base_url = reverse('metering-api:metering-disk-detail', kwargs={'id': 'xxx'})
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=404, code='NotFound', response=r)

        base_url = reverse('metering-api:metering-disk-detail', kwargs={'id': m1_user.id})
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        base_url = reverse('metering-api:metering-disk-detail', kwargs={'id': m2_vo1.id})
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.client.logout()
        self.client.force_login(self.user)

        base_url = reverse('metering-api:metering-disk-detail', kwargs={'id': m1_user.id})
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["id", "original_amount", "trade_amount", "daily_statement_id", "disk_id",
                           'date', 'creation_time', 'user_id', 'username', 'vo_id', 'vo_name', 'owner_type',
                           'size_hours', 'pay_type', 'disk'], r.data)
        self.assertKeysIn(["id", "remarks", "size", 'creation_time'], r.data['disk'])

        base_url = reverse('metering-api:metering-disk-detail', kwargs={'id': m2_vo1.id})
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["id", "original_amount", "trade_amount", "daily_statement_id", "disk_id",
                           'date', 'creation_time', 'user_id', 'username', 'vo_id', 'vo_name', 'owner_type',
                           'size_hours', 'pay_type', 'disk'], r.data)
        self.assertKeysIn(["id", "remarks", "size", 'creation_time'], r.data['disk'])
        self.assertEqual(r.data['disk']['size'], disk1.size)

    def test_aggregate_metering_by_disk(self):
        disk1 = create_disk_metadata(
            service_id=self.service.id, azone_id='', disk_size=11, pay_type=PayType.POSTPAID.value,
            classification=Disk.Classification.PERSONAL.value, user_id=self.user.id, vo_id=None,
            creation_time=timezone.now(), remarks='disk1 remarks'
        )
        disk2 = create_disk_metadata(
            service_id=self.service2.id, azone_id='', disk_size=22, pay_type=PayType.PREPAID.value,
            classification=Disk.Classification.VO.value, user_id=None, vo_id=self.vo.id, creation_time=timezone.now(),
            deleted=True, detached_time=timezone.now(), remarks='disk2 remarks'
        )
        disk3 = create_disk_metadata(
            service_id=None, azone_id='', disk_size=33, pay_type=PayType.POSTPAID.value,
            classification=Disk.Classification.VO.value, user_id=None, vo_id=self.vo.id, creation_time=timezone.now(),
            deleted=True, detached_time=timezone.now(), remarks='disk3 remarks'
        )

        create_disk_metering(
            service_id=self.service.id, disk_id=disk1.id, _date=date(year=2022, month=3, day=29),
            pay_type=PayType.POSTPAID.value, size_hours=5.1,
            original_amount=Decimal('1.11'), trade_amount=Decimal('1.1'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service.id, disk_id=disk1.id, _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=6,
            original_amount=Decimal('2.22'), trade_amount=Decimal('2.2'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service.id, disk_id=disk1.id, _date=date(year=2022, month=4, day=30),
            pay_type=PayType.POSTPAID.value, size_hours=6.1,
            original_amount=Decimal('3.33'), trade_amount=Decimal('3.3'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id=disk2.id, _date=date(year=2022, month=3, day=20),
            pay_type=PayType.POSTPAID.value, size_hours=7.0,
            original_amount=Decimal('4.44'), trade_amount=Decimal('4.4'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id=disk2.id, _date=date(year=2022, month=3, day=29),
            pay_type=PayType.POSTPAID.value, size_hours=8.0,
            original_amount=Decimal('5.55'), trade_amount=Decimal('5.5'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id=self.vo.id, vo_name=self.vo.name
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id=disk2.id, _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=9.0,
            original_amount=Decimal('6.66'), trade_amount=Decimal('6.6'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id='vo1', vo_name=self.vo.name
        )
        create_disk_metering(
            service_id=self.service.id, disk_id=disk3.id, _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=10.0,
            original_amount=Decimal('7.77'), trade_amount=Decimal('7.7'),
            owner_type=OwnerType.USER.value, user_id='user2', username='', vo_id='vo1', vo_name=''
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id=disk3.id, _date=date(year=2022, month=4, day=2),
            pay_type=PayType.POSTPAID.value, size_hours=10.1,
            original_amount=Decimal('8.88'), trade_amount=Decimal('8.8'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id='vo1', vo_name=''
        )

        base_url = reverse('metering-api:metering-disk-aggregation-by-disk')
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 401)
        self.client.force_login(self.user)

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
        self.assertKeysIn(['disk_id', 'total_size_hours', 'total_original_amount', 'total_trade_amount',
                           'service_name', 'disk'], r.data['results'][0])
        self.assertKeysIn(['id', 'size', 'remarks'], r.data['results'][0]['disk'])
        self.assertEqual(r.data['results'][0]['total_size_hours'], 5.1)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('1.11'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('1.1'))
        self.assertEqual(r.data['results'][0]['disk']['size'], 11)
        self.assertEqual(r.data['results'][1]['total_size_hours'], 7)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('4.44'))
        self.assertEqual(r.data['results'][1]['total_trade_amount'], Decimal('4.4'))
        self.assertEqual(r.data['results'][1]['disk']['size'], 22)
        self.assertEqual(r.data['results'][1]['disk']['remarks'], disk2.remarks)

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
        self.assertEqual(r.data['results'][0]['total_size_hours'], 8)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('5.5'))
        self.assertEqual(r.data['results'][0]['disk']['size'], 22)
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
        self.assertEqual(r.data['results'][0]['total_size_hours'], 5.1)

        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['total_size_hours'], 11.1)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal(f'{(1.11+2.22):.2f}'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal(f'{(1.1+2.2):2f}'))
        self.assertEqual(r.data['results'][1]['total_size_hours'], 10)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('7.77'))
        self.assertEqual(r.data['results'][1]['total_trade_amount'], Decimal('7.7'))

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
        self.assertEqual(r.data['results'][0]['total_size_hours'], 10)
        self.assertEqual(r.data['results'][0]['disk']['size'], 33)

        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '',
            'user_id': self.user.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['total_size_hours'], 11.1)
        self.assertEqual(r.data['results'][0]['disk']['size'], 11)

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
        self.assertEqual(r.data['results'][0]['total_size_hours'], 8)

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
        self.assertEqual(r.data['results'][0]['total_size_hours'], 8)
        self.assertEqual(r.data['results'][0]['disk']['size'], 22)

        # federal admin, service_id
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['total_size_hours'], 11.1)
        self.assertEqual(r.data['results'][1]['total_size_hours'], 10)

        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['total_size_hours'], 24)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal(f'{(4.44 + 5.55 + 6.66):.2f}'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal(f'{(4.4 + 5.5 + 6.6):2f}'))
        self.assertEqual(r.data['results'][0]['disk']['size'], 22)
        self.assertEqual(r.data['results'][1]['total_size_hours'], 10.1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('8.88'))
        self.assertEqual(r.data['results'][1]['total_trade_amount'], Decimal('8.8'))
        self.assertEqual(r.data['results'][1]['disk']['size'], 33)

        # federal admin, user_id
        query = parse.urlencode(query={
            'date_start': '2022-04-01', 'date_end': '2022-04-30', 'as-admin': '', 'user_id': 'user2'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['total_size_hours'], 10)

        # federal admin, user_id, service_id
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '', 'user_id': self.user.id,
            'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['total_size_hours'], 11.1)

        # federal admin, vo_id, service_id
        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-02', 'as-admin': '', 'vo_id': 'vo1',
            'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['total_size_hours'], 9)
        self.assertEqual(r.data['results'][1]['total_size_hours'], 10.1)

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

        create_disk_metering(
            service_id=self.service.id, disk_id='disk1', _date=date(year=2022, month=3, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=111,
            original_amount=Decimal('1.11'), trade_amount=Decimal('1.00'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service.id, disk_id='disk1', _date=date(year=2022, month=3, day=2),
            pay_type=PayType.POSTPAID.value, size_hours=222,
            original_amount=Decimal('2.22'), trade_amount=Decimal('2.00'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id='disk1', _date=date(year=2022, month=3, day=3),
            pay_type=PayType.POSTPAID.value, size_hours=333,
            original_amount=Decimal('3.33'), trade_amount=Decimal('3.00'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id='disk2', _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=444,
            original_amount=Decimal('4.44'), trade_amount=Decimal('4.00'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username=self.user.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service.id, disk_id='disk3', _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=555,
            original_amount=Decimal('5.55'), trade_amount=Decimal('5.00'),
            owner_type=OwnerType.USER.value, user_id=user2.id, username=user2.username, vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id='disk4', _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=666,
            original_amount=Decimal('6.66'), trade_amount=Decimal('6.00'),
            owner_type=OwnerType.USER.value, user_id=user3.id, username=user3.username, vo_id='', vo_name=''
        )

        create_disk_metering(
            service_id=self.service2.id, disk_id='disk5', _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=777,
            original_amount=Decimal('7.77'), trade_amount=Decimal('7.00'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id='vo1', vo_name=''
        )

        base_url = reverse('metering-api:metering-disk-aggregation-by-user')

        # no param 'as-admin'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 401)
        self.client.force_login(self.user)
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
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('7.77'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('7'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
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
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('7.77'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('7'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
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
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('11.10'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][1]['user']['id'], user2.id)
        self.assertEqual(r.data['results'][2]['total_disk'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][2]['user']['id'], user3.id)

        # federal admin, list all, order_by
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '',
            'order_by': '-total_original_amount'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('11.10'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('10.00'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['user']['id'], user3.id)
        self.assertEqual(r.data['results'][2]['total_disk'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][2]['user']['id'], user2.id)

        # federal admin, service_id
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['total_disk'], 1)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('3.33'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][1]['user']['id'], user2.id)

        query = parse.urlencode(query={
            'date_start': '2022-04-01', 'as-admin': '', 'service_id': self.service2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['total_disk'], 1)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('4.44'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('4.00'))
        self.assertEqual(r.data['results'][0]['user']['id'], self.user.id)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['total_trade_amount'], Decimal('6.00'))
        self.assertEqual(r.data['results'][1]['user']['id'], user3.id)

        # param 'download'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'download': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertIs(r.streaming, True)
        self.assertEqual(r.status_code, 200)

    def test_aggregate_metering_by_vo(self):
        owner1 = UserProfile(id='owner1', username='owner1')
        owner1.save(force_insert=True)
        owner2 = UserProfile(id='owner2', username='owner2')
        owner2.save(force_insert=True)
        owner3 = UserProfile(id='owner3', username='owner3')
        owner3.save(force_insert=True)

        vo1 = VirtualOrganization(id='vo1', name='name1', company='company1', owner_id=owner1.id)
        vo1.save(force_insert=True)
        vo2 = VirtualOrganization(id='vo2', name='name2', company='company2', owner_id=owner2.id)
        vo2.save(force_insert=True)
        vo3 = VirtualOrganization(id='vo3', name='name3', company='company3', owner_id=owner3.id)
        vo3.save(force_insert=True)

        create_disk_metering(
            service_id=self.service.id, disk_id='disk1', _date=date(year=2022, month=3, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=111,
            original_amount=Decimal('1.11'), trade_amount=Decimal('1.00'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id=vo1.id, vo_name=vo1.name
        )
        create_disk_metering(
            service_id=self.service.id, disk_id='disk1', _date=date(year=2022, month=3, day=2),
            pay_type=PayType.POSTPAID.value, size_hours=222,
            original_amount=Decimal('2.22'), trade_amount=Decimal('2.00'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id=vo1.id, vo_name=vo1.name
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id='disk1', _date=date(year=2022, month=3, day=3),
            pay_type=PayType.POSTPAID.value, size_hours=333,
            original_amount=Decimal('3.33'), trade_amount=Decimal('3.00'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id=vo1.id, vo_name=vo1.name
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id='disk2', _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=444,
            original_amount=Decimal('4.44'), trade_amount=Decimal('4.00'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id=vo1.id, vo_name=vo1.name
        )
        create_disk_metering(
            service_id=self.service.id, disk_id='disk3', _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=555,
            original_amount=Decimal('5.55'), trade_amount=Decimal('5.00'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id=vo2.id, vo_name=vo2.name
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id='disk4', _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=666,
            original_amount=Decimal('6.66'), trade_amount=Decimal('6.00'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id=vo3.id, vo_name=vo3.name
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id='disk5', _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=777,
            original_amount=Decimal('7.77'), trade_amount=Decimal('7.00'),
            owner_type=OwnerType.USER.value, user_id=self.user.id, username='', vo_id='', vo_name=''
        )

        base_url = reverse('metering-api:metering-disk-aggregation-by-vo')

        # no param 'as-admin'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 401)
        self.client.force_login(self.user)
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
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('7.77'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('7'))
        self.assertEqual(r.data['results'][0]['vo']['id'], vo1.id)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
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
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('7.77'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('7'))
        self.assertEqual(r.data['results'][0]['vo']['id'], vo1.id)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
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
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('11.10'))
        self.assertEqual(r.data['results'][0]['vo']['id'], vo1.id)
        self.assertEqual(r.data['results'][0]['vo']['company'], vo1.company)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][1]['vo']['id'], vo2.id)
        self.assertEqual(r.data['results'][1]['vo']['company'], vo2.company)
        self.assertEqual(r.data['results'][2]['total_disk'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][2]['vo']['id'], vo3.id)
        self.assertEqual(r.data['results'][2]['vo']['company'], vo3.company)

        # federal admin, list all, order_by
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '',
            'order_by': '-total_original_amount'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('11.10'))
        self.assertEqual(r.data['results'][0]['vo']['id'], vo1.id)
        self.assertEqual(r.data['results'][0]['vo']['company'], vo1.company)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['vo']['id'], vo3.id)
        self.assertEqual(r.data['results'][1]['vo']['company'], vo3.company)
        self.assertEqual(r.data['results'][2]['total_disk'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][2]['vo']['id'], vo2.id)
        self.assertEqual(r.data['results'][2]['vo']['company'], vo2.company)

        # federal admin, service_id
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'service_id': self.service.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['total_disk'], 1)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('3.33'))
        self.assertEqual(r.data['results'][0]['vo']['id'], vo1.id)
        self.assertEqual(r.data['results'][0]['vo']['name'], vo1.name)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
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
        self.assertEqual(r.data['results'][0]['total_disk'], 1)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('4.44'))
        self.assertEqual(r.data['results'][0]['vo']['id'], vo1.id)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][1]['vo']['id'], vo3.id)

        # param 'download'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'download': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertIs(r.streaming, True)
        self.assertEqual(r.status_code, 200)

    def test_aggregate_metering_by_service(self):
        service3 = ServiceConfig(id='service3', name='name3')
        service3.save(force_insert=True)
        create_disk_metering(
            service_id=self.service.id, disk_id='disk1', _date=date(year=2022, month=3, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=111,
            original_amount=Decimal('1.11'), trade_amount=Decimal('1.00'),
            owner_type=OwnerType.VO.value, user_id='', username='', vo_id='vo1', vo_name=''
        )
        create_disk_metering(
            service_id=self.service.id, disk_id='disk1', _date=date(year=2022, month=3, day=2),
            pay_type=PayType.POSTPAID.value, size_hours=222,
            original_amount=Decimal('2.22'), trade_amount=Decimal('2.00'),
            owner_type=OwnerType.USER.value, user_id='user1', username='', vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service.id, disk_id='disk2', _date=date(year=2022, month=3, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=333,
            original_amount=Decimal('3.33'), trade_amount=Decimal('3.00'),
            owner_type=OwnerType.USER.value, user_id='user1', username='', vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=self.service2.id, disk_id='disk3', _date=date(year=2022, month=3, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=444,
            original_amount=Decimal('4.44'), trade_amount=Decimal('4.00'),
            owner_type=OwnerType.USER.value, user_id='user2', username='', vo_id='', vo_name=''
        )
        create_disk_metering(
            service_id=service3.id, disk_id='disk3', _date=date(year=2022, month=4, day=1),
            pay_type=PayType.POSTPAID.value, size_hours=555,
            original_amount=Decimal('5.55'), trade_amount=Decimal('5.00'),
            owner_type=OwnerType.USER.value, user_id='user2', username='', vo_id='', vo_name=''
        )

        base_url = reverse('metering-api:metering-disk-aggregation-by-service')

        # no param 'as-admin'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 401)
        self.client.force_login(self.user)
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
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
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
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][0]['total_trade_amount'], Decimal('6'))
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
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
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][0]['service']['id'], self.service.id)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('4.44'))
        self.assertEqual(r.data['results'][1]['service']['id'], self.service2.id)
        self.assertEqual(r.data['results'][2]['total_disk'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][2]['service']['id'], service3.id)
        self.assertEqual(r.data['results'][2]['service']['name'], service3.name)

        # federal admin, list all, order_by
        self.user.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '',
            'order_by': '-total_original_amount'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 3)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][0]['total_disk'], 2)
        self.assertEqual(r.data['results'][0]['total_original_amount'], Decimal('6.66'))
        self.assertEqual(r.data['results'][0]['service']['id'], self.service.id)
        self.assertEqual(r.data['results'][1]['total_disk'], 1)
        self.assertEqual(r.data['results'][1]['total_original_amount'], Decimal('5.55'))
        self.assertEqual(r.data['results'][1]['service']['id'], service3.id)
        self.assertEqual(r.data['results'][1]['service']['name'], service3.name)
        self.assertEqual(r.data['results'][2]['total_disk'], 1)
        self.assertEqual(r.data['results'][2]['total_original_amount'], Decimal('4.44'))
        self.assertEqual(r.data['results'][2]['service']['id'], self.service2.id)

        # param 'download'
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-01', 'as-admin': '', 'download': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertIs(r.streaming, True)
        self.assertEqual(r.status_code, 200)


class StatementDiskTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.user2 = get_or_create_user(username='user2')

        self.vo = VirtualOrganization(
            id='test vo id', name='test vo', owner=self.user
        )
        self.vo.save()

        self.service = get_or_create_service()
        self.service2 = ServiceConfig(
            name='test2', org_data_center_id=self.service.org_data_center_id, endpoint_url='test2',
            username='', password='', need_vpn=False
        )
        self.service2.save()

    def create_statement_disk(self):
        # ## user
        # # user
        # 2022-1-1 service
        u_st0 = DailyStatementDisk(
            original_amount='1.11',
            payable_amount='1.11',
            trade_amount='1.11',
            payment_status=PaymentStatus.PAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=1),
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
        )
        u_st0.save(force_insert=True)

        # 2022-1-1 service2
        u_st1 = DailyStatementDisk(
            original_amount='2.22',
            payable_amount='2.22',
            trade_amount='0',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service2.id,
            date=date(year=2022, month=1, day=1),
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
        )
        u_st1.save(force_insert=True)

        # 2022-1-2 service1
        u_st2 = DailyStatementDisk(
            original_amount='3.33',
            payable_amount='3.33',
            trade_amount='0',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=2),
            user_id=self.user.id,
            username=self.user.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
        )
        u_st2.save(force_insert=True)

        # # user2
        u_st3 = DailyStatementDisk(
            original_amount='4.44',
            payable_amount='4.44',
            trade_amount='0',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=2),
            user_id=self.user2.id,
            username=self.user2.username,
            vo_id='',
            vo_name='',
            owner_type=OwnerType.USER.value,
        )
        u_st3.save(force_insert=True)

        # ## vo
        # 2022-1-1 service
        v_st0 = DailyStatementDisk(
            original_amount='5.55',
            payable_amount='5.55',
            trade_amount='5.55',
            payment_status=PaymentStatus.PAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=1),
            user_id='',
            username='',
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
        )
        v_st0.save(force_insert=True)

        # 2022-1-1 service2
        v_st1 = DailyStatementDisk(
            original_amount='6.66',
            payable_amount='6.66',
            trade_amount='0',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service2.id,
            date=date(year=2022, month=1, day=1),
            user_id='',
            username='',
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
        )
        v_st1.save(force_insert=True)

        # 2022-1-2 service1
        v_st2 = DailyStatementDisk(
            original_amount='7.77',
            payable_amount='7.77',
            trade_amount='0',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            service_id=self.service.id,
            date=date(year=2022, month=1, day=2),
            user_id='',
            username='',
            vo_id=self.vo.id,
            vo_name=self.vo.name,
            owner_type=OwnerType.VO.value,
        )
        v_st2.save(force_insert=True)

        return u_st0, u_st1, u_st2, u_st3, v_st0, v_st1, v_st2

    def test_list_statement_disk(self):
        base_url = reverse('metering-api:statement-disk-list')

        # list user statement-disk
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'statements'], response.data)
        self.assertIsInstance(response.data['statements'], list)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['statements']), 0)

        # list vo statement-disk
        query = parse.urlencode(query={
            'vo_id': self.vo.id
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'statements'], response.data)
        self.assertIsInstance(response.data['statements'], list)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['statements']), 0)

        # create statement disk
        u_st0, u_st1, u_st2, u_st3, v_st0, v_st1, v_st2 = self.create_statement_disk()

        # ------ list user -------
        # no params
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['statements']), 3)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "service", "date", "creation_time",
                           "user_id", "username", "vo_id", "vo_name", "owner_type"], response.data['statements'][0])

        self.assertEqual(response.data['statements'][0]['original_amount'], u_st2.original_amount)
        self.assertEqual(response.data['statements'][1]['original_amount'], u_st1.original_amount)
        self.assertEqual(response.data['statements'][2]['original_amount'], u_st0.original_amount)

        # date_start - date_end
        query = parse.urlencode(query={
            'date_start': '2022-01-02', 'time_end': '2022-01-02'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['statements']), 1)
        self.assertEqual(response.data['statements'][0]['user_id'], self.user.id)
        self.assertEqual(response.data['statements'][0]['user_id'], u_st2.user_id)
        self.assertEqual(response.data['statements'][0]['original_amount'], u_st2.original_amount)

        query = parse.urlencode(query={
            'date_start': '2022-01-01', 'time_end': '2022-01-02'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['statements']), 3)

        # payment_status
        query = parse.urlencode(query={
            'payment_status': PaymentStatus.PAID.value,
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['statements']), 1)
        self.assertEqual(response.data['statements'][0]['original_amount'], u_st0.original_amount)

        # date_start - date_end  && payment_status
        query = parse.urlencode(query={
            'date_start': '2022-01-01', 'time_end': '2022-01-02',
            'payment_status': PaymentStatus.UNPAID.value,

        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['statements']), 2)

        # ---- list vo ------
        query = parse.urlencode(query={
            'vo_id': self.vo.id
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['statements']), 3)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "service", "date", "creation_time",
                           "user_id", "username", "vo_id", "vo_name", "owner_type"], response.data['statements'][0])
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['statements'][0]['service'])
        self.assertEqual(response.data['statements'][0]['original_amount'], v_st2.original_amount)
        self.assertEqual(response.data['statements'][1]['original_amount'], v_st1.original_amount)
        self.assertEqual(response.data['statements'][2]['original_amount'], v_st0.original_amount)

        # date_start - date_end
        query = parse.urlencode(query={
            'vo_id': self.vo.id,
            'date_start': '2022-01-02', 'time_end': '2022-01-02',
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['statements']), 1)
        self.assertEqual(response.data['statements'][0]['vo_id'], self.vo.id)
        self.assertEqual(response.data['statements'][0]['vo_id'], v_st2.vo_id)
        self.assertEqual(response.data['statements'][0]['original_amount'], v_st2.original_amount)

        query = parse.urlencode(query={
            'vo_id': self.vo.id,
            'date_start': '2022-01-01', 'time_end': '2022-01-02'
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['statements']), 3)

        # payment_status
        query = parse.urlencode(query={
            'vo_id': self.vo.id,
            'payment_status': PaymentStatus.PAID.value,
        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['statements']), 1)
        self.assertEqual(response.data['statements'][0]['original_amount'], v_st0.original_amount)

        # date_start - date_end  && payment_status
        query = parse.urlencode(query={
            'vo_id': self.vo.id,
            'date_start': '2022-01-01', 'time_end': '2022-01-02',
            'payment_status': PaymentStatus.UNPAID.value,

        })
        response = self.client.get(f'{base_url}?{query}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['statements']), 2)

    def test_detail_statement_disk(self):
        # not found
        url = reverse('order-api:order-detail', kwargs={'id': '1234567891234567891234'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

        # create statement disk
        u_st0, u_st1, u_st2, u_st3, v_st0, v_st1, v_st2 = self.create_statement_disk()

        # user statement disk detail
        url = reverse('metering-api:statement-disk-detail', kwargs={'id': u_st0.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "service", "date", "creation_time",
                           "user_id", "username", "vo_id", "vo_name", "owner_type", "service"], response.data)
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['service'])

        self.assert_is_subdict_of(sub={
            "id": u_st0.id,
            "original_amount": u_st0.original_amount,
            "payable_amount": u_st0.payable_amount,
            "trade_amount": u_st0.trade_amount,
            "payment_status": u_st0.payment_status,
            "payment_history_id": u_st0.payment_history_id,
            "user_id": self.user.id,
            "username": self.user.username,
            "vo_id": '',
            "vo_name": '',
            "owner_type": OwnerType.USER.value,
        }, d=response.data)
        self.assert_is_subdict_of(sub={
            "id": self.service.id,
            "name": self.service.name,
            "name_en": self.service.name_en,
            "service_type": self.service.service_type,
        }, d=response.data['service'])

        # vo statement disk detail
        url = reverse('metering-api:statement-disk-detail', kwargs={'id': v_st0.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "service", "date", "creation_time",
                           "user_id", "username", "vo_id", "vo_name", "owner_type", "service",
                           'meterings'], response.data)
        self.assertIsInstance(response.data['meterings'], list)
        self.assertKeysIn(["id", "name", "name_en", "service_type"], response.data['service'])
        self.assertEqual(response.data['original_amount'], v_st0.original_amount)
        self.assertEqual(response.data['payable_amount'], v_st0.payable_amount)
        self.assertEqual(response.data['trade_amount'], v_st0.trade_amount)
        self.assertEqual(response.data['payment_status'], v_st0.payment_status)
        self.assertEqual(response.data['service_id'], v_st0.service_id)
        self.assertEqual(response.data['payment_history_id'], v_st0.payment_history_id)
        self.assertEqual(response.data['user_id'], '')
        self.assertEqual(response.data['username'], '')
        self.assertEqual(response.data['vo_id'], self.vo.id)
        self.assertEqual(response.data['vo_name'], self.vo.name)
        self.assertEqual(response.data['owner_type'], OwnerType.VO.value)

        # user2 no vo permission test
        self.client.logout()
        self.client.force_login(user=self.user2)
        url = reverse('metering-api:statement-disk-detail', kwargs={'id': v_st0.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        url = reverse('metering-api:statement-disk-detail', kwargs={'id': v_st1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
