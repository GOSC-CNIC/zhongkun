from decimal import Decimal

from django.utils.translation import gettext as _
from django.db import models
from django.utils import timezone
from rest_framework.response import Response

from core import errors as exceptions
from apps.api.viewsets import StorageGenericViewSet, serializer_error_msg
from apps.app_wallet.managers import PaymentManager
from apps.storage.adapter import inputs
from apps.storage.managers import BucketManager, ObjectsServiceManager
from apps.storage.models import Bucket, ObjectsService
from apps.storage import serializers as storage_serializers
from apps.servers.managers import ResourceActionLogManager


class BucketHandler:
    class LockActionChoices(models.TextChoices):
        NORMAL = 'normal', _('正常')
        ARREARS_LOCK = 'arrears-lock', _('欠费锁定读写')
        LOCK = 'lock', _('锁定读写')
        LOCK_WRITE = 'lock-write', _('锁定写(只读)')

    @staticmethod
    def create_bucket(view: StorageGenericViewSet, request, kwargs):
        try:
            params = BucketHandler._bucket_create_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        bucket_name = params['name']
        user = request.user

        try:
            service = view.get_service(request=request, lookup='service_id', in_='body')
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

        bcount = BucketManager.get_user_service_bucket_count(service_id=service.id, user=user)
        money_amount = Decimal('100') * (bcount + 1)
        if not PaymentManager().has_enough_balance_user(
                user_id=user.id, money_amount=money_amount, with_coupons=True,
                app_service_id=service.pay_app_service_id
        ):
            return view.exception_response(
                exceptions.BalanceNotEnough(
                    message=_('你已经拥有%(value)d个存储桶在指定服务单元中，') % {
                        'value': bcount} + _('您的余额或资源券余额不足，不能创建更多的存储桶。')))

        try:
            bucket = BucketManager.get_bucket(service_id=service.id, bucket_name=bucket_name)
            if bucket:
                return view.exception_response(exceptions.BucketAlreadyExists())
        except exceptions.BucketNotExist:
            pass

        try:
            params = inputs.BucketCreateInput(bucket_name=bucket_name, username=user.username)
            r = view.request_service(service=service, method='bucket_create', params=params)
        except Exception as exc:
            if isinstance(exc, exceptions.Error):
                if exc.code == 'Adapter.GatewayTimeout':
                    BucketManager.create_bucket(
                        bucket_name=bucket_name, bucket_id='', user_id=user.id,
                        service_id=service.id, task_status=Bucket.TaskStatus.CREATING.value
                    )

            return view.exception_response(exceptions.convert_to_error(exc))

        bucket = BucketManager.create_bucket(
            bucket_name=bucket_name, bucket_id=r.bucket_id, user_id=user.id,
            service_id=service.id, task_status=Bucket.TaskStatus.SUCCESS.value
        )
        return Response(data=storage_serializers.BucketSerializer(instance=bucket).data)

    @staticmethod
    def _bucket_create_validate_params(view, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'name' in s_errors:
                exc = exceptions.BadRequest(message=_('无效的存储桶名。') + s_errors['name'][0], code='InvalidName')
            else:
                msg = serializer_error_msg(serializer.errors)
                exc = exceptions.BadRequest(message=msg)

            raise exc

        data = serializer.validated_data
        name: str = data['name']
        service_id = data['service_id']

        if len(name) < 3:
            raise exceptions.BadRequest(message=_('存储桶名称长度不能少于3个字符'), code='InvalidName')

        if name.startswith('-') or name.endswith('-'):
            raise exceptions.BadRequest(message=_('存储桶名称不允许以字符“-”开头或结尾'), code='InvalidName')

        b_name = name.lower()
        if b_name != name:
            raise exceptions.BadRequest(message=_('存储桶名称不允许使用大写字母'), code='InvalidName')

        return {
            'name': b_name,
            'service_id': service_id
        }

    @staticmethod
    def delete_bucket(view: StorageGenericViewSet, request, kwargs):
        bucket_name = kwargs.get(view.lookup_field)
        user = request.user

        try:
            service = view.get_service(request=request, lookup='service_id', in_='path')
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

        try:
            bucket = BucketManager.get_user_bucket(service_id=service.id, bucket_name=bucket_name, user=user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            params = inputs.BucketDeleteInput(bucket_name=bucket.name, username=user.username)
            r = view.request_service(service=service, method='bucket_delete', params=params)
        except exceptions.Error as exc:
            if 'Adapter.BucketNotOwned' != exc.code:
                return view.exception_response(exc)
        except Exception as exc:
            return view.exception_response(exc)

        bucket_id = bucket.id
        if bucket.do_archive(archiver=user.username):
            bucket.id = bucket_id
            ResourceActionLogManager.add_delete_log_for_resource(res=bucket, user=request.user, raise_error=False)

        return Response(data={}, status=204)

    @staticmethod
    def list_bucket(view: StorageGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)

        queryset = BucketManager().filter_bucket_queryset(user_id=request.user.id, service_id=service_id)
        try:
            services = view.paginate_queryset(queryset=queryset)
            serializer = view.get_serializer(services, many=True)
            return view.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def admin_list_bucket(view: StorageGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        user_id = request.query_params.get('user_id', None)

        queryset = BucketManager().admin_filter_bucket_queryset(
            admin_user=request.user, service_id=service_id, user_id=user_id)
        try:
            services = view.paginate_queryset(queryset=queryset)
            serializer = view.get_serializer(services, many=True)
            return view.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def admin_stats_bucket(view: StorageGenericViewSet, request, kwargs):
        service_id = kwargs.get('service_id', None)
        bucket_name = kwargs.get(view.lookup_field, '')

        try:
            bucket = BucketManager().get_bucket(service_id=service_id, bucket_name=bucket_name)
            service: ObjectsService = bucket.service
            if not request.user.is_federal_admin():
                s = ObjectsServiceManager.get_service_if_admin(user=request.user, service_id=service.id)
                if not s:
                    raise exceptions.AccessDenied(message=_('你没有指定服务单元的管理权限。'))

            params = inputs.BucketStatsInput(bucket_name=bucket.name)
            r = view.request_service(service=service, method='bucket_stats', params=params)

            stats_time = r.stats_time or timezone.now()
            try:
                if bucket.stats_time is None or bucket.stats_time != r.stats_time:
                    bucket.storage_size = r.bucket_size_byte
                    bucket.object_count = r.objects_count
                    bucket.stats_time = stats_time
                    bucket.save(update_fields=['storage_size', 'object_count', 'stats_time'])
            except Exception as exc:
                pass

            return Response(data={
                'bucket': {
                    'id': bucket.id, 'name': bucket.name, 'service_id': service.id, 'service_name': service.name
                },
                'stats': {
                    'objects_count': r.objects_count,
                    'bucket_size_byte': r.bucket_size_byte,
                    'stats_time': stats_time.isoformat()
                }
            })
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def admin_delete_bucket(view: StorageGenericViewSet, request, kwargs):
        bucket_name = kwargs.get(view.lookup_field, '')
        service_id = request.query_params.get('service_id', None)

        if not service_id:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('必须指定服务单元id。'))
            )

        try:
            bucket = BucketManager().get_bucket(service_id=service_id, bucket_name=bucket_name)
            service: ObjectsService = bucket.service
            if not request.user.is_federal_admin():
                s = ObjectsServiceManager.get_service_if_admin(user=request.user, service_id=service.id)
                if not s:
                    raise exceptions.AccessDenied(message=_('你没有指定服务单元的管理权限。'))

            params = inputs.BucketDeleteInput(bucket_name=bucket.name, username=bucket.user.username)
            r = view.request_service(service=service, method='bucket_delete', params=params)
            bucket.do_archive(archiver=request.user.username)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)

    @staticmethod
    def admin_lock_bucket(view: StorageGenericViewSet, request, kwargs):
        bucket_name = kwargs.get(view.lookup_field, '')
        service_id = request.query_params.get('service_id', None)
        act = request.query_params.get('action', None)

        if not service_id:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('必须指定服务单元id。'), code='MissingParam')
            )

        if not act:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('必须指定操作选项。'), code='MissingParam')
            )

        if act not in BucketHandler.LockActionChoices.values:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('操作选项无效。'))
            )

        try:
            bucket = BucketManager().get_bucket(service_id=service_id, bucket_name=bucket_name)
            service: ObjectsService = bucket.service
            if not request.user.is_federal_admin():
                s = ObjectsServiceManager.get_service_if_admin(user=request.user, service_id=service.id)
                if not s:
                    raise exceptions.AccessDenied(message=_('你没有指定服务单元的管理权限。'))

            lock = {
                BucketHandler.LockActionChoices.NORMAL.value: inputs.BucketLockInput.LOCK_FREE,
                BucketHandler.LockActionChoices.ARREARS_LOCK.value: inputs.BucketLockInput.LOCK_READWRITE,
                BucketHandler.LockActionChoices.LOCK.value: inputs.BucketLockInput.LOCK_READWRITE,
                BucketHandler.LockActionChoices.LOCK_WRITE.value: inputs.BucketLockInput.LOCK_WRITE
            }[act]
            params = inputs.BucketLockInput(bucket_name=bucket.name, lock=lock)
            r = view.request_service(service=service, method='bucket_lock', params=params)

            status = {
                BucketHandler.LockActionChoices.NORMAL.value: Bucket.Situation.NORMAL.value,
                BucketHandler.LockActionChoices.ARREARS_LOCK.value: Bucket.Situation.ARREARS_LOCK.value,
                BucketHandler.LockActionChoices.LOCK.value: Bucket.Situation.LOCK.value,
                BucketHandler.LockActionChoices.LOCK_WRITE.value: Bucket.Situation.LOCK_WRITE.value
            }[act]
            bucket.set_situation(status=status)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={'action': act}, status=200)
