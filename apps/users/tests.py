from django.test import TestCase
from django.core import mail

from .models import Email


class EmailTest(TestCase):
    def test_send_email(self):
        self.assertEqual(len(mail.outbox), 0)
        Email.send_email(
            subject='test发送邮件1', receivers=['tomtest1@cnic.cnn', 'tomtest2@qq.com'], message='message邮件内容',
            tag=Email.Tag.TICKET.value, save_db=False
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(Email.objects.count(), 0)

        email2 = Email.send_email(
            subject='test发送邮件2', receivers=['tomtest1@cnic.cnn', 'tomtest2@qq.com'], message='message邮件内容',
            tag=Email.Tag.TICKET.value
        )
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(Email.objects.count(), 1)
        self.assertEqual(email2.status, Email.Status.SUCCESS.value)
        email2.refresh_from_db()
        self.assertEqual(email2.status, Email.Status.SUCCESS.value)
        self.assertEqual(email2.tag, Email.Tag.TICKET.value)
        self.assertIsNotNone(email2.success_time)
        self.assertIs(email2.is_html, False)

        email3 = Email.send_email(
            subject='test发送邮件3', receivers=['tomtest1@cnic.cnn', 'tomtest2@qq.com'], message='',
            html_message='message邮件内容',
            tag=Email.Tag.MONTH.value
        )
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(Email.objects.count(), 2)
        self.assertEqual(email3.status, Email.Status.SUCCESS.value)
        email3.refresh_from_db()
        self.assertEqual(email3.status, Email.Status.SUCCESS.value)
        self.assertEqual(email3.tag, Email.Tag.MONTH.value)
        self.assertIsNotNone(email3.success_time)
        self.assertIs(email3.is_html, True)

        email4 = Email.send_email(
            subject='test发送邮件4', receivers=[], message='',
            html_message='message邮件内容',
            tag=Email.Tag.COUPON.value
        )
        self.assertIsNone(email4)

        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(Email.objects.count(), 3)
        email4 = Email.objects.order_by('-send_time').first()
        self.assertEqual(email4.subject, 'test发送邮件4')
        self.assertEqual(email4.status, Email.Status.FAILED.value)
        self.assertEqual(email4.tag, Email.Tag.COUPON.value)
        self.assertIsNone(email4.success_time)
        self.assertIs(email4.is_html, True)
