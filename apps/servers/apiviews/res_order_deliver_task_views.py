from decimal import Decimal
from datetime import timedelta

from django.utils.translation import gettext_lazy, gettext as _
from django.utils import timezone as dj_timezone
from django.conf import settings
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from core import errors as exceptions
from core import site_configs_manager
from core.taskqueue import submit_task
from utils.model import PayType, OwnerType
from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import NewPageNumberPagination100
from apps.servers.handlers.server_handler import ServerHandler
from apps.servers import serializers
from apps.servers.models import ResourceOrderDeliverTask
from apps.servers.managers import ServiceManager
from apps.app_order.models import Order, Resource
from apps.app_order.managers import OrderPaymentManager, OrderManager
from apps.app_order.deliver_resource import OrderResourceDeliverer
from apps.vo.managers import VoManager
from apps.users.managers import get_user_by_id
from apps.app_wallet.models import CashCoupon
from apps.app_wallet.managers import CashCouponManager


class ResTaskManager:
    @staticmethod
    def get_task(task_id, select_for_update: bool = False):
        qs = ResourceOrderDeliverTask.objects.filter(id=task_id)
        if select_for_update:
            qs = qs.select_for_update()

        return qs.first()

    @staticmethod
    def create_task(
            status: str, status_desc: str, progress: str, order: Order,
            submitter_id, submitter: str, service, task_desc: str,
            coupon: CashCoupon = None, creation_time = None, update_time = None
    ) -> ResourceOrderDeliverTask:
        if not creation_time:
            creation_time = dj_timezone.now()

        if not update_time:
            update_time = creation_time

        task = ResourceOrderDeliverTask(
            status=status, status_desc=status_desc, progress=progress,
            order=order, coupon=coupon,
            submitter_id=submitter_id, submitter=submitter,
            service=service, task_desc=task_desc,
            creation_time=creation_time, update_time=update_time
        )
        task.save(force_insert=True)
        return task

    def async_do_task_submit(self, res_task: ResourceOrderDeliverTask, auth_user):
        return submit_task(task=self.res_task_handler, kwargs={'task': res_task, 'auth_user': auth_user})

    def res_task_handler(self, task: ResourceOrderDeliverTask, auth_user):
        """
        异步任务处理入口
        """
        with transaction.atomic():
            task = self.get_task(task_id=task.id, select_for_update=True)
            if not task:
                raise exceptions.TargetNotExist(message=_('任务不存在'))

            self.check_pre_handle_task(task=task)
            order = OrderManager.get_order(order_id=task.order_id)
            task.set_status(
                status=ResourceOrderDeliverTask.Status.IN_PROGRESS.value,
                status_desc=_('正在处理任务'), update_time=dj_timezone.now()
            )

        try:
            self.handle_task(task=task, order=order, auth_user=auth_user)
        except Exception as e:
            task.set_status(
                status=ResourceOrderDeliverTask.Status.FAILED.value,
                status_desc=str(e), update_time=dj_timezone.now()
            )
            raise e

    def handle_task(self, task: ResourceOrderDeliverTask, order: Order, auth_user):
        """
        处理任务

        :raises: Error
        """
        if task.progress in [
            ResourceOrderDeliverTask.Progress.ORDERAED.value,
            ResourceOrderDeliverTask.Progress.COUPON.value
        ]:
            # 发券，支付
            try:
                self.create_coupon_and_pay_order(task=task, order=order, executor=auth_user.username)
            except Exception as e:
                raise e

        # 订单资源交付
        try:
            self.deliver_task_order(order=order)
        except Exception as e:
            raise e

        task.status = ResourceOrderDeliverTask.Status.COMPLETED.value
        task.status_desc = _('任务完成')
        task.update_time = dj_timezone.now()
        task.progress = ResourceOrderDeliverTask.Progress.DELIVERED.value
        task.save(update_fields=['status', 'task_desc', 'update_time', 'progress'])
        return task

    @staticmethod
    def deliver_task_order(order: Order):
        """
        交付任务的订单资源

        * 此函数定义是为了方便写测试用例，测试用例会替换此函数，以模拟订单资源成交付功
        :raises: Error
        """
        if order.trading_status not in [Order.TradingStatus.COMPLETED.value, Order.TradingStatus.CLOSED.value]:
            OrderResourceDeliverer().deliver_order(order=order)

    @staticmethod
    def create_coupon_for_order(order: Order, issuer: str) -> CashCoupon:
        """
        为订单发券
        """
        face_value = order.payable_amount
        if face_value <= Decimal('0'):
            raise exceptions.ConflictError(message=_('订单应付金额不大于0'))

        # 创建券
        user = get_user_by_id(order.user_id)
        if order.owner_type == OwnerType.USER.value:
            vo = None
        else:
            vo = VoManager.get_vo_by_id(order.vo_id)

        coupon = CashCouponManager().create_one_coupon_to_user_or_vo(
            user=user, vo=vo, app_service_id=order.app_service_id,
            face_value=face_value,
            effective_time=dj_timezone.now(),
            expiration_time=dj_timezone.now() + timedelta(days=30),
            issuer=issuer, remark='为指定订单发放的券',
            use_scope=CashCoupon.UseScope.ORDER.value, order_id=order.id
        )
        return coupon

    def create_coupon_and_pay_order(self, task: ResourceOrderDeliverTask, order: Order, executor: str):
        """
        发券并支付订单
        """
        if task.service_id != order.service_id:
            raise exceptions.ConflictError(message=_('任务关联的服务单元和任务订单的服务单元不一致'))

        with transaction.atomic():
            # 未发券，先发券
            if task.progress == ResourceOrderDeliverTask.Progress.ORDERAED.value:
                coupon = self.create_coupon_for_order(order=order, issuer=executor)
            elif task.progress == ResourceOrderDeliverTask.Progress.COUPON.value:
                # 已发券，使用券，否者发券
                if task.coupon:
                    coupon = task.coupon
                else:
                    coupon = self.create_coupon_for_order(order=order, issuer=executor)

            # 支付订单
            subject = order.build_subject()
            order = OrderPaymentManager().pay_order(
                order=order, app_id=site_configs_manager.get_pay_app_id(settings), subject=subject,
                executor=executor, remark=_('管理员任务，发券支付'),
                coupon_ids=[coupon.id], only_coupon=True,
                required_enough_balance=True
            )
            task.coupon = coupon
            task.progress = ResourceOrderDeliverTask.Progress.PAID.value
            task.update_time = dj_timezone.now()
            task.save(update_fields=['coupon', 'progress', 'update_time'])

        return task, order, coupon

    @staticmethod
    def check_pre_handle_task(task: ResourceOrderDeliverTask):
        """
        处理任务前检查
        """
        if task.status == ResourceOrderDeliverTask.Status.COMPLETED.value:
            raise exceptions.ConflictError(message=_('任务已完成'), code='ConflictStatus')
        elif task.status == ResourceOrderDeliverTask.Status.CANCELLED.value:
            raise exceptions.ConflictError(message=_('任务已作废'), code='ConflictStatus')
        elif task.status == ResourceOrderDeliverTask.Status.IN_PROGRESS.value:
            raise exceptions.ConflictError(message=_('任务正在处理中'), code='ConflictStatus')
        elif task.progress == ResourceOrderDeliverTask.Progress.DELIVERED.value:
            raise exceptions.ConflictError(message=_('任务资源已交付'), code='ConflictProgress')

    @staticmethod
    def filter_res_task_qs(queryset, status, search: str, service_ids: list = None):
        """
        :search: 任务描述
        :service_ids: None(不过滤)；空数组返回空，非空数组过滤
        """
        lookups = {}
        if status:
            lookups['status'] = status

        if search:
            lookups['task_desc__contains'] = search

        if lookups:
            queryset = queryset.filter(**lookups)

        if service_ids is not None:
            if service_ids:
                queryset = queryset.filter(service_id__in=service_ids)
            else:
                queryset = queryset.none()

        return queryset

    def get_perm_task_qs(self, auth_user, status, search: str, service_id: str):
        """
        用户用权限的任务
        """
        qs = ResourceOrderDeliverTask.objects.select_related('order', 'service')

        if service_id:
            if auth_user.is_federal_admin():
                pass
            elif not ServiceManager.has_perm(user_id=auth_user.id, service_id=service_id):
                raise exceptions.AccessDenied(message=_('没有指定服务单元的管理员权限'))

            service_ids = [service_id]
        else:
            if auth_user.is_federal_admin():
                service_ids = None  # 所有服务单元
            else:
                # 有权限的服务单元
                service_ids = ServiceManager.get_has_perm_service_ids(user_id=auth_user.id)
                service_ids = list(service_ids)

        qs = self.filter_res_task_qs(queryset=qs, status=status, search=search, service_ids=service_ids)
        return qs.order_by('-creation_time')


