from decimal import Decimal

from django.urls import reverse

from utils.test import get_or_create_user, MyAPITestCase
from apps.app_vo.models import VirtualOrganization
from apps.app_vo.managers import VoManager
from apps.app_wallet.managers import PaymentManager


class PonitAccountTests(MyAPITestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.client.force_login(self.user)
        self.user2 = get_or_create_user(username='user2')
        self.vo = VirtualOrganization(
            name='test vo', owner=self.user
        )
        self.vo.save(force_insert=True)

        self.vo2 = VirtualOrganization(
            name='test vo2', owner=self.user2
        )
        self.vo2.save(force_insert=True)

    def test_get_user_point_account(self):
        base_url = reverse('wallet-api:account-balance-balance-user')
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["id", "balance", "creation_time", "user"], r.data)
        self.assertEqual(r.data['user']['id'], self.user.id)
        self.assertEqual(r.data['balance'], '0.00')

        account = PaymentManager().get_user_point_account(user_id=self.user.id)
        account.balance = Decimal('22.33')
        account.save(update_fields=['balance'])
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['balance'], '22.33')

    def test_get_vo_point_account(self):
        base_url = reverse('wallet-api:account-balance-balance-vo', kwargs={'vo_id': self.vo.id})
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["id", "balance", "creation_time", "vo"], r.data)
        self.assertEqual(r.data['vo']['id'], self.vo.id)
        self.assertEqual(r.data['balance'], '0.00')

        account = PaymentManager().get_vo_point_account(vo_id=self.vo.id)
        account.balance = Decimal('66.88')
        account.save(update_fields=['balance'])
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['balance'], '66.88')

        # test vo2
        # no vo permission
        base_url = reverse('wallet-api:account-balance-balance-vo', kwargs={'vo_id': self.vo2.id})
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 403)

        # has vo permission
        VoManager().add_members(vo_id=self.vo2.id, usernames=[self.user.username], admin_user=self.user2)
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertKeysIn(["id", "balance", "creation_time", "vo"], r.data)
        self.assertEqual(r.data['vo']['id'], self.vo2.id)
        self.assertEqual(r.data['balance'], '0.00')

        account = PaymentManager().get_vo_point_account(vo_id=self.vo2.id)
        account.balance = Decimal('166.88')
        account.save(update_fields=['balance'])
        r = self.client.get(base_url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data['balance'], '166.88')
