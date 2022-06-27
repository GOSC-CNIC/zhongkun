from datetime import timedelta, datetime

from django.db import transaction
from django.utils.translation import gettext as _
from django.utils import timezone
from core import errors as exceptions
from core.quota import QuotaAPI
from core import request as core_request
from service.managers import ServiceManager
from servers.models import Server
from servers. managers import ServerManager
from adapters import inputs
from utils.model import PayType, OwnerType
from order.models import ResourceType, Order, Resource
from order.managers import OrderManager, ServerConfig, PriceManager


class OrderResourceDeliverer:
    """
    订单资源创建交付管理器
    """
    @staticmethod
    def deliver_order(order: Order, resource: Resource):
        if order.order_type == Order.OrderType.NEW.value:   # 新购
            if order.resource_type == ResourceType.VM.value:
                OrderResourceDeliverer().deliver_new_server(order=order, resource=resource)
            else:
                raise exceptions.Error(message=_('订购的资源类型无法交付，资源类型服务不支持。'))
        elif order.order_type == Order.OrderType.RENEWAL.value:     # 续费
            if order.resource_type == ResourceType.VM.value:
                OrderResourceDeliverer().deliver_renewal_server(order=order, resource=resource)
            else:
                raise exceptions.Error(message=_('订购的资源类型无法交付，资源类型服务不支持。'))
        else:
            raise exceptions.Error(message=_('订购的类型不支持交付。'))

    @staticmethod
    def create_server_resource_for_order(order: Order, resource: Resource):
        """
        为订单创建云服务器资源

        :return:
            service, server

        :raises: Error, NeetReleaseResource
        """
        if order.resource_type != ResourceType.VM.value:
            raise exceptions.Error(message=_('订单的资源类型不是云服务器'))

        try:
            config = ServerConfig.from_dict(order.instance_config)
        except Exception as exc:
            raise exceptions.Error(message=str(exc))

        try:
            service = ServiceManager().get_server_service(order.service_id)
        except exceptions.Error as exc:
            raise exc

        # 资源配额扣除
        try:
            QuotaAPI().server_create_quota_apply(
                service=service, vcpu=config.vm_cpu, ram=config.vm_ram, public_ip=config.vm_public_ip)
        except exceptions.Error as exc:
            raise exc

        params = inputs.ServerCreateInput(
            ram=config.vm_ram, vcpu=config.vm_cpu, image_id=config.vm_image_id, azone_id=config.vm_azone_id,
            region_id=service.region_id, network_id=config.vm_network_id, remarks=resource.instance_remark)
        try:
            out = core_request.request_service(service=service, method='server_create', params=params)
        except exceptions.APIException as exc:
            try:
                QuotaAPI().server_quota_release(
                    service=service, vcpu=config.vm_cpu, ram=config.vm_ram, public_ip=config.vm_public_ip)
            except exceptions.Error:
                pass

            raise exc

        out_server = out.server
        kwargs = {'center_quota': Server.QUOTA_PRIVATE}
        if order.owner_type == OwnerType.VO.value:
            kwargs['classification'] = Server.Classification.VO
            kwargs['vo_id'] = order.vo_id
        else:
            kwargs['classification'] = Server.Classification.PERSONAL
            kwargs['vo_id'] = None

        creation_time = timezone.now()
        if order.pay_type == PayType.PREPAID.value:
            due_time = creation_time + timedelta(PriceManager.period_month_days(order.period))
        else:
            due_time = None

        server = Server(
            id=resource.instance_id,
            service=service,
            instance_id=out_server.uuid,
            instance_name=out_server.name,
            remarks=resource.instance_remark,
            user_id=order.user_id,
            vcpus=config.vm_cpu,
            ram=config.vm_ram,
            task_status=Server.TASK_IN_CREATING,
            public_ip=config.vm_public_ip,
            expiration_time=due_time,
            image_id=config.vm_image_id,
            default_user=out_server.default_user,
            creation_time=creation_time,
            start_time=creation_time,
            azone_id=config.vm_azone_id,
            disk_size=0,
            network_id=config.vm_network_id,
            **kwargs
        )
        if out_server.default_password:
            server.raw_default_password = out_server.default_password
        try:
            server.save(force_insert=True)
        except Exception as e:
            try:
                if Server.objects.filter(id=server.id).exists():
                    server.id = None  # 清除id，save时会更新id

                server.save(force_insert=True)
            except Exception:
                message = f'向服务({service.id})请求创建云主机{out_server.uuid}成功，创建云主机记录元素据失败，{str(e)}。'
                params = inputs.ServerDeleteInput(
                    instance_id=server.instance_id, instance_name=server.instance_name, force=True)
                try:
                    core_request.request_service(server.service, method='server_delete', params=params)
                except exceptions.APIException as exc:
                    message += f'尝试向服务请求删除云主机失败，{str(exc)}'

                raise exceptions.NeetReleaseResource(message=message)

        return service, server

    @staticmethod
    def _pre_check_deliver(order: Order, resource: Resource):
        """
        交付订单资源前检查

        :return:
            order, resource

        :raises: Error
        """
        try:
            with transaction.atomic():
                order = OrderManager.get_order(order_id=order.id, select_for_update=True)
                if order.trading_status == order.TradingStatus.CLOSED.value:
                    raise exceptions.OrderTradingClosed(message=_('订单交易已关闭'))
                elif order.trading_status == order.TradingStatus.COMPLETED.value:
                    raise exceptions.OrderTradingCompleted(message=_('订单交易已完成'))

                if order.status == Order.Status.UNPAID.value:
                    raise exceptions.OrderUnpaid(message=_('订单未支付'))
                elif order.status == Order.Status.CANCELLED.value:
                    raise exceptions.OrderCancelled(message=_('订单已作废'))
                elif order.status == Order.Status.REFUND.value:
                    raise exceptions.OrderRefund(message=_('订单已退款'))
                elif order.status != Order.Status.PAID.value:
                    raise exceptions.OrderStatusUnknown(message=_('未知状态的订单'))

                resource = OrderManager.get_resource(resource_id=resource.id, select_for_update=True)
                time_now = timezone.now()
                if resource.last_deliver_time is not None:
                    delta = time_now - resource.last_deliver_time
                    if delta < timedelta(minutes=2):
                        raise exceptions.TryAgainLater(message=_('为避免重复为订单交付资源，请2分钟后重试'))

                resource.last_deliver_time = time_now
                resource.save(update_fields=['last_deliver_time'])
        except exceptions.Error as exc:
            raise exc
        except Exception as exc:
            raise exceptions.Error(message=_('检查订单交易状态，或检查更新资源上次交付时间错误。') + str(exc))

        return order, resource

    def deliver_new_server(self, order: Order, resource: Resource):
        """
        :return:
            service, server            # success

        :raises: Error, NeetReleaseResource
        """
        order, resource = self._pre_check_deliver(order=order, resource=resource)

        try:
            service, server = self.create_server_resource_for_order(order=order, resource=resource)
        except exceptions.Error as exc:
            try:
                OrderManager.set_order_resource_deliver_failed(
                    order=order, resource=resource, failed_msg='无法为订单创建云服务器资源, ' + str(exc))
            except exceptions.Error:
                pass

            raise exc

        try:
            OrderManager.set_order_resource_deliver_ok(
                order=order, resource=resource, start_time=server.creation_time,
                due_time=server.expiration_time, instance_id=server.id
            )
        except exceptions.Error:
            pass

        return service, server

    @staticmethod
    def renewal_server_resource_for_order(order: Order, resource: Resource):
        """
        为订单续费云服务器资源

        :return:
            server

        :raises: Error
        """
        if order.resource_type != ResourceType.VM.value:
            raise exceptions.Error(message=_('订单的资源类型不是云服务器'))

        if isinstance(order.start_time, datetime) and isinstance(order.end_time, datetime):
            if order.start_time >= order.end_time:
                raise exceptions.Error(message=_('续费订单续费时长或时段无效。'))

        try:
            with transaction.atomic():
                server = ServerManager.get_server(server_id=resource.instance_id, select_for_update=True)
                if server.pay_type != PayType.PREPAID.value:
                    raise exceptions.Error(message=_('云服务器不是包年包月预付费模式，无法完成续费。'))
                elif not isinstance(server.expiration_time, datetime):
                    raise exceptions.Error(message=_('云服务器没有过期时间，无法完成续费。'))
                try:
                    config = ServerConfig.from_dict(order.instance_config)
                except Exception as exc:
                    raise exceptions.Error(message=_('续费订单中云服务器配置信息有误。') + str(exc))

                if (config.vm_ram != server.ram) or (config.vm_cpu != server.vcpus):
                    raise exceptions.Error(message=_('续费订单中云服务器配置信息与云服务器配置规格不一致。'))

                if order.period > 0 and (order.start_time is None and order.end_time is None):
                    start_time = server.expiration_time
                    end_time = start_time + timedelta(days=PriceManager.period_month_days(order.period))
                elif order.period <= 0 and (
                        isinstance(order.start_time, datetime) and isinstance(order.end_time, datetime)):
                    if order.start_time != server.expiration_time:
                        delta_seconds = abs((order.start_time - server.expiration_time).total_seconds())
                        if delta_seconds > 60:
                            raise exceptions.Error(message=_('续费订单续费时长或时段与云服务器过期时间有冲突。'))

                    start_time = order.start_time
                    end_time = order.end_time
                else:
                    raise exceptions.Error(message=_('续费订单续费时长或时段无效。'))

                server.expiration_time = end_time
                server.save(update_fields=['expiration_time'])
                OrderManager.set_order_resource_deliver_ok(
                    order=order, resource=resource, start_time=start_time, due_time=end_time)
                return server
        except Exception as e:
            raise exceptions.Error.from_error(e)

    def deliver_renewal_server(self, order: Order, resource: Resource):
        """
        云服务器续费交付
        :return:
            server            # success

        :raises: Error
        """
        order, resource = self._pre_check_deliver(order=order, resource=resource)
        try:
            server = self.renewal_server_resource_for_order(order=order, resource=resource)
        except exceptions.Error as exc:
            try:
                OrderManager.set_order_resource_deliver_failed(
                    order=order, resource=resource, failed_msg='无法为订单创建云服务器资源, ' + str(exc))
            except exceptions.Error:
                pass

            raise exc

        return server
