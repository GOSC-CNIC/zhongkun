from decimal import Decimal

from django.utils.translation import gettext as _
from django.utils import timezone
from rest_framework.response import Response

from core import errors as exceptions
from api.viewsets import StorageGenericViewSet
from api.serializers import storage as storage_serializers
from bill.managers import PaymentManager
from storage.adapter import inputs
from storage.managers import BucketManager
from storage.models import Bucket
from .handlers import serializer_error_msg


class BucketHandler:
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
                        'value': bcount} + _('您的余额或代金券余额不足，不能创建更多的存储桶。')))

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

        bucket.do_archive(archiver=user.username)
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
