from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model

from service.models import DataCenter
from .managers import UserQuotaManager, DataCenterPrivateQuotaManager, DataCenterShareQuotaManager
from core.errors import QuotaShortageError


User = get_user_model()


class TestUserQuotaManager(TransactionTestCase):
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
        with self.assertRaises(QuotaShortageError, msg='UserQuotaManager requires vcpus failed'):
            mgr.requires(quota=new_quota, vcpus=new_quota.vcpu_total + 1)

        ok = mgr.requires(quota=new_quota, ram=ram_add)
        self.assertTrue(ok, 'UserQuotaManager requires ram failed')
        with self.assertRaises(QuotaShortageError, msg='UserQuotaManager requires ram failed'):
            mgr.requires(quota=new_quota, ram=new_quota.ram_total + 1)

        ok = mgr.requires(quota=new_quota, disk_size=disk_size_add)
        self.assertTrue(ok, 'UserQuotaManager requires disk_size failed')
        with self.assertRaises(QuotaShortageError, msg='UserQuotaManager requires ram failed'):
            mgr.requires(quota=new_quota, disk_size=new_quota.disk_size_total + 1)

        ok = mgr.requires(quota=new_quota, public_ip=public_ip_add)
        self.assertTrue(ok, 'UserQuotaManager requires public_ip failed')
        with self.assertRaises(QuotaShortageError, msg='UserQuotaManager requires public_ip failed'):
            mgr.requires(quota=new_quota, public_ip=new_quota.public_ip_total + 1)

        ok = mgr.requires(quota=new_quota, private_ip=private_ip_add)
        self.assertTrue(ok, 'UserQuotaManager requires private_ip failed')
        with self.assertRaises(QuotaShortageError, msg='UserQuotaManager requires private_ip failed'):
            mgr.requires(quota=new_quota, private_ip=new_quota.private_ip_total + 1)

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

        new_quota = mgr.release(user=user, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
                                public_ip=public_ip_add, private_ip=private_ip_add)
        self.assertEqual(new_quota.vcpu_used, old_quota.vcpu_used,
                         msg='UserQuotaManager release vcpu failed')
        self.assertEqual(new_quota.ram_used, old_quota.ram_used,
                         msg='UserQuotaManager release ram failed')
        self.assertEqual(new_quota.disk_size_used, old_quota.disk_size_used,
                         msg='UserQuotaManager release disk_size failed')
        self.assertEqual(new_quota.public_ip_used, old_quota.public_ip_used,
                         msg='UserQuotaManager release public_ip failed')
        self.assertEqual(new_quota.private_ip_used, old_quota.private_ip_used,
                         msg='UserQuotaManager release private_ip failed')

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


