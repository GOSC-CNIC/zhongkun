from django.test import TransactionTestCase, SimpleTestCase
from django.contrib.auth import get_user_model

from core.errors import QuotaShortageError, QuotaOnlyIncreaseError
from core.quota import QuotaAPI
from utils.test import get_or_create_user, get_or_create_service
from utils.crypto import Encryptor
from ..managers import ServicePrivateQuotaManager, ServiceShareQuotaManager

User = get_user_model()


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
        new_quota = mgr.increase(service=service, vcpus=vcpus_add, ram_gib=ram_add, disk_size=disk_size_add,
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

        ok = mgr.requires(quota=new_quota, vcpus=vcpus_add, ram_gib=ram_add, disk_size=disk_size_add,
                          public_ip=public_ip_add, private_ip=private_ip_add)
        self.assertTrue(ok, f'{manager_cls} requires failed')

        ok = mgr.requires(quota=new_quota, vcpus=vcpus_add)
        self.assertTrue(ok, f'{manager_cls} requires vcpus failed')
        with self.assertRaises(QuotaShortageError, msg=f'{manager_cls} requires vcpus failed'):
            mgr.requires(quota=new_quota, vcpus=new_quota.vcpu_total + 1)

        ok = mgr.requires(quota=new_quota, ram_gib=ram_add)
        self.assertTrue(ok, f'{manager_cls} requires ram failed')
        with self.assertRaises(QuotaShortageError, msg=f'{manager_cls} requires ram failed'):
            mgr.requires(quota=new_quota, ram_gib=new_quota.ram_total + 1)

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

        new_quota = mgr.deduct(service=service, vcpus=vcpus_add, ram_gib=ram_add, disk_size=disk_size_add,
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

        new_quota = mgr.release(service=service, vcpus=vcpus_add, ram_gib=ram_add, disk_size=disk_size_add,
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

        new_quota = mgr.decrease(service=service, vcpus=vcpus_add, ram_gib=ram_add, disk_size=disk_size_add,
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

    def update_case(self, manager_cls):
        update_vcpu = 8
        update_ram = 1024   # MB
        update_disk = 2048  # Gb
        update_private_ip = 10
        update_public_ip = 9

        mgr = manager_cls()
        service = self.service
        mgr.update(service=service, vcpus=update_vcpu, ram_gib=update_ram, disk_size=update_disk,
                   public_ip=update_public_ip, private_ip=update_private_ip, only_increase=True)
        new_quota = mgr.get_quota(service=service)
        self.assertEqual(new_quota.vcpu_total, update_vcpu)
        self.assertEqual(new_quota.ram_total, update_ram)
        self.assertEqual(new_quota.disk_size_total, update_disk)
        self.assertEqual(new_quota.public_ip_total, update_public_ip)
        self.assertEqual(new_quota.private_ip_total, update_private_ip)

        with self.assertRaises(QuotaOnlyIncreaseError):
            mgr.update(service=service, vcpus=update_vcpu - 1, only_increase=True)

        with self.assertRaises(QuotaOnlyIncreaseError):
            mgr.update(service=service, vcpus=update_vcpu, ram_gib=update_ram - 1, only_increase=True)

        with self.assertRaises(QuotaOnlyIncreaseError):
            mgr.update(service=service, vcpus=update_vcpu, ram_gib=update_ram, disk_size=update_disk - 1,
                       only_increase=True)

        with self.assertRaises(QuotaOnlyIncreaseError):
            mgr.update(service=service, vcpus=update_vcpu, ram_gib=update_ram, disk_size=update_disk,
                       public_ip=update_public_ip - 1, only_increase=True)

        with self.assertRaises(QuotaOnlyIncreaseError):
            mgr.update(service=service, vcpus=update_vcpu, ram_gib=update_ram, disk_size=update_disk,
                       public_ip=update_public_ip, private_ip=update_private_ip - 1, only_increase=True)

        new_quota = mgr.get_quota(service=service)
        self.assertEqual(new_quota.vcpu_total, update_vcpu)
        self.assertEqual(new_quota.ram_total, update_ram)
        self.assertEqual(new_quota.disk_size_total, update_disk)
        self.assertEqual(new_quota.public_ip_total, update_public_ip)
        self.assertEqual(new_quota.private_ip_total, update_private_ip)

        mgr.update(service=service, vcpus=update_vcpu - 1, ram_gib=update_ram - 1, disk_size=update_disk - 1,
                   public_ip=update_public_ip - 1, private_ip=update_private_ip - 1, only_increase=False)
        new_quota = mgr.get_quota(service=service)
        self.assertEqual(new_quota.vcpu_total, update_vcpu - 1)
        self.assertEqual(new_quota.ram_total, update_ram - 1)
        self.assertEqual(new_quota.disk_size_total, update_disk - 1)
        self.assertEqual(new_quota.public_ip_total, update_public_ip - 1)
        self.assertEqual(new_quota.private_ip_total, update_private_ip - 1)

    def test_shared_quota_manager(self):
        self.manager_test(ServiceShareQuotaManager)

    def test_shared_update(self):
        self.update_case(ServiceShareQuotaManager)

    def test_private_quota_manager(self):
        self.manager_test(ServicePrivateQuotaManager)

    def test_private_update(self):
        self.update_case(ServicePrivateQuotaManager)


class QuotaAPITests(TransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.service = get_or_create_service()
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

        # 配额都是1
        ServicePrivateQuotaManager().update(
            service=self.service, vcpus=1, ram_gib=1, disk_size=1,
            public_ip=1, private_ip=1, only_increase=False)

        with self.assertRaises(QuotaShortageError):
            QuotaAPI.server_create_quota_apply(
                service=self.service, vcpu=1, ram_gib=1024, public_ip=True)

        with self.assertRaises(QuotaShortageError):
            QuotaAPI.server_create_quota_apply(
                service=self.service, vcpu=vcpus_apply, ram_gib=ram_apply, public_ip=is_public_ip_apply)

        # 配额都是0，不限制
        ServicePrivateQuotaManager().update(
            service=self.service, vcpus=0, ram_gib=0, disk_size=0,
            public_ip=0, private_ip=0, only_increase=False)

        QuotaAPI.server_create_quota_apply(
            service=self.service, vcpu=vcpus_apply, ram_gib=ram_apply, public_ip=is_public_ip_apply)
        self.pri_quota.refresh_from_db()
        self.assertEqual(self.pri_quota.vcpu_total, 0)
        self.assertEqual(self.pri_quota.vcpu_used, vcpus_apply)
        self.assertEqual(self.pri_quota.ram_total, 0)
        self.assertEqual(self.pri_quota.ram_used, ram_apply)
        self.assertEqual(self.pri_quota.disk_size_total, 0)
        self.assertEqual(self.pri_quota.disk_size_used, 0)
        self.assertEqual(self.pri_quota.public_ip_total, 0)
        self.assertEqual(self.pri_quota.private_ip_total, 0)
        if is_public_ip_apply:
            self.assertEqual(self.pri_quota.public_ip_used, 1)
            self.assertEqual(self.pri_quota.private_ip_used, 0)
        else:
            self.assertEqual(self.pri_quota.public_ip_used, 0)
            self.assertEqual(self.pri_quota.private_ip_used, 1)

        # 释放服务配额
        QuotaAPI().server_quota_release(
            self.service, vcpu=vcpus_apply, ram_gib=ram_apply,
            public_ips=1 if is_public_ip_apply else 0,
            private_ips=0 if is_public_ip_apply else 1
        )

        ServicePrivateQuotaManager().update(
            service=self.service, vcpus=0, ram_gib=0, disk_size=0,
            public_ip=0, private_ip=0, only_increase=False)

        # 增加服务私有配额
        ServicePrivateQuotaManager().increase(
            service=self.service, vcpus=vcpus_add, ram_gib=ram_add, disk_size=disk_size_add,
            public_ip=public_ip_add, private_ip=private_ip_add)

        # 创建vm扣除配额
        QuotaAPI.server_create_quota_apply(
            service=self.service, vcpu=vcpus_apply, ram_gib=ram_apply, public_ip=is_public_ip_apply)

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

        # 创建失败，释放服务配额
        QuotaAPI().server_quota_release(
            self.service, vcpu=vcpus_apply, ram_gib=ram_apply,
            public_ips=1 if is_public_ip_apply else 0,
            private_ips=0 if is_public_ip_apply else 1
        )
        self.pri_quota.refresh_from_db()
        self.assertEqual(self.pri_quota.vcpu_used, 0)
        self.assertEqual(self.pri_quota.ram_used, 0)
        self.assertEqual(self.pri_quota.disk_size_used, 0)
        self.assertEqual(self.pri_quota.public_ip_used, 0)
        self.assertEqual(self.pri_quota.private_ip_used, 0)

        # 创建vm扣除配额
        is_public_ip_apply = False
        QuotaAPI.server_create_quota_apply(
            service=self.service, vcpu=vcpus_apply, ram_gib=ram_apply, public_ip=is_public_ip_apply)
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

        # 释放服务配额
        QuotaAPI().server_quota_release(
            self.service, vcpu=vcpus_apply, ram_gib=ram_apply,
            public_ips=1 if is_public_ip_apply else 0,
            private_ips=0 if is_public_ip_apply else 1
        )

        self.pri_quota.refresh_from_db()
        self.assertEqual(self.pri_quota.vcpu_used, 0)
        self.assertEqual(self.pri_quota.ram_used, 0)
        self.assertEqual(self.pri_quota.disk_size_used, 0)
        self.assertEqual(self.pri_quota.public_ip_used, 0)
        self.assertEqual(self.pri_quota.private_ip_used, 0)


class TestEncryptor(SimpleTestCase):
    def normal_test(self, encryptor, text):
        encrypted = encryptor.encrypt(text)
        raw_text = encryptor.decrypt(encrypted)
        self.assertEqual(text, raw_text)

    def test_encrypt(self):
        text1 = 'iefaba!@#4567$%&^&?<<adJGKKkhafoewgfieuq:"{}HHV'
        text2 = 'iefaba!@#4567$%&^&?<<adJGK发hi发fieuq:"{}HHV'
        text3 = ''
        text4 = '哈'
        encryptor = Encryptor(key="""!2#$fk*76/';:""")
        self.normal_test(encryptor, text1)
        self.normal_test(encryptor, text2)
        self.normal_test(encryptor, text3)
        self.normal_test(encryptor, text4)

        with self.assertRaises(encryptor.InvalidEncrypted):
            encryptor.decrypt('x33')

        with self.assertRaises(encryptor.InvalidEncrypted):
            encryptor.decrypt('xsdf')
