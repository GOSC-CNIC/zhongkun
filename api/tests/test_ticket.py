from django.urls import reverse

from utils.test import get_or_create_user
from ticket.models import Ticket
from . import MyAPITestCase


class TicketTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(username='lilei@xx.com')

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
