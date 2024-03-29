import time
from urllib import parse

from django.urls import reverse
from django.core import mail as dj_mail

from utils.test import get_or_create_user, MyAPITestCase
from ticket.models import Ticket, FollowUp, TicketChange
from ticket.managers import TicketManager


class TicketTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='lilei@xx.com')
        self.user2 = get_or_create_user(username='tom@xx.com')

    def test_create_ticket(self):
        self.assertEqual(len(dj_mail.outbox), 0)
        self.user.set_federal_admin()
        url = reverse('ticket-api:support-ticket-list')
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
        self.assertEqual(len(r.data['id']), 16)
        time.sleep(0.5)
        self.assertEqual(len(dj_mail.outbox), 1)

        # TooManyTicket
        for i in range(2, 7):
            data = {
                'title': 'test 标题, 不能少于10个字符', 'description': '这里是问题的描述，不少于10个字符',
                'service_type': Ticket.ServiceType.SERVER.value, 'contact': 'test'
            }
            time.sleep(0.1)
            r = self.client.post(url, data=data)
            if i < 6:
                self.assertEqual(r.status_code, 200)
            else:
                self.assertErrorResponse(status_code=409, code='TooManyTicket', response=r)

    def test_list_tickets(self):
        role_user = get_or_create_user(username='role@xx.com')
        ticket1_user = Ticket(
            title='工单1',
            description='工单1问题描述',
            service_type=Ticket.ServiceType.BILL.value,
            contact='',
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user,
            username=self.user.username,
            assigned_to_id=role_user.id
        )
        ticket1_user.save(force_insert=True)
        time.sleep(0.1)
        ticket2_user = Ticket(
            title='工单2',
            description='工单2问题描述',
            service_type=Ticket.ServiceType.SERVER.value,
            contact='',
            status=Ticket.Status.PROGRESS.value,
            severity=Ticket.Severity.HIGH.value,
            submitter=self.user,
            username=self.user.username
        )
        ticket2_user.save(force_insert=True)
        time.sleep(0.1)
        ticket3_user2 = Ticket(
            title='工单3',
            description='工单3问题描述',
            service_type=Ticket.ServiceType.STORAGE.value,
            contact='',
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user2,
            username=self.user2.username,
            assigned_to_id=self.user.id
        )
        ticket3_user2.save(force_insert=True)
        time.sleep(0.1)
        ticket4_user2 = Ticket(
            title='工单2',
            description='工单2问题描述',
            service_type=Ticket.ServiceType.ACCOUNT.value,
            contact='',
            status=Ticket.Status.CLOSED.value,
            severity=Ticket.Severity.CRITICAL.value,
            submitter=self.user2,
            username=self.user2.username,
            assigned_to_id=role_user.id
        )
        ticket4_user2.save(force_insert=True)

        # user, no query
        base_url = reverse('ticket-api:support-ticket-list')
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
            'modified_time', 'contact', 'resolution', 'submitter', 'assigned_to', 'rating'
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

        # user, query "assigned_to" no "as_role"
        query = parse.urlencode(query={'assigned_to': ''})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=400, code='ParameterConflict', response=r)

        # user, query "assigned_to" 、 "as_role"
        query = parse.urlencode(query={'assigned_to': '', 'as_role': 'admin'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], ticket3_user2.id)

        # role_user, query "assigned_to" 、 "as_role"
        role_user.set_federal_admin()
        self.client.logout()
        self.client.force_login(role_user)
        query = parse.urlencode(query={'assigned_to': '', 'as_role': 'admin'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], ticket4_user2.id)
        self.assertEqual(r.data['results'][1]['id'], ticket1_user.id)

        # role_user, query notfound, "assigned_to" 、 "as_role"
        query = parse.urlencode(query={'assigned_to': 'notfound', 'as_role': 'admin'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertErrorResponse(status_code=404, code='UserNotExist', response=r)

        # role_user, query user, "assigned_to" 、 "as_role"
        query = parse.urlencode(query={'assigned_to': self.user.username, 'as_role': 'admin'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], ticket3_user2.id)

        # role_user, query role_user, "assigned_to" 、 "as_role"
        query = parse.urlencode(query={'assigned_to': role_user.username, 'as_role': 'admin'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 2)
        self.assertEqual(len(r.data['results']), 2)
        self.assertEqual(r.data['results'][0]['id'], ticket4_user2.id)
        self.assertEqual(r.data['results'][1]['id'], ticket1_user.id)

        # role_user, query user2, "assigned_to" 、 "as_role"
        query = parse.urlencode(query={'assigned_to': self.user2.username, 'as_role': 'admin'})
        r = self.client.get(f'{base_url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)

    def test_detail_ticket(self):
        ticket1_user = Ticket(
            title='工单1',
            description='工单1问题描述',
            service_type=Ticket.ServiceType.BILL.value,
            contact='',
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user,
            username=self.user.username,
            assigned_to=self.user2
        )
        ticket1_user.save(force_insert=True)
        time.sleep(0.1)
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
        url = reverse('ticket-api:support-ticket-detail', kwargs={'id': 'test'})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # user, TicketNotExist
        url = reverse('ticket-api:support-ticket-detail', kwargs={'id': 'test'})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='TicketNotExist', response=r)

        # user, ok
        url = reverse('ticket-api:support-ticket-detail', kwargs={'id': ticket1_user.id})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'title', 'description', 'status', 'service_type', 'severity', 'submit_time',
            'modified_time', 'contact', 'resolution', 'submitter', 'assigned_to', 'rating'
        ], container=r.data)
        self.assertEqual(r.data['submitter'], {'id': self.user.id, 'username': self.user.username})
        self.assertEqual(r.data['assigned_to'], {'id': self.user2.id, 'username': self.user2.username})
        self.assertEqual(r.data['id'], ticket1_user.id)

        # user, AccessDenied
        url = reverse('ticket-api:support-ticket-detail', kwargs={'id': ticket2_user2.id})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user, invalid "as_role"
        url = reverse('ticket-api:support-ticket-detail', kwargs={'id': ticket2_user2.id})
        query = parse.urlencode(query={'as_role': 'test'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidAsRole', response=r)

        # user, "as_role", not federal admin
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user, "as_role", federal admin, ok
        self.user.set_federal_admin()
        url = reverse('ticket-api:support-ticket-detail', kwargs={'id': ticket2_user2.id})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'title', 'description', 'status', 'service_type', 'severity', 'submit_time',
            'modified_time', 'contact', 'resolution', 'submitter', 'assigned_to', 'rating'
        ], container=r.data)
        self.assertEqual(r.data['id'], ticket2_user2.id)

    def test_update_ticket(self):
        ticket_data = {
            'title': '工单1abcdef标题',
            'description': '工单1问题描述, 不少于10个字符长度',
            'service_type': Ticket.ServiceType.BILL.value,
            'contact': '联系方式'
        }
        ticket1_user = Ticket(
            title=ticket_data['title'],
            description=ticket_data['description'],
            service_type=ticket_data['service_type'],
            contact=ticket_data['contact'],
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user,
            username=self.user.username,
            assigned_to=None
        )
        ticket1_user.save(force_insert=True)
        time.sleep(0.1)
        ticket2_user2 = Ticket(
            title='工单2',
            description='工单2问题描述',
            service_type=Ticket.ServiceType.STORAGE.value,
            contact='',
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user2,
            username=self.user2.username
        )
        ticket2_user2.save(force_insert=True)

        # user, NotAuthenticated
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': 'test'})
        r = self.client.post(url, data=ticket_data)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # user, TicketNotExist
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': 'test'})
        r = self.client.post(url, data=ticket_data)
        self.assertErrorResponse(status_code=404, code='TicketNotExist', response=r)

        # user, InvalidTitle
        data = ticket_data.copy()
        data['title'] = '标题少于10字符'
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidTitle', response=r)

        # user, InvalidDescription
        data = ticket_data.copy()
        data['description'] = '描述少于10字符'
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidDescription', response=r)

        # user, InvalidServiceType
        data = ticket_data.copy()
        data['service_type'] = 'test'
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidServiceType', response=r)

        # user, AccessDenied
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': ticket2_user2.id})
        r = self.client.post(url, data=ticket_data)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user, no change, ok
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data=ticket_data)
        self.assertEqual(r.status_code, 200)
        self.assert_is_subdict_of(sub=ticket_data, d=r.data)

        # user, no change, ok
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data=ticket_data)
        self.assertEqual(r.status_code, 200)
        sub = ticket_data.copy()
        sub['status'] = Ticket.Status.OPEN.value
        self.assert_is_subdict_of(sub=sub, d=r.data)

        # user, open status, change all, ok
        new_ticket_data = {
            'title': 'abcdefghij' * 20,     # length 200
            'description': '工单1问题描述, 不少于10个字符长度sss',
            'service_type': Ticket.ServiceType.ACCOUNT.value,
            'contact': '联系方式dd'
        }
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data=new_ticket_data)
        self.assertEqual(r.status_code, 200)
        new_ticket_data['status'] = Ticket.Status.OPEN.value
        self.assert_is_subdict_of(sub=new_ticket_data, d=r.data)
        # open status, no action FollowUp
        count = FollowUp.objects.all().count()
        self.assertEqual(count, 0)

        # user, open status but assigned_to user2, change title, ok
        ticket1_user.assigned_to_id = self.user2.id
        ticket1_user.save(update_fields=['assigned_to_id'])
        new_ticket_data1 = {
            'title': 'abcdefghijdds',  # length 200
            'description': '工单1问题描述, 不少于10个字符长度sss',
            'service_type': Ticket.ServiceType.ACCOUNT.value,
            'contact': '联系方式dd'
        }
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data=new_ticket_data1)
        self.assertEqual(r.status_code, 200)
        new_ticket_data1['status'] = Ticket.Status.OPEN.value
        self.assert_is_subdict_of(sub=new_ticket_data1, d=r.data)
        # open status, assigned_to user2, has action FollowUp
        fus = FollowUp.objects.select_related('ticket_change').all()
        self.assertEqual(len(fus), 1)
        fu = fus[0]
        self.assertEqual(fu.fu_type, FollowUp.FuType.ACTION.value)
        tc = fu.ticket_change
        self.assertEqual(tc.ticket_field, TicketChange.TicketField.TITLE.value)
        self.assertEqual(tc.old_value, new_ticket_data['title'])
        self.assertEqual(tc.new_value, new_ticket_data1['title'])

        # user, "progress" status, change all, ok
        ticket1_user.status = Ticket.Status.PROGRESS.value
        ticket1_user.save(update_fields=['status'])
        new_ticket_data2 = {
            'title': '工单1abcdef标题ggg好还是123' * 10,       # length 200
            'description': '呃呃工单1问题描述, 不少于10个字符长度sss',
            'service_type': Ticket.ServiceType.STORAGE.value,
            'contact': '联系方式ddhjj'
        }
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data=new_ticket_data2)
        self.assertEqual(r.status_code, 200)
        new_ticket_data2['status'] = Ticket.Status.PROGRESS.value
        self.assert_is_subdict_of(sub=new_ticket_data2, d=r.data)
        fus = FollowUp.objects.select_related('ticket_change').all()
        self.assertEqual(len(fus), 3)
        for fu in fus[0:2]:
            self.assertEqual(fu.fu_type, FollowUp.FuType.ACTION.value)
            tc: TicketChange = fu.ticket_change
            if tc.ticket_field == TicketChange.TicketField.TITLE.value:
                self.assertEqual(tc.old_value, new_ticket_data1['title'])
                self.assertEqual(tc.new_value, new_ticket_data2['title'])
            else:
                self.assertEqual(tc.ticket_field, TicketChange.TicketField.DESCRIPTION.value)
                self.assertEqual(tc.old_value, new_ticket_data['description'])
                self.assertEqual(tc.new_value, new_ticket_data2['description'])

        # user, "CLOSED" status, not allow change
        ticket1_user.status = Ticket.Status.CLOSED.value
        ticket1_user.save(update_fields=['status'])
        new_ticket_data2 = {
            'title': '工单1abcdef标题ggg好还是',
            'description': '呃呃工单1问题描述, 不少于10个字符长度sss',
            'service_type': Ticket.ServiceType.STORAGE.value,
            'contact': '联系方式ddhjj'
        }
        url = reverse('ticket-api:support-ticket-update-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data=new_ticket_data2)
        self.assertErrorResponse(status_code=409, code='ConflictTicketStatus', response=r)

    def test_change_ticket_severity(self):
        ticket_data = {
            'title': '工单1abcdef标题',
            'description': '工单1问题描述, 不少于10个字符长度',
            'service_type': Ticket.ServiceType.BILL.value,
            'contact': '联系方式'
        }
        ticket1_user = Ticket(
            title=ticket_data['title'],
            description=ticket_data['description'],
            service_type=ticket_data['service_type'],
            contact=ticket_data['contact'],
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user,
            username=self.user.username,
            assigned_to=None
        )
        ticket1_user.save(force_insert=True)

        # user, NotAuthenticated
        url = reverse('ticket-api:support-ticket-ticket-severity-change', kwargs={'id': 'test', 'severity': 'ss'})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # user, InvalidSeverity
        url = reverse('ticket-api:support-ticket-ticket-severity-change', kwargs={'id': 'test', 'severity': 'ss'})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=400, code='InvalidSeverity', response=r)

        # user, AccessDenied
        url = reverse('ticket-api:support-ticket-ticket-severity-change', kwargs={
            'id': 'test', 'severity': Ticket.Severity.HIGH.value})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user.set_federal_admin()

        # user, TicketNotExist
        url = reverse('ticket-api:support-ticket-ticket-severity-change', kwargs={
            'id': 'test', 'severity': Ticket.Severity.HIGH.value})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=404, code='TicketNotExist', response=r)

        # only ticket assigned_to user has permission
        url = reverse('ticket-api:support-ticket-ticket-severity-change', kwargs={
            'id': ticket1_user.id, 'severity': Ticket.Severity.HIGH.value})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        ticket1_user.assigned_to_id = self.user.id
        ticket1_user.save(update_fields=['assigned_to_id'])

        # user, ok
        url = reverse('ticket-api:support-ticket-ticket-severity-change', kwargs={
            'id': ticket1_user.id, 'severity': Ticket.Severity.HIGH.value})
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['severity'], Ticket.Severity.HIGH.value)
        old_severity = ticket1_user.severity
        ticket1_user.refresh_from_db()
        self.assertEqual(ticket1_user.severity, Ticket.Severity.HIGH.value)
        fus = FollowUp.objects.select_related('ticket_change').all()
        self.assertEqual(len(fus), 1)
        for fu in fus:
            self.assertEqual(fu.fu_type, FollowUp.FuType.ACTION.value)
            tc: TicketChange = fu.ticket_change
            self.assertEqual(tc.ticket_field, TicketChange.TicketField.SEVERITY.value)
            self.assertEqual(tc.old_value, old_severity)
            self.assertEqual(tc.new_value, Ticket.Severity.HIGH.value)

        # same severity again ok
        url = reverse('ticket-api:support-ticket-ticket-severity-change', kwargs={
            'id': ticket1_user.id, 'severity': Ticket.Severity.HIGH.value})
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['severity'], Ticket.Severity.HIGH.value)
        ticket1_user.refresh_from_db()
        self.assertEqual(ticket1_user.severity, Ticket.Severity.HIGH.value)
        fus = FollowUp.objects.select_related('ticket_change').all()
        self.assertEqual(len(fus), 1)

        # 'closed' ticket, ConflictTicketStatus
        ticket1_user.status = Ticket.Status.CLOSED.value
        ticket1_user.save(update_fields=['status'])
        url = reverse('ticket-api:support-ticket-ticket-severity-change', kwargs={
            'id': ticket1_user.id, 'severity': Ticket.Severity.HIGH.value})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=409, code='ConflictTicketStatus', response=r)

    def test_change_ticket_status(self):
        ticket_data = {
            'title': '工单1abcdef标题',
            'description': '工单1问题描述, 不少于10个字符长度',
            'service_type': Ticket.ServiceType.BILL.value,
            'contact': '联系方式'
        }
        ticket1_user = Ticket(
            title=ticket_data['title'],
            description=ticket_data['description'],
            service_type=ticket_data['service_type'],
            contact=ticket_data['contact'],
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user,
            username=self.user.username,
            assigned_to=None
        )
        ticket1_user.save(force_insert=True)

        # user, NotAuthenticated
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={'id': 'test', 'status': 'ss'})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # user, InvalidStatus
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={'id': 'test', 'status': 'ss'})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=400, code='InvalidStatus', response=r)

        # user, TicketNotExist
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': 'test', 'status': Ticket.Status.OPEN.value})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=404, code='TicketNotExist', response=r)

        # user, ok, open -> closed
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': ticket1_user.id, 'status': Ticket.Status.CLOSED.value})
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], Ticket.Status.CLOSED.value)
        ticket1_user.refresh_from_db()
        self.assertEqual(ticket1_user.status, Ticket.Status.CLOSED.value)
        fus = FollowUp.objects.select_related('ticket_change').all()
        self.assertEqual(len(fus), 1)
        fu = fus[0]
        self.assertEqual(fu.fu_type, FollowUp.FuType.ACTION.value)
        tc: TicketChange = fu.ticket_change
        self.assertEqual(tc.ticket_field, TicketChange.TicketField.STATUS.value)
        self.assertEqual(tc.old_value, Ticket.Status.OPEN.value)
        self.assertEqual(tc.new_value, Ticket.Status.CLOSED.value)

        # user, ConflictTicketStatus, closed -> open
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': ticket1_user.id, 'status': Ticket.Status.OPEN.value})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=409, code='ConflictTicketStatus', response=r)

        # user, ok, progress -> closed
        ticket1_user.status = Ticket.Status.PROGRESS.value
        ticket1_user.save(update_fields=['status'])
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': ticket1_user.id, 'status': Ticket.Status.CLOSED.value})
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], Ticket.Status.CLOSED.value)
        ticket1_user.refresh_from_db()
        self.assertEqual(ticket1_user.status, Ticket.Status.CLOSED.value)
        fus = FollowUp.objects.select_related('ticket_change').all()
        self.assertEqual(len(fus), 2)
        fu = fus[0]
        self.assertEqual(fu.fu_type, FollowUp.FuType.ACTION.value)
        tc: TicketChange = fu.ticket_change
        self.assertEqual(tc.ticket_field, TicketChange.TicketField.STATUS.value)
        self.assertEqual(tc.old_value, Ticket.Status.PROGRESS.value)
        self.assertEqual(tc.new_value, Ticket.Status.CLOSED.value)

        # user, ConflictTicketStatus, progress -> open
        ticket1_user.status = Ticket.Status.PROGRESS.value
        ticket1_user.save(update_fields=['status'])
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': ticket1_user.id, 'status': Ticket.Status.OPEN.value})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=409, code='ConflictTicketStatus', response=r)

        # user, as_role, AccessDenied
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': ticket1_user.id, 'status': Ticket.Status.CLOSED.value})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user2, AccessDenied
        self.client.logout()
        self.client.force_login(self.user2)
        ticket1_user.status = Ticket.Status.OPEN.value
        ticket1_user.save(update_fields=['status'])
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': ticket1_user.id, 'status': Ticket.Status.CLOSED.value})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # --------- as_role ---------
        # user2, InvalidAsRole
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': ticket1_user.id, 'status': Ticket.Status.CLOSED.value})
        query = parse.urlencode(query={'as_role': 'test'})
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidAsRole', response=r)

        self.user2.set_federal_admin()

        # user2, TicketNotExist
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': 'test', 'status': Ticket.Status.OPEN.value})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=404, code='TicketNotExist', response=r)

        # only ticket assigned_to user has permission
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': ticket1_user.id, 'status': Ticket.Status.PROGRESS.value})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.post(f'{url}?{query}')
        self.assertEqual(r.status_code, 403)

        ticket1_user.assigned_to_id = self.user2.id
        ticket1_user.save(update_fields=['assigned_to_id'])

        # user2, ok, open -> progress
        self._status_change_test_as_role(
            ticket=ticket1_user, old_value=Ticket.Status.OPEN.value,
            new_value=Ticket.Status.PROGRESS.value
        )
        # user2, ok, progress -> closed
        self._status_change_test_as_role(
            ticket=ticket1_user, old_value=Ticket.Status.PROGRESS.value,
            new_value=Ticket.Status.CLOSED.value
        )

        # user2, ConflictTicketStatus, closed -> open
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': ticket1_user.id, 'status': Ticket.Status.OPEN.value})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.post(f'{url}?{query}')
        self.assertErrorResponse(status_code=409, code='ConflictTicketStatus', response=r)

        # user2, ok, progress -> open
        ticket1_user.status = Ticket.Status.PROGRESS.value
        ticket1_user.save(update_fields=['status'])
        self._status_change_test_as_role(
            ticket=ticket1_user, old_value=Ticket.Status.PROGRESS.value,
            new_value=Ticket.Status.OPEN.value
        )

    def _status_change_test_as_role(self, ticket, old_value, new_value):
        url = reverse('ticket-api:support-ticket-ticket-status-change', kwargs={
            'id': ticket.id, 'status': new_value})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.post(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['status'], new_value)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, new_value)
        fu = FollowUp.objects.select_related('ticket_change').first()
        self.assertEqual(fu.fu_type, FollowUp.FuType.ACTION.value)
        tc: TicketChange = fu.ticket_change
        self.assertEqual(tc.ticket_field, TicketChange.TicketField.STATUS.value)
        self.assertEqual(tc.old_value, old_value)
        self.assertEqual(tc.new_value, new_value)

    def test_add_followup(self):
        self.assertEqual(len(dj_mail.outbox), 0)
        ticket_data = {
            'title': '工单1abcdef标题',
            'description': '工单1问题描述, 不少于10个字符长度',
            'service_type': Ticket.ServiceType.BILL.value,
            'contact': '联系方式'
        }
        ticket1_user = Ticket(
            title=ticket_data['title'],
            description=ticket_data['description'],
            service_type=ticket_data['service_type'],
            contact=ticket_data['contact'],
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user,
            username=self.user.username,
            assigned_to=None
        )
        ticket1_user.save(force_insert=True)

        # user, NotAuthenticated
        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': 'test'})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # user, InvalidComment
        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': ticket1_user.id})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=400, code='InvalidComment', response=r)

        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data={'comment': ''})
        self.assertErrorResponse(status_code=400, code='InvalidComment', response=r)

        # user, TicketNotExist
        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': 'test'})
        r = self.client.post(url, data={'comment': '测试test回复'})
        self.assertErrorResponse(status_code=404, code='TicketNotExist', response=r)

        # user, ok add followup
        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data={'comment': '测试test回复2'})
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'title', 'comment', 'submit_time', 'fu_type', 'ticket_id', 'user', 'ticket_change'
        ], container=r.data)
        self.assertEqual(r.data['user'], {'id': self.user.id, 'username': self.user.username})
        self.assertIsNone(r.data['ticket_change'])
        self.assertEqual(r.data['comment'], '测试test回复2')

        time.sleep(0.5)
        self.assertEqual(len(dj_mail.outbox), 0)    # 工单未指派处理人时，工单提交人回复，不发邮件

        # user, CLOSED ticket, ConflictTicketStatus
        ticket1_user.status = Ticket.Status.CLOSED.value
        ticket1_user.save(update_fields=['status'])
        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data={'comment': 'adada测试test回复2'})
        self.assertErrorResponse(status_code=409, code='ConflictTicketStatus', response=r)

        # user2, AccessDenied
        self.client.logout()
        self.client.force_login(self.user2)

        ticket1_user.status = Ticket.Status.PROGRESS.value
        ticket1_user.save(update_fields=['status'])
        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data={'comment': 'adada测试test回复2'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # ---- as_role ------
        # user2, InvalidAsRole
        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'as_role': 'test'})
        r = self.client.post(f'{url}?{query}', data={'comment': 'adada测试test回复2'})
        self.assertErrorResponse(status_code=400, code='InvalidAsRole', response=r)

        # user2, as_role, AccessDenied
        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.post(f'{url}?{query}', data={'comment': 'adada测试test回复2'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user2.set_federal_admin()

        # only ticket assigned_to user has permission
        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.post(f'{url}?{query}', data={'comment': 'adada测试test回复2'})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        ticket1_user.assigned_to_id = self.user2.id
        ticket1_user.save(update_fields=['assigned_to_id'])

        # user2, as_role, ok
        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.post(f'{url}?{query}', data={'comment': 'user2 adada测试test回复2'})
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'title', 'comment', 'submit_time', 'fu_type', 'ticket_id', 'user', 'ticket_change'
        ], container=r.data)
        self.assertEqual(r.data['user'], {'id': self.user2.id, 'username': self.user2.username})
        self.assertIsNone(r.data['ticket_change'])
        self.assertEqual(r.data['comment'], 'user2 adada测试test回复2')

        time.sleep(0.5)
        self.assertEqual(len(dj_mail.outbox), 1)    # 工单处理人回复，向工单提交人发邮件通知

        # user2, as_role, ConflictTicketStatus
        ticket1_user.status = Ticket.Status.CLOSED.value
        ticket1_user.save(update_fields=['status'])
        url = reverse('ticket-api:support-ticket-add-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.post(f'{url}?{query}', data={'comment': 'user2 adada测试test回复2'})
        self.assertErrorResponse(status_code=409, code='ConflictTicketStatus', response=r)

    def test_list_followup(self):
        ticket_data = {
            'title': '工单1abcdef标题',
            'description': '工单1问题描述, 不少于10个字符长度',
            'service_type': Ticket.ServiceType.BILL.value,
            'contact': '联系方式'
        }
        ticket1_user = Ticket(
            title=ticket_data['title'],
            description=ticket_data['description'],
            service_type=ticket_data['service_type'],
            contact=ticket_data['contact'],
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user,
            username=self.user.username,
            assigned_to=self.user2
        )
        ticket1_user.save(force_insert=True)

        fu1 = TicketManager.create_followup_reply(user=self.user, ticket_id=ticket1_user.id, comment='test reply')
        fu2 = TicketManager.create_followup_action(
            user=self.user2, ticket_id=ticket1_user.id, field_name=TicketChange.TicketField.STATUS.value,
            old_value=Ticket.Status.OPEN.value, new_value=Ticket.Status.PROGRESS.value
        )
        fu3 = TicketManager.create_followup_reply(user=self.user2, ticket_id=ticket1_user.id, comment='rereply test')

        # user, NotAuthenticated
        url = reverse('ticket-api:support-ticket-list-followup', kwargs={'id': 'test'})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # user, TicketNotExist
        url = reverse('ticket-api:support-ticket-list-followup', kwargs={'id': 'test'})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=404, code='TicketNotExist', response=r)

        # user, ok list followup, only reply
        url = reverse('ticket-api:support-ticket-list-followup', kwargs={'id': ticket1_user.id})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'has_next', 'page_size', 'marker', 'next_marker', 'results'
        ], container=r.data)
        self.assertEqual(len(r.data['results']), 2)
        self.assertKeysIn(keys=[
            'id', 'title', 'comment', 'submit_time', 'fu_type', 'ticket_id', 'user', 'ticket_change'
        ], container=r.data['results'][1])

        # user, page_size
        url = reverse('ticket-api:support-ticket-list-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'page_size': 1})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], fu3.id)
        self.assertIs(r.data['has_next'], True)
        self.assertEqual(r.data['page_size'], 1)
        next_marker = r.data['next_marker']

        # user, page_size, marker
        url = reverse('ticket-api:support-ticket-list-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'page_size': 2, 'marker': next_marker})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], fu1.id)
        # self.assertEqual(r.data['results'][1]['id'], fu1.id)
        self.assertIs(r.data['has_next'], False)
        self.assertEqual(r.data['page_size'], 2)
        self.assertIsNone(r.data['next_marker'])

        # user2, AccessDenied
        self.client.logout()
        self.client.force_login(self.user2)

        url = reverse('ticket-api:support-ticket-list-followup', kwargs={'id': ticket1_user.id})
        r = self.client.get(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # ---- as_role ------
        # user2, InvalidAsRole
        url = reverse('ticket-api:support-ticket-list-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'as_role': 'test'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=400, code='InvalidAsRole', response=r)

        # user2, as_role, AccessDenied
        url = reverse('ticket-api:support-ticket-list-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.get(f'{url}?{query}')
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user2.set_federal_admin()

        # user2, as_role, ok
        url = reverse('ticket-api:support-ticket-list-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'as_role': 'admin'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'has_next', 'page_size', 'marker', 'next_marker', 'results'
        ], container=r.data)
        self.assertEqual(len(r.data['results']), 3)
        self.assertEqual(r.data['results'][1]['id'], fu2.id)
        self.assertEqual(r.data['results'][1]['user'], {'id': self.user2.id, 'username': self.user2.username})
        self.assertIsNotNone(r.data['results'][1]['ticket_change'], None)
        self.assertEqual(r.data['results'][1]['ticket_change'], {
            'id': fu2.ticket_change.id, 'ticket_field': TicketChange.TicketField.STATUS.value,
            'old_value': Ticket.Status.OPEN.value, 'new_value': Ticket.Status.PROGRESS.value
        })

        # user2, as_role, page_size
        url = reverse('ticket-api:support-ticket-list-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'page_size': 1, 'as_role': 'admin'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], fu3.id)
        self.assertIsNone(r.data['results'][0]['ticket_change'], None)
        self.assertIs(r.data['has_next'], True)
        self.assertEqual(r.data['page_size'], 1)
        next_marker = r.data['next_marker']

        # user2, as_role, page_size, marker
        url = reverse('ticket-api:support-ticket-list-followup', kwargs={'id': ticket1_user.id})
        query = parse.urlencode(query={'page_size': 1, 'marker': next_marker, 'as_role': 'admin'})
        r = self.client.get(f'{url}?{query}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)
        self.assertEqual(r.data['results'][0]['id'], fu2.id)
        self.assertIs(r.data['has_next'], True)
        self.assertEqual(r.data['page_size'], 1)
        self.assertIsNotNone(r.data['next_marker'])

    def test_take_ticket(self):
        ticket1_user = Ticket(
            title='test',
            description='description',
            service_type=Ticket.ServiceType.SERVER.value,
            contact='text',
            status=Ticket.Status.CLOSED.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user,
            username=self.user.username,
            assigned_to_id=None
        )
        ticket1_user.save(force_insert=True)

        url = reverse('ticket-api:support-ticket-take-ticket', kwargs={'id': 'test'})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        url = reverse('ticket-api:support-ticket-take-ticket', kwargs={'id': 'test'})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user.set_federal_admin()
        r = self.client.post(url)
        self.assertErrorResponse(status_code=404, code='TicketNotExist', response=r)

        url = reverse('ticket-api:support-ticket-take-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=409, code='ConflictTicketStatus', response=r)

        ticket1_user.status = Ticket.Status.OPEN.value
        ticket1_user.save(update_fields=['status'])
        url = reverse('ticket-api:support-ticket-take-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        ticket1_user.refresh_from_db()
        self.assertEqual(ticket1_user.assigned_to_id, self.user.id)
        self.assertEqual(ticket1_user.status, Ticket.Status.PROGRESS.value)
        fu = FollowUp.objects.filter(ticket_id=ticket1_user.id, fu_type=FollowUp.FuType.ACTION.value).first()
        self.assertEqual(fu.ticket_change.ticket_field, TicketChange.TicketField.ASSIGNED_TO.value)
        self.assertEqual(fu.ticket_change.old_value, '')
        self.assertEqual(fu.ticket_change.new_value, self.user.username)

        url = reverse('ticket-api:support-ticket-take-ticket', kwargs={'id': ticket1_user.id})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

    def test_ticket_assigned_to(self):
        ticket1_user = Ticket(
            title='test',
            description='description',
            service_type=Ticket.ServiceType.SERVER.value,
            contact='text',
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user,
            username=self.user.username,
            assigned_to_id=None
        )
        ticket1_user.save(force_insert=True)

        url = reverse('ticket-api:support-ticket-ticket-assigned-to', kwargs={'id': 'test', 'username': 'testuser'})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)
        url = reverse('ticket-api:support-ticket-ticket-assigned-to', kwargs={'id': 'test', 'username': 'testuser'})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=404, code='TicketNotExist', response=r)

        url = reverse('ticket-api:support-ticket-ticket-assigned-to',
                      kwargs={'id': ticket1_user.id, 'username': 'testuser'})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.user.set_federal_admin()
        url = reverse('ticket-api:support-ticket-ticket-assigned-to',
                      kwargs={'id': ticket1_user.id, 'username': 'testuser'})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=404, code='UserNotExist', response=r)

        # assigned to user2 ( not federal admin )
        url = reverse(
            'ticket-api:support-ticket-ticket-assigned-to',
            kwargs={'id': ticket1_user.id, 'username': self.user2.username})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=409, code='Conflict', response=r)

        # user from none assigned to user2 ok
        self.user2.set_federal_admin()
        url = reverse(
            'ticket-api:support-ticket-ticket-assigned-to',
            kwargs={'id': ticket1_user.id, 'username': self.user2.username})
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        ticket1_user.refresh_from_db()
        self.assertEqual(ticket1_user.assigned_to_id, self.user2.id)
        fus = FollowUp.objects.filter(
            ticket_id=ticket1_user.id, fu_type=FollowUp.FuType.ACTION.value).order_by('-submit_time')
        self.assertEqual(len(fus), 1)
        fu = fus[0]
        self.assertEqual(fu.user_id, self.user.id)
        self.assertEqual(fu.ticket_change.ticket_field, TicketChange.TicketField.ASSIGNED_TO.value)
        self.assertEqual(fu.ticket_change.old_value, '')
        self.assertEqual(fu.ticket_change.new_value, self.user2.username)

        # user, from user2 assigned to user, ok
        url = reverse(
            'ticket-api:support-ticket-ticket-assigned-to',
            kwargs={'id': ticket1_user.id, 'username': self.user.username})
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        ticket1_user.refresh_from_db()
        self.assertEqual(ticket1_user.assigned_to_id, self.user.id)
        fus = FollowUp.objects.filter(
            ticket_id=ticket1_user.id, fu_type=FollowUp.FuType.ACTION.value).order_by('-submit_time')
        self.assertEqual(len(fus), 2)
        fu = fus[0]
        self.assertEqual(fu.user_id, self.user.id)
        self.assertEqual(fu.ticket_change.ticket_field, TicketChange.TicketField.ASSIGNED_TO.value)
        self.assertEqual(fu.ticket_change.old_value, self.user2.username)
        self.assertEqual(fu.ticket_change.new_value, self.user.username)

        # user2, from user assigned to user2, ok
        self.client.logout()
        self.client.force_login(self.user2)
        url = reverse(
            'ticket-api:support-ticket-ticket-assigned-to',
            kwargs={'id': ticket1_user.id, 'username': self.user2.username})
        r = self.client.post(url)
        self.assertEqual(r.status_code, 200)
        ticket1_user.refresh_from_db()
        self.assertEqual(ticket1_user.assigned_to_id, self.user2.id)
        fus = FollowUp.objects.filter(
            ticket_id=ticket1_user.id, fu_type=FollowUp.FuType.ACTION.value).order_by('-submit_time')
        self.assertEqual(len(fus), 3)
        fu = fus[0]
        self.assertEqual(fu.user_id, self.user2.id)
        self.assertEqual(fu.ticket_change.ticket_field, TicketChange.TicketField.ASSIGNED_TO.value)
        self.assertEqual(fu.ticket_change.old_value, self.user.username)
        self.assertEqual(fu.ticket_change.new_value, self.user2.username)

        # user2, from user assigned to user2, 'closed' ticket, ConflictTicketStatus
        ticket1_user.status = Ticket.Status.CLOSED.value
        ticket1_user.save(update_fields=['status'])
        url = reverse(
            'ticket-api:support-ticket-ticket-assigned-to',
            kwargs={'id': ticket1_user.id, 'username': self.user2.username})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=409, code='ConflictTicketStatus', response=r)

    def test_ticket_rating_add_query(self):
        ticket1_user = Ticket(
            title='test',
            description='description',
            service_type=Ticket.ServiceType.SERVER.value,
            contact='text',
            status=Ticket.Status.OPEN.value,
            severity=Ticket.Severity.NORMAL.value,
            submitter=self.user2,
            username=self.user2.username,
            assigned_to_id=self.user.id
        )
        ticket1_user.save(force_insert=True)

        url = reverse('ticket-api:support-ticket-add-rating', kwargs={'id': 'test'})
        r = self.client.post(url, data={"score": 6, "comment": ""})
        self.assertErrorResponse(status_code=401, code='NotAuthenticated', response=r)

        self.client.force_login(self.user)

        # user, InvalidScore
        url = reverse('ticket-api:support-ticket-add-rating', kwargs={'id': ticket1_user.id})
        r = self.client.post(url)
        self.assertErrorResponse(status_code=400, code='InvalidScore', response=r)
        r = self.client.post(url, data={"score": 0, "comment": ""})
        self.assertErrorResponse(status_code=400, code='InvalidScore', response=r)
        r = self.client.post(url, data={"score": 6, "comment": ""})
        self.assertErrorResponse(status_code=400, code='InvalidScore', response=r)

        # user, query ticket rating
        url = reverse('ticket-api:support-ticket-query-rating', kwargs={'id': 'test'})
        r = self.client.get(url)
        self.assertIn('ratings', r.data)
        self.assertIsInstance(r.data['ratings'], list)
        self.assertEqual(len(r.data['ratings']), 0)

        url = reverse('ticket-api:support-ticket-query-rating', kwargs={'id': ticket1_user.id})
        r = self.client.get(url)
        self.assertIn('ratings', r.data)
        self.assertIsInstance(r.data['ratings'], list)
        self.assertEqual(len(r.data['ratings']), 0)

        # TicketNotExist
        url = reverse('ticket-api:support-ticket-add-rating', kwargs={'id': 'test'})
        r = self.client.post(url, data={"score": 5, "comment": ""})
        self.assertErrorResponse(status_code=404, code='TicketNotExist', response=r)

        # user, AccessDenied
        url = reverse('ticket-api:support-ticket-add-rating', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data={"score": 5, "comment": ""})
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        # user2, ticket not closed
        self.client.logout()
        self.client.force_login(self.user2)
        url = reverse('ticket-api:support-ticket-add-rating', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data={"score": 5, "comment": ""})
        self.assertErrorResponse(status_code=409, code='ConflictTicketStatus', response=r)

        # user2, ticket closed, ok
        ticket1_user.status = Ticket.Status.CLOSED.value
        ticket1_user.save(update_fields=['status'])
        url = reverse('ticket-api:support-ticket-add-rating', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data={"score": 5, "comment": ""})
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'score', 'comment', 'ticket_id', 'submit_time', 'modified_time',
            'user_id', 'username', 'is_sys_submit'
        ], container=r.data)
        self.assertEqual(r.data['score'], 5)
        self.assertEqual(r.data['comment'], '')

        # user2, query ticket rating
        url = reverse('ticket-api:support-ticket-query-rating', kwargs={'id': ticket1_user.id})
        r = self.client.get(url)
        self.assertIn('ratings', r.data)
        self.assertIsInstance(r.data['ratings'], list)
        self.assertEqual(len(r.data['ratings']), 1)
        self.assertKeysIn(keys=[
            'id', 'score', 'comment', 'ticket_id', 'submit_time', 'modified_time',
            'user_id', 'username', 'is_sys_submit'
        ], container=r.data['ratings'][0])

        # user2, one ticket only one rating
        url = reverse('ticket-api:support-ticket-add-rating', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data={"score": 4, "comment": "test奥法后"})
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=r)

        # user2, delete add again, ok
        ticket1_user.ticket_rating.delete()
        comment = 'test奥法后' * 10
        url = reverse('ticket-api:support-ticket-add-rating', kwargs={'id': ticket1_user.id})
        r = self.client.post(url, data={"score": 4, "comment": comment})
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(keys=[
            'id', 'score', 'comment', 'ticket_id', 'submit_time', 'modified_time',
            'user_id', 'username', 'is_sys_submit'
        ], container=r.data)
        self.assertEqual(r.data['score'], 4)
        self.assertEqual(r.data['comment'], comment)

        # user2, InvalidComment
        url = reverse('ticket-api:support-ticket-add-rating', kwargs={'id': ticket1_user.id})
        comment = 'testtest' * 128
        r = self.client.post(url, data={"score": 3, "comment": comment})
        self.assertErrorResponse(status_code=409, code='TargetAlreadyExists', response=r)

        # user2, InvalidComment, max length 1024
        r = self.client.post(url, data={"score": 3, "comment": comment + 'a'})
        self.assertErrorResponse(status_code=400, code='InvalidComment', response=r)