class TestDataCenterQuotaManager(TransactionTestCase):
    def setUp(self):
        center = DataCenter.objects.filter(name='test').first()
        if center is None:
            center = DataCenter(name='test')
            center.save()

        self.center = center

    def manager_test(self, manager_cls):
        vcpus_add = 6
        ram_add = 1024
        disk_size_add = 2048
        public_ip_add = 2
        private_ip_add = 3

        mgr = manager_cls()
        center = self.center
        old_quota = mgr.get_quota(center=center)
        new_quota = mgr.increase(center=center, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
                                 public_ip=public_ip_add, private_ip=private_ip_add)
        self.assertEqual(new_quota.vcpu_total - old_quota.vcpu_total, vcpus_add,
                         msg=f'{manager_cls} increase vcpu failed')
        self.assertEqual(new_quota.ram_total - old_quota.ram_total, ram_add,
                         msg=f'{manager_cls} increase ram failed')
        self.assertEqual(new_quota.disk_size_total - old_quota.disk_size_total, disk_size_add,
                         msg=f'{manager_cls} increase disk_size failed')
        self.assertEqual(new_quota.public_ip_total - old_quota.public_ip_total, public_ip_add,
                         msg=f'{manager_cls} increase public_ip failed')
        self.assertEqual(new_quota.private_ip_total - old_quota.private_ip_total, private_ip_add,
                         msg=f'{manager_cls} increase private_ip failed')

        ok = mgr.requires(quota=new_quota, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
                          public_ip=public_ip_add, private_ip=private_ip_add)
        self.assertTrue(ok, f'{manager_cls} requires failed')

        ok = mgr.requires(quota=new_quota, vcpus=vcpus_add)
        self.assertTrue(ok, f'{manager_cls} requires vcpus failed')
        with self.assertRaises(QuotaShortageError, msg=f'{manager_cls} requires vcpus failed'):
            mgr.requires(quota=new_quota, vcpus=new_quota.vcpu_total + 1)

        ok = mgr.requires(quota=new_quota, ram=ram_add)
        self.assertTrue(ok, f'{manager_cls} requires ram failed')
        with self.assertRaises(QuotaShortageError, msg=f'{manager_cls} requires ram failed'):
            mgr.requires(quota=new_quota, ram=new_quota.ram_total + 1)

        ok = mgr.requires(quota=new_quota, disk_size=disk_size_add)
        self.assertTrue(ok, f'{manager_cls} requires disk_size failed')
        with self.assertRaises(QuotaShortageError, msg=f'{manager_cls} requires ram failed'):
            mgr.requires(quota=new_quota, disk_size=new_quota.disk_size_total + 1)

        ok = mgr.requires(quota=new_quota, public_ip=public_ip_add)
        self.assertTrue(ok, f'{manager_cls} requires public_ip failed')
        with self.assertRaises(QuotaShortageError, msg=f'{manager_cls} requires public_ip failed'):
            mgr.requires(quota=new_quota, public_ip=new_quota.public_ip_total + 1)

        ok = mgr.requires(quota=new_quota, private_ip=private_ip_add)
        self.assertTrue(ok, f'{manager_cls} requires private_ip failed')
        with self.assertRaises(QuotaShortageError, msg=f'{manager_cls} requires private_ip failed'):
            mgr.requires(quota=new_quota, private_ip=new_quota.private_ip_total + 1)

        new_quota = mgr.deduct(center=center, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
                               public_ip=public_ip_add, private_ip=private_ip_add)
        self.assertEqual(new_quota.vcpu_used, vcpus_add,
                         msg=f'{manager_cls} deduct vcpu failed')
        self.assertEqual(new_quota.ram_used, ram_add,
                         msg=f'{manager_cls} deduct ram failed')
        self.assertEqual(new_quota.disk_size_used, disk_size_add,
                         msg=f'{manager_cls} deduct disk_size failed')
        self.assertEqual(new_quota.public_ip_used, public_ip_add,
                         msg=f'{manager_cls} deduct public_ip failed')
        self.assertEqual(new_quota.private_ip_used, private_ip_add,
                         msg=f'{manager_cls} deduct private_ip failed')

        new_quota = mgr.release(center=center, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
                                public_ip=public_ip_add, private_ip=private_ip_add)
        self.assertEqual(new_quota.vcpu_used, old_quota.vcpu_used,
                         msg=f'{manager_cls} release vcpu failed')
        self.assertEqual(new_quota.ram_used, old_quota.ram_used,
                         msg=f'{manager_cls} release ram failed')
        self.assertEqual(new_quota.disk_size_used, old_quota.disk_size_used,
                         msg=f'{manager_cls} release disk_size failed')
        self.assertEqual(new_quota.public_ip_used, old_quota.public_ip_used,
                         msg=f'{manager_cls} release public_ip failed')
        self.assertEqual(new_quota.private_ip_used, old_quota.private_ip_used,
                         msg=f'{manager_cls} release private_ip failed')

        new_quota = mgr.decrease(center=center, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
                                 public_ip=public_ip_add, private_ip=private_ip_add)
        self.assertEqual(new_quota.vcpu_total, old_quota.vcpu_total,
                         msg=f'{manager_cls} deduct vcpu failed')
        self.assertEqual(new_quota.ram_total, old_quota.ram_total,
                         msg=f'{manager_cls} deduct ram failed')
        self.assertEqual(new_quota.disk_size_total, old_quota.disk_size_total,
                         msg=f'{manager_cls} deduct disk_size failed')
        self.assertEqual(new_quota.public_ip_total, old_quota.public_ip_total,
                         msg=f'{manager_cls} deduct public_ip failed')
        self.assertEqual(new_quota.private_ip_total, old_quota.private_ip_total,
                         msg=f'{manager_cls} deduct private_ip failed')

    def test_shared_quota_manager(self):
        self.manager_test(DataCenterShareQuotaManager)

    def test_private_quota_manager(self):
        self.manager_test(DataCenterPrivateQuotaManager)
