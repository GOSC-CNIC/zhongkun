import time

from django.urls import reverse
from django.core import mail

from utils.test import get_or_create_user
from apps.users.models import Email
from apps.api.apiviews.email_views import EmailIPRestrictor
from . import MyAPITransactionTestCase


class EmailTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')

    def test_send_email(self):
        base_url = reverse('api:email-list')
        data = {
            "receiver": "wangyushun@cnic",
            "message": "",
            "is_html": False
        }
        r = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidSubject', response=r)

        data['subject'] = 'test'
        r = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidMessage', response=r)

        data['message'] = 'string message对我的'
        r = self.client.post(base_url, data=data)
        self.assertErrorResponse(status_code=400, code='InvalidReceivers', response=r)

        r = self.client.post(base_url, data={
            'subject': 'test',
            "receiver": "test@cnic.com",
            "message": "string message对我的",
            "is_html": False
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        self.client.force_login(self.user)
        r = self.client.get(reverse('api:email-realip'))
        real_ip = r.data['real_ip']
        if real_ip:
            EmailIPRestrictor.add_ip_rule(ip_value=real_ip)
            EmailIPRestrictor.clear_cache()

        self.client.logout()

        # ok, text
        r = self.client.post(base_url, data={
            'subject': 'test',
            "receiver": "test@cnic.com",
            "message": "string message对我的",
            "is_html": False
        })

        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(['id', 'subject', 'receiver', 'message', 'is_html', 'status', 'status_desc',
                           'success_time', 'remote_ip'], r.data)
        self.assertEqual(r.data['status'], 'wait')
        self.assertEqual(r.data['is_html'], False)
        self.assertEqual(r.data['receiver'], 'test@cnic.com')
        self.assertEqual(r.data['is_feint'], False)

        # 等待邮件异步发送
        time.sleep(0.5)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Email.objects.count(), 1)
        email1: Email = Email.objects.order_by('-send_time').first()
        self.assertEqual(email1.receiver, 'test@cnic.com')
        self.assertEqual(email1.is_feint, False)
        self.assertEqual(email1.status, 'success')

        # ok, html
        r = self.client.post(base_url, data={
            'subject': 'test测试',
            "receiver": "test@cnic.com;test66@cnic.com; test888@qq.com ",
            "message": """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>测试</title>
            </head>
            <body>
                <details>
                    <summary>Languages Used</summary>
                    <p>This page was written in HTML and CSS. The CSS was compiled from SASS. Regardless, 
                    this could all be done in plain HTML and CSS测试哦哦哦吼</p>
                </details>
            </body>
            </html>
            """,
            "is_html": True,
            'is_feint': 'false'
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(['id', 'subject', 'receiver', 'message', 'is_html', 'status', 'status_desc',
                           'success_time', 'remote_ip'], r.data)
        self.assertEqual(r.data['status'], 'wait')
        self.assertEqual(r.data['is_html'], True)
        self.assertEqual(r.data['is_feint'], False)
        self.assertEqual(r.data['receiver'], 'test@cnic.com;test66@cnic.com;test888@qq.com')

        # 等待邮件异步发送
        time.sleep(0.5)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(Email.objects.count(), 2)
        email1: Email = Email.objects.order_by('-send_time').first()
        self.assertEqual(email1.is_feint, False)
        self.assertEqual(email1.status, 'success')

        # 假装发送，只入库不真实发送
        r = self.client.post(base_url, data={
            'subject': 'test is_feint',
            "receiver": "test@cnic.com",
            "message": "string message对我的",
            "is_html": False,
            'is_feint': 'true'
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(['id', 'subject', 'receiver', 'message', 'is_html', 'status', 'status_desc',
                           'success_time', 'remote_ip'], r.data)
        self.assertEqual(r.data['status'], 'wait')
        self.assertEqual(r.data['is_html'], False)
        self.assertEqual(r.data['receiver'], 'test@cnic.com')
        self.assertEqual(r.data['is_feint'], True)

        # 等待邮件异步发送
        time.sleep(0.5)
        self.assertEqual(len(mail.outbox), 2)   # 不真的发送

        self.assertEqual(Email.objects.count(), 3)
        email1: Email = Email.objects.order_by('-send_time').first()
        self.assertEqual(email1.receiver, 'test@cnic.com')
        self.assertEqual(email1.is_feint, True)

        r = self.client.post(base_url, data={
            'subject': 'test is_feint',
            "receiver": "test@cnic.com",
            "message": "string message对我的ada",
            "is_html": False,
            'is_feint': True
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(['id', 'subject', 'receiver', 'message', 'is_html', 'status', 'status_desc',
                           'success_time', 'remote_ip'], r.data)
        self.assertEqual(r.data['status'], 'wait')
        self.assertEqual(r.data['is_html'], False)
        self.assertEqual(r.data['receiver'], 'test@cnic.com')
        self.assertEqual(r.data['is_feint'], True)

        # 等待邮件异步发送
        time.sleep(0.5)
        self.assertEqual(len(mail.outbox), 2)  # 不真的发送

        self.assertEqual(Email.objects.count(), 4)
        email1: Email = Email.objects.order_by('-send_time').first()
        self.assertEqual(email1.receiver, 'test@cnic.com')
        self.assertEqual(email1.is_feint, True)
