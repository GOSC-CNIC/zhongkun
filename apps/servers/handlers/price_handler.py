from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from core.request import update_server_detail
from apps.api.viewsets import CustomGenericViewSet
from apps.order.models import Order
from apps.order.managers import PriceManager
from utils.decimal_utils import quantize_10_2
from apps.servers.managers import ServerManager, ServerSnapshotManager


class DescribePriceHandler:
    @staticmethod
    def param_period_validate(period):
        """
        :return: int or None
        """
        if period is not None:
            try:
                period = int(period)
            except ValueError:
                raise errors.InvalidArgument(message=_('参数“period”的值无效'))

            if period <= 0:
                raise errors.InvalidArgument(message=_('参数“period”的值无效，必须大于0'))

        return period

    def describe_price_snapshot(self, view: CustomGenericViewSet, request):
        try:
            data = self.validate_snapshot_params(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        server_id = data['server_id']
        period = data['period']
        period_unit = data['period_unit']

        try:
            try:
                server = ServerManager.get_server(server_id=server_id)
            except errors.NotFound as exc:
                raise errors.TargetNotExist(message=str(exc))

            if server.disk_size <= 0:
                if not server.service:
                    return view.exception_response(errors.ConflictError(
                        message=_('无法完成询价，云主机系统盘大小未知，云主机服务单元未知')))

                try:
                    server = update_server_detail(server=server)
                except errors.Error as exc:
                    return view.exception_response(errors.ConflictError(
                        message=_('无法完成询价，云主机系统盘大小未知，尝试更新云主机系统盘大小失败') + str(exc)))

            if server.disk_size <= 0:
                return view.exception_response(errors.ConflictError(message=_('无法完成询价，云主机系统盘大小未知')))
        except errors.Error as exc:
            return view.exception_response(exc)

        original_price, trade_price = PriceManager().describe_snapshot_price(
            disk_gib=server.disk_size, is_prepaid=True,
            period=period, period_unit=period_unit, days=0)

        return Response(data={
            'price': {
                'original': str(quantize_10_2(original_price)),
                'trade': str(quantize_10_2(trade_price))
            }
        })

    def validate_snapshot_params(self, request):
        period, period_unit = self.validate_period_and_unit(request)
        server_id = request.query_params.get('server_id', None)
        if not server_id:
            raise errors.InvalidArgument(message=_('必须指定云主机'))

        return {
            'server_id': server_id,
            'period': period,
            'period_unit': period_unit
        }

    def validate_period_and_unit(self, request):
        period = request.query_params.get('period', None)
        period_unit = request.query_params.get('period_unit', None)

        period = self.param_period_validate(period=period)
        if not period:
            raise errors.InvalidArgument(message=_('必须指定时长'))

        if period_unit not in Order.PeriodUnit.values:
            raise errors.InvalidArgument(message=_('时长单位无效'))

        return period, period_unit

    def describe_price_renew_snapshot(self, view: CustomGenericViewSet, request):
        try:
            data = self.validate_renew_snapshot_params(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        snapshot_id = data['snapshot_id']
        period = data['period']
        period_unit = data['period_unit']

        try:
            snapshot = ServerSnapshotManager().get_has_perm_snapshot(
                snapshot_id=snapshot_id, user=request.user, is_readonly=True)
            if snapshot.size <= 0:
                raise errors.ConflictError(message=_('无法询价，快照大小未知。'))
        except errors.Error as exc:
            return view.exception_response(exc)

        original_price, trade_price = PriceManager().describe_snapshot_price(
            disk_gib=snapshot.size, is_prepaid=True,
            period=period, period_unit=period_unit, days=0)

        return Response(data={
            'price': {
                'original': str(quantize_10_2(original_price)),
                'trade': str(quantize_10_2(trade_price))
            }
        })

    def validate_renew_snapshot_params(self, request):
        period, period_unit = self.validate_period_and_unit(request)
        snapshot_id = request.query_params.get('snapshot_id', None)
        if not snapshot_id:
            raise errors.InvalidArgument(message=_('必须指定云主机快照'))

        return {
            'snapshot_id': snapshot_id,
            'period': period,
            'period_unit': period_unit
        }

