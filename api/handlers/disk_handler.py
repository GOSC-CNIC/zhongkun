from decimal import Decimal

from django.utils.translation import gettext as _
from django.conf import settings
from django.db.models import TextChoices
from rest_framework.response import Response

from core import errors as exceptions
from core.quota import QuotaAPI
from servers.managers import DiskManager
from api.viewsets import CustomGenericViewSet
from api.deliver_resource import OrderResourceDeliverer
from api import request_logger
from vo.managers import VoManager
from vo.models import VirtualOrganization
from adapters import inputs
from utils.model import PayType, OwnerType
from order.models import ResourceType, Order
from order.managers import OrderManager, OrderPaymentManager, DiskConfig
from bill.managers import PaymentManager
from .handlers import serializer_error_msg


class DiskHandler:
    class ListDiskQueryStatus(TextChoices):
        EXPIRED = 'expired', _('过期')
        PREPAID = 'prepaid', _('预付费')
        POSTPAID = 'postpaid', _('后付费')

    @staticmethod
    def _disk_create_validate_params(view: CustomGenericViewSet, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'pay_type' in s_errors:
                exc = exceptions.BadRequest(
                    message=_('无效的付费模式。') + s_errors['pay_type'][0], code='InvalidPayType')
            elif 'service_id' in s_errors:
                exc = exceptions.BadRequest(
                    message=_('无效的服务单元。') + s_errors['service_id'][0], code='InvalidServiceId')
            elif 'azone_id' in s_errors:
                exc = exceptions.BadRequest(
                    message=_('无效的可用区。') + s_errors['azone_id'][0], code='InvalidAzoneId')
            elif 'size' in s_errors:
                exc = exceptions.BadRequest(
                    message=_('无效的硬盘容量大小。') + s_errors['size'][0], code='InvalidSize')
            else:
                msg = serializer_error_msg(s_errors)
                exc = exceptions.BadRequest(message=msg)

            raise exc

        data = serializer.validated_data
        remarks = data.get('remarks', '')
        pay_type = data.get('pay_type', None)
        azone_id = data.get('azone_id', None)
        vo_id = data.get('vo_id', None)
        period = data.get('period', None)
        disk_size = data.get('size', None)

        if not azone_id:
            raise exceptions.BadRequest(message=_('必须指可用区'), code='InvalidAzoneId')

        if not pay_type:
            raise exceptions.BadRequest(message=_('必须指定付费模式'), code='MissingPayType')

        pay_type_values = [PayType.POSTPAID.value, PayType.PREPAID.value]
        if pay_type not in pay_type_values:
            raise exceptions.BadRequest(message=_('付费模式无效'), code='InvalidPayType')

        if period is not None:
            if period <= 0:
                raise exceptions.BadRequest(message=_('订购时长参数"period"值必须大于0'), code='InvalidPeriod')

            if period > (12 * 5):
                raise exceptions.BadRequest(message=_('订购时长最长为5年'), code='InvalidPeriod')
        else:
            period = 0

        if pay_type == PayType.PREPAID.value and period == 0:
            raise exceptions.BadRequest(message=_('预付费模式时，必须指定订购时长'), code='MissingPeriod')

        if vo_id:
            try:
                vo, member = VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=request.user)
            except exceptions.Error as exc:
                if exc.status_code == 404:
                    raise exceptions.BadRequest(message=str(exc), code='InvalidVoId')
                raise exc
        else:
            vo = None

        try:
            service = view.get_service(request, in_='body')
        except exceptions.NoFoundArgument:
            raise exceptions.BadRequest(message=_('参数service_id不得为空'), code='MissingServiceId')
        except exceptions.APIException as exc:
            raise exceptions.BadRequest(message=str(exc), code='InvalidServiceId')

        if not service.pay_app_service_id:
            raise exceptions.ConflictError(message=_('服务未配置对应的结算系统APP服务id'), code='ServiceNoPayAppServiceId')

        if azone_id:
            try:
                out_azones = view.request_service(
                    service=service, method='list_availability_zones',
                    params=inputs.ListAvailabilityZoneInput(region_id=service.region_id)
                )
            except exceptions.APIException as exc:
                raise exc

            azone = None
            for az in out_azones.zones:
                if az.id == azone_id:
                    azone = az
                    break

            if azone is None:
                raise exceptions.BadRequest(message=_('指定的可用区不存在'), code='InvalidAzoneId')

            azone_name = azone.name
        else:
            raise exceptions.BadRequest(message=_('必须指定可用区'), code='InvalidAzoneId')

        return {
            'pay_type': pay_type,
            'azone_id': azone_id,
            'azone_name': azone_name,
            'vo': vo,
            'remarks': remarks,
            'service': service,
            'period': period,
            'disk_size': disk_size
        }

    @staticmethod
    def _create_disk_pretend_check(view, service, azone_id: str, disk_size: int):
        """
        :raises: Error
        """
        params = inputs.DiskCreateInput(
            region_id=service.region_id, azone_id=azone_id, size_gib=disk_size, description='')
        try:
            r = view.request_service(service, method='disk_create_pretend', params=params)
            if not r.ok:
                raise exceptions.ConflictError(
                    message=_('向服务单元确认是否满足创建云硬盘条件时错误') + str(r.error))
        except exceptions.APIException as exc:
            raise exceptions.ConflictError(message=_('向服务单元确认是否满足创建云硬盘条件时错误') + str(exc))

        if not r.result:
            raise exceptions.QuotaShortageError(message=r.reason)

    def disk_order_create(self, view, request):
        """
        云服务器订单创建
        """
        try:
            data = DiskHandler._disk_create_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        pay_type = data['pay_type']
        azone_id = data['azone_id']
        azone_name = data['azone_name']
        vo = data['vo']
        remarks = data['remarks']
        service = data['service']
        period = data['period']
        disk_size = data['disk_size']

        user = request.user
        if vo or isinstance(vo, VirtualOrganization):
            vo_id = vo.id
            vo_name = vo.name
            owner_type = OwnerType.VO.value
        else:
            vo_id = ''
            vo_name = ''
            owner_type = OwnerType.USER.value

        instance_config = DiskConfig(
            disk_size=disk_size, azone_id=azone_id, azone_name=azone_name
        )
        omgr = OrderManager()
        # 按量付费模式时，检查是否有余额
        if pay_type == PayType.POSTPAID.value:
            # 计算按量付费一天的计费
            original_price, trade_price = omgr.calculate_amount_money(
                resource_type=ResourceType.DISK.value, config=instance_config, is_prepaid=False, period=0, days=1
            )

            try:
                self.__check_balance_create_disk_order(
                    service=service, owner_type=owner_type, user=user, vo_id=vo_id, day_price=original_price
                )
            except Exception as exc:
                return view.exception_response(exc)

        try:
            # 服务私有资源配额是否满足需求
            QuotaAPI.service_private_disk_quota_meet(
                service=service, disk_size=instance_config.disk_size
            )
            # 向服务单元确认一下是否满足创建条件
            self._create_disk_pretend_check(view=view, service=service, azone_id=azone_id, disk_size=disk_size)
        except exceptions.QuotaShortageError as exc:
            return view.exception_response(
                exceptions.QuotaShortageError(message=_('指定服务单元无法提供足够的资源。') + str(exc)))
        except exceptions.Error as exc:
            return view.exception_response(exc)

        # 创建订单
        order, resource = omgr.create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=service.pay_app_service_id,
            service_id=service.id,
            service_name=service.name,
            resource_type=ResourceType.DISK.value,
            instance_config=instance_config,
            period=period,
            pay_type=pay_type,
            user_id=user.id,
            username=user.username,
            vo_id=vo_id,
            vo_name=vo_name,
            owner_type=owner_type,
            remark=remarks
        )

        # 预付费模式时
        if pay_type == PayType.PREPAID.value:
            return Response(data={
                'order_id': order.id
            })

        try:
            subject = order.build_subject()
            order = OrderPaymentManager().pay_order(
                order=order, app_id=settings.PAYMENT_BALANCE['app_id'], subject=subject,
                executor=request.user.username, remark='',
                coupon_ids=None, only_coupon=False,
                required_enough_balance=True
            )
            OrderResourceDeliverer().deliver_order(order=order, resource=resource)
        except exceptions.Error as exc:
            request_logger.error(msg=f'[{type(exc)}] {str(exc)}')

        return Response(data={
            'order_id': order.id
        })

    @staticmethod
    def __check_balance_create_disk_order(service, owner_type: str, user, vo_id: str, day_price: Decimal):
        """
        按量付费模式云硬盘订购时，检查余额是否满足限制条件

            * 余额和券金额 / 按量一天计费金额 = 服务单元可以创建的按量付费云硬盘数量

        :raises: Error, BalanceNotEnough
        """

        if owner_type == OwnerType.USER.value:
            qs = DiskManager().get_user_disks_queryset(
                user=user, service_id=service.id, pay_type=PayType.POSTPAID.value)
            s_count = qs.count()
            money_amount = day_price * (s_count + 1)

            if not PaymentManager().has_enough_balance_user(
                    user_id=user.id, money_amount=money_amount, with_coupons=True,
                    app_service_id=service.pay_app_service_id
            ):
                raise exceptions.BalanceNotEnough(
                    message=_('你在指定服务单元中已拥有%(value)d块按量计费的云硬盘，你的余额不足，不能订购更多的云硬盘。'
                              ) % {'value': s_count})
        else:
            qs = DiskManager().get_vo_disks_queryset(
                vo_id=vo_id, service_id=service.id, pay_type=PayType.POSTPAID.value)
            s_count = qs.count()
            money_amount = day_price * (s_count + 1)

            if not PaymentManager().has_enough_balance_vo(
                    vo_id=vo_id, money_amount=money_amount, with_coupons=True,
                    app_service_id=service.pay_app_service_id
            ):
                raise exceptions.BalanceNotEnough(
                    message=_('项目组在指定服务单元中已拥有%(value)d块按量计费的云硬盘，项目组的余额不足，不能订购更多的云硬盘。'
                              ) % {'value': s_count}, code='VoBalanceNotEnough')

    @staticmethod
    def list_disk(view: CustomGenericViewSet, request):
        """
        列举云硬盘
        """
        service_id = request.query_params.get('service_id', None)
        vo_id = request.query_params.get('vo_id', None)

        if vo_id is not None:
            if not vo_id:
                return view.exception_response(exceptions.InvalidArgument(message=_('项目组ID无效')))

            try:
                VoManager().get_has_read_perm_vo(vo_id=vo_id, user=request.user)
            except exceptions.Error as exc:
                return view.exception_response(exc)

            queryset = DiskManager().get_vo_disks_queryset(vo_id=vo_id, service_id=service_id)
        else:
            queryset = DiskManager().get_user_disks_queryset(user=request.user, service_id=service_id)

        try:
            disks = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=disks, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)
