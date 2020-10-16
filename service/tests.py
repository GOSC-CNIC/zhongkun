from django.test import TestCase
from django.contrib.auth import get_user_model

from .managers import UserQuotaManager


User = get_user_model()


class TestUserQuotaManager(TestCase):
    def setUp(self):
        user = User.objects.filter(username='test').first()
        if user is None:
            user = User(username='test')
            user.set_password('test')
            user.save()

        self.user = user

    def test_methods(self):
        vcpus_add = 6
        ram_add = 1024
        disk_size_add = 2048
        public_ip_add = 2
        private_ip_add = 3

        user = self.user
        mgr = UserQuotaManager()
        old_quota = mgr.get_quota(user=user)
        new_quota = mgr.increase(user=user, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
                                 public_ip=public_ip_add, private_ip=private_ip_add)
        self.assertEqual(new_quota.vcpu_total - old_quota.vcpu_total, vcpus_add,
                         msg='UserQuotaManager increase vcpu failed')
        self.assertEqual(new_quota.ram_total - old_quota.ram_total, ram_add,
                         msg='UserQuotaManager increase ram failed')
        self.assertEqual(new_quota.disk_size_total - old_quota.disk_size_total, disk_size_add,
                         msg='UserQuotaManager increase disk_size failed')
        self.assertEqual(new_quota.public_ip_total - old_quota.public_ip_total, public_ip_add,
                         msg='UserQuotaManager increase public_ip failed')
        self.assertEqual(new_quota.private_ip_total - old_quota.private_ip_total, private_ip_add,
                         msg='UserQuotaManager increase private_ip failed')

        ok = mgr.requires(quota=new_quota, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
                          public_ip=public_ip_add, private_ip=private_ip_add)
        self.assertTrue(ok, 'UserQuotaManager requires failed')

        ok = mgr.requires(quota=new_quota, vcpus=vcpus_add)
        self.assertTrue(ok, 'UserQuotaManager requires vcpus failed')
        ok = mgr.requires(quota=new_quota, vcpus=new_quota.vcpu_total + 1)
        self.assertFalse(ok, 'UserQuotaManager requires vcpus failed')

        ok = mgr.requires(quota=new_quota, ram=ram_add)
        self.assertTrue(ok, 'UserQuotaManager requires ram failed')
        ok = mgr.requires(quota=new_quota, ram=new_quota.ram_total + 1)
        self.assertFalse(ok, 'UserQuotaManager requires ram failed')

        ok = mgr.requires(quota=new_quota, disk_size=disk_size_add)
        self.assertTrue(ok, 'UserQuotaManager requires disk_size failed')
        ok = mgr.requires(quota=new_quota, disk_size=new_quota.disk_size_total + 1)
        self.assertFalse(ok, 'UserQuotaManager requires ram failed')

        ok = mgr.requires(quota=new_quota, public_ip=public_ip_add)
        self.assertTrue(ok, 'UserQuotaManager requires public_ip failed')
        ok = mgr.requires(quota=new_quota, public_ip=new_quota.public_ip_total + 1)
        self.assertFalse(ok, 'UserQuotaManager requires public_ip failed')

        ok = mgr.requires(quota=new_quota, private_ip=private_ip_add)
        self.assertTrue(ok, 'UserQuotaManager requires private_ip failed')
        ok = mgr.requires(quota=new_quota, private_ip=new_quota.private_ip_total + 1)
        self.assertFalse(ok, 'UserQuotaManager requires private_ip failed')

        new_quota = mgr.deduct(user=user, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
                               public_ip=public_ip_add, private_ip=private_ip_add)
        self.assertEqual(new_quota.vcpu_used, vcpus_add,
                         msg='UserQuotaManager deduct vcpu failed')
        self.assertEqual(new_quota.ram_used, ram_add,
                         msg='UserQuotaManager deduct ram failed')
        self.assertEqual(new_quota.disk_size_used, disk_size_add,
                         msg='UserQuotaManager deduct disk_size failed')
        self.assertEqual(new_quota.public_ip_used, public_ip_add,
                         msg='UserQuotaManager deduct public_ip failed')
        self.assertEqual(new_quota.private_ip_used, private_ip_add,
                         msg='UserQuotaManager deduct private_ip failed')

        new_quota = mgr.decrease(user=user, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
                                 public_ip=public_ip_add, private_ip=private_ip_add)
        self.assertEqual(new_quota.vcpu_total, old_quota.vcpu_total,
                         msg='UserQuotaManager deduct vcpu failed')
        self.assertEqual(new_quota.ram_total, old_quota.ram_total,
                         msg='UserQuotaManager deduct ram failed')
        self.assertEqual(new_quota.disk_size_total, old_quota.disk_size_total,
                         msg='UserQuotaManager deduct disk_size failed')
        self.assertEqual(new_quota.public_ip_total, old_quota.public_ip_total,
                         msg='UserQuotaManager deduct public_ip failed')
        self.assertEqual(new_quota.private_ip_total, old_quota.private_ip_total,
                         msg='UserQuotaManager deduct private_ip failed')



