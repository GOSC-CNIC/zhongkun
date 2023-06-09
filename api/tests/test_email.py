from django.urls import reverse
from django.conf import settings
from django.core import mail

from . import MyAPITestCase


class EmailTests(MyAPITestCase):
    def setUp(self):
        pass

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

        settings.API_EMAIL_ALLOWED_IPS = []
        r = self.client.post(base_url, data={
            'subject': 'test',
            "receiver": "test@cnic.com",
            "message": "string message对我的",
            "is_html": False
        })
        self.assertErrorResponse(status_code=403, code='AccessDenied', response=r)

        r = self.client.get(reverse('api:email-realip'))
        real_ip = r.data['real_ip']
        if real_ip:
            settings.API_EMAIL_ALLOWED_IPS = [real_ip]

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
        self.assertEqual(r.data['status'], 'success')
        self.assertEqual(r.data['is_html'], False)
        self.assertEqual(r.data['receiver'], 'test@cnic.com')
        self.assertEqual(len(mail.outbox), 1)

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
            "is_html": True
        })
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(['id', 'subject', 'receiver', 'message', 'is_html', 'status', 'status_desc',
                           'success_time', 'remote_ip'], r.data)
        self.assertEqual(r.data['status'], 'success')
        self.assertEqual(r.data['is_html'], True)
        self.assertEqual(r.data['receiver'], 'test@cnic.com;test66@cnic.com;test888@qq.com')
        self.assertEqual(len(mail.outbox), 2)
