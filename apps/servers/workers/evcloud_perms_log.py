from datetime import timedelta

from django.db.models import F
from django.utils import timezone as dj_timezone

from apps.servers.models import EVCloudPermsLog
from apps.servers.evcloud_perms import EVCloudPermsSynchronizer


class EVCloudPermsWorker:
    def run(self):
        total, ok_count, failed_count = self.do_work()
        print(f'End,all={total}, ok: {ok_count}, failed: {failed_count}')
        try:
            self.set_invalid_records()
        except Exception as exc:
            print(f'Error, set invalid records, {str(exc)}')

        return total, ok_count, failed_count

    def do_work(self):
        objs = self.get_failed_records()
        total = len(objs)
        ok_count = 0
        failed_count = 0
        for obj in objs:
            try:
                ok = self.retry_failed_record(record=obj)
                if ok is True:
                    ok_count += 1
                elif ok is False:
                    failed_count += 1
            except Exception as exc:
                pass

        return total, ok_count, failed_count

    def retry_failed_record(self, record: EVCloudPermsLog):
        if not self.is_need_retry(record=record):
            return None

        try:
            EVCloudPermsSynchronizer.check_need_sync_vo_perm(server=record.server)
        except Exception as exc:
            return None

        try:
            EVCloudPermsSynchronizer().sync_vo_server_perms_to_evcloud(server=record.server)
        except Exception as exc:
            self.update_record(record=record, is_ok=False, remarks=str(exc))
            return False

        self.update_record(record=record, is_ok=True, remarks='')
        return True

    @staticmethod
    def update_record(record: EVCloudPermsLog, is_ok: bool, remarks: str):
        if is_ok:
            status = EVCloudPermsLog.Status.OK.value
        else:
            status = EVCloudPermsLog.Status.FAILED.value

        record.status = status
        record.num = F('num') + 1
        record.remarks = remarks
        record.update_time = dj_timezone.now()
        record.save(update_fields=['status', 'num', 'remarks', 'update_time'])
        return record

    @staticmethod
    def get_failed_records():
        # 10天前的记录不再同步
        days_10_ago = dj_timezone.now() - timedelta(days=10)
        return EVCloudPermsLog.objects.filter(
            status=EVCloudPermsLog.Status.FAILED.value, server__isnull=False,
            creation_time__gte=days_10_ago
        ).select_related('server__vo__owner', 'server__service').order_by('-creation_time')[0:2000]

    @staticmethod
    def is_need_retry(record: EVCloudPermsLog):
        if record.status != EVCloudPermsLog.Status.FAILED.value:
            return False

        if not record.server:
            return False

        if record.num < 6:
            return True

        # 重试次数超过6次后，每小时尝试一次
        if (dj_timezone.now() - record.update_time) > timedelta(hours=1):
            return True

        return False

    @staticmethod
    def set_invalid_records():
        return EVCloudPermsLog.objects.filter(
            status=EVCloudPermsLog.Status.FAILED.value, server__isnull=True
        ).update(status=EVCloudPermsLog.Status.INVALID.value)
