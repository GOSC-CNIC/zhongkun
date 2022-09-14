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
from .handlers import serializer_error_msg


class BucketHandler:
    @staticmethod
    def create_bucket(view: StorageGenericViewSet, request, kwargs):
        try:
            params = BucketHandler._bucket_create_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        bucket_name = params['name']
        service_id = params['service_id']
        user = request.user

        try:
            service = view.get_service(request=request, lookup='service_id', in_='body')
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

        if not PaymentManager().has_enough_balance_user(
                user_id=user.id, money_amount=Decimal('100'), with_coupons=True,
                app_service_id=service.pay_app_service_id
        ):
            return view.exception_response(
                exceptions.BalanceNotEnough(message=_('创建存储桶要求余额或代金券余额大于100')))

        try:
            bucket = BucketManager.get_bucket(service_id=service_id, bucket_name=bucket_name)
            if bucket:
                return view.exception_response(exceptions.BucketAlreadyExists())
        except exceptions.BucketNotExist:
            pass

        try:
            params = inputs.BucketCreateInput(bucket_name=bucket_name, username=user.username)
            r = view.request_service(service=service, method='bucket_create', params=params)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

        bucket = BucketManager.create_bucket(
            bucket_name=bucket_name, bucket_id=r.bucket_id, user_id=user.id,
            service_id=service.id
        )
        return Response(data=storage_serializers.BucketSerializer(instance=bucket).data)

    @staticmethod
    def _bucket_create_validate_params(view, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise exceptions.BadRequest(msg)

        data = serializer.validated_data
        name = data['name']
        service_id = data['service_id']

        if len(name) < 3:
            raise exceptions.BadRequest(message=_('存储桶名称长度不能少于3个字符'), code='InvalidName')

        return {
            'name': name,
            'service_id': service_id
        }
