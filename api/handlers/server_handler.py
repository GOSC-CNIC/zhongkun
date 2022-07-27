from datetime import datetime

from django.utils.translation import gettext as _
from django.db import transaction
from django.conf import settings
from rest_framework.response import Response

from core import errors as exceptions
from core.quota import QuotaAPI
from core.taskqueue import server_build_status
from core import request as core_request
from service.managers import ServiceManager
from servers.models import Server, Flavor
from servers.managers import ServerManager, ServerArchiveManager
from api import paginations
from api.viewsets import CustomGenericViewSet
from api.deliver_resource import OrderResourceDeliverer
from api.serializers import serializers
from api import request_logger
from vo.managers import VoManager
from vo.models import VirtualOrganization
from adapters import inputs
from utils.model import PayType, OwnerType
from utils.time import iso_utc_to_datetime
from order.models import ResourceType, Order, Resource
from order.managers import OrderManager, ServerConfig, OrderPaymentManager
from bill.managers import PaymentManager
from .handlers import serializer_error_msg


class ServerHandler:
    @staticmethod
    def list_servers(view: CustomGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        ip_contain = request.query_params.get('ip-contain', None)
        username = request.query_params.get('username')
        user_id = request.query_params.get('user-id')
        vo_id = request.query_params.get('vo-id')
        expired = request.query_params.get('expired', None)
        expired = expired is not None

        if (username or user_id) and vo_id:
            return view.exception_response(exceptions.BadRequest(
                message=_('参数“vo-id”不能和“user-id”、“username”之一同时提交')))

        if view.is_as_admin_request(request):
            try:
                servers = ServerManager().get_admin_servers_queryset(
                    user=request.user, service_id=service_id, user_id=user_id, username=username, vo_id=vo_id,
                    ipv4_contains=ip_contain, expired=expired
                )
            except Exception as exc:
                return view.exception_response(exceptions.convert_to_error(exc))
        else:
            if user_id or username or vo_id:
                return view.exception_response(exceptions.BadRequest(
                    message=_('参数“user-id”、“user-id”和“vo-id”只能和参数“as-admin”一起提交')))

            servers = ServerManager().get_user_servers_queryset(
                user=request.user, service_id=service_id, ipv4_contains=ip_contain)

        service_id_map = ServiceManager.get_service_id_map(use_cache=True)
        paginator = paginations.ServersPagination()
        try:
            page = paginator.paginate_queryset(servers, request, view=view)
            serializer = serializers.ServerSerializer(page, many=True, context={'service_id_map': service_id_map})
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def list_vo_servers(view, request, kwargs):
        vo_id = kwargs.get('vo_id')
        service_id = request.query_params.get('service_id', None)

        try:
            VoManager().get_has_read_perm_vo(vo_id=vo_id, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        servers = ServerManager().get_vo_servers_queryset(vo_id=vo_id, service_id=service_id)

        service_id_map = ServiceManager.get_service_id_map(use_cache=True)
        paginator = paginations.ServersPagination()
        try:
            page = paginator.paginate_queryset(servers, request, view=view)
            serializer = serializers.ServerSerializer(page, many=True, context={'service_id_map': service_id_map})
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def server_lock(view, request, kwargs):
        server_id = kwargs.get(view.lookup_field, '')
        lock = request.query_params.get('lock', None)
        if lock is None:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('参数"lock"必须提交的')))

        if lock not in Server.Lock.values:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('参数"lock"的值无效')))

        try:
            if view.is_as_admin_request(request=request):
                server = ServerManager().get_read_perm_server(
                    server_id=server_id, user=request.user, as_admin=True)
            else:
                server = ServerManager().get_read_perm_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        try:
            server.lock = lock
            server.save(update_fields=['lock'])
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={'lock': lock})

    @staticmethod
    def server_rebuild(view, request, kwargs):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            return view.exception_response(exceptions.BadRequest(msg))

        data = serializer.validated_data
        image_id = data.get('image_id', '')
        server_id = kwargs.get(view.lookup_field)
        try:
            server = ServerManager().get_manage_perm_server(
                server_id=server_id, user=request.user, related_fields=['vo'])
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        if server.task_status == server.TASK_CREATE_FAILED:
            return view.exception_response(
                exceptions.ConflictError(message=_('创建失败的云主机不支持重建'))
            )
        if server.task_status == server.TASK_IN_CREATING:
            return view.exception_response(
                exceptions.ConflictError(message=_('正在创建中的云主机不支持重建'))
            )

        if server.is_locked_operation():
            return view.exception_response(exceptions.ResourceLocked(
                message=_('云主机已加锁锁定了任何操作，请解锁后重试')
            ))

        # 过期，欠费挂起，不允许重建，需要检查是否续费，是否不再欠费
        try:
            ServerManager.check_situation_suspend(server=server)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        server.task_status = server.TASK_IN_CREATING
        server.image = ''
        server.image_id = image_id
        server.image_desc = ''
        server.default_user = ''
        server.raw_default_password = ''
        try:
            with transaction.atomic():
                server.save(update_fields=['task_status', 'image', 'image_id', 'image_desc',
                                           'default_user', 'default_password'])

                params = inputs.ServerRebuildInput(instance_id=server.instance_id, instance_name=server.instance_name,
                                                   image_id=image_id)
                try:
                    r = view.request_service(server.service, method='server_rebuild', params=params)
                except exceptions.APIException as exc:
                    raise exc

                if not r.ok:
                    raise r.error
        except Exception as exc:
            return view.exception_response(exc)

        update_fields = []
        admin_password = r.default_password
        if admin_password:
            server.raw_default_password = admin_password
            server.default_user = r.default_user if r.default_user else 'root'
            update_fields.append('default_user')
            update_fields.append('default_password')

        if r.instance_id and server.instance_id != r.instance_id:
            server.instance_id = r.instance_id
            update_fields.append('instance_id')

        if r.instance_name and server.instance_name != r.instance_name:
            server.instance_name = r.instance_name
            update_fields.append('instance_name')

        if update_fields:
            server.save(update_fields=update_fields)

        server_build_status.creat_task(server)  # 异步任务查询server创建结果，更新server信息和创建状态
        data = {
            'id': server.id,
            'image_id': r.image_id
        }
        return Response(data=data, status=202)

    @staticmethod
    def _server_create_validate_params(view, request):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise exceptions.BadRequest(msg)

        data = serializer.validated_data
        image_id = data.get('image_id', '')
        flavor_id = data.get('flavor_id', '')
        network_id = data.get('network_id', '')
        remarks = data.get('remarks', '')
        pay_type = data.get('pay_type', None)
        azone_id = data.get('azone_id', None)
        vo_id = data.get('vo_id', None)
        period = data.get('period', None)

        if azone_id == '':
            raise exceptions.BadRequest(message=_('"azone_id"参数不能为空字符'), code='InvalidAzoneId')

        if not pay_type:
            raise exceptions.BadRequest(message=_('必须指定付费模式参数"pay_type"'), code='MissingPayType')

        pay_type_values: list = PayType.values
        pay_type_values.remove(PayType.QUOTA.value)
        if pay_type not in pay_type_values:
            raise exceptions.BadRequest(message=_('付费模式参数"pay_type"值无效'), code='InvalidPayType')

        if period is not None:
            if period <= 0:
                raise exceptions.BadRequest(message=_('订购时长参数"period"值必须大于0'), code='InvalidPeriod')

            if period > (12 * 5):
                raise exceptions.BadRequest(message=_('订购时长最长为5年'), code='InvalidPeriod')
        else:
            period = 0

        if pay_type == PayType.PREPAID.value and period == 0:
            raise exceptions.BadRequest(message=_('预付费模式时，必须指定订购时长'), code='MissingPeriod')

        flavor = Flavor.objects.filter(id=flavor_id, enable=True).first()
        if not flavor:
            raise exceptions.BadRequest(message=_('无效的配置规格flavor id'), code='InvalidFlavorId')

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

        try:
            out_net = view.request_service(
                service=service, method='network_detail', params=inputs.NetworkDetailInput(network_id=network_id))
        except exceptions.APIException as exc:
            if exc.status_code in [400, 404]:
                raise exceptions.BadRequest(message=_('指定网络不存在.'), code='InvalidNetworkId')

            raise exceptions.APIException(message=_('校验网络id，查询网络时错误.') + str(exc))

        network = out_net.network

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
                raise exceptions.BadRequest(message=_('指定的可用区azone_id不存在'), code='InvalidAzoneId')

            azone_name = azone.name
        else:
            azone_id = azone_name = ''

        return {
            'pay_type': pay_type,
            'image_id': image_id,
            'flavor': flavor,
            'network': network,
            'azone_id': azone_id,
            'azone_name': azone_name,
            'vo': vo,
            'remarks': remarks,
            'service': service,
            'period': period
        }

    def server_order_create(self, view, request):
        """
        云服务器订单创建
        """
        try:
            data = ServerHandler._server_create_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        pay_type = data['pay_type']
        image_id = data['image_id']
        flavor = data['flavor']
        network = data['network']
        azone_id = data['azone_id']
        azone_name = data['azone_name']
        vo = data['vo']
        remarks = data['remarks']
        service = data['service']
        period = data['period']

        user = request.user
        is_public_network = network.public
        if vo or isinstance(vo, VirtualOrganization):
            vo_id = vo.id
            vo_name = vo.name
            owner_type = OwnerType.VO.value
        else:
            vo_id = ''
            vo_name = ''
            owner_type = OwnerType.USER.value

        instance_config = ServerConfig(
            vm_cpu=flavor.vcpus, vm_ram=flavor.ram, systemdisk_size=50, public_ip=is_public_network,
            image_id=image_id, image_name='', network_id=network.id, network_name=network.name,
            azone_id=azone_id, azone_name=azone_name
        )
        omgr = OrderManager()
        # 按量付费模式时，检查是否有余额
        if pay_type == PayType.POSTPAID.value:
            # 计算按量付费一天的计费
            original_price, trade_price = omgr.calculate_amount_money(
                resource_type=ResourceType.VM.value, config=instance_config, is_prepaid=False, period=0, days=1
            )
            if owner_type == OwnerType.USER.value:
                if not PaymentManager().has_enough_balance_user(
                    user_id=user.id, money_amount=original_price, with_coupons=True,
                    app_service_id=service.pay_app_service_id
                ):
                    return view.exception_response(
                        exceptions.BalanceNotEnough(message=_('余额不足')))
            else:
                if not PaymentManager().has_enough_balance_vo(
                        vo_id=vo_id, money_amount=original_price, with_coupons=True,
                        app_service_id=service.pay_app_service_id
                ):
                    return view.exception_response(
                        exceptions.BalanceNotEnough(message=_('余额不足'), code='VoBalanceNotEnough'))

        # 服务私有资源配额是否满足需求
        try:
            QuotaAPI.service_private_quota_meet(
                service=service, vcpu=instance_config.vm_cpu, ram=instance_config.vm_ram,
                public_ip=instance_config.vm_public_ip
            )
        except exceptions.QuotaShortageError as exc:
            return view.exception_response(
                exceptions.QuotaShortageError(message=_('指定服务无法提供足够的资源。') + str(exc)))
        except exceptions.Error as exc:
            return view.exception_response(exc)

        # 创建订单
        order, resource = omgr.create_order(
            order_type=Order.OrderType.NEW.value,
            pay_app_service_id=service.pay_app_service_id,
            service_id=service.id,
            service_name=service.name,
            resource_type=ResourceType.VM.value,
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
            self._create_server(order=order, resource=resource)
        except exceptions.Error as exc:
            request_logger.error(msg=f'[{type(exc)}] {str(exc)}')

        return Response(data={
            'order_id': order.id
        })

    @staticmethod
    def _create_server(order: Order, resource: Resource):
        """
        :return:
            server            # success

        :raises: Error
        """
        try:
            service, server = OrderResourceDeliverer().deliver_new_server(order=order, resource=resource)
        except exceptions.Error as exc:
            raise exc

        if service.service_type == service.ServiceType.EVCLOUD:
            try:
                server = core_request.update_server_detail(server=server, task_status=server.TASK_CREATED_OK)
            except exceptions.Error as e:
                pass
            else:
                return server

        server_build_status.creat_task(server)  # 异步任务查询server创建结果，更新server信息和创建状态
        return server

    def renew_server(self, view, request, kwargs):
        """
        续费云服务器
        """
        try:
            data = ServerHandler._renew_server_validate_params(request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        period = data['period']
        renew_to_time = data['renew_to_time']

        server_id = kwargs.get(view.lookup_field, '')

        try:
            server = ServerManager().get_manage_perm_server(server_id=server_id, user=request.user)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        if server.expiration_time is None:
            return view.exception_response(exceptions.UnknownExpirationTime(message=_('没有过期时间的云服务器无法续费。')))

        if renew_to_time:
            if server.expiration_time >= renew_to_time:
                return view.exception_response(exceptions.ConflictError(
                    message=_('指定的续费终止日期必须在云服务器的过期时间之后。'), code='InvalidRenewToTime'))

        if server.is_locked_operation():
            return view.exception_response(exceptions.ResourceLocked(
                message=_('云主机已加锁锁定了一切操作')
            ))

        if server.pay_type != PayType.PREPAID.value:
            return view.exception_response(exceptions.RenewPrepostOnly(message=_('只允许包年包月按量计费的云服务器续费。')))

        if server.task_status != server.TASK_CREATED_OK:
            return view.exception_response(exceptions.RenewDeliveredOkOnly(message=_('只允许为创建成功的云服务器续费。')))

        try:
            service = ServiceManager.get_service(server.service_id)
            if not service.pay_app_service_id:
                raise exceptions.ConflictError(
                    message=_('云主机服务未配置对应的结算系统APP服务id'), code='ServiceNoPayAppServiceId')
        except exceptions.Error as exc:
            return view.exception_response(exc)

        network_id = server.network_id
        network_name = ''
        if network_id:
            try:
                out_net = view.request_service(
                    service=service, method='network_detail', params=inputs.NetworkDetailInput(network_id=network_id))
                network_name = out_net.network.name
            except Exception as exc:
                pass

        if not network_name:
            network_name = server.ipv4

        _order = Order.objects.filter(
            resource_type=ResourceType.VM.value, resource_set__instance_id=server.id,
            trading_status__in=[Order.TradingStatus.OPENING.value, Order.TradingStatus.UNDELIVERED.value]
        ).order_by('-creation_time').first()
        if _order is not None:
            return view.exception_response(exceptions.SomeOrderNeetToTrade(
                message=_('此云服务器存在未完成的订单（%s）, 请先完成已有订单后再提交新的订单。') % _order.id))

        with transaction.atomic():
            server = ServerManager.get_server_queryset().select_related(
                'service', 'user', 'vo').select_for_update().get(id=server_id)

            start_time = None
            end_time = None
            if renew_to_time:
                start_time = server.expiration_time
                end_time = renew_to_time
                period = 0

            if server.belong_to_vo():
                owner_type = OwnerType.VO.value
                vo_id = server.vo_id
                vo_name = server.vo.name
            else:
                owner_type = OwnerType.USER.value
                vo_id = ''
                vo_name = ''

            instance_config = ServerConfig(
                vm_cpu=server.vcpus, vm_ram=server.ram, systemdisk_size=server.disk_size, public_ip=server.public_ip,
                image_id=server.image_id, image_name=server.image, network_id=network_id, network_name=network_name,
                azone_id=server.azone_id, azone_name=''
            )
            order, resource = OrderManager().create_renew_order(
                pay_app_service_id=service.pay_app_service_id,
                service_id=server.service_id,
                service_name=server.service.name,
                resource_type=ResourceType.VM.value,
                instance_id=server.id,
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
    def _renew_server_validate_params(request):
        period = request.query_params.get('period', None)
        renew_to_time = request.query_params.get('renew_to_time', None)
        if period is not None and renew_to_time is not None:
            raise exceptions.BadRequest(message=_('参数“period”和“renew_to_time”不能同时提交'))

        if period is None and renew_to_time is None:
            raise exceptions.BadRequest(message=_('参数“period”不得为空'), code='MissingPeriod')

        if period is not None:
            try:
                period = int(period)
                if period <= 0:
                    raise ValueError
            except ValueError:
                raise exceptions.InvalidArgument(message=_('参数“period”的值无效'), code='InvalidPeriod')

        if renew_to_time is not None:
            renew_to_time = iso_utc_to_datetime(renew_to_time)
            if not isinstance(renew_to_time, datetime):
                raise exceptions.InvalidArgument(
                    message=_('参数“renew_to_time”的值无效的时间格式'), code='InvalidRenewToTime')

        return {
            'period': period,
            'renew_to_time': renew_to_time
        }

    @staticmethod
    def server_suspend(view, request, kwargs):
        """云服务器过期、欠费停机挂起"""
        server_id = kwargs.get(view.lookup_field, '')
        act = request.query_params.get('act', None)
        if act is None:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('参数"act"必须提交')))

        if act not in Server.Situation.values:
            return view.exception_response(
                exceptions.InvalidArgument(message=_('参数"act"的值无效')))

        try:
            server = ServerManager().get_read_perm_server(
                server_id=server_id, user=request.user, as_admin=True)
        except exceptions.APIException as exc:
            return view.exception_response(exc)

        try:
            ServerManager.do_suspend_server(server=server, situation=act)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={'act': act})


class ServerArchiveHandler:
    @staticmethod
    def list_archives(view, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        queryset = ServerArchiveManager().get_user_archives_queryset(
            user=request.user, service_id=service_id)

        paginator = view.paginator
        try:
            page = paginator.paginate_queryset(queryset, request=request, view=view)
            serializer = serializers.ServerArchiveSerializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))

    @staticmethod
    def list_vo_archives(view, request, kwargs):
        vo_id = kwargs.get('vo_id')
        service_id = request.query_params.get('service_id', None)

        vo_mgr = VoManager()
        vo = vo_mgr.get_vo_by_id(vo_id)
        if vo is None:
            raise exceptions.NotFound(message=_('项目组不存在'))

        try:
            vo_mgr.check_read_perm(vo=vo, user=request.user)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        queryset = ServerArchiveManager().get_vo_archives_queryset(vo_id=vo_id, service_id=service_id)
        paginator = view.paginator
        try:
            page = paginator.paginate_queryset(queryset, request, view=view)
            serializer = serializers.ServerArchiveSerializer(page, many=True)
            return paginator.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exceptions.convert_to_error(exc))