class ResOdDeliverTaskViewSet(CustomGenericViewSet):
    """
    虚拟服务器实例视图
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员提交云服务器订购任务，自动发放资源券，支付订单交付资源'),
        responses={
            202: '''    
                {
                    "task_id": "xxx",      # 任务id
                }
            '''
        }
    )
    @action(methods=['post'], detail=False, url_path='server/create', url_name='server-create')
    def create_server(self, request, *args, **kwargs):
        """
        管理员提交云服务器订购任务，自动发放资源券，支付订单交付资源

            * 服务单元管理员和联邦管理员可以帮用户提交资源创建任务
            * 可通过 number 指定订购资源数量，可选1-3，默认为1
            * 时长单位可选 天（day）、月（month），默认为月
            * 任务提交成功返回202, 任务在后台异步处理，任务记录会记录执行的结果和业务进度

            http Code 202 Ok:
                {
                    "task_id": "xxx"
                }

            Http Code 400, 409, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                BadRequest: 请求出现语法错误
                InvalidAzoneId: "azone_id"参数不能为空字符
                MissingPayType: 必须指定付费模式参数"pay_type"
                InvalidPayType: 付费模式参数"pay_type"值无效
                InvalidPeriod: 订购时长参数"period"值必须大于0 / 订购时长最长为5年
                MissingPeriod： 预付费模式时，必须指定订购时长
                InvalidFlavorId: 无效的配置规格flavor id
                InvalidVoId: vo不存在
                MissingServiceId：参数service_id不得为空
                InvalidServiceId：无效的服务id
                InvalidNetworkId: 指定网络不存在
                InvalidAzoneId: 指定的可用区azone_id不存在
                FlavorServiceMismatch: 配置规格和服务单元不匹配
                ArgumentConflict: 不能同时提交vo组和用户名
                MissingArgument: 以管理员身份请求时需要提交用户名或者vo组

                403:
                AccessDenied: 没有服务单元管理权限

                409:
                BalanceNotEnough: 余额不足
                QuotaShortage: 指定服务无法提供足够的资源

                500:
                InternalError: xxx
        """
        try:
            data = ServerHandler._server_create_validate_params(view=self, request=request, is_as_admin=True)
            task_desc = request.data.get('task_desc', '')
            pay_type = data['pay_type']
            if pay_type != PayType.PREPAID.value:
                raise exceptions.BadRequest(message=_('付费模式参数"pay_type"值无效'), code='InvalidPayType')

            pay_app_id = site_configs_manager.get_pay_app_id(settings, check_valid=True)
            auth_user = request.user
            od_desc = _('管理员（%(name)s）以管理员身份请求订购') % {'name': auth_user.username}
            service = data['service']

            with transaction.atomic():
                order, resource_list = ServerHandler().create_server_order(
                    data=data, auth_user=request.user, od_desc=od_desc)
                res_task = ResTaskManager.create_task(
                    status=ResourceOrderDeliverTask.Status.WAIT.value, status_desc='',
                    progress=ResourceOrderDeliverTask.Progress.ORDERAED.value, order=order,
                    coupon=None, submitter_id=auth_user.id, submitter=auth_user.username,
                    task_desc=task_desc, service=service
                )
        except exceptions.Error as exc:
            return self.exception_response(exc)

        # 发券、支付、资源交付 异步任务
        ResTaskManager().async_do_task_submit(res_task=res_task, auth_user=auth_user)

        return Response(data={'task_id': res_task.id}, status=202)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举管理员云服务器订购任务'),
        manual_parameters=[
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=f'{ResourceOrderDeliverTask.Status.choices}'
            ),
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('任务描述关键字查询')
            ),
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('服务单元筛选')
            ),
        ],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举管理员云服务器订购任务

            http code 200 Ok:
            {
                "count": 3,
                "page_num": 1,
                "page_size": 100,
                "results": [
                    {
                        "id": "u2crcvggpif6dyry4fwrznqog",
                        "status": "completed",
                        "status_desc": "",
                        "progress": "delivered",
                        "submitter_id": "u270orx13tm4ubmkhr70vtyt1",
                        "submitter": "user2",
                        "creation_time": "2024-12-23T06:48:54.066790Z",
                        "update_time": "2024-12-23T06:48:54.065855Z",
                        "task_desc": "test task3 desc",
                        "service": {
                            "id": "u2axgc6x4o6f5wo2kw8fp8c61",
                            "name": "test2",
                            "name_en": "test2_en"
                        },
                        "order": {          # maybe null
                            "id": "2024122306485405471025",
                            "resource_type": "vm",
                            "number": 1,
                            "order_type": "new",
                            "total_amount": "18771.84"
                        },
                        "coupon_id": "241223046803"     # maybe null
                    }
                ]
            }
            * status（任务状态）:
                wait: 待执行
                in-progress: 执行中
                failed: 失败
                completed: 完成
                cancelled: 作废

            * rogress(任务进度):
                ordered: 已订购        # 创建好订单
                coupon: 已发资源券
                paid: 已支付           # 订单已支付
                partdeliver: 部分交付   # 订购多个资源时，资源部分交付
                delivered: 已交付      # 订购资源交付完成
        """
        status = request.query_params.get('status', None)
        search = request.query_params.get('search', None)
        service_id = request.query_params.get('service_id', None)

        try:
            if status is not None and status not in ResourceOrderDeliverTask.Status.values:
                raise exceptions.InvalidArgument(message=_('指定的任务的状态无效'))

            qs = ResTaskManager().get_perm_task_qs(
                auth_user=request.user, status=status, search=search, service_id=service_id)
            objs = self.paginate_queryset(queryset=qs)
            slr = self.get_serializer(objs, many=True)
        except Exception as exc:
            return self.exception_response(exc)

        return self.get_paginated_response(data=slr.data)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员云服务器订购任务详情'),
        responses={
            200: ''' '''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        管理员云服务器订购任务详情

            http code 200 Ok:
            {
                "id": "7yh1hdjqojd8fs14od2siqwyq",
                "status": "completed",
                "status_desc": "",
                "progress": "delivered",
                "submitter_id": "7ye4fzoatsnyfqi4bzxmw8n35",
                "submitter": "user2",
                "creation_time": "2024-12-24T02:17:47.261191Z",
                "update_time": "2024-12-24T02:17:47.260453Z",
                "task_desc": "test task3 desc",
                "service": {
                    "id": "7yewsmder5ettnowipngvkkta",
                    "name": "test",
                    "name_en": "test_en"
                },
                "order": {
                    "id": "2024122402174725672027",
                    "order_type": "new",
                    "status": "unpaid",
                    "total_amount": "18771.84",
                    "pay_amount": "0.00",
                    "payable_amount": "12389.41",
                    "balance_amount": "0.00",
                    "coupon_amount": "0.00",
                    "service_id": "7yewsmder5ettnowipngvkkta",
                    "service_name": "test",
                    "resource_type": "vm",
                    "instance_config": {
                        "vm_cpu": 2,
                        "vm_ram": 2,
                        "vm_systemdisk_size": 100,
                        "vm_public_ip": true,
                        "vm_image_id": "image_id",
                        "vm_image_name": "",
                        "vm_network_id": "network_id",
                        "vm_network_name": "",
                        "vm_azone_id": "azone_id",
                        "vm_azone_name": "azone_name",
                        "vm_flavor_id": ""
                    },
                    "period": 2,
                    "period_unit": "month",
                    "start_time": null,
                    "end_time": null,
                    "payment_time": null,
                    "pay_type": "prepaid",
                    "creation_time": "2024-12-24T02:17:47.257327Z",
                    "user_id": "7ydwpfxk669tggu1dscxues30",
                    "username": "test",
                    "vo_id": "7yf5jnr4ndyk5fdvb6g44n1qv",
                    "vo_name": "test vo",
                    "owner_type": "vo",
                    "cancelled_time": null,
                    "app_service_id": "123",
                    "trading_status": "opening",
                    "number": 1,
                    "resources": [
                    {
                      "id": "81d9aad0-a03b-11ec-ba16-c8009fe2eb10",
                      "order_id": "2022031006103240183511",
                      "resource_type": "vm",
                      "instance_id": "test",
                      "instance_status": "wait",
                      "desc": "xxx",    # 资源交付结果描述
                      "delivered_time": "2022-03-10T06:10:32.478101Z",
                      "instance_delete_time": "2022-03-10T06:10:32.478101Z"     # 不为null时，表示对应资源实例删除时间
                    }
                  ]
                },
                "coupon_id": "241224000001",
                "coupon": {
                    "id": "241224000001",
                    "face_value": "12389.41",
                    "creation_time": "2024-12-24T02:17:47.380474Z",
                    "effective_time": "2024-12-24T02:17:47.378205Z",
                    "expiration_time": "2025-01-23T02:17:47.378209Z",
                    "balance": "12389.41",
                    "status": "available",
                    "granted_time": "2024-12-24T02:17:47.383615Z",
                    "owner_type": "vo",
                    "app_service": {
                        "id": "123",
                        "name": "service1",
                        "name_en": "",
                        "category": "vms-server",
                        "service_id": ""
                    },
                    "user": {
                        "id": "7ydwpfxk669tggu1dscxues30",
                        "username": "test"
                    },
                    "vo": {
                        "id": "7yf5jnr4ndyk5fdvb6g44n1qv",
                        "name": "test vo"
                    },
                    "activity": null,
                    "issuer": "test",
                    "remark": "为指定订单发放的券",
                    "use_scope": "order",
                    "order_id": "2024122402174725672027"
                }
            }
        """
        try:
            task_id = kwargs[self.lookup_field]
            task = ResourceOrderDeliverTask.objects.select_related(
                'order', 'service', 'coupon__user', 'coupon__vo', 'coupon__app_service'
            ).filter(id=task_id).first()
            if task is None:
                raise exceptions.TargetNotExist(message=_('任务不存在'))

            if not self.has_perm_of_task(auth_user=request.user, task=task):
                raise exceptions.AccessDenied(message=_('没有任务的管理权限'))

            if task.order:
                resources = Resource.objects.filter(order_id=task.order.id).all()
                task.order.resources = list(resources)

            return Response(data=self.get_serializer(task).data)
        except Exception as exc:
            return self.exception_response(exc)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('进度未完成任务重试'),
        request_body=no_body,
        responses={
            202: ''''''
        }
    )
    @action(methods=['post'], detail=True, url_path='retry', url_name='retry')
    def retry_task(self, request, *args, **kwargs):
        """
        进度未完成任务重试

            http code 202:
            {
                "task_id": "xxx"
            }
        """
        try:
            task_id = kwargs[self.lookup_field]
            task = ResourceOrderDeliverTask.objects.filter(id=task_id).first()
            if task is None:
                raise exceptions.TargetNotExist(message=_('任务不存在'))

            if not self.has_perm_of_task(auth_user=request.user, task=task):
                raise exceptions.AccessDenied(message=_('没有任务的管理权限'))

            ResTaskManager.check_pre_handle_task(task=task)
        except Exception as exc:
            return self.exception_response(exc)

        # 提交异步任务
        ResTaskManager().async_do_task_submit(res_task=task, auth_user=request.user)

        return Response(data={'task_id': task.id}, status=202)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('作废任务'),
        request_body=no_body,
        responses={
            202: ''''''
        }
    )
    @action(methods=['post'], detail=True, url_path='cancel', url_name='cancel')
    def cancel_task(self, request, *args, **kwargs):
        """
        作废未完成的任务，任务进度不回滚

            * 已发的资源券和关联的订单 会被删除（软删除，用户不可见），即未使用的券不再可使用，未交付的资源不再交付；
              已支付的订单不会退款，已交付的资源不会删除

            http code 200:
            {
                "task_id": "xxx"
            }
        """
        try:
            with transaction.atomic():
                task_id = kwargs[self.lookup_field]
                task = ResourceOrderDeliverTask.objects.select_related('order', 'coupon').filter(id=task_id).first()
                if task is None:
                    raise exceptions.TargetNotExist(message=_('任务不存在'))

                if not self.has_perm_of_task(auth_user=request.user, task=task):
                    raise exceptions.AccessDenied(message=_('没有任务的管理权限'))

                if task.status == ResourceOrderDeliverTask.Status.COMPLETED.value:
                    raise exceptions.ConflictError(message=_('任务已完成'), code='ConflictStatus')
                elif task.status == ResourceOrderDeliverTask.Status.IN_PROGRESS.value:
                    # 更新时间距现在时间超过几分钟，判定任务“处理中”的状态大概率无效，允许作废
                    if not task.update_time or (dj_timezone.now() - task.update_time) < timedelta(minutes=2):
                        raise exceptions.ConflictError(message=_('任务正在处理中'), code='ConflictStatus')

                order = task.order
                coupon = task.coupon
                if order:
                    order.deleted = True
                    order.save(update_fields=['deleted'])

                if coupon:
                    coupon.status = CashCoupon.Status.DELETED.value
                    coupon.save(update_fields=['status'])

                task.set_status(
                    status=ResourceOrderDeliverTask.Status.CANCELLED.value,
                    status_desc=_('管理员 %(value)s 作废任务') % {'value': request.user.username},
                    update_time=dj_timezone.now()
                )
        except Exception as exc:
            return self.exception_response(exc)

        return Response(data={'task_id': task.id}, status=200)

    @staticmethod
    def has_perm_of_task(auth_user, task):
        if auth_user.is_federal_admin():
            return True
        elif ServiceManager.has_perm(user_id=auth_user.id, service_id=task.service_id):
            return True

        return False

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.AdminResTaskSerializer
        elif self.action == 'create_server':
            return serializers.ServerCreateTaskSerializer
        elif self.action == 'retrieve':
            return serializers.AdminResTaskDetailSerializer

        return Serializer
