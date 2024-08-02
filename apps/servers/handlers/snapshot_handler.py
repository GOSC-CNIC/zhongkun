from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors as exceptions
from core.adapters import inputs
from core.request import request_service, update_server_detail
from utils.model import ResourceType, PayType, OwnerType
from apps.api.viewsets import CustomGenericViewSet, serializer_error_msg
from apps.vo.managers import VoManager
from apps.servers.managers import ServerSnapshotManager, ServerManager
from apps.servers import serializers
from apps.order.models import Order
from apps.order.managers import OrderManager, ServerSnapshotConfig


class SnapshotHandler:

    @staticmethod
    def list_server_snapshot(view: CustomGenericViewSet, request):
        """
        列举云主机快照
        """
        try:
            params = SnapshotHandler._list_snapshot_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        service_id = params['service_id']
        server_id = params['server_id']
        remark = params['remark']
        vo_id: str = params['vo_id']
        vo_name = params['vo_name']
        username = params['username']
        user_id = params['user_id']
        exclude_vo = params['exclude_vo']

        if view.is_as_admin_request(request):
            try:
                queryset = ServerSnapshotManager().get_admin_snapshot_queryset(
                    admin_user=request.user, service_id=service_id, server_id=server_id, remark=remark,
                    user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, exclude_vo=exclude_vo
                )
            except Exception as exc:
                return view.exception_response(exc)
        elif vo_id:
            try:
                VoManager().get_has_read_perm_vo(vo_id=vo_id, user=request.user)
            except exceptions.Error as exc:
                return view.exception_response(exc)

            queryset = ServerSnapshotManager().get_vo_snapshot_queryset(
                vo_id=vo_id, service_id=service_id, server_id=server_id, remark=remark
            )
        else:
            queryset = ServerSnapshotManager().get_user_snapshot_queryset(
                user=request.user, service_id=service_id, server_id=server_id, remark=remark
            )

        try:
            snapshots = view.paginate_queryset(queryset)
            serializer = serializers.ServerSnapshotSerializer(instance=snapshots, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def _list_snapshot_validate_params(view, request):
        service_id = request.query_params.get('service_id', None)
        server_id = request.query_params.get('server_id', None)
        remark = request.query_params.get('remark', None)
        vo_id = request.query_params.get('vo_id', None)
        # as-admin only
        vo_name = request.query_params.get('vo_name', None)
        username = request.query_params.get('username', None)
        user_id = request.query_params.get('user_id', None)
        exclude_vo = request.query_params.get('exclude_vo', None)

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
            'server_id': server_id,
            'remark': remark,
            'vo_id': vo_id,
            'vo_name': vo_name,
            'username': username,
            'user_id': user_id,
            'exclude_vo': exclude_vo
        }

    @staticmethod
    def detail_server_snapshot(view: CustomGenericViewSet, request, kwargs):
        snapshot_id = kwargs.get(view.lookup_field, '')

        try:
            if view.is_as_admin_request(request):
                snapshot = ServerSnapshotManager().admin_get_snapshot(
                    snapshot_id=snapshot_id, user=request.user)
            else:
                snapshot = ServerSnapshotManager().get_has_perm_snapshot(
                    snapshot_id=snapshot_id, user=request.user, is_readonly=True)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        slr = serializers.ServerSnapshotSerializer(instance=snapshot, many=False)
        return Response(data=slr.data)

    @staticmethod
    def delete_server_snapshot(view: CustomGenericViewSet, request, kwargs):
        snapshot_id = kwargs.get(view.lookup_field, '')

        try:
            if view.is_as_admin_request(request):
                snapshot = ServerSnapshotManager().admin_get_snapshot(
                    snapshot_id=snapshot_id, user=request.user)
            else:
                snapshot = ServerSnapshotManager().get_has_perm_snapshot(
                    snapshot_id=snapshot_id, user=request.user, is_readonly=False)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        who_action = request.user.username
        try:
            r = request_service(
                service=snapshot.service, method='server_snapshot_delete',
                params=inputs.ServerSnapshotDeleteInput(snap_id=snapshot.instance_id, _who_action=who_action)
            )
            if r.ok:
                snapshot.do_soft_delete(deleted_user=who_action)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)

    @staticmethod
    def rollback_server_to_snapshot(view: CustomGenericViewSet, request, kwargs):
        snapshot_id = kwargs.get(view.lookup_field, '')
        server_id = kwargs['server_id']

        try:
            snapshot = ServerSnapshotManager().get_snapshot(snapshot_id=snapshot_id)
            server = ServerManager().get_manage_perm_server(server_id=server_id, user=request.user)
            if server.is_locked_operation():
                raise exceptions.ResourceLocked(message=_('云主机已加锁锁定了一切操作'))

            if server.id != snapshot.server_id:
                raise exceptions.ConflictError(message=_('快照不属于此云主机'))
        except exceptions.Error as exc:
            return view.exception_response(exc)

        try:
            request_service(
                service=snapshot.service, method='server_rollback_snapshot',
                params=inputs.ServerRollbackSnapshotInput(
                    instance_id=server.instance_id, snap_id=snapshot.instance_id, _who_action=request.user.username)
            )
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=200)

    @staticmethod
    def create_server_snapshot(view: CustomGenericViewSet, request, kwargs):
        try:
            data = SnapshotHandler._snapshot_create_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        server_id = data['server_id']
        period = data['period']
        period_unit = data['period_unit']
        snapshot_name = data['snapshot_name']
        description = data['description']

        try:
            server = ServerManager().get_manage_perm_server(
                server_id=server_id, user=request.user, as_admin=False)

            service = server.service
            if not service:
                raise exceptions.ConflictError(message=_('云主机服务单元未知'))

            if not service.pay_app_service_id:
                raise exceptions.ConflictError(
                    message=_('服务未配置对应的结算系统APP服务id'), code='ServiceNoPayAppServiceId')

            if server.disk_size <= 0:
                try:
                    server = update_server_detail(server=server)
                except exceptions.Error as exc:
                    raise exceptions.ConflictError(
                        message=_('云主机系统盘大小未知，尝试更新云主机系统盘大小失败') + str(exc))

            if server.disk_size <= 0:
                raise exceptions.ConflictError(message=_('云主机系统盘大小未知'))

            if server.classification == server.Classification.PERSONAL.value:
                user_id = server.user_id
                username = server.user.username
                vo_id = ''
                vo_name = ''
                owner_type = OwnerType.USER.value
            else:
                user_id = request.user.id
                username = request.user.username
                vo_id = server.vo_id
                vo_name = server.vo.name
                owner_type = OwnerType.VO.value

            ins_config = ServerSnapshotConfig(
                server_id=server_id, systemdisk_size=server.disk_size, azone_id=server.azone_id,
                snapshot_name=snapshot_name, snapshot_desc=description
            )
            order, resources = OrderManager().create_order(
                order_type=Order.OrderType.NEW.value, service_id=service.id, service_name=service.name,
                pay_app_service_id=service.pay_app_service_id, resource_type=ResourceType.VM_SNAPSHOT.value,
                instance_config=ins_config, period=period, period_unit=period_unit, pay_type=PayType.PREPAID.value,
                user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type,
                number=1, remark=description
            )
        except exceptions.Error as exc:
            return view.exception_response(exc)

        return Response(data={'order_id': order.id})

    @staticmethod
    def _snapshot_create_validate_params(view: CustomGenericViewSet, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise exceptions.BadRequest(msg)

        data = serializer.validated_data
        server_id = data.get('server_id', None)
        period = data.get('period', None)
        period_unit = data.get('period_unit', None)
        snapshot_name = data.get('snapshot_name', '')
        description = data.get('description', '')

        if not server_id:
            raise exceptions.BadRequest(message=_('必须指定云主机'), code='InvalidServerId')

        if not period_unit:
            raise exceptions.BadRequest(message=_('必须指定订购时长单位'), code='InvalidPeriodUnit')

        if period_unit not in Order.PeriodUnit.values:
            raise exceptions.BadRequest(message=_('订购时长单位无效，可选为天或月'), code='InvalidPeriodUnit')

        if period <= 0:
            raise exceptions.BadRequest(message=_('订购时长必须大于0'), code='InvalidPeriod')

        period_days = period
        if period_unit == Order.PeriodUnit.MONTH.value:
            period_days = 30 * period

        if period_days > (30 * 12 * 5):
            raise exceptions.BadRequest(message=_('订购时长最长为5年'), code='InvalidPeriod')

        return {
            'server_id': server_id,
            'snapshot_name': snapshot_name,
            'description': description,
            'period': period,
            'period_unit': period_unit
        }

    @staticmethod
    def renew_server_snapshot(view: CustomGenericViewSet, request, kwargs):
        try:
            data = SnapshotHandler._snapshot_renew_validate_params(view=view, request=request)
        except exceptions.Error as exc:
            return view.exception_response(exc)

        snapshot_id = data['snapshot_id']
        period = data['period']
        period_unit = data['period_unit']

        try:
            snapshot = ServerSnapshotManager().get_has_perm_snapshot(
                snapshot_id=snapshot_id, user=request.user, is_readonly=True)
            if snapshot.size <= 0:
                raise exceptions.ConflictError(message=_('无法续费，快照大小未知。'))
            if snapshot.expiration_time is None:
                raise exceptions.UnknownExpirationTime(message=_('无法续费，快照没有过期时间。'))

            server = snapshot.get_server()
            if not server:
                raise exceptions.ConflictError(message=_('无法续费，快照所属云主机未知'))

            service = server.service
            if not service:
                raise exceptions.ConflictError(message=_('快照所属云主机服务单元未知'))

            if not service.pay_app_service_id:
                raise exceptions.ConflictError(
                    message=_('服务单元未配置对应的结算系统APP服务id'), code='ServiceNoPayAppServiceId')

            _order = Order.objects.filter(
                resource_type=ResourceType.VM_SNAPSHOT.value, resource_set__instance_id=snapshot.id,
                trading_status__in=[Order.TradingStatus.OPENING.value, Order.TradingStatus.UNDELIVERED.value]
            ).order_by('-creation_time').first()
            if _order is not None:
                raise exceptions.SomeOrderNeetToTrade(
                    message=_('此快照存在未完成的订单（%s）, 请先完成已有订单后再提交新的订单。') % _order.id)

            if snapshot.classification == snapshot.Classification.PERSONAL.value:
                user_id = snapshot.user_id
                username = snapshot.user.username
                vo_id = ''
                vo_name = ''
                owner_type = OwnerType.USER.value
            else:
                user_id = request.user.id
                username = request.user.username
                vo_id = snapshot.vo_id
                vo_name = snapshot.vo.name
                owner_type = OwnerType.VO.value

            ins_config = ServerSnapshotConfig(
                server_id=server.id, systemdisk_size=snapshot.size, azone_id=server.azone_id,
                snapshot_name=snapshot.name, snapshot_desc=snapshot.remarks
            )
            order, resources = OrderManager().create_renew_order(
                service_id=service.id, service_name=service.name, pay_app_service_id=service.pay_app_service_id,
                resource_type=ResourceType.VM_SNAPSHOT.value, instance_id=snapshot_id,
                instance_config=ins_config,
                period=period, period_unit=period_unit, start_time=None, end_time=None,
                user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type
            )
        except exceptions.Error as exc:
            return view.exception_response(exc)

        return Response(data={'order_id': order.id})

    @staticmethod
    def _snapshot_renew_validate_params(view: CustomGenericViewSet, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise exceptions.BadRequest(msg)

        data = serializer.validated_data
        snapshot_id = data.get('snapshot_id', None)
        period = data.get('period', None)
        period_unit = data.get('period_unit', None)

        if not snapshot_id:
            raise exceptions.BadRequest(message=_('必须指定云主机快照'), code='InvalidSnapshotId')

        if not period_unit:
            raise exceptions.BadRequest(message=_('必须指定订购时长单位'), code='InvalidPeriodUnit')

        if period_unit not in Order.PeriodUnit.values:
            raise exceptions.BadRequest(message=_('订购时长单位无效，可选为天或月'), code='InvalidPeriodUnit')

        if period <= 0:
            raise exceptions.BadRequest(message=_('订购时长必须大于0'), code='InvalidPeriod')

        period_days = period
        if period_unit == Order.PeriodUnit.MONTH.value:
            period_days = 30 * period

        if period_days > (30 * 12 * 5):
            raise exceptions.BadRequest(message=_('订购时长最长为5年'), code='InvalidPeriod')

        return {
            'snapshot_id': snapshot_id,
            'period': period,
            'period_unit': period_unit
        }

    @staticmethod
    def update_server_snapshot(view: CustomGenericViewSet, request, kwargs):
        snapshot_id = kwargs.get(view.lookup_field, '')

        try:
            serializer = view.get_serializer(data=request.data)
            if not serializer.is_valid(raise_exception=False):
                msg = serializer_error_msg(serializer.errors)
                raise exceptions.BadRequest(msg)

            data = serializer.validated_data
            snapshot_name = data.get('snapshot_name', '')
            description = data.get('description', '')

            if not snapshot_name and not description:
                return Response(data=None)

            snapshot = ServerSnapshotManager().get_has_perm_snapshot(
                snapshot_id=snapshot_id, user=request.user, is_readonly=False)

            update_fields = []
            if snapshot_name:
                snapshot.name = snapshot_name
                update_fields.append('name')

            if description:
                snapshot.remarks = description
                update_fields.append('remarks')

            if update_fields:
                try:
                    snapshot.save(update_fields=update_fields)
                except Exception as exc:
                    raise exceptions.Error(message=_('更新快照元数据错误') + str(exc))
        except exceptions.Error as exc:
            return view.exception_response(exc)

        return Response(data=None)
