from django.utils import timezone
from django.utils.translation import gettext as _
from django.db import transaction
from django.db.models import Case, F, When, Value

from core import errors
from .models import QuotaActivity, QuotaActivityGotRecord


class QuotaActivityManager:
    MODEL = QuotaActivity

    @staticmethod
    def get_queryset():
        return QuotaActivity.objects.all()

    @staticmethod
    def get_activity_by_id(_id: str):
        return QuotaActivity.objects.select_related('service').filter(id=_id, deleted=False).first()

    def filter_queryset(self, deleted: bool = False, status: str = None, exclude_not_start: bool = None,
                        exclude_ended: bool = None):
        """
        查询配额活动

        :param deleted: None(不过滤)，True(只查询已删除的)，默认False(只查询未删除的)
        :param status: 默认None(不过滤)，closed(只查询已关闭的)，active(只查询未关闭的)
        :param exclude_not_start: True(查询不包括未开始的活动)，默认None或其他值(不过滤)
        :param exclude_ended: True(查询不包括已结束的活动)，默认None或其他值(不过滤)
        """
        queryset = self.get_queryset().select_related('service')
        filters = {}
        if deleted is not None:
            filters['deleted'] = bool(deleted)

        if status is not None:
            filters['status'] = status

        if exclude_not_start is True:
            filters['start_time__lte'] = timezone.now()

        if exclude_ended is True:
            filters['end_time__gt'] = timezone.now()

        if filters:
            queryset = queryset.filter(**filters)

        return queryset

    @staticmethod
    def create_activity(data, user) -> QuotaActivity:
        """
        :param data: QuotaActivitySerializer.validated_data
        :param user:
        :raises: Error
        """
        qa = QuotaActivity()
        qa.name = data.get('name')
        qa.name_en = data.get('name_en')
        qa.start_time = data.get('start_time')
        qa.end_time = data.get('end_time')
        qa.count = data.get('count')
        qa.times_per_user = data.get('times_per_user')
        qa.status = data.get('status')
        qa.tag = data.get('tag')
        qa.cpus = data.get('cpus')
        qa.private_ip = data.get('private_ip')
        qa.public_ip = data.get('public_ip')
        qa.ram = data.get('ram')
        qa.disk_size = data.get('disk_size')
        qa.expiration_time = data.get('expiration_time')
        qa.duration_days = data.get('duration_days')
        qa.service_id = data.get('service_id')
        qa.user = user
        try:
            qa.save()
        except Exception as exc:
            raise errors.Error.from_error(exc)

        return qa

    @staticmethod
    def check_during_activity_now(qa: QuotaActivity):
        """
        是否在活动期间（活动是否已开始，并且还没有结束）

        :raises: Error
        """
        if qa.status == qa.Status.CLOSED:
            raise errors.ConflictError(code='IsClosed', message=_('活动已经关闭'))

        now = timezone.now()
        if now < qa.start_time:
            raise errors.ConflictError(code='NotStart', message=_('活动还未开始'))

        if now >= qa.end_time:
            raise errors.ConflictError(code='IsOver', message=_('活动已结束'))

        return True

    def check_activity_pre_got(self, qa: QuotaActivity, user) -> QuotaActivityGotRecord:
        """
        领取前检查

        :raises: Error
        """
        self.check_during_activity_now(qa)
        if qa.got_count >= qa.count:
            raise errors.ConflictError(code='NoneLeft', message=_('配额已经被领完了'))

        record = QuotaActivityGotRecord.objects.filter(quota_activity_id=qa.id, user_id=user.id).first()
        if record is None:
            try:
                record = QuotaActivityGotRecord(user_id=user.id, quota_activity_id=qa.id, got_count=0)
                record.save()
            except Exception as exc:
                raise errors.Error.from_error(exc)

            return record

        if record.got_count >= qa.times_per_user:
            raise errors.ConflictError(code='TooMany', message=_('不能领取更多了'))

        return record

    def activity_got_once(self, _id, user):
        """
        :raises: Error
        """
        qa = self.get_activity_by_id(_id=_id)
        if qa is None:
            raise errors.NotFound(message=_('活动不存在'))

        record = self.check_activity_pre_got(qa=qa, user=user)
        with transaction.atomic():
            r = QuotaActivity.objects.filter(id=_id, got_count__lt=F('count')).update(
                got_count=F('got_count') + 1)
            if r <= 0:
                raise errors.ConflictError(code='NoneLeft', message=_('配额已经被领完了'))

            try:
                r = QuotaActivityGotRecord.objects.filter(
                    id=record.id, got_count__lt=qa.times_per_user).update(
                    got_count=F('got_count') + 1
                )
                if r <= 0:
                    raise errors.ConflictError(code='TooMany', message=_('不能领取更多了'))
            except Exception as exc:
                raise errors.convert_to_error(exc)

            quota = qa.build_quota_obj(user_id=user.id)
            try:
                quota.save()
            except Exception as e:
                raise errors.Error(message=_('创建配额时错误') + str(e))

            return quota
