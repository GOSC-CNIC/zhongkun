from decimal import Decimal
from datetime import datetime

from django.utils.translation import gettext as _
from django.conf import settings
from django.db.models import TextChoices
from django.db import transaction
from rest_framework.response import Response

from core import errors as exceptions
from core import request as core_request
from core.quota import QuotaAPI
from api.viewsets import CustomGenericViewSet, serializer_error_msg
from api import request_logger
from vo.managers import VoManager
from vo.models import VirtualOrganization
from adapters import inputs
from utils.model import PayType, OwnerType
from utils.time import iso_utc_to_datetime
from order.deliver_resource import OrderResourceDeliverer
from order.models import ResourceType, Order
from order.managers import OrderManager, OrderPaymentManager, DiskConfig
from bill.managers import PaymentManager
from service.managers import ServiceManager
from servers.managers import ServerManager, DiskManager, ResourceActionLogManager
from servers.models import Server, Disk
from servers import disk_serializers


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

        azone_name = ''
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

        if azone_id is None:
            azone_id = ''

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

            * (余额和券金额 - 100) / 按量一天计费金额 = 服务单元可以创建的按量付费云硬盘数量

        :raises: Error, BalanceNotEnough
        """
        lower_limit_amount = Decimal('100.00')
        if owner_type == OwnerType.USER.value:
            qs = DiskManager().get_user_disks_queryset(
                user=user, service_id=service.id, pay_type=PayType.POSTPAID.value)
            s_count = qs.count()
            money_amount = day_price * s_count + lower_limit_amount

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
            money_amount = day_price * s_count + lower_limit_amount

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
        try:
            params = DiskHandler._list_disk_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        service_id = params['service_id']
        volume_min = params['volume_min']
        volume_max = params['volume_max']
        remark = params['remark']
        pay_type = params['pay_type']
        expired = params['expired']
        ip_contain = params['ip_contain']
        vo_id: str = params['vo_id']
        vo_name = params['vo_name']
        username = params['username']
        user_id = params['user_id']
        exclude_vo = params['exclude_vo']

        if view.is_as_admin_request(request):
            try:
                disk_qs = DiskManager().get_admin_disk_queryset(
                    user=request.user, volume_min=volume_min, volume_max=volume_max, service_id=service_id,
                    expired=expired, remark=remark, pay_type=pay_type, ipv4_contains=ip_contain,
                    user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, exclude_vo=exclude_vo
                )
            except Exception as exc:
                return view.exception_response(exc)
        elif vo_id:
            try:
                VoManager().get_has_read_perm_vo(vo_id=vo_id, user=request.user)
            except exceptions.Error as exc:
                return view.exception_response(exc)

            disk_qs = DiskManager().get_vo_disks_queryset(
                vo_id=vo_id, volume_min=volume_min, volume_max=volume_max, service_id=service_id,
                expired=expired, remark=remark, pay_type=pay_type, ipv4_contains=ip_contain
            )
        else:
            disk_qs = DiskManager().get_user_disks_queryset(
                user=request.user, volume_min=volume_min, volume_max=volume_max, service_id=service_id,
                expired=expired, remark=remark, pay_type=pay_type, ipv4_contains=ip_contain
            )

        try:
            disks = view.paginate_queryset(disk_qs)
            serializer = view.get_serializer(instance=disks, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_disk_validate_params(view, request):
        service_id = request.query_params.get('service_id', None)
        volume_min = request.query_params.get('volume_min', None)
        volume_max = request.query_params.get('volume_max', None)
        status = request.query_params.get('status', None)
        remark = request.query_params.get('remark', None)
        ip_contain = request.query_params.get('ip_contain', None)
        vo_id = request.query_params.get('vo_id', None)
        # as-admin only
        vo_name = request.query_params.get('vo_name', None)
        username = request.query_params.get('username', None)
        user_id = request.query_params.get('user_id', None)
        exclude_vo = request.query_params.get('exclude_vo', None)

        if volume_min is not None:
            try:
                volume_min = int(volume_min)
            except ValueError:
                raise exceptions.InvalidArgument(message=_('参数“volume_min”的值无效'))

        if volume_max is not None:
            try:
                volume_max = int(volume_max)
            except ValueError:
                raise exceptions.InvalidArgument(message=_('参数“volume_max”的值无效'))

        if user_id is not None and username is not None:
            raise exceptions.BadRequest(
                message=_('参数“user_id”和“username”不允许同时提交')
            )

        if vo_id is not None and vo_name is not None:
            raise exceptions.BadRequest(
                message=_('参数“vo_id”和“vo_name”不允许同时提交')
            )

        if exclude_vo is not None:
            exclude_vo = True
            if vo_id is not None or vo_name is not None:
                raise exceptions.BadRequest(
                    message=_('参数"exclude_vo"不允许与参数“vo_id”和“vo_name”同时提交')
                )
        else:
            exclude_vo = False

        expired = None
        pay_type = None
        if status is not None:
            if status == DiskHandler.ListDiskQueryStatus.EXPIRED.value:
                expired = True
            elif status == DiskHandler.ListDiskQueryStatus.PREPAID.value:
                pay_type = PayType.PREPAID.value
            elif status == DiskHandler.ListDiskQueryStatus.POSTPAID.value:
                pay_type = PayType.POSTPAID.value
            else:
                raise exceptions.InvalidArgument(message=_('参数“status”的值无效'))

        if not view.is_as_admin_request(request):
            if username is not None:
                raise exceptions.InvalidArgument(
                    message=_('参数"username"只有以管理员身份请求时有效'))
            if user_id is not None:
                raise exceptions.InvalidArgument(
                    message=_('参数"user_id"只有以管理员身份请求时有效'))
            if vo_name is not None:
                raise exceptions.InvalidArgument(
                    message=_('参数"vo_name"只有以管理员身份请求时有效'))
            if exclude_vo:
                raise exceptions.InvalidArgument(
                    message=_('参数"exclude_vo"只有以管理员身份请求时有效'))

        return {
            'service_id': service_id,
            'volume_min': volume_min,
            'volume_max': volume_max,
            'remark': remark,
            'pay_type': pay_type,
            'expired': expired,  # True or None
            'ip_contain': ip_contain,
            'vo_id': vo_id,
            'vo_name': vo_name,
            'username': username,
            'user_id': user_id,
            'exclude_vo': exclude_vo
        }

    @staticmethod
    def delete_disk(view: CustomGenericViewSet, request, kwargs):
        """
        删除云硬盘
        """
        disk_id = kwargs.get(view.lookup_field, '')

        try:
            is_as_admin = view.is_as_admin_request(request=request)
            if is_as_admin:
                disk = DiskManager().admin_get_disk(disk_id=disk_id, user=request.user)
            else:
                disk = DiskManager().get_manage_perm_disk(disk_id=disk_id, user=request.user)

            if disk.is_attached():
                raise exceptions.DiskAttached(message=_('云硬盘已挂载于云主机，请先卸载后再尝试删除。'))

            if not is_as_admin:
                if disk.is_locked_delete():
                    raise exceptions.ResourceLocked(message=_('无法删除，云硬盘已加锁锁定了删除'))
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            params = inputs.DiskDeleteInput(disk_id=disk.instance_id, disk_name=disk.instance_name)
            r = view.request_service(disk.service, method='disk_delete', params=params)
            if not r.ok:
                raise exceptions.ConflictError(message=_('向服务单元删除云硬盘时错误') + str(r.error))

            disk.do_soft_delete(deleted_user=request.user.username, raise_exception=True)
            ResourceActionLogManager.add_delete_log_for_resource(res=disk, user=request.user, raise_error=False)
            QuotaAPI().disk_quota_release(service=disk.service, disk_size=disk.size)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        return Response(status=204)

    @staticmethod
    def _pre_attach_disk_check(server, disk):
        """
        挂载前可挂载性检测

        :raises: ResourcesNotSameOwner, ResourcesNotInSameService, ResourcesNotInSameZone
        """
        if disk.classification == Disk.Classification.PERSONAL.value:
            if server.classification != Server.Classification.PERSONAL.value:
                raise exceptions.ResourcesNotSameOwner()
            else:
                if server.user_id != disk.user_id:
                    raise exceptions.ResourcesNotSameOwner()
        elif disk.classification == Disk.Classification.VO.value:
            if server.classification != Server.Classification.VO.value:
                raise exceptions.ResourcesNotSameOwner()
            else:
                if server.vo_id != disk.vo_id:
                    raise exceptions.ResourcesNotSameOwner()
        else:
            raise exceptions.ResourcesNotSameOwner()

        if server.service_id != disk.service_id:
            raise exceptions.ResourcesNotInSameService()

        # if not server.azone_id:
        #     # 尝试更新云主机元数据，更新可用区信息
        #     try:
        #         server = core_request.update_server_detail(server=server, task_status=None)
        #     except exceptions.Error as e:
        #         pass
        #
        #     if not server.azone_id:
        #         raise exceptions.ResourcesNotInSameZone(extend_msg='无法确认云主机所在可用区。')
        #
        # if server.azone_id != disk.azone_id:
        #     raise exceptions.ResourcesNotInSameZone()

    @staticmethod
    def attach_disk(view: CustomGenericViewSet, request, kwargs):
        """
        挂载云硬盘
        """
        disk_id = kwargs.get(view.lookup_field, '')
        server_id = request.query_params.get('server_id', None)

        if not server_id:
            return view.exception_response(exceptions.InvalidArgument(message=_('必须指定要挂载的云主机。')))

        try:
            disk = DiskManager().get_manage_perm_disk(disk_id=disk_id, user=request.user)
            if disk.is_attached():
                raise exceptions.DiskAttached(message=_('云硬盘已被挂载，不允许多重挂载。'))

            if disk.is_locked_operation():
                raise exceptions.ResourceLocked(message=_('无法挂载，云硬盘已加锁锁定了操作'))

            server = ServerManager().get_manage_perm_server(server_id=server_id, user=request.user)
            if server.is_locked_operation():
                raise exceptions.ResourceLocked(message=_('无法挂载，目标云主机已加锁锁定了操作'))

            DiskHandler._pre_attach_disk_check(server=server, disk=disk)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            DiskHandler.do_attach_disk(server=server, disk=disk)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        return Response(data={'server_id': server.id, 'disk_id': disk.id})

    @staticmethod
    def do_attach_disk(server: Server, disk: Disk):
        """
        挂载硬盘
        :raises: Error，Conflict
        """
        params = inputs.DiskAttachInput(instance_id=server.instance_id, disk_id=disk.instance_id)
        r = core_request.request_service(disk.service, method='disk_attach', params=params)
        if not r.ok:
            raise exceptions.ConflictError(message=_('向云主机挂载云硬盘时错误') + str(r.error))

        try:
            disk.set_attach(server_id=server.id)
        except Exception as exc:
            request_logger.error(f'硬盘{disk.id}已成功挂载到云主机 {server.id}，但是硬盘元数据更新记录server id失败。')
            raise exceptions.Error(message=_('更新硬盘元数据错误，') + str(exc))

    @staticmethod
    def detach_disk(view: CustomGenericViewSet, request, kwargs):
        """
        卸载云硬盘
        """
        disk_id = kwargs.get(view.lookup_field, '')
        server_id = request.query_params.get('server_id', None)

        if not server_id:
            return view.exception_response(exceptions.InvalidArgument(message=_('必须指定硬盘挂载的云主机。')))

        is_as_admin = view.is_as_admin_request(request=request)
        try:
            if is_as_admin:
                disk = DiskManager().admin_get_disk(disk_id=disk_id, user=request.user)
            else:
                disk = DiskManager().get_manage_perm_disk(disk_id=disk_id, user=request.user)

            if not disk.is_attached():
                raise exceptions.DiskNotAttached(message=_('云硬盘未挂载，无需卸载。'))

            if disk.server_id != server_id:
                raise exceptions.DiskNotOnServer(message=_('云硬盘没有挂载在指定的云主机上'))

            if not is_as_admin:
                if disk.is_locked_operation():
                    raise exceptions.ResourceLocked(message=_('云硬盘已加锁锁定了操作'))

            server = ServerManager().get_manage_perm_server(
                server_id=server_id, user=request.user, as_admin=is_as_admin)
            if not is_as_admin:
                if server.is_locked_operation():
                    raise exceptions.ResourceLocked(message=_('无法卸载，目标云主机已加锁锁定了操作'))
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            DiskHandler.do_detach_disk(server=server, disk=disk)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        return Response(data={'server_id': server.id, 'disk_id': disk.id})

    @staticmethod
    def do_detach_disk(server: Server, disk: Disk):
        """
        卸载硬盘
        :raises: Error，Conflict
        """
        params = inputs.DiskDetachInput(instance_id=server.instance_id, disk_id=disk.instance_id)
        r = core_request.request_service(disk.service, method='disk_detach', params=params)
        if not r.ok:
            raise exceptions.ConflictError(message=_('向云主机卸载云硬盘时错误') + str(r.error))

        try:
            disk.set_detach()
        except Exception as exc:
            request_logger.error(f'硬盘{disk.id}已成功从云主机{server.id}卸载，但是硬盘元数据更新清除server id失败。')
            raise exceptions.Error(message=_('更新硬盘元数据错误，') + str(exc))

    @staticmethod
    def detail_disk(view: CustomGenericViewSet, request, kwargs):
        disk_id = kwargs.get(view.lookup_field, '')

        try:
            disk = DiskManager().get_read_perm_disk(disk_id=disk_id, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        slr = disk_serializers.DiskSerializer(instance=disk, many=False)
        return Response(data=slr.data)

    @staticmethod
    def renew_disk(view, request, kwargs):
        """
        续费云硬盘
        """
        try:
            data = DiskHandler._renew_disk_validate_params(request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        period = data['period']
        renew_to_time = data['renew_to_time']

        disk_id = kwargs.get(view.lookup_field, '')

        try:
            disk = DiskManager().get_manage_perm_disk(disk_id=disk_id, user=request.user)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        if disk.pay_type != PayType.PREPAID.value:
            return view.exception_response(exceptions.RenewPrepostOnly(message=_('只允许包年包月按量计费的云硬盘续费。')))

        if disk.expiration_time is None:
            return view.exception_response(exceptions.UnknownExpirationTime(message=_('没有过期时间的云硬盘无法续费。')))

        if renew_to_time:
            if disk.expiration_time >= renew_to_time:
                return view.exception_response(exceptions.ConflictError(
                    message=_('指定的续费终止日期必须在云硬盘的过期时间之后。'), code='InvalidRenewToTime'))

        if disk.is_locked_operation():
            return view.exception_response(exceptions.ResourceLocked(
                message=_('云主机已加锁锁定了一切操作')
            ))

        if disk.task_status != disk.TaskStatus.OK.value:
            return view.exception_response(exceptions.RenewDeliveredOkOnly(message=_('只允许为创建成功的云硬盘续费。')))

        try:
            service = ServiceManager.get_service(disk.service_id)
            if not service.pay_app_service_id:
                raise exceptions.ConflictError(
                    message=_('云主机服务未配置对应的结算系统APP服务id'), code='ServiceNoPayAppServiceId')
        except exceptions.Error as exc:
            return view.exception_response(exc)

        if service.status != service.Status.ENABLE.value:
            return view.exception_response(
                exceptions.ConflictError(message=_('提供此云硬盘资源的服务单元停止服务，不允许续费'))
            )

        _order = Order.objects.filter(
            resource_type=ResourceType.DISK.value, resource_set__instance_id=disk.id,
            trading_status__in=[Order.TradingStatus.OPENING.value, Order.TradingStatus.UNDELIVERED.value]
        ).order_by('-creation_time').first()
        if _order is not None:
            return view.exception_response(exceptions.SomeOrderNeetToTrade(
                message=_('此云硬盘存在未完成的订单（%s）, 请先完成已有订单后再提交新的订单。') % _order.id))

        with transaction.atomic():
            disk: Disk = DiskManager.get_disk_queryset().select_related(
                'service', 'user', 'vo').select_for_update().get(id=disk_id)

            start_time = None
            end_time = None
            if renew_to_time:
                start_time = disk.expiration_time
                end_time = renew_to_time
                period = 0

            if disk.belong_to_vo():
                owner_type = OwnerType.VO.value
                vo_id = disk.vo_id
                vo_name = disk.vo.name
            else:
                owner_type = OwnerType.USER.value
                vo_id = ''
                vo_name = ''

            instance_config = DiskConfig(
                disk_size=disk.size, azone_id=disk.azone_id, azone_name=disk.azone_name
            )
            order, resource = OrderManager().create_renew_order(
                pay_app_service_id=service.pay_app_service_id,
                service_id=disk.service_id,
                service_name=disk.service.name,
                resource_type=ResourceType.DISK.value,
                instance_id=disk.id,
                instance_config=instance_config,
                period=period,
                start_time=start_time,
                end_time=end_time,
                user_id=request.user.id,
                username=request.user.username,
                vo_id=vo_id,
                vo_name=vo_name,
                owner_type=owner_type
            )

        return Response(data={'order_id': order.id})

    @staticmethod
    def _renew_disk_validate_params(request):
        period = request.query_params.get('period', None)
        renew_to_time = request.query_params.get('renew_to_time', None)
        if period is not None and renew_to_time is not None:
            raise exceptions.BadRequest(message=_('不能同时指定续费时长和续费到指定日期'))

        if period is None and renew_to_time is None:
            raise exceptions.BadRequest(message=_('必须指定续费时长或续费到指定日期'), code='MissingPeriod')

        if period is not None:
            try:
                period = int(period)
                if period <= 0:
                    raise ValueError
            except ValueError:
                raise exceptions.InvalidArgument(message=_('续费时长无效'), code='InvalidPeriod')

        if renew_to_time is not None:
            renew_to_time = iso_utc_to_datetime(renew_to_time)
            if not isinstance(renew_to_time, datetime):
                raise exceptions.InvalidArgument(
                    message=_('续费到指定日期的时间格式无效'), code='InvalidRenewToTime')

        return {
            'period': period,
            'renew_to_time': renew_to_time
        }

    @staticmethod
    def change_disk_remarks(view: CustomGenericViewSet, request, kwargs):
        """
        vo组云主机需要vo组管理员权限
        """
        disk_id = kwargs.get(view.lookup_field, '')
        remark = request.query_params.get('remark', None)
        if remark is None:
            return view.exception_response(
                exceptions.InvalidArgument(message='query param "remark" is required'))

        try:
            disk = DiskManager().get_manage_perm_disk(disk_id=disk_id, user=request.user)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        try:
            disk.remarks = remark
            disk.save(update_fields=['remarks'])
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={'remark': remark})

    @staticmethod
    def modify_disk_pay_type(view: CustomGenericViewSet, request, kwargs):
        """
        修改云硬盘计费方式
        """
        try:
            data = DiskHandler._modify_pay_type_validate_params(request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        period = data['period']
        new_pay_type = data['pay_type']
        disk_id = kwargs.get(view.lookup_field, '')

        try:
            disk = DiskManager().get_manage_perm_disk(disk_id=disk_id, user=request.user)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        if disk.is_locked_operation():
            return view.exception_response(exceptions.ResourceLocked(
                message=_('云硬盘已加锁锁定了一切操作')
            ))

        if disk.task_status != disk.TaskStatus.OK.value:
            return view.exception_response(
                exceptions.ConflictError(message=_('只允许为创建成功的云硬盘修改计费方式。')))

        try:
            service = ServiceManager.get_service(disk.service_id)
            if not service.pay_app_service_id:
                raise exceptions.ConflictError(
                    message=_('云硬盘所在服务单元未配置对应的结算系统APP服务id'), code='ServiceNoPayAppServiceId')
        except exceptions.Error as exc:
            return view.exception_response(exc)

        if service.status != service.Status.ENABLE.value:
            return view.exception_response(
                exceptions.ConflictError(message=_('提供此云硬盘资源的服务单元停止服务，不允许修改计费方式。'))
            )

        if new_pay_type == PayType.PREPAID.value:
            if disk.pay_type != PayType.POSTPAID.value:
                return view.exception_response(
                    exceptions.ConflictError(message=_('必须是按量计费方式的云硬盘才可以转为包年包月计费方式。')))

        _order = Order.objects.filter(
            resource_type=ResourceType.DISK.value, resource_set__instance_id=disk_id,
            trading_status__in=[Order.TradingStatus.OPENING.value, Order.TradingStatus.UNDELIVERED.value]
        ).order_by('-creation_time').first()
        if _order is not None:
            return view.exception_response(exceptions.SomeOrderNeetToTrade(
                message=_('此云硬盘存在未完成的订单（%s）, 请先完成已有订单后再提交新的订单。') % _order.id))

        with transaction.atomic():
            disk = DiskManager.get_disk(
                disk_id=disk_id, related_fields=['service', 'user', 'vo'], select_for_update=True)

            if disk.belong_to_vo():
                owner_type = OwnerType.VO.value
                vo_id = disk.vo_id
                vo_name = disk.vo.name
            else:
                owner_type = OwnerType.USER.value
                vo_id = ''
                vo_name = ''

            instance_config = DiskConfig(
                disk_size=disk.size, azone_id=disk.azone_id, azone_name=disk.azone_name
            )
            order, resource = OrderManager().create_change_pay_type_order(
                pay_type=new_pay_type,
                pay_app_service_id=service.pay_app_service_id,
                service_id=disk.service_id,
                service_name=disk.service.name,
                resource_type=ResourceType.DISK.value,
                instance_id=disk.id,
                instance_config=instance_config,
                period=period,
                user_id=request.user.id,
                username=request.user.username,
                vo_id=vo_id,
                vo_name=vo_name,
                owner_type=owner_type
            )

        return Response(data={'order_id': order.id})

    @staticmethod
    def _modify_pay_type_validate_params(request):
        period = request.query_params.get('period', None)
        pay_type = request.query_params.get('pay_type', None)

        if pay_type is None:
            raise exceptions.BadRequest(message=_('必须指定付费方式'), code='MissingPayType')

        if pay_type not in [PayType.PREPAID.value]:
            raise exceptions.InvalidArgument(message=_('指定付费方式无效'), code='InvalidPayType')

        if pay_type == PayType.PREPAID.value:
            if period is None:
                raise exceptions.BadRequest(message=_('按量计费转包年包月必须指定续费时长'), code='MissingPeriod')

            try:
                period = int(period)
                if period <= 0:
                    raise ValueError
            except ValueError:
                raise exceptions.InvalidArgument(message=_('指定续费时长无效'), code='InvalidPeriod')

        return {
            'period': period,
            'pay_type': pay_type
        }
