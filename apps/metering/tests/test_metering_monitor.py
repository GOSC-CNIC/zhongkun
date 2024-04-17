from decimal import Decimal
from urllib import parse
from datetime import date

from django.urls import reverse
from django.utils import timezone

from utils.test import get_or_create_user, MyAPITestCase
from apps.metering.models import MeteringMonitorWebsite, DailyStatementMonitorWebsite, PaymentStatus


def create_site_metering(
        date_, website_id: str, website_name: str, user_id, username: str, hours: int, tamper_count: int,
        trade_amount: Decimal, original_amount: Decimal,
        creation_time=None, daily_statement_id: str = ''):
    metering = MeteringMonitorWebsite(
        website_id=website_id,
        website_name=website_name,
        date=date_,
        hours=hours,
        detection_count=0,
        tamper_resistant_count=tamper_count,
        security_count=0,
        user_id=user_id,
        username=username,
        creation_time=creation_time if creation_time else timezone.now(),
        trade_amount=trade_amount,
        original_amount=original_amount,
        daily_statement_id=daily_statement_id,
    )
    metering.save(force_insert=True)
    return metering


class MeteringMonitorSiteTests(MyAPITestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='user1')
        self.user2 = get_or_create_user(username='user2')

    def test_list_metering(self):
        m1_u1 = create_site_metering(
            date_=date(year=2022, month=2, day=16),
            website_id='website_id1',
            website_name='website_name1',
            user_id=self.user1.id,
            username=self.user1.username,
            hours=11,
            tamper_count=1,
            original_amount=Decimal('1.11'),
            trade_amount=Decimal('1.11'),
        )
        m2_u1 = create_site_metering(
            date_=date(year=2022, month=3, day=16),
            website_id='website_id2',
            website_name='website_name2',
            user_id=self.user1.id,
            username=self.user1.username,
            hours=22,
            tamper_count=2,
            original_amount=Decimal('2.22'),
            trade_amount=Decimal('2.22'),
        )
        m3_u2 = create_site_metering(
            date_=date(year=2022, month=2, day=8),
            website_id='website_id3',
            website_name='website_name3',
            user_id=self.user2.id,
            username=self.user2.username,
            hours=33,
            tamper_count=3,
            original_amount=Decimal('3.33'),
            trade_amount=Decimal('3.33'),
        )
        m4_u2 = create_site_metering(
            date_=date(year=2022, month=3, day=8),
            website_id='website_id4',
            website_name='website_name4',
            user_id=self.user2.id,
            username=self.user2.username,
            hours=44,
            tamper_count=4,
            original_amount=Decimal('4.44'),
            trade_amount=Decimal('4.4'),
        )
        m5_u1 = create_site_metering(
            date_=date(year=2022, month=3, day=18),
            website_id='website_id5',
            website_name='website_name5',
            user_id=self.user1.id,
            username=self.user1.username,
            hours=55,
            tamper_count=5,
            original_amount=Decimal('5.55'),
            trade_amount=Decimal('5.55'),
        )
        m6_u1 = create_site_metering(
            date_=date(year=2022, month=3, day=9),
            website_id='website_id6',
            website_name='website_name6',
            user_id=self.user1.id,
            username=self.user1.username,
            hours=66,
            tamper_count=6,
            original_amount=Decimal('6.66'),
            trade_amount=Decimal('6.66'),
        )

        base_url = reverse('metering-api:metering-monitor-site-list')
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # list user1 metering, default current month
        self.client.force_login(self.user1)
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", "results"], r.data)
        self.assertEqual(r.data["count"], 0)
        self.assertEqual(len(r.data['results']), 0)

        # list user1 metering, date_start - date_end
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["count", "page_num", "page_size", "results"], r.data)
        self.assertEqual(r.data["count"], 4)
        self.assertEqual(len(r.data['results']), 4)
        self.assertKeysIn([
            "id", "original_amount", "trade_amount",
            "daily_statement_id", "website_id", "website_name", "date",
            "creation_time", "user_id", "username", "hours", "tamper_resistant_count"
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

        # list user1 metering, date_start date_end timedelta less than one year
        query = parse.urlencode(query={
            'date_start': '2021-02-01', 'date_end': '2022-02-02'
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 400)

        # list user1 metering, query page_size
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'page_size': 1
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 4)
        self.assertEqual(r.data["page_size"], 1)
        self.assertEqual(len(r.data['results']), 1)

        # no permission
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 403)

        # federal admin， list all
        self.user1.set_federal_admin()
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': ''
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 6)
        self.assertEqual(len(r.data['results']), 6)

        # federal admin, user_id
        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'user_id': self.user2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 2)
        self.assertEqual(len(r.data['results']), 2)

        query = parse.urlencode(query={
            'date_start': '2022-02-01', 'date_end': '2022-04-06', 'as-admin': '', 'user_id': self.user1.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 4)
        self.assertEqual(len(r.data['results']), 4)

        query = parse.urlencode(query={
            'date_start': '2022-03-01', 'date_end': '2022-04-06', 'as-admin': '', 'user_id': self.user2.id
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["count"], 1)
        self.assertEqual(len(r.data['results']), 1)
        item = r.data['results'][0]
        self.assertEqual(m4_u2.website_id, item['website_id'])
        self.assertEqual(m4_u2.website_name, item['website_name'])
        self.assertEqual(m4_u2.date, date.fromisoformat(item['date']))
        self.assertEqual('4.44', item['original_amount'])
        self.assertEqual('4.40', item['trade_amount'])
        self.assertEqual(44, item['hours'])
        self.assertEqual(4, item['tamper_resistant_count'])


class StatementMonitorSiteTests(MyAPITestCase):
    def setUp(self):
        self.user1 = get_or_create_user(username='user1')
        self.user2 = get_or_create_user(username='user2')

    def create_statement_site(self):
        # user 2022-1-1 service
        u_st0 = DailyStatementMonitorWebsite(
            original_amount='1.11',
            trade_amount='1.11',
            payable_amount='1.11',
            payment_status=PaymentStatus.PAID.value,
            payment_history_id='',
            date=date(year=2022, month=1, day=1),
            user_id=self.user1.id,
            username=self.user1.username
        )
        u_st0.save(force_insert=True)

        # user service2 2022-1-1
        u_st1 = DailyStatementMonitorWebsite(
            original_amount='2.22',
            trade_amount='0',
            payable_amount='2.22',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            date=date(year=2022, month=1, day=1),
            user_id=self.user1.id,
            username=self.user1.username
        )
        u_st1.save(force_insert=True)

        # user 2022-1-2 service
        u_st2 = DailyStatementMonitorWebsite(
            original_amount='3.33',
            trade_amount='0',
            payable_amount='3.33',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            date=date(year=2022, month=1, day=2),
            user_id=self.user1.id,
            username=self.user1.username
        )
        u_st2.save(force_insert=True)

        # user2 service 2022-1-2
        u_st3 = DailyStatementMonitorWebsite(
            original_amount='4.44',
            trade_amount='0',
            payable_amount='4.44',
            payment_status=PaymentStatus.UNPAID.value,
            payment_history_id='',
            date=date(year=2022, month=1, day=2),
            user_id=self.user2.id,
            username=self.user2.username
        )
        u_st3.save(force_insert=True)

        return u_st0, u_st1, u_st2, u_st3

    def test_list_statement(self):
        base_url = reverse('metering-api:statement-monitor-site-list')
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # list user1 statement-storage
        self.client.force_login(self.user1)
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(['count', 'page_num', 'page_size', 'statements'], response.data)
        self.assertIsInstance(response.data['statements'], list)
        self.assertEqual(response.data['count'], 0)
        self.assertEqual(len(response.data['statements']), 0)
        # create statement
        u_st0, u_st1, u_st2, u_st3 = self.create_statement_site()
        # ------ list user -------
        # no params
        response = self.client.get(base_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(len(response.data['statements']), 3)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "date", "creation_time",
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
        self.assertEqual(response.data['statements'][0]['user_id'], self.user1.id)
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
        url = reverse('metering-api:statement-monitor-site-detail', kwargs={'id': '1234567891234567891234'})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        # list user1 statement-storage
        self.client.force_login(self.user1)
        # not found
        r = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='TargetNotExist', response=r)

        # create statement server
        u_st0, u_st1, u_st2, u_st3 = self.create_statement_site()

        # user statement detail
        metering1 = create_site_metering(
            date_=u_st0.date,
            website_id='website_id1',
            website_name='website_name1',
            user_id=self.user1.id,
            username=self.user1.username,
            hours=11,
            tamper_count=1,
            original_amount=Decimal('2.22'),
            trade_amount=Decimal('0'),
            daily_statement_id=u_st0.id
        )

        url = reverse('metering-api:statement-monitor-site-detail', kwargs={'id': u_st0.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertKeysIn(["id", "original_amount", "payable_amount", "trade_amount",
                           "payment_status", "payment_history_id", "date", "creation_time",
                           "user_id", "username", 'meterings'], response.data)
        self.assertIsInstance(response.data['meterings'], list)
        self.assertEqual(len(response.data['meterings']), 1)
        self.assertEqual(response.data['meterings'][0]['id'], metering1.id)
        self.assertKeysIn([
            "id", "original_amount", "trade_amount",
            "daily_statement_id", "website_id", "website_name", "date",
            "creation_time", "user_id", "username", "hours", "tamper_resistant_count"
        ], response.data['meterings'][0])
        self.assert_is_subdict_of(sub={
            "id": u_st0.id,
            "original_amount": u_st0.original_amount,
            "payable_amount": u_st0.payable_amount,
            "trade_amount": u_st0.trade_amount,
            "payment_status": u_st0.payment_status,
            "payment_history_id": u_st0.payment_history_id,
            "user_id": self.user1.id,
            "username": self.user1.username,
        }, d=response.data)
