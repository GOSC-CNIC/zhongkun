from django.urls import reverse

from utils.test import get_or_create_service, get_or_create_user
from utils.model import PayType
from core.request import request_vpn_service
from apps.app_vo.models import VirtualOrganization, VoMember
from apps.app_servers.models import Server
from apps.app_servers.tests import create_server_metadata
from apps.app_servers import format_who_action_str
from . import MyAPITestCase


class VpnAdapterTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.service = get_or_create_service()

    def test_vpn(self):
        vpn_username = 'testvpn'
        r = request_vpn_service(
            service=self.service,
            method='get_vpn_or_create',
            username=vpn_username,
            who_action=format_who_action_str(username='test@qq.com', vo_name='vo名称')
        )
        self.assertEqual(r['username'], vpn_username)
        self.assertIs(r['active'], False)

        r = request_vpn_service(
            service=self.service,
            method='active_vpn',
            username=vpn_username,
            who_action=format_who_action_str(username=vpn_username)
        )
        self.assertIs(r['active'], True)
        self.assertEqual(r['username'], vpn_username)

        r = request_vpn_service(
            service=self.service,
            method='deactive_vpn',
            username=vpn_username,
            who_action=format_who_action_str(username=vpn_username)
        )
        self.assertEqual(r['username'], vpn_username)
        self.assertIs(r['active'], False)


class VpnTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user(password='password')
        self.user2 = get_or_create_user(username='test2', password='password')
        self.client.force_login(self.user)
        self.service = get_or_create_service()

    def test_active_deactive_vpn(self):
        server_user = create_server_metadata(
            service=self.service, user=self.user,
            default_user='', default_password='',
            ipv4='127.0.0.1', remarks='test miss server', pay_type=PayType.PREPAID.value
        )
        detail_url = reverse('api:vpn-detail', kwargs={'service_id': self.service.id})
        r = self.client.get(detail_url)
        self.assertEqual(r.status_code, 200)
        server_user.delete()

        deactive_url = reverse('api:vpn-deactive-vpn', kwargs={'service_id': self.service.id})
        r = self.client.post(deactive_url)
        self.assertEqual(r.status_code, 200)
        r = self.client.get(detail_url)
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.data['vpn']['active'], False)

        active_url = reverse('api:vpn-active-vpn', kwargs={'service_id': self.service.id})
        r = self.client.post(active_url)
        self.assertErrorResponse(status_code=409, code='NoResourcesInService', response=r)

        server_user = create_server_metadata(
            service=self.service, user=self.user,
            default_user='', default_password='',
            ipv4='127.0.0.1', remarks='test miss server', pay_type=PayType.PREPAID.value
        )
        active_url = reverse('api:vpn-active-vpn', kwargs={'service_id': self.service.id})
        r = self.client.post(active_url)
        self.assertEqual(r.status_code, 200)
        r = self.client.get(detail_url)
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.data['vpn']['active'], True)

        server_user.delete()
        r = self.client.post(active_url)
        self.assertErrorResponse(status_code=409, code='NoResourcesInService', response=r)

        vo = VirtualOrganization(
            name='test vo', owner=self.user2
        )
        vo.save(force_insert=True)

        r = self.client.post(active_url)
        self.assertErrorResponse(status_code=409, code='NoResourcesInService', response=r)

        server_vo = create_server_metadata(
            service=self.service, user=self.user, vo_id=vo.id, classification=Server.Classification.VO.value,
            default_user='', default_password='',
            ipv4='127.0.0.1', remarks='test miss server', pay_type=PayType.PREPAID.value
        )

        r = self.client.post(active_url)
        self.assertErrorResponse(status_code=409, code='NoResourcesInService', response=r)

        member = VoMember(user_id=self.user.id, vo_id=vo.id, role=VoMember.Role.MEMBER.value,
                          inviter=self.user.username, inviter_id=self.user.id)
        member.save(force_insert=True)

        r = self.client.post(active_url)
        self.assertEqual(r.status_code, 200)

        member.delete()
        r = self.client.post(active_url)
        self.assertErrorResponse(status_code=409, code='NoResourcesInService', response=r)

        member.save(force_insert=True)
        r = self.client.post(active_url)
        self.assertEqual(r.status_code, 200)

        server_vo.delete()
        r = self.client.post(active_url)
        self.assertErrorResponse(status_code=409, code='NoResourcesInService', response=r)

        r = self.client.get(detail_url)
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.data['vpn']['active'], True)

        deactive_url = reverse('api:vpn-deactive-vpn', kwargs={'service_id': self.service.id})
        r = self.client.post(deactive_url)
        self.assertEqual(r.status_code, 200)
        r = self.client.get(detail_url)
        self.assertEqual(r.status_code, 200)
        self.assertIs(r.data['vpn']['active'], False)
