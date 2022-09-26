from urllib import parse

from django.urls import reverse

from utils.test import get_or_create_user
from ticket.models import Ticket
from . import MyAPITestCase


class TicketTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='lilei@xx.com')
        self.user2 = get_or_create_user(username='tom@xx.com')

    def test_create_ticket(self):
        url = reverse('api:support-ticket-list')
        r = self.client.post(url, data={
            'title': 'test 标题', 'description': '这里是问题的描述，不能少于10个字符',
            'service_type': Ticket.ServiceType.SERVER.value, 'contact': ''
        })
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.post(url, data={
            'title': 'test 标题', 'description': '这里是问题的描述，不能少于10个字符',
            'service_type': Ticket.ServiceType.SERVER.value, 'contact': ''
        })

        self.assertErrorResponse(status_code=400, code='InvalidTitle', response=r)
        r = self.client.post(url, data={
            'title': 'test 标题, 不能少于10个字符', 'description': '少于10个字符',
            'service_type': Ticket.ServiceType.SERVER.value, 'contact': ''
        })
        self.assertErrorResponse(status_code=400, code='InvalidDescription', response=r)

        r = self.client.post(url, data={
            'title': 'test 标题, 不能少于10个字符', 'description': '这里是问题的描述，不少于10个字符',
            'service_type': 'sss', 'contact': ''
        })
        self.assertErrorResponse(status_code=400, code='InvalidServiceType', response=r)

        # ok
        data = {
            'title': 'test 标题, 不能少于10个字符', 'description': '这里是问题的描述，不少于10个字符',
            'service_type': Ticket.ServiceType.SERVER.value, 'contact': 'test'
        }
        r = self.client.post(url, data=data)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'title', 'description', 'status', 'service_type', 'severity', 'submit_time', 'modified_time',
            'contact', 'resolution', 'submitter', 'assigned_to'
        ], container=r.data)
        self.assertKeysIn(keys=['id', 'username'], container=r.data['submitter'])
        sub = {
            'status': Ticket.Status.OPEN.value,
            'severity': Ticket.Severity.NORMAL.value,
            'assigned_to': None,
            'submitter': {'id': self.user.id, 'username': self.user.username}
        }
        sub.update(data)
        self.assert_is_subdict_of(sub=sub, d=r.data)

        # TooManyTicket
        for i in range(2, 7):
            data = {
                'title': 'test 标题, 不能少于10个字符', 'description': '这里是问题的描述，不少于10个字符',
                'service_type': Ticket.ServiceType.SERVER.value, 'contact': 'test'
            }
            r = self.client.post(url, data=data)
            if i < 6:
                self.assertEqual(r.status_code, 200)
            else:
                self.assertErrorResponse(status_code=409, code='TooManyTicket', response=r)

    def test_list_tickets(self):
        ticket1_user = Ticket(
            title='工单1',
            description='工单1问题描述',
            service_type=Ticket.ServiceType.BILL.value,
            contact='',
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user,
            username=self.user.username
        )
        ticket1_user.save(force_insert=True)
        ticket2_user = Ticket(
            title='工单2',
            description='工单2问题描述',
            service_type=Ticket.ServiceType.SERVER.value,
            contact='',
            status=Ticket.Status.REOPENED.value,
            severity=Ticket.Severity.HIGH.value,
            submitter=self.user,
            username=self.user.username
        )
        ticket2_user.save(force_insert=True)
        ticket3_user2 = Ticket(
            title='工单3',
            description='工单3问题描述',
            service_type=Ticket.ServiceType.STORAGE.value,
            contact='',
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user2,
            username=self.user2.username
        )
        ticket3_user2.save(force_insert=True)
        ticket4_user2 = Ticket(
            title='工单2',
            description='工单2问题描述',
            service_type=Ticket.ServiceType.ACCOUNT.value,
            contact='',
            status=Ticket.Status.CLOSED.value,
            severity=Ticket.Severity.CRITICAL.value,
            submitter=self.user2,
            username=self.user2.username
        )
        ticket4_user2.save(force_insert=True)

        # user, no query
        base_url = reverse('api:support-ticket-list')
        r = self.client.get(base_url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=['count', 'page_num', 'page_size', 'results'], container=r.data)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn(keys=[
            'id', 'title', 'description', 'status', 'service_type', 'severity', 'submit_time',
            'modified_time', 'contact', 'resolution', 'submitter', 'assigned_to'
        ], container=r.data['results'][0])
        self.assertEqual(r.data['results'][0]['id'], ticket2_user.id)

        # user, query "page_size"
        query = parse.urlencode(query={'page_size': 1})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], ticket2_user.id)

        # user, query "page_size"、“page”
        query = parse.urlencode(query={'page_size': 1, 'page': 2})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], ticket1_user.id)

        # user, query "status"
        query = parse.urlencode(query={'status': 'test'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidStatus', response=r)

        query = parse.urlencode(query={'status': Ticket.Status.OPEN.value})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], ticket1_user.id)

        # user, query "service_type"
        query = parse.urlencode(query={'service_type': 'test'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidServiceType', response=r)

        query = parse.urlencode(query={'service_type': Ticket.ServiceType.SERVER.value})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], ticket2_user.id)

        # user, query "severity"
        query = parse.urlencode(query={'severity': 'test'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidSeverity', response=r)

        query = parse.urlencode(query={'severity': Ticket.Severity.HIGH.value})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], ticket2_user.id)

        query = parse.urlencode(query={'severity': Ticket.Severity.LOW.value})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

        # user, query "submitter_id" no "as_role"
        query = parse.urlencode(query={'submitter_id': self.user2.id})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='ParameterConflict', response=r)

        # user, query "submitter_id" 、 "as_role"
        query = parse.urlencode(query={'submitter_id': self.user2.id, 'as_role': 'test'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidAsRole', response=r)

        query = parse.urlencode(query={'submitter_id': self.user2.id, 'as_role': 'admin'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user.set_federal_admin()
        query = parse.urlencode(query={'submitter_id': self.user2.id, 'as_role': 'admin'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], ticket4_user2.id)

        # user, query "as_role"
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(len(r.data['results']), 4)
        self.assertEqual(r.data['results'][0]['id'], ticket4_user2.id)

        # user, query "as_role", "page_size", "page"
        query = parse.urlencode(query={'as_role': 'admin', 'page_size': 1, 'page': 2})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 4)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], ticket3_user2.id)

        # user, query "as_role", "status"
        query = parse.urlencode(query={'as_role': 'admin', 'status': Ticket.Status.OPEN.value})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)

        # user, query "as_role", "status", "service_type"
        query = parse.urlencode(query={
            'as_role': 'admin', 'status': Ticket.Status.OPEN.value,
            'service_type': Ticket.ServiceType.BILL.value
        })
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], ticket1_user.id)

        # # user, query "as_role", "severity"
        query = parse.urlencode(query={'as_role': 'admin', 'severity': Ticket.Severity.CRITICAL.value})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], ticket4_user2.id)

    def test_detail_ticket(self):
        ticket1_user = Ticket(
            title='工单1',
            description='工单1问题描述',
            service_type=Ticket.ServiceType.BILL.value,
            contact='',
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user,
            username=self.user.username
        )
        ticket1_user.save(force_insert=True)
        ticket2_user2 = Ticket(
            title='工单3',
            description='工单3问题描述',
            service_type=Ticket.ServiceType.STORAGE.value,
            contact='',
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user2,
            username=self.user2.username
        )
        ticket2_user2.save(force_insert=True)

        # user, NotAuthenticated
        url = reverse('api:support-ticket-detail', kwargs={'id': 'test'})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # user, TicketNotExist
        url = reverse('api:support-ticket-detail', kwargs={'id': 'test'})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='TicketNotExist', response=r)

        # user, ok
        url = reverse('api:support-ticket-detail', kwargs={'id': ticket1_user.id})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'title', 'description', 'status', 'service_type', 'severity', 'submit_time',
            'modified_time', 'contact', 'resolution', 'submitter', 'assigned_to'
        ], container=r.data)
        self.assertEqual(r.data['id'], ticket1_user.id)

        # user, AccessDenied
        url = reverse('api:support-ticket-detail', kwargs={'id': ticket2_user2.id})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user, invalid "as_role"
        url = reverse('api:support-ticket-detail', kwargs={'id': ticket2_user2.id})
        query = parse.urlencode(query={'as_role': 'test'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidAsRole', response=r)

        # user, "as_role", not federal admin
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user, "as_role", federal admin, ok
        self.user.set_federal_admin()
        url = reverse('api:support-ticket-detail', kwargs={'id': ticket2_user2.id})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'title', 'description', 'status', 'service_type', 'severity', 'submit_time',
            'modified_time', 'contact', 'resolution', 'submitter', 'assigned_to'
        ], container=r.data)
        self.assertEqual(r.data['id'], ticket2_user2.id)
