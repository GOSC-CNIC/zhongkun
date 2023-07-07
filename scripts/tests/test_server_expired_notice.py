from datetime import timedelta

from django.utils import timezone
from django.test.testcases import TransactionTestCase
from django.core import mail

from utils.model import PayType
from utils.test import get_or_create_user
from vo.models import VirtualOrganization, VoMember
from servers.models import Server
from scripts.workers.server_notifier import (
    ServerNotifier
)
from api.tests.tests import create_server_metadata


class ServerExpiredTests(TransactionTestCase):
    def setUp(self):
        pass

    def init_users_and_vo(self):
        self.user1 = get_or_create_user(username='user1@cnic.cn')
        self.user2 = get_or_create_user(username='user2@qq.com')
        self.user3 = get_or_create_user(username='user3@qq.com')
        self.user4 = get_or_create_user(username='user4@cnic.cn')
        self.user5 = get_or_create_user(username='user5@cnic.cn')
        self.user6 = get_or_create_user(username='user6@cnic.cn')

        # user1\2\3\4\5\6
        self.vo1 = VirtualOrganization(name='vo1', owner_id=self.user1.id)
        self.vo1.save(force_insert=True)
        VoMember(user=self.user2, vo=self.vo1, role=VoMember.Role.LEADER.value).save(force_insert=True)
        VoMember(user=self.user3, vo=self.vo1, role=VoMember.Role.LEADER.value).save(force_insert=True)
        VoMember(user=self.user4, vo=self.vo1, role=VoMember.Role.MEMBER.value).save(force_insert=True)
        VoMember(user=self.user5, vo=self.vo1, role=VoMember.Role.MEMBER.value).save(force_insert=True)
        VoMember(user=self.user6, vo=self.vo1, role=VoMember.Role.MEMBER.value).save(force_insert=True)
        # user2\3\4\5\6
        self.vo2 = VirtualOrganization(name='vo2', owner_id=self.user2.id)
        self.vo2.save(force_insert=True)
        VoMember(user=self.user3, vo=self.vo2, role=VoMember.Role.LEADER.value).save(force_insert=True)
        VoMember(user=self.user4, vo=self.vo2, role=VoMember.Role.LEADER.value).save(force_insert=True)
        VoMember(user=self.user5, vo=self.vo2, role=VoMember.Role.LEADER.value).save(force_insert=True)
        VoMember(user=self.user6, vo=self.vo2, role=VoMember.Role.MEMBER.value).save(force_insert=True)
        # user3\4\5\6
        self.vo3 = VirtualOrganization(name='vo3', owner_id=self.user3.id)
        self.vo3.save(force_insert=True)
        VoMember(user=self.user4, vo=self.vo3, role=VoMember.Role.LEADER.value).save(force_insert=True)
        VoMember(user=self.user5, vo=self.vo3, role=VoMember.Role.MEMBER.value).save(force_insert=True)
        VoMember(user=self.user6, vo=self.vo3, role=VoMember.Role.LEADER.value).save(force_insert=True)
        # user4\5\6
        self.vo4 = VirtualOrganization(name='vo4', owner_id=self.user4.id)
        self.vo4.save(force_insert=True)
        VoMember(user=self.user5, vo=self.vo4, role=VoMember.Role.MEMBER.value).save(force_insert=True)
        VoMember(user=self.user6, vo=self.vo4, role=VoMember.Role.LEADER.value).save(force_insert=True)
        # user5\6
        self.vo5 = VirtualOrganization(name='vo5', owner_id=self.user5.id)
        self.vo5.save(force_insert=True)
        VoMember(user=self.user6, vo=self.vo5, role=VoMember.Role.LEADER.value).save(force_insert=True)
        # user6
        self.vo6 = VirtualOrganization(name='vo6', owner_id=self.user6.id)
        self.vo6.save(force_insert=True)

        nt = timezone.now()
        # user1, 过期0天
        self.server1 = create_server_metadata(
            service=None, user=self.user1, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.1', pay_type=PayType.PREPAID.value, expiration_time=nt
        )
        # user2, 过期2天
        self.server2 = create_server_metadata(
            service=None, user=self.user2, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.2', pay_type=PayType.PREPAID.value, expiration_time=nt-timedelta(days=2)
        )
        # user3, 过期6天
        self.server3 = create_server_metadata(
            service=None, user=self.user3, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.3', pay_type=PayType.PREPAID.value, expiration_time=nt - timedelta(days=6)
        )
        # user4, 6天后到期
        self.server4 = create_server_metadata(
            service=None, user=self.user4, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.4', pay_type=PayType.PREPAID.value, expiration_time=nt + timedelta(days=6)
        )
        # user5, 10天后到期
        self.server5 = create_server_metadata(
            service=None, user=self.user5, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.5', pay_type=PayType.PREPAID.value, expiration_time=nt + timedelta(days=10)
        )
        # user6, 20天后到期
        self.server6 = create_server_metadata(
            service=None, user=self.user6, vo_id=None, classification=Server.Classification.PERSONAL.value,
            ipv4='10.0.0.6', pay_type=PayType.PREPAID.value, expiration_time=nt + timedelta(days=20)
        )
        # ------ vo ------
        # vo1, 1天后过期
        self.server1_vo1 = create_server_metadata(
            service=None, user=self.user1, vo_id=self.vo1.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.11', pay_type=PayType.PREPAID.value, expiration_time=nt + timedelta(days=1)
        )
        # vo2, 过期3天，按量计费
        self.server2_vo2 = create_server_metadata(
            service=None, user=self.user1, vo_id=self.vo2.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.12', pay_type=PayType.POSTPAID.value, expiration_time=nt - timedelta(days=3)
        )
        # vo3, 16天后到期
        self.server3_vo3 = create_server_metadata(
            service=None, user=self.user3, vo_id=self.vo3.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.13', pay_type=PayType.PREPAID.value, expiration_time=nt + timedelta(days=16)
        )
        # vo4, 3天后到期
        self.server4_vo4 = create_server_metadata(
            service=None, user=self.user4, vo_id=self.vo4.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.14', pay_type=PayType.PREPAID.value, expiration_time=nt + timedelta(days=3)
        )
        # vo5, 过期16天
        self.server5_vo5 = create_server_metadata(
            service=None, user=self.user5, vo_id=self.vo5.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.15', pay_type=PayType.PREPAID.value, expiration_time=nt - timedelta(days=16)
        )
        # vo6, 到期2天
        self.server6_vo6 = create_server_metadata(
            service=None, user=self.user6, vo_id=self.vo6.id, classification=Server.Classification.VO.value,
            ipv4='10.0.0.16', pay_type=PayType.PREPAID.value, expiration_time=nt - timedelta(days=2)
        )

    def test_server_expired(self):
        self.init_users_and_vo()
        snfr = ServerNotifier(is_update_server_email_time=True, filter_out_notified=True)
        # after_days = 0, need email 5
        cxt1 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user1.id, username=self.user1.username, after_days=0)
        user1_servers = cxt1['user_servers']
        user1_vo_servers = cxt1['vo_servers']
        self.assertEqual(len(user1_servers), 1)
        self.assertEqual(len(user1_vo_servers), 0)
        self.assertEqual(self.server1.id, user1_servers[0].id)

        cxt2 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user2.id, username=self.user2.username, after_days=0)
        user2_servers = cxt2['user_servers']
        user2_vo_servers = cxt2['vo_servers']
        self.assertEqual(len(user2_servers), 1)
        self.assertEqual(len(user2_vo_servers), 0)
        self.assertEqual(self.server2.id, user2_servers[0].id)

        cxt3 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user3.id, username=self.user3.username, after_days=0)
        user3_servers = cxt3['user_servers']
        user3_vo_servers = cxt3['vo_servers']
        self.assertEqual(len(user3_servers), 1)
        self.assertEqual(len(user3_vo_servers), 0)
        self.assertEqual(self.server3.id, user3_servers[0].id)

        cxt4 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user4.id, username=self.user4.username, after_days=0)
        user4_servers = cxt4['user_servers']
        user4_vo_servers = cxt4['vo_servers']
        self.assertEqual(len(user4_servers), 0)
        self.assertEqual(len(user4_vo_servers), 0)

        cxt5 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user5.id, username=self.user5.username, after_days=0)
        user5_servers = cxt5['user_servers']
        user5_vo_servers = cxt5['vo_servers']
        self.assertEqual(len(user5_servers), 0)
        self.assertEqual(len(user5_vo_servers), 1)
        self.assertEqual(self.server5_vo5.id, user5_vo_servers[0].id)

        cxt6 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user6.id, username=self.user6.username, after_days=0)
        user6_servers = cxt6['user_servers']
        user6_vo_servers = cxt6['vo_servers']
        self.assertEqual(len(user6_servers), 0)
        self.assertEqual(len(user6_vo_servers), 2)

        # after_days = 7, , need email 6
        cxt1 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user1.id, username=self.user1.username, after_days=7)
        user1_servers = cxt1['user_servers']
        user1_vo_servers = cxt1['vo_servers']
        self.assertEqual(len(user1_servers), 1)
        self.assertEqual(len(user1_vo_servers), 1)
        self.assertEqual(self.server1.id, user1_servers[0].id)
        self.assertEqual(self.server1_vo1.id, user1_vo_servers[0].id)

        cxt2 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user2.id, username=self.user2.username, after_days=7)
        user2_servers = cxt2['user_servers']
        user2_vo_servers = cxt2['vo_servers']
        self.assertEqual(len(user2_servers), 1)
        self.assertEqual(len(user2_vo_servers), 1)
        self.assertEqual(self.server2.id, user2_servers[0].id)
        self.assertEqual(self.server1_vo1.id, user2_vo_servers[0].id)

        cxt3 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user3.id, username=self.user3.username, after_days=7)
        user3_servers = cxt3['user_servers']
        user3_vo_servers = cxt3['vo_servers']
        self.assertEqual(len(user3_servers), 1)
        self.assertEqual(len(user3_vo_servers), 1)
        self.assertEqual(self.server3.id, user3_servers[0].id)
        self.assertEqual(self.server1_vo1.id, user3_vo_servers[0].id)

        cxt4 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user4.id, username=self.user4.username, after_days=7)
        user4_servers = cxt4['user_servers']
        user4_vo_servers = cxt4['vo_servers']
        self.assertEqual(len(user4_servers), 1)
        self.assertEqual(len(user4_vo_servers), 2)

        cxt5 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user5.id, username=self.user5.username, after_days=7)
        user5_servers = cxt5['user_servers']
        user5_vo_servers = cxt5['vo_servers']
        self.assertEqual(len(user5_servers), 0)
        self.assertEqual(len(user5_vo_servers), 3)
        self.assertEqual(self.server1_vo1.id, user5_vo_servers[0].id)
        self.assertEqual(self.server4_vo4.id, user5_vo_servers[1].id)
        self.assertEqual(self.server5_vo5.id, user5_vo_servers[2].id)

        cxt6 = snfr.get_personal_vo_expired_servers_context(
            user_id=self.user6.id, username=self.user6.username, after_days=7)
        user6_servers = cxt6['user_servers']
        user6_vo_servers = cxt6['vo_servers']
        self.assertEqual(len(user6_servers), 0)
        self.assertEqual(len(user6_vo_servers), 4)
        self.assertEqual(self.server1_vo1.id, user6_vo_servers[0].id)
        self.assertEqual(self.server4_vo4.id, user6_vo_servers[1].id)
        self.assertEqual(self.server5_vo5.id, user6_vo_servers[2].id)
        self.assertEqual(self.server6_vo6.id, user6_vo_servers[3].id)

        self.assertEqual(len(mail.outbox), 0)
        ServerNotifier(is_update_server_email_time=False, filter_out_notified=True).run(after_days=0)
        self.assertEqual(len(mail.outbox), 5)

        ServerNotifier(is_update_server_email_time=False, filter_out_notified=True).run(after_days=7)
        self.assertEqual(len(mail.outbox), 11)

        ServerNotifier(is_update_server_email_time=True, filter_out_notified=True).run(after_days=0)
        self.assertEqual(len(mail.outbox), 16)

        ServerNotifier(is_update_server_email_time=True, filter_out_notified=True).run(after_days=0)
        self.assertEqual(len(mail.outbox), 16)

        ServerNotifier(is_update_server_email_time=True, filter_out_notified=True).run(after_days=7)
        self.assertEqual(len(mail.outbox), 16 + 6)

        ServerNotifier(is_update_server_email_time=True, filter_out_notified=True).run(after_days=7)
        self.assertEqual(len(mail.outbox), 22)

        ServerNotifier(is_update_server_email_time=True, filter_out_notified=False).run(after_days=0)
        self.assertEqual(len(mail.outbox), 22 + 5)

        ServerNotifier(is_update_server_email_time=True, filter_out_notified=False).run(after_days=7)
        self.assertEqual(len(mail.outbox), 27 + 6)
