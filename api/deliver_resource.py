from datetime import timedelta

from django.db import transaction
from django.utils.translation import gettext as _
from django.utils import timezone
from core import errors as exceptions
from core.quota import QuotaAPI
from core import request as core_request
from service.managers import ServiceManager
from servers.models import Server
from adapters import inputs
from utils.model import PayType, OwnerType
from order.models import ResourceType, Order, Resource
from order.managers import OrderManager, ServerConfig, PriceManager


class OrderResourceDeliverer:
    """
    订单资源创建交付管理器
    """
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

        service = ServiceManager().get_server_service(order.service_id)
        if service is None:
            raise exceptions.Error(message=_('资源提供者服务不存在'))

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
        if order.pay_type == PayType.POSTPAID.value:
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
            **kwargs
        )
        if out_server.default_password:
            server.raw_default_password = out_server.default_password
        try:
            server.save(force_insert=True)
        except Exception as e:
            message = f'向服务({service.id})请求创建云主机{out_server.uuid}成功，创建云主机记录元素据失败，{str(e)}。'
            params = inputs.ServerDeleteInput(
                instance_id=server.instance_id, instance_name=server.instance_name, force=True)
            try:
                core_request.request_service(server.service, method='server_delete', params=params)
            except exceptions.APIException as exc:
                message += f'尝试向服务请求删除云主机失败，{str(exc)}'

            raise exceptions.NeetReleaseResource(message=message)

        return service, server

    def deliver_server(self, order: Order, resource: Resource):
        """
        :return:
            service, server            # success

        :raises: Error, NeetReleaseResource
        """
        try:
            with transaction.atomic():
                order = OrderManager.get_order(order_id=order.id, select_for_update=True)
                if order.trading_status in [order.TradingStatus.CLOSED.value, order.TradingStatus.COMPLETED.value]:
                    raise exceptions.Error(message=_('订单处于交易关闭和交易完成状态'))

                resource = OrderManager.get_resource(resource_id=resource.id, select_for_update=True)
                time_now = timezone.now()
                if resource.last_deliver_time is not None:
                    delta = time_now - resource.last_deliver_time
                    if delta < timedelta(minutes=2):
                        raise exceptions.ConflictError(message=_('为避免重复为订单交付资源，请2分钟后重试'))

                resource.last_deliver_time = time_now
                resource.save(update_fields=['last_deliver_time'])
        except exceptions.Error as exc:
            raise exc
        except Exception as exc:
            raise exceptions.Error(message=_('检查订单交易状态，或检查更新资源上次交付时间错误。') + str(exc))

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
                order=order, resource=resource, start_time=server.creation_time, due_time=server.creation_time)
        except exceptions.Error:
            pass

        return service, server
