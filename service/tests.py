from django.test import TransactionTestCase, SimpleTestCase
from django.contrib.auth import get_user_model

from core.errors import QuotaShortageError
from core.quota import QuotaAPI
from utils.test import get_or_create_user, get_or_create_service
from utils.crypto import Encryptor
from .managers import UserQuotaManager, ServicePrivateQuotaManager, ServiceShareQuotaManager

User = get_user_model()


class TestUserQuotaManager(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()

    def test_methods(self):
        vcpus_add = 6
        ram_add = 1024
        disk_size_add = 2048
        public_ip_add = 2
        private_ip_add = 3

        user = self.user
        mgr = UserQuotaManager()
        old_quota = mgr.get_base_quota_queryset(user=user).first()
        if not old_quota:
            old_quota = mgr.create_quota(user=user, service=self.service)

        new_quota = mgr.increase(user=user, quota_id=old_quota.id, vcpus=vcpus_add, ram=ram_add,
                                 disk_size=disk_size_add, public_ip=public_ip_add, private_ip=private_ip_add)
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

        new_quota = mgr.deduct(user=user, quota_id=old_quota.id, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
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

        new_quota = mgr.release(user=user, quota_id=old_quota.id, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
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

        new_quota = mgr.decrease(user=user, quota_id=old_quota.id, vcpus=vcpus_add, ram=ram_add,
                                 disk_size=disk_size_add, public_ip=public_ip_add, private_ip=private_ip_add)
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


class TestServiceQuotaManager(TransactionTestCase):
    def setUp(self):
        self.service = get_or_create_service()

    def manager_test(self, manager_cls):
        vcpus_add = 6
        ram_add = 1024
        disk_size_add = 2048
        public_ip_add = 2
        private_ip_add = 3

        mgr = manager_cls()
        service = self.service
        old_quota = mgr.get_quota(service=service)
        new_quota = mgr.increase(service=service, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
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

        new_quota = mgr.deduct(service=service, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
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

        new_quota = mgr.release(service=service, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
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

        new_quota = mgr.decrease(service=service, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
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
        self.manager_test(ServiceShareQuotaManager)

    def test_private_quota_manager(self):
        self.manager_test(ServicePrivateQuotaManager)


class QuotaAPITests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()
        self.user_quota = UserQuotaManager().create_quota(
            user=self.user, service=self.service)

        mgr = ServicePrivateQuotaManager()
        service = self.service
        self.pri_quota = mgr.get_quota(service=service)

    def test_quota_apply_and_release(self):
        vcpus_add = 6
        ram_add = 1024
        disk_size_add = 2048
        public_ip_add = 1
        private_ip_add = 1

        vcpus_apply = 2
        ram_apply = 1024
        is_public_ip_apply = True

        # 配额都是0
        with self.assertRaises(QuotaShortageError):
            QuotaAPI.server_create_quota_apply(service=self.service, user=self.user,
                                               vcpu=1, ram=1024, public_ip=True, user_quota_id=self.user_quota.id)

        # 增加用户配额
        self.user_quota = UserQuotaManager().increase(
            user=self.user, quota_id=self.user_quota.id, vcpus=vcpus_add,
            ram=ram_add, disk_size=disk_size_add, public_ip=public_ip_add,
            private_ip=private_ip_add)

        with self.assertRaises(QuotaShortageError):
            QuotaAPI.server_create_quota_apply(
                service=self.service, user=self.user, vcpu=vcpus_apply, ram=ram_apply,
                public_ip=is_public_ip_apply, user_quota_id=self.user_quota.id)

        # 增加服务私有配额
        self.pri_quota = ServicePrivateQuotaManager().increase(
            service=self.service, vcpus=vcpus_add, ram=ram_add, disk_size=disk_size_add,
            public_ip=public_ip_add, private_ip=private_ip_add)

        # 创建vm扣除配额
        user_quota = QuotaAPI.server_create_quota_apply(
            service=self.service, user=self.user, vcpu=vcpus_apply, ram=ram_apply,
            public_ip=is_public_ip_apply, user_quota_id=self.user_quota.id)
        self.assertIsInstance(user_quota, UserQuotaManager.MODEL)

        self.user_quota.refresh_from_db()
        self.assertEqual(self.user_quota.vcpu_total, vcpus_add)
        self.assertEqual(self.user_quota.vcpu_used, vcpus_apply)
        self.assertEqual(self.user_quota.ram_total, ram_add)
        self.assertEqual(self.user_quota.ram_used, ram_apply)
        self.assertEqual(self.user_quota.disk_size_total, disk_size_add)
        self.assertEqual(self.user_quota.disk_size_used, 0)
        self.assertEqual(self.user_quota.public_ip_total, public_ip_add)
        self.assertEqual(self.user_quota.private_ip_total, private_ip_add)
        if is_public_ip_apply:
            self.assertEqual(self.user_quota.public_ip_used, 1)
            self.assertEqual(self.user_quota.private_ip_used, 0)
        else:
            self.assertEqual(self.user_quota.public_ip_used, 0)
            self.assertEqual(self.user_quota.private_ip_used, 1)

        self.pri_quota.refresh_from_db()
        self.assertEqual(self.pri_quota.vcpu_total, vcpus_add)
        self.assertEqual(self.pri_quota.vcpu_used, vcpus_apply)
        self.assertEqual(self.pri_quota.ram_total, ram_add)
        self.assertEqual(self.pri_quota.ram_used, ram_apply)
        self.assertEqual(self.pri_quota.disk_size_total, disk_size_add)
        self.assertEqual(self.pri_quota.disk_size_used, 0)
        self.assertEqual(self.pri_quota.public_ip_total, public_ip_add)
        self.assertEqual(self.pri_quota.private_ip_total, private_ip_add)
        if is_public_ip_apply:
            self.assertEqual(self.pri_quota.public_ip_used, 1)
            self.assertEqual(self.pri_quota.private_ip_used, 0)
        else:
            self.assertEqual(self.pri_quota.public_ip_used, 0)
            self.assertEqual(self.pri_quota.private_ip_used, 1)

        # 创建失败，释放服务配额和用户配额
        QuotaAPI().server_quota_release(self.service, vcpu=vcpus_apply,
                                        ram=ram_apply, public_ip=is_public_ip_apply,
                                        user=self.user, user_quota_id=self.user_quota.id)

        self.user_quota.refresh_from_db()
        self.assertEqual(self.user_quota.vcpu_used, 0)
        self.assertEqual(self.user_quota.ram_used, 0)
        self.assertEqual(self.user_quota.disk_size_used, 0)
        self.assertEqual(self.user_quota.public_ip_used, 0)
        self.assertEqual(self.user_quota.private_ip_used, 0)

        self.pri_quota.refresh_from_db()
        self.assertEqual(self.pri_quota.vcpu_used, 0)
        self.assertEqual(self.pri_quota.ram_used, 0)
        self.assertEqual(self.pri_quota.disk_size_used, 0)
        self.assertEqual(self.pri_quota.public_ip_used, 0)
        self.assertEqual(self.pri_quota.private_ip_used, 0)

        # 创建vm扣除配额
        is_public_ip_apply = False
        user_quota = QuotaAPI.server_create_quota_apply(
            service=self.service, user=self.user, vcpu=vcpus_apply, ram=ram_apply,
            public_ip=is_public_ip_apply, user_quota_id=self.user_quota.id)
        self.assertIsInstance(user_quota, UserQuotaManager.MODEL)

        self.pri_quota.refresh_from_db()
        self.assertEqual(self.pri_quota.vcpu_used, vcpus_apply)
        self.assertEqual(self.pri_quota.ram_used, ram_apply)
        self.assertEqual(self.pri_quota.disk_size_used, 0)
        if is_public_ip_apply:
            self.assertEqual(self.pri_quota.public_ip_used, 1)
            self.assertEqual(self.pri_quota.private_ip_used, 0)
        else:
            self.assertEqual(self.pri_quota.public_ip_used, 0)
            self.assertEqual(self.pri_quota.private_ip_used, 1)

        self.user_quota.refresh_from_db()
        self.assertEqual(self.user_quota.vcpu_used, vcpus_apply)
        self.assertEqual(self.user_quota.ram_used, ram_apply)
        self.assertEqual(self.user_quota.disk_size_used, 0)
        if is_public_ip_apply:
            self.assertEqual(self.user_quota.public_ip_used, 1)
            self.assertEqual(self.user_quota.private_ip_used, 0)
        else:
            self.assertEqual(self.user_quota.public_ip_used, 0)
            self.assertEqual(self.user_quota.private_ip_used, 1)

        # 释放服务配额
        QuotaAPI().server_quota_release(self.service, vcpu=vcpus_apply,
                                        ram=ram_apply, public_ip=is_public_ip_apply)

        self.pri_quota.refresh_from_db()
        self.assertEqual(self.pri_quota.vcpu_used, 0)
        self.assertEqual(self.pri_quota.ram_used, 0)
        self.assertEqual(self.pri_quota.disk_size_used, 0)
        self.assertEqual(self.pri_quota.public_ip_used, 0)
        self.assertEqual(self.pri_quota.private_ip_used, 0)

        self.user_quota.refresh_from_db()
        self.assertEqual(self.user_quota.vcpu_used, vcpus_apply)
        self.assertEqual(self.user_quota.ram_used, ram_apply)
        self.assertEqual(self.user_quota.disk_size_used, 0)
        if is_public_ip_apply:
            self.assertEqual(self.user_quota.public_ip_used, 1)
            self.assertEqual(self.user_quota.private_ip_used, 0)
        else:
            self.assertEqual(self.user_quota.public_ip_used, 0)
            self.assertEqual(self.user_quota.private_ip_used, 1)


class TestEncrypter(SimpleTestCase):
    def normal_test(self, encrypter, text):
        encypted = encrypter.encrypt(text)
        raw_text = encrypter.decrypt(encypted)
        self.assertEqual(text, raw_text)

    def test_encrypt(self):
        text1 = 'iefaba!@#4567$%&^&?<<adJGKKkhafoewgfieuq:"{}HHV'
        text2 = 'iefaba!@#4567$%&^&?<<adJGK发hi发fieuq:"{}HHV'
        text3 = ''
        text4 = '哈'
        encrypter = Encryptor(key="""!2#$fk*76/';:""")
        self.normal_test(encrypter, text1)
        self.normal_test(encrypter, text2)
        self.normal_test(encrypter, text3)
        self.normal_test(encrypter, text4)

        with self.assertRaises(encrypter.InvalidEncrypted):
            encrypter.decrypt('x33')

        with self.assertRaises(encrypter.InvalidEncrypted):
            encrypter.decrypt('xsdf')
