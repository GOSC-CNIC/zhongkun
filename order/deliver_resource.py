from typing import List, Tuple, Union
from datetime import timedelta, datetime

from django.db import transaction
from django.utils.translation import gettext as _
from django.utils import timezone
from core import errors as exceptions
from core.quota import QuotaAPI
from core import request as core_request
from core.taskqueue import server_build_status
from servers.managers import ServiceManager
from servers.models import Server, Disk, ServerArchive, DiskChangeLog, ServiceConfig
from servers.managers import ServerManager, DiskManager
from adapters import inputs, outputs
from utils.model import PayType, OwnerType, ResourceType
from order.models import Order, Resource
from order.managers import OrderManager, ServerConfig, PriceManager, DiskConfig, ScanConfig
from scan.models import VtTask
from scan.managers import TaskManager


class OrderResourceDeliverer:
    """
    订单资源创建交付管理器
    """
    def deliver_order(self, order: Order, resource: Resource = None) -> List[Union[Server, Disk]]:
        """
        :return:
            list

        :raises: Error
        """
        if order.order_type == Order.OrderType.NEW.value:  # 新购
            if order.resource_type == ResourceType.VM.value:
                service, server_list, err_list = self.deliver_new_servers(order=order)
                self.after_deliver_server_list(service=service, servers=server_list)
                if err_list:
                    raise err_list[0]
                return server_list
            elif order.resource_type == ResourceType.DISK.value:
                service, disk = self.deliver_new_disk(order=order, resource=resource)
                self.after_deliver_disk(service=service, disk=disk)
                return [disk]
            if order.resource_type == ResourceType.SCAN.value:
                tasks = self.deliver_new_sacn(order=order)
                return tasks
        elif order.order_type == Order.OrderType.RENEWAL.value:  # 续费
            if order.resource_type == ResourceType.VM.value:
                server = self.deliver_renewal_server(order=order, resource=resource)
                return [server]
            elif order.resource_type == ResourceType.DISK.value:
                disk = self.deliver_renewal_disk(order=order, resource=resource)
                return [disk]
        elif order.order_type in [Order.OrderType.POST2PRE.value]:  # 付费方式修改
            if order.resource_type == ResourceType.VM.value:
                server = self.deliver_modify_server_pay_type(order=order, resource=resource)
                return [server]
            elif order.resource_type == ResourceType.DISK.value:
                disk = self.deliver_modify_disk_pay_type(order=order, resource=resource)
                return [disk]
        else:
            raise exceptions.Error(message=_('订单的类型不支持交付。'))

        raise exceptions.Error(message=_('订购的资源类型无法交付，资源类型服务不支持。'))

    def after_deliver_server_list(self, service: ServiceConfig, servers: List[Server]):
        if len(servers) == 1:
            self.after_deliver_server(service=service, server=servers[0])
            return servers

        for s in servers:
            server_build_status.creat_task(s)  # 异步任务查询server创建结果，更新server信息和创建状态

        return servers

    @staticmethod
    def after_deliver_server(service: ServiceConfig, server: Server):
        if service.service_type == service.ServiceType.EVCLOUD.value:
            try:
                server = core_request.update_server_detail(server=server, task_status=server.TASK_CREATED_OK)
            except exceptions.Error as e:
                pass
            else:
                return server

        server_build_status.creat_task(server)  # 异步任务查询server创建结果，更新server信息和创建状态
        return server

    @staticmethod
    def after_deliver_disk(service: ServiceConfig, disk: Disk):
        if service.service_type == service.ServiceType.EVCLOUD.value:
            try:
                disk = core_request.update_disk_detail(disk=disk, task_status=disk.TaskStatus.OK.value)
            except exceptions.Error as e:
                pass
            else:
                return disk

        server_build_status.creat_disk_task(disk=disk)  # 异步任务查询disk创建结果，更新disk信息和创建状态
        return disk

    @staticmethod
    def _check_pre_create_server_resources(order: Order, resources: List[Resource]) -> (ServiceConfig, ServerConfig):
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

        number = len(resources)
        # 资源配额是否满足
        try:
            QuotaAPI().service_private_quota_meet(
                service=service,
                vcpu=config.vm_cpu * number,
                ram_gib=config.vm_ram_gib * number,
                public_ips=number if config.vm_public_ip else 0,
                private_ips=0 if config.vm_public_ip else number
            )
        except exceptions.Error as exc:
            raise exc

        return service, config

    def create_server_resources_for_order(
            self, order: Order, resources: List[Resource], service: ServiceConfig, config: ServerConfig
    ) -> Tuple[List[Server], List[Tuple[Resource, exceptions.Error]]]:
        """
        为订单创建云服务器资源

        :return:
            server_list, list[(failed_resources, error)]
        """
        server_list = []
        failed_resources = []    # 交付失败的
        for res in resources:
            try:
                server = self.create_server_resource(
                    order=order, resource=res, service=service, config=config)
            except exceptions.Error as exc:
                failed_resources.append((res, exc))
                res.set_deliver_failed(failed_msg=_('创建云服务器资源失败, ') + str(exc), raise_exc=False)
                continue

            res.set_deliver_success(instance_id=server.id, raise_exc=False)
            server_list.append(server)

        return server_list, failed_resources

    @staticmethod
    def _request_create_server(service, params: inputs.ServerCreateInput):
        return core_request.request_service(service=service, method='server_create', params=params)

    def create_server_resource(self, order: Order, resource: Resource, service, config: ServerConfig):
        """
        为订单创建云服务器资源

        :return:
            server

        :raises: Error, NeetReleaseResource
        """
        # 资源配额扣除
        if config.vm_public_ip:
            public_ips = 1
            private_ips = 0
        else:
            public_ips = 0
            private_ips = 1

        try:
            QuotaAPI().server_create_quota_apply(
                service=service, vcpu=config.vm_cpu, ram_gib=config.vm_ram_gib, public_ip=config.vm_public_ip)
        except exceptions.Error as exc:
            raise exc

        params = inputs.ServerCreateInput(
            ram=config.vm_ram_mib, vcpu=config.vm_cpu, image_id=config.vm_image_id, azone_id=config.vm_azone_id,
            region_id=service.region_id, network_id=config.vm_network_id, remarks=resource.instance_remark,
            systemdisk_size=config.vm_systemdisk_size, flavor_id=config.vm_flavor_id
        )
        try:
            out = self._request_create_server(service=service, params=params)
        except exceptions.APIException as exc:
            try:
                QuotaAPI().server_quota_release(
                    service=service, vcpu=config.vm_cpu, ram_gib=config.vm_ram_gib,
                    public_ips=public_ips, private_ips=private_ips
                )
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
            ram=config.vm_ram_gib,
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
            pay_type=order.pay_type,
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

        return server

    @staticmethod
    def _check_order_pre_deliver(order_id: str) -> Order:
        """
        在订单资源交付前，检查订单的交易状态

        * 此方法需要在事务中调用
        """
        order = OrderManager.get_order(order_id=order_id, select_for_update=True)
        OrderManager.can_deliver_or_refund_for_order(order)
        return order

    @staticmethod
    def _check_order_resources_pre_deliver(order_id: str, resource_ids: list[str] = None) -> List[Resource]:
        """
        在订单资源交付前，检查订单的资源交付状态

        * 此方法需要在事务中调用

        :resource_ids: 如果未指定，就查询订单的资源列表
        """
        # 订单资源
        if resource_ids:
            resources = OrderManager.get_resources(resource_ids=resource_ids, select_for_update=True)
        else:
            resources = OrderManager.get_order_resources(order_id=order_id, select_for_update=True)

        resources.sort(key=lambda x: x.creation_time, reverse=False)

        time_now = timezone.now()
        need_deliver_resources = []
        for res in resources:
            if res.order_id != order_id:
                raise exceptions.OrderStatusUnknown(message=_('订单和订单资源不匹配'))

            # 未成功交付的资源，检查上次交付时间，并更新本次交付时间
            if res.instance_status == res.InstanceStatus.SUCCESS.value:
                continue
            if res.last_deliver_time is not None:
                delta = time_now - res.last_deliver_time
                if delta < timedelta(minutes=1):
                    raise exceptions.TryAgainLater(message=_('为避免重复为订单交付资源，请1分钟后重试'))

            res.last_deliver_time = time_now
            need_deliver_resources.append(res)

        if not need_deliver_resources:
            if resources:
                raise exceptions.OrderTradingCompleted(message=_('订单的资源已交付成功，没有待交付的资源'))
            else:
                raise exceptions.OrderTradingCompleted(message=_('订单没有待交付的资源'))

        need_deli_res_ids = [x.id for x in need_deliver_resources]
        if len(need_deli_res_ids) == 1:
            Resource.objects.filter(id=need_deli_res_ids[0]).update(last_deliver_time=time_now)
        else:
            Resource.objects.filter(id__in=need_deli_res_ids).update(last_deliver_time=time_now)

        return resources

    def _pre_check_deliver(self, order: Order, resource_ids: list[str] = None) -> (Order, List[Resource]):
        """
        交付订单资源前检查

        :resource_ids: 如果未指定，就查询订单的资源列表
        :return:
            order, resources

        :raises: Error
        """
        try:
            with transaction.atomic():
                order = self._check_order_pre_deliver(order_id=order.id)
                resources = self._check_order_resources_pre_deliver(
                    order_id=order.id, resource_ids=resource_ids
                )
                order.set_order_action(act=Order.OrderAction.DELIVERING.value)
        except exceptions.Error as exc:
            raise exc
        except Exception as exc:
            raise exceptions.Error(message=_('检查订单交易状态，或检查更新资源上次交付时间错误。') + str(exc))

        return order, resources

    @staticmethod
    def clear_order_action(order) -> Union[Order, exceptions.Error]:
        """
        清除订单交付资源动作标记
        """
        try:
            with transaction.atomic():
                new_order = OrderManager.get_order(order_id=order.id, select_for_update=True)
                new_order.set_order_action(act=Order.OrderAction.NONE.value)
        except Exception as exc:
            return exceptions.Error(message=_('清除订单操作动作标记失败。') + str(exc))

        return new_order

    @staticmethod
    def _update_order_failed(order: Order, all_res_count: int, failed_res_count: int):
        if all_res_count <= failed_res_count:  # 订单订购资源全部创建失败
            trading_status = Order.TradingStatus.UNDELIVERED.value
        else:  # 部分交付失败
            trading_status = Order.TradingStatus.PART_DELIVER.value

        try:
            OrderManager.set_order_deliver_failed(order=order, trading_status=trading_status)
        except exceptions.Error:
            pass

    def deliver_new_servers(self, order: Order) -> (ServiceConfig, List[Server], List[exceptions.Error]):
        """
        :return:
            service, servers            # success

        :raises: Error
        """
        order, resources = self._pre_check_deliver(order=order)
        try:
            service, server_list, err_list = self._deliver_new_servers(order=order, resources=resources)
        except Exception as exc:
            raise exc
        finally:
            self.clear_order_action(order=order)

        return service, server_list, err_list

    def _deliver_new_servers(
            self, order: Order, resources: List[Resource]
    ) -> (ServiceConfig, List[Server], List[exceptions.Error]):
        """
        :return:
            service, servers            # success

        :raises: Error
        """
        if len(resources) > order.number:
            raise exceptions.ConflictError(message=_('订单资源记录数量大于订单订购数量'))

        need_deliver_resources = []
        success_deliver_resources = []
        for res in resources:
            if res.instance_status == res.InstanceStatus.SUCCESS.value:
                success_deliver_resources.append(res)
            else:
                need_deliver_resources.append(res)

        try:
            service, server_config = self._check_pre_create_server_resources(
                order=order, resources=need_deliver_resources)
        except exceptions.Error as exc:
            res_ids = [x.id for x in need_deliver_resources]
            Resource.set_many_deliver_failed(res_ids=res_ids, failed_msg=str(exc), raise_exc=False)
            self._update_order_failed(
                order=order, all_res_count=len(resources), failed_res_count=len(need_deliver_resources))
            raise exc

        server_list, failed_resources = self.create_server_resources_for_order(
            order=order, resources=need_deliver_resources, service=service, config=server_config)
        err_list = []
        if failed_resources:
            self._update_order_failed(order=order, all_res_count=len(resources), failed_res_count=len(failed_resources))
            err_list = [x[1] for x in failed_resources]
            # res, err = failed_resources[0]
            # raise err
        else:       # 没有交付失败的资源
            try:
                OrderManager.set_order_deliver_success(order=order)
            except exceptions.Error:
                pass

        return service, server_list, err_list

    @staticmethod
    def check_pre_renewal_server_resource(order: Order, server):
        """
        检查是否满足云主机续费的条件

        :return:
            start_time, end_time    # 此订单续费的起始和截止时间

        :raises: Error
        """
        if server.pay_type != PayType.PREPAID.value:
            raise exceptions.Error(message=_('云服务器不是包年包月预付费模式，无法完成续费。'))
        elif not isinstance(server.expiration_time, datetime):
            raise exceptions.Error(message=_('云服务器没有过期时间，无法完成续费。'))
        try:
            config = ServerConfig.from_dict(order.instance_config)
        except Exception as exc:
            raise exceptions.Error(message=_('续费订单中云服务器配置信息有误。') + str(exc))

        if (config.vm_ram_gib != server.ram_gib) or (config.vm_cpu != server.vcpus):
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

        return start_time, end_time

    def renewal_server_resource_for_order(self, order: Order, resource: Resource):
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
                start_time, end_time = self.check_pre_renewal_server_resource(
                    order=order, server=server
                )
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
        order, resource_list = self._pre_check_deliver(order=order, resource_ids=[resource.id])

        try:
            resource = resource_list[0]
            server = self.renewal_server_resource_for_order(order=order, resource=resource)
        except exceptions.Error as exc:
            try:
                OrderManager.set_order_resource_deliver_failed(
                    order=order, resource=resource, failed_msg='无法为订单完成云服务器资源续费, ' + str(exc))
            except exceptions.Error:
                pass

            raise exc
        finally:
            self.clear_order_action(order=order)

        return server

    def deliver_new_disk(self, order: Order, resource: Resource):
        """
        :return:
            service, disk            # success

        :raises: Error, NeetReleaseResource
        """
        order, resource_list = self._pre_check_deliver(order=order, resource_ids=[resource.id])

        try:
            resource = resource_list[0]
            service, disk = self.create_disk_resource_for_order(order=order, resource=resource)
        except exceptions.Error as exc:
            try:
                OrderManager.set_order_resource_deliver_failed(
                    order=order, resource=resource, failed_msg='无法为订单创建云硬盘资源, ' + str(exc))
            except exceptions.Error:
                pass

            raise exc
        finally:
            self.clear_order_action(order=order)

        try:
            OrderManager.set_order_resource_deliver_ok(
                order=order, resource=resource, start_time=disk.creation_time,
                due_time=disk.expiration_time, instance_id=disk.id
            )
        except exceptions.Error:
            pass

        return service, disk

    @staticmethod
    def create_disk_resource_for_order(order: Order, resource: Resource):
        """
        为订单创建云硬盘资源

        :return:
            service, disk

        :raises: Error, NeetReleaseResource
        """
        if order.resource_type != ResourceType.DISK.value:
            raise exceptions.Error(message=_('订单的资源类型不是云硬盘'))

        try:
            config = DiskConfig.from_dict(order.instance_config)
        except Exception as exc:
            raise exceptions.Error(message=str(exc))

        try:
            service = ServiceManager().get_service(service_id=order.service_id)
        except exceptions.Error as exc:
            raise exc

        disk_size = config.disk_size
        # 资源配额扣除
        try:
            QuotaAPI().disk_create_quota_apply(service=service, disk_size=disk_size)
        except exceptions.Error as exc:
            raise exc

        params = inputs.DiskCreateInput(
            region_id=service.region_id, azone_id=config.disk_azone_id,
            size_gib=config.disk_size, description=resource.instance_remark
        )
        try:
            out = core_request.request_service(service=service, method='disk_create', params=params)
        except exceptions.APIException as exc:
            try:
                QuotaAPI().disk_quota_release(service=service, disk_size=disk_size)
            except exceptions.Error:
                pass

            raise exc

        out_disk: outputs.SimpleDisk = out.disk
        kwargs = {}
        if order.owner_type == OwnerType.VO.value:
            kwargs['classification'] = Disk.Classification.VO.value
            kwargs['vo_id'] = order.vo_id
        else:
            kwargs['classification'] = Disk.Classification.PERSONAL.value
            kwargs['vo_id'] = None

        creation_time = timezone.now()
        if order.pay_type == PayType.PREPAID.value:
            due_time = creation_time + timedelta(PriceManager.period_month_days(order.period))
        else:
            due_time = None

        disk = Disk(
            id=resource.instance_id,
            name='',
            instance_id=out_disk.disk_id,
            instance_name=out_disk.name,
            size=disk_size,
            service=service,
            azone_id=config.disk_azone_id,
            azone_name=config.disk_azone_name,
            quota_type=Disk.QuotaType.PRIVATE.value,
            creation_time=creation_time,
            remarks=resource.instance_remark,
            task_status=Disk.TaskStatus.CREATING.value,
            expiration_time=due_time,
            start_time=creation_time,
            pay_type=order.pay_type,
            user_id=order.user_id,
            lock=Disk.Lock.FREE.value,
            deleted=False,
            server=None,
            mountpoint='',
            **kwargs
        )
        try:
            disk.save(force_insert=True)
        except Exception as e:
            try:
                if Disk.objects.filter(id=disk.id).exists():
                    disk.id = None  # 清除id，save时会更新id

                disk.save(force_insert=True)
            except Exception:
                message = f'向服务单元({service.id})请求创建云硬盘{out_disk.disk_id}成功，创建云硬盘记录元素据失败，{str(e)}。'
                params = inputs.DiskDeleteInput(disk_id=disk.instance_id, disk_name=disk.instance_name)
                try:
                    core_request.request_service(disk.service, method='disk_delete', params=params)
                except exceptions.APIException as exc:
                    message += f'尝试向服务单元请求删除云硬盘失败，{str(exc)}'
                else:
                    try:
                        QuotaAPI().disk_quota_release(service=service, disk_size=disk_size)
                    except exceptions.Error:
                        pass

                raise exceptions.NeetReleaseResource(message=message)

        return service, disk

    def deliver_renewal_disk(self, order: Order, resource: Resource):
        """
        云硬盘续费交付
        :return:
            server            # success

        :raises: Error
        """
        order, resource_list = self._pre_check_deliver(order=order, resource_ids=[resource.id])

        try:
            resource = resource_list[0]
            disk = self.renewal_disk_resource_for_order(order=order, resource=resource)
        except exceptions.Error as exc:
            try:
                OrderManager.set_order_resource_deliver_failed(
                    order=order, resource=resource, failed_msg='无法为订单完成云硬盘续费, ' + str(exc))
            except exceptions.Error:
                pass

            raise exc
        finally:
            self.clear_order_action(order=order)

        return disk

    def renewal_disk_resource_for_order(self, order: Order, resource: Resource):
        """
        为订单续费云硬盘资源

        :return:
            server

        :raises: Error
        """
        if order.resource_type != ResourceType.DISK.value:
            raise exceptions.Error(message=_('订单的资源类型不是云硬盘'))

        if isinstance(order.start_time, datetime) and isinstance(order.end_time, datetime):
            if order.start_time >= order.end_time:
                raise exceptions.Error(message=_('续费订单续费时长或时段无效。'))

        try:
            with transaction.atomic():
                disk = DiskManager.get_disk(disk_id=resource.instance_id, select_for_update=True)
                start_time, end_time = self.check_pre_renewal_disk_resource(
                    order=order, disk=disk
                )
                disk.expiration_time = end_time
                disk.save(update_fields=['expiration_time'])
                OrderManager.set_order_resource_deliver_ok(
                    order=order, resource=resource, start_time=start_time, due_time=end_time)
                return disk
        except Exception as e:
            raise exceptions.Error.from_error(e)

    @staticmethod
    def check_pre_renewal_disk_resource(order: Order, disk: Disk):
        """
        检查是否满足云硬盘续费的条件

        :return:
            start_time, end_time    # 此订单续费的起始和截止时间

        :raises: Error
        """
        if disk.pay_type != PayType.PREPAID.value:
            raise exceptions.Error(message=_('云硬盘不是包年包月预付费模式，无法完成续费。'))
        elif not isinstance(disk.expiration_time, datetime):
            raise exceptions.Error(message=_('云硬盘没有过期时间，无法完成续费。'))
        try:
            config = DiskConfig.from_dict(order.instance_config)
        except Exception as exc:
            raise exceptions.Error(message=_('续费订单中云硬盘配置信息有误。') + str(exc))

        if config.disk_size != disk.size:
            raise exceptions.Error(message=_('续费订单中云硬盘容量大小与云硬盘容量大小不一致。'))

        if order.period > 0 and (order.start_time is None and order.end_time is None):
            start_time = disk.expiration_time
            end_time = start_time + timedelta(days=PriceManager.period_month_days(order.period))
        elif order.period <= 0 and (
                isinstance(order.start_time, datetime) and isinstance(order.end_time, datetime)):
            if order.start_time != disk.expiration_time:
                delta_seconds = abs((order.start_time - disk.expiration_time).total_seconds())
                if delta_seconds > 60:
                    raise exceptions.Error(message=_('续费订单续费时长或时段与云硬盘过期时间有冲突。'))

            start_time = order.start_time
            end_time = order.end_time
        else:
            raise exceptions.Error(message=_('续费订单续费时长或时段无效。'))

        return start_time, end_time

    def deliver_modify_server_pay_type(self, order: Order, resource: Resource):
        """
        云服务器付费方式变更
        :return:
            server            # success

        :raises: Error
        """
        order, resource_list = self._pre_check_deliver(order=order, resource_ids=[resource.id])

        try:
            resource = resource_list[0]
            server = self.modify_server_pay_type_for_order(order=order, resource=resource)
        except exceptions.Error as exc:
            try:
                OrderManager.set_order_resource_deliver_failed(
                    order=order, resource=resource, failed_msg='无法为订单修改云服务器资源付费方式, ' + str(exc))
            except exceptions.Error:
                pass

            raise exc
        finally:
            self.clear_order_action(order=order)

        return server

    def modify_server_pay_type_for_order(self, order: Order, resource: Resource):
        """
        为订单修改云服务器付费方式

        :return:
            server

        :raises: Error
        """
        if order.resource_type != ResourceType.VM.value:
            raise exceptions.Error(message=_('订单的资源类型不是云服务器'))

        if order.order_type == Order.OrderType.POST2PRE.value:
            if not (order.period >= 1):
                raise exceptions.Error(message=_('订单续费时长无效。'))

        try:
            with transaction.atomic():
                server = ServerManager.get_server(server_id=resource.instance_id, select_for_update=True)
                self.pre_modify_server_pay_type_check(
                    order=order, server=server
                )
                now_t = timezone.now()
                if order.order_type == Order.OrderType.POST2PRE.value:
                    pay_type = PayType.PREPAID.value
                    start_time = now_t
                    end_time = start_time + timedelta(days=PriceManager.period_month_days(order.period))
                else:
                    raise exceptions.Error(message='订单类型无效，不是有效的付费方式变更订单')

                # 付费方式修改记录
                ServerArchive.init_archive_from_server(
                    server=server, archive_user=None, archive_type=ServerArchive.ArchiveType.POST2PRE.value,
                    archive_time=start_time, commit=True
                )

                server.pay_type = pay_type
                server.start_time = start_time
                server.expiration_time = end_time
                server.save(update_fields=['pay_type', 'start_time', 'expiration_time'])

                OrderManager.set_order_resource_deliver_ok(
                    order=order, resource=resource, start_time=start_time, due_time=end_time)
                return server
        except Exception as e:
            raise exceptions.Error.from_error(e)

    @staticmethod
    def pre_modify_server_pay_type_check(order: Order, server):
        """
        检查是否满足云主机付费方式修改的条件

        :return:
            start_time, end_time    # 此订单续费的起始和截止时间

        :raises: Error
        """
        try:
            config = ServerConfig.from_dict(order.instance_config)
        except Exception as exc:
            raise exceptions.Error(message=_('订单中云服务器配置信息有误。') + str(exc))

        if (config.vm_ram_gib != server.ram_gib) or (config.vm_cpu != server.vcpus):
            raise exceptions.Error(message=_('订单中云服务器配置信息与当前云服务器配置规格不一致。'))

        if order.order_type == Order.OrderType.POST2PRE.value:
            if server.pay_type != PayType.POSTPAID.value:
                raise exceptions.Error(message=_('云服务器不是按量付费模式，无法完成订单交付。'))
        else:
            raise exceptions.Error(message=_('不是付费方式修改类型的订单，无法完成订单交付。'))

    def deliver_modify_disk_pay_type(self, order: Order, resource: Resource):
        """
        云硬盘付费方式变更
        :return:
            disk            # success

        :raises: Error
        """
        order, resource_list = self._pre_check_deliver(order=order, resource_ids=[resource.id])

        try:
            resource = resource_list[0]
            disk = self.modify_disk_pay_type_for_order(order=order, resource=resource)
        except exceptions.Error as exc:
            try:
                OrderManager.set_order_resource_deliver_failed(
                    order=order, resource=resource, failed_msg='无法为订单修改云硬盘资源付费方式, ' + str(exc))
            except exceptions.Error:
                pass

            raise exc
        finally:
            self.clear_order_action(order=order)

        return disk

    def modify_disk_pay_type_for_order(self, order: Order, resource: Resource):
        """
        为订单修改云硬盘付费方式

        :return:
            server

        :raises: Error
        """
        if order.resource_type != ResourceType.DISK.value:
            raise exceptions.Error(message=_('订单的资源类型不是云硬盘'))

        if order.order_type == Order.OrderType.POST2PRE.value:
            if not (order.period >= 1):
                raise exceptions.Error(message=_('订单续费时长无效。'))

        try:
            with transaction.atomic():
                disk = DiskManager.get_disk(disk_id=resource.instance_id, select_for_update=True)
                self.pre_modify_disk_pay_type_check(
                    order=order, disk=disk
                )
                now_t = timezone.now()
                if order.order_type == Order.OrderType.POST2PRE.value:
                    pay_type = PayType.PREPAID.value
                    start_time = now_t
                    end_time = start_time + timedelta(days=PriceManager.period_month_days(order.period))
                else:
                    raise exceptions.Error(message='订单类型无效，不是有效的付费方式变更订单')

                # 付费方式修改记录
                DiskChangeLog.add_change_log_for_disk(
                    disk=disk, log_type=DiskChangeLog.LogType.POST2PRE.value,
                    change_time=start_time, change_user=order.username, save_db=True)

                disk.pay_type = pay_type
                disk.start_time = start_time
                disk.expiration_time = end_time
                disk.save(update_fields=['pay_type', 'start_time', 'expiration_time'])

                OrderManager.set_order_resource_deliver_ok(
                    order=order, resource=resource, start_time=start_time, due_time=end_time)
                return disk
        except Exception as e:
            raise exceptions.Error.from_error(e)

    @staticmethod
    def pre_modify_disk_pay_type_check(order: Order, disk):
        """
        检查是否满足云硬盘付费方式修改的条件

        :return:
            start_time, end_time    # 此订单续费的起始和截止时间

        :raises: Error
        """
        try:
            config = DiskConfig.from_dict(order.instance_config)
        except Exception as exc:
            raise exceptions.Error(message=_('订单中云硬盘配置信息有误。') + str(exc))

        if config.disk_size != disk.size:
            raise exceptions.Error(message=_('订单中云硬盘配置信息与当前云硬盘配置规格不一致。'))

        if order.order_type == Order.OrderType.POST2PRE.value:
            if disk.pay_type != PayType.POSTPAID.value:
                raise exceptions.Error(message=_('云硬盘不是按量付费模式，无法完成订单交付。'))
        else:
            raise exceptions.Error(message=_('不是付费方式修改类型的订单，无法完成订单交付。'))

    def deliver_new_sacn(self, order: Order) -> List[VtTask]:
        """
        raises: Error
        """
        try:
            with transaction.atomic():
                order = self._check_order_pre_deliver(order_id=order.id)
                resources = self._check_order_resources_pre_deliver(order_id=order.id)
                tasks = self._do_deliver_new_sacn(order=order, resources=resources)
                return tasks
        except Exception as exc:
            raise exceptions.Error.from_error(exc)

    @staticmethod
    def _do_deliver_new_sacn(order: Order, resources: List[Resource]):
        """
        需在一个事务中心执行
        """
        scan_config = ScanConfig.from_dict(order.instance_config)
        if len(resources) > 2:
            raise exceptions.ConflictError(message=_('订单资源记录数量大于订单订购任务数量'))
        elif len(resources) == 2:
            if not (scan_config.host_addr and scan_config.web_url):
                raise exceptions.ConflictError(message=_('订单资源记录数量为2，与订单订购任务数量不一致'))

            host_task = (resources[0], scan_config.host_addr)
            web_task = (resources[1], scan_config.web_url)
        else:
            res = resources[0]
            if scan_config.host_addr and scan_config.web_url:
                raise exceptions.ConflictError(message=_('订单资源记录数量为1，与订单订购任务数量不一致'))

            if scan_config.host_addr:
                host_task = (res, scan_config.host_addr)
                web_task = None
            else:
                host_task = None
                web_task = (res, scan_config.web_url)

        user_id = order.user_id
        task_name = scan_config.name
        task_remark = scan_config.remark

        # 创建任务
        tasks = []
        if web_task:
            res, target = web_task
            tasks.append(
                TaskManager.create_task(
                    user_id=user_id,
                    name=task_name,
                    type=VtTask.TaskType.WEB.value,
                    target=target,
                    remark=task_remark,
                    task_id=res.instance_id
                )
            )
            res.set_deliver_success()

        if host_task:
            res, target = host_task
            tasks.append(
                TaskManager.create_task(
                    user_id=user_id,
                    name=task_name,
                    type=VtTask.TaskType.HOST,
                    target=target,
                    remark=task_remark,
                    task_id=res.instance_id
                )
            )
            res.set_deliver_success()

        OrderManager.set_order_deliver_success(order=order, select_for_update=False)
        return tasks
