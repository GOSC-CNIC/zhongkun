from datetime import timedelta
from django.utils import timezone as dj_timezone

from utils.test import get_or_create_user,  MyAPITransactionTestCase
from utils.model import PayType

from apps.vo.models import VirtualOrganization
from apps.servers.models import ServiceConfig, Server, EVCloudPermsLog
from apps.servers.tests import create_server_metadata
from apps.servers.workers.evcloud_perms_log import EVCloudPermsWorker


def create_evcloud_perm_log(
        server: Server = None, status: str = EVCloudPermsLog.Status.FAILED.value,
        num: int = 1, creation_time=None, update_time=None, remarks: str = ''
):
    nt = dj_timezone.now()
    creation_time = creation_time if creation_time else nt
    update_time = update_time if update_time else nt
    ins = EVCloudPermsLog(
        server=server, status=status, num=num,
        creation_time=creation_time, update_time=update_time, remarks=remarks
    )
    ins.save(force_insert=True)
    return ins


class EVCloudPermWorkerTests(MyAPITransactionTestCase):
    def setUp(self):
        self.user = get_or_create_user()
        self.user2 = get_or_create_user(username='user2')
        self.vo = VirtualOrganization(name='test vo', owner=self.user2)
        self.vo.save(force_insert=True)

    def test_list_snapshot(self):
        service1 = ServiceConfig(
            name='test2', name_en='test2_en', org_data_center=None, endpoint_url='https://test.com'
        )
        service1.save(force_insert=True)

        server1 = create_server_metadata(
            service=service1, user=self.user, ram=8, vcpus=6,
            vo_id=self.vo.id, classification=Server.Classification.VO.value,
            default_user='user', default_password='password',
            ipv4='127.12.33.111', remarks='test server', pay_type=PayType.PREPAID.value
        )
        server2 = create_server_metadata(
            service=service1, user=self.user, ram=8, vcpus=6,
            default_user='user', default_password='password',
            ipv4='127.12.33.111', remarks='test server', pay_type=PayType.PREPAID.value
        )
        # 无效的数据
        log1 = create_evcloud_perm_log(server=None)
        log2 = create_evcloud_perm_log(server=server1, status=EVCloudPermsLog.Status.OK.value)
        log3 = create_evcloud_perm_log(server=server1, creation_time=dj_timezone.now()-timedelta(days=10))
        now_tm = dj_timezone.now()
        # 10 day内有效
        # num < 6, 会重试
        log4 = create_evcloud_perm_log(
            server=server1, num=1, creation_time=dj_timezone.now() - timedelta(days=9), update_time=now_tm
        )
        # num>6, 更新时间不超过1小时 不会重试
        log5 = create_evcloud_perm_log(
            server=server1, num=8, creation_time=dj_timezone.now() - timedelta(days=9),
            update_time=dj_timezone.now() - timedelta(minutes=58)
        )
        # num>6, 更新时间超过1小时 会重试
        log6 = create_evcloud_perm_log(
            server=server1, num=7, creation_time=dj_timezone.now(),
            update_time=dj_timezone.now() - timedelta(hours=1)
        )
        # 个人server 不会重试
        log7 = create_evcloud_perm_log(
            server=server2, num=1, creation_time=dj_timezone.now(),
            update_time=dj_timezone.now() - timedelta(hours=1)
        )

        self.assertEqual(EVCloudPermsLog.objects.count(), 7)
        total, ok_count, failed_count = EVCloudPermsWorker().run()
        self.assertEqual(total, 4)
        self.assertEqual(ok_count, 0)  # 没有成功的，1个不重试的,1个个人不重试的
        self.assertEqual(failed_count, 2)  # 2个重试都失败
        log4.refresh_from_db()
        self.assertEqual(log4.status, EVCloudPermsLog.Status.FAILED.value)
        self.assertEqual(log4.num, 2)
        self.assertGreater(log4.update_time, now_tm)
        # log5 不变
        log5_update_time = log5.update_time
        log5.refresh_from_db()
        self.assertEqual(log5.status, EVCloudPermsLog.Status.FAILED.value)
        self.assertEqual(log5.num, 8)
        self.assertEqual(log5.update_time, log5_update_time)
        log6.refresh_from_db()
        self.assertEqual(log6.status, EVCloudPermsLog.Status.FAILED.value)
        self.assertEqual(log6.num, 8)
        self.assertGreater(log6.update_time, now_tm)
        log1.refresh_from_db()
        self.assertEqual(log1.status, EVCloudPermsLog.Status.INVALID.value)
