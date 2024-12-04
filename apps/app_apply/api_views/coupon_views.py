from datetime import datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.utils import timezone as dj_timezone
from django.utils.translation import gettext_lazy, gettext as _
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from core import errors, site_configs_manager
from utils.time import iso_to_datetime
from utils.model import OwnerType, ResourceType, PayType
from apps.api.viewsets import NormalGenericViewSet, serializer_error_msg
from apps.api.paginations import NewPageNumberPagination100
from apps.vo.managers import VoManager
from apps.servers.managers import ServiceManager as ServerServiceManager
from apps.storage.managers import ObjectsServiceManager
from apps.monitor.models import MonitorWebsiteVersion
from apps.monitor.models import ErrorLog
from apps.order.models import Order
from apps.order.managers import OrderManager, OrderPaymentManager
from apps.order.deliver_resource import OrderResourceDeliverer
from apps.app_scan.models import VtScanService
from apps.app_apply import serializers
from apps.app_apply.models import CouponApply
from apps.app_apply.managers.coupon import CouponApplyManager
from apps.app_apply.notifiers import CouponApplyEmailNotifier


class CouponApplyViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举资源券申请记录'),
        manual_parameters=NormalGenericViewSet.PARAMETERS_AS_ADMIN + [
            openapi.Parameter(
                name='service_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('服务类型') + f'{CouponApply.ServiceType.choices}'
            ),
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('申请状态') + f'{CouponApply.Status.choices}'
            ),
            openapi.Parameter(
                name='time_start',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('起始时间，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ')
            ),
            openapi.Parameter(
                name='time_end',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('截止时间，ISO8601格式：YYYY-MM-ddTHH:mm:ssZ')
            ),
            openapi.Parameter(
                name='vo_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('查询vo组的申请')
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举资源券申请记录

            Http Code: 状态码200，返回数据：
            {
                "count": 1,
                "page_num": 1,
                "page_size": 100,
                "results": [
                    {
                        "id": "o783c5q0y0ttbmwmwkq0d2vgi",
                        "service_type": "server",   # server:云主机; storage：对象存储; monitor-site：站点监控; scan：安全扫描
                        "odc": {                    # 数据中心, maybe null
                            "id": "o77ab69z9tsj824todcp9pwji",
                            "name": "odc2",
                            "name_en": "test_en"
                        },
                        "service_id": "service_id2",
                        "service_name": "service_name2",
                        "service_name_en": "service_name_en2",
                        "face_value": "6000.12",                    # 申请券金额
                        "expiration_time": "2023-12-15T00:00:00Z",  # 申请券到期时间
                        "apply_desc": "申请原因说明",
                        "contact_info": "122xx",                    # 联系方式
                        "creation_time": "2023-10-09T00:00:00Z",
                        "update_time": "2023-10-09T00:00:00Z",
                        "user_id": "o76e976pt9w6xbgya4c5acc1o",
                        "username": "tom@cnic.cn",
                        "vo_id": "o76gz1xw3tv2hky5nedw35bwy",
                        "vo_name": "test vo",
                        "owner_type": "vo",     # user, vo
                        "status": "pending",
                        "approver": "",         # 审批人
                        "reject_reason": "",    # 审批拒绝时，拒绝原因
                        "approved_amount": "0.00",  # 审批通过的实际资源券金额
                        "coupon_id": "",
                        "order_id": "xxx",       # 申请关联的订单id，为此订单申请资源券，可能null
                        "deleted": false,
                        "delete_user": "xx"
                    }
                ]
            }
            * status:
                wait: 待审批
                cancel: 取消
                pending: 审批中    # 防止审批的同时申请人进行修改
                reject: 拒绝      # 拒绝后用户可以修改重新提交
                pass: 通过
        """
        try:
            data = self._list_validate_params(request)
        except errors.Error as exc:
            return self.exception_response(exc)

        user = request.user
        vo_id = data['vo_id']
        try:
            if self.is_as_admin_request(request):
                queryset = CouponApplyManager().admin_filter_apply_qs(
                    service_type=data['service_type'], status=data['status'],
                    start_time=data['time_start'], end_time=data['time_end'],
                    admin_user=user, vo_id=vo_id
                )
            elif vo_id:
                queryset = CouponApplyManager().filter_vo_apply_qs(
                    service_type=data['service_type'], status=data['status'],
                    start_time=data['time_start'], end_time=data['time_end'],
                    user=user, vo_id=vo_id
                )
            else:
                queryset = CouponApplyManager().filter_user_apply_qs(
                    service_type=data['service_type'], status=data['status'],
                    start_time=data['time_start'], end_time=data['time_end'], user_id=user.id
                )

            objs = self.paginate_queryset(queryset)
            serializer = self.get_serializer(instance=objs, many=True)
            return self.get_paginated_response(serializer.data)
        except errors.Error as exc:
            return self.exception_response(exc)

    @staticmethod
    def _list_validate_params(request) -> dict:
        service_type = request.query_params.get('service_type', None)
        status = request.query_params.get('status', None)
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)
        vo_id = request.query_params.get('vo_id', None)

        if service_type is not None and service_type not in CouponApply.ServiceType.values:
            raise errors.InvalidArgument(message=_('无效的服务类型'))

        if status is not None and status not in CouponApply.Status.values:
            raise errors.InvalidArgument(message=_('无效的申请状态'))

        if time_start is not None:
            time_start = iso_to_datetime(time_start)
            if not isinstance(time_start, datetime):
                raise errors.InvalidArgument(message=_('起始时间格式有误'))

        if time_end is not None:
            time_end = iso_to_datetime(time_end)
            if not isinstance(time_end, datetime):
                raise errors.InvalidArgument(message=_('截止时间格式有误'))

        if time_start and time_end:
            if time_start >= time_end:
                raise errors.InvalidArgument(message=_('起始时间必须小于截止时间'))

        if vo_id is not None and not vo_id:
            raise errors.InvalidArgument(message=_('无效的vo id'))

        return {
            'service_type': service_type,
            'status': status,
            'time_start': time_start,
            'time_end': time_end,
            'vo_id': vo_id
        }

    @swagger_auto_schema(
        operation_summary=gettext_lazy('提交资源券申请'),
        responses={
            201: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        提交资源券申请

            * 只有云主机服务可以为vo组申请资源券
            * 服务类型为云主机和对象存储时，需要指定服务单元id

            http code 201:
            {
                "id": "oft85v49io35e3kmsf2wd1yev",
                "service_type": "server",
                "odc": {                            # 数据中心，站点监控和安全扫描服务时 为 null
                    "id": "of5z7h3pnagywp3f1g05fpx95",
                    "name": "odc1",
                    "name_en": "test_en"
                },
                "service_id": "ofma1ygtqkwpe9vjh43gr769v",  # 对应各服务类型的服务单元id
                "service_name": "server1",
                "service_name_en": "server1 en",
                "face_value": "2000.12",
                "expiration_time": "2024-03-18T06:44:32Z",
                "apply_desc": "申请说明",
                "contact_info": "122xx",                    # 联系方式
                "creation_time": "2024-03-14T02:44:32.576110Z",
                "update_time": "2024-03-14T02:44:32.576110Z",
                "user_id": "of4wiym05t41g7zyov60ifofv",
                "username": "test",
                "vo_id": "",
                "vo_name": "",
                "owner_type": "user",
                "status": "wait",
                "approver": "",
                "reject_reason": "",
                "approved_amount": "0.00",
                "coupon_id": "",
                "order_id": "null"
            }

            http code 400, 401, 403, 404, 409:
            {
                "code": "BadRequest",
                "message": "xxx"
            }
            * code
            400：BadRequest、InvalidArgument: 请求有误、参数无效
            403：AccessDenied: 你不是组管理员，没有组管理权限
            404：
                VoNotExist：项目组不存在
                TargetNotExist：云主机、对象存储服务单元不存在
            409：Conflict：服务单元停止服务中 / 指定服务可能未注册钱包结算单元
                TooManyApply: 已有多个申请待审批，暂不能提交更多的申请
        """
        try:
            slizer = self.get_serializer(data=request.data)
            data = self._create_validate_params(request=request, serializer=slizer)
        except errors.Error as exc:
            return self.exception_response(exc)

        face_value = data['face_value']
        expiration_time = data['expiration_time']
        apply_desc = data['apply_desc']
        service_type = data['service_type']
        service_id = data['service_id']
        vo = data['vo']
        contact_info = data['contact_info']

        user = request.user
        user_id = user.id
        username = user.username
        if vo:
            vo_id = vo.id
            vo_name = vo.name
            owner_type = OwnerType.VO.value
        else:
            vo_id = ''
            vo_name = ''
            owner_type = OwnerType.USER.value

        try:
            CouponApplyManager.check_apply_limit(owner_type=owner_type, user_id=user_id, vo_id=vo_id)
            odc, service_id, service_name, service_name_en, pay_service_id = self._get_service_info(
                service_type=service_type, service_id=service_id
            )
            apply = CouponApplyManager.create_apply(
                service_type=service_type, odc=odc, service_id=service_id, service_name=service_name,
                service_name_en=service_name_en, pay_service_id=pay_service_id,
                face_value=face_value, expiration_time=expiration_time, apply_desc=apply_desc,
                contact_info=contact_info,
                user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type
            )
        except errors.Error as exc:
            return self.exception_response(exc)

        try:
            self.email_notify_admin_new_apply(new_apply=apply)
        except Exception as exc:
            pass

        return Response(data=serializers.CouponApplySerializer(apply).data, status=201)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('为订单提交资源券申请'),
        responses={
            201: ''
        }
    )
    @action(methods=['post'], detail=False, url_path='order', url_name='order')
    def for_order_apply(self, request, *args, **kwargs):
        """
        为订单提交资源券申请

            * 需要是待支付状态的预付费订单

            http code 201:
            {
                "id": "oft85v49io35e3kmsf2wd1yev",
                "service_type": "server",
                "odc": {                            # 数据中心，站点监控和安全扫描服务时 为 null
                    "id": "of5z7h3pnagywp3f1g05fpx95",
                    "name": "odc1",
                    "name_en": "test_en"
                },
                "service_id": "ofma1ygtqkwpe9vjh43gr769v",  # 对应各服务类型的服务单元id
                "service_name": "server1",
                "service_name_en": "server1 en",
                "face_value": "2000.12",
                "expiration_time": "2024-03-18T06:44:32Z",
                "apply_desc": "申请说明",
                "contact_info": "122xx",                    # 联系方式
                "creation_time": "2024-03-14T02:44:32.576110Z",
                "update_time": "2024-03-14T02:44:32.576110Z",
                "user_id": "of4wiym05t41g7zyov60ifofv",
                "username": "test",
                "vo_id": "",
                "vo_name": "",
                "owner_type": "user",
                "status": "wait",
                "approver": "",
                "reject_reason": "",
                "approved_amount": "0.00",
                "coupon_id": "",
                "order_id": "xxx"       # 申请关联的订单id，为此订单申请资源券
            }

            http code 400, 401, 403, 404, 409:
            {
                "code": "BadRequest",
                "message": "xxx"
            }
            * code
            400：BadRequest: 请求有误、参数无效
            403：AccessDenied: 你没有订单管理权限
            404：
                VoNotExist：项目组不存在
                TargetNotExist：云主机、对象存储服务单元不存在
            409：Conflict：
                    服务单元停止服务中 / 指定服务可能未注册钱包结算单元 / 订单不是未支付状态 / 订单不在交易中，订单交易可能已完成或关闭
                    不是预付费订单 / 订单应付金额不大于0
                TooManyApply: 已有多个申请待审批，暂不能提交更多的申请
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            exc = errors.BadRequest(message=msg)
            return self.exception_response(exc)

        data = serializer.validated_data
        apply_desc = data['apply_desc']
        order_id = data['order_id']
        contact_info = data['contact_info']
        try:
            order = OrderManager().get_permission_order(
                order_id=order_id, user=request.user, check_permission=True, read_only=False)
            if order.status != Order.Status.UNPAID.value:
                raise errors.ConflictError(message=_('订单不是未支付状态'))
            if order.trading_status != Order.TradingStatus.OPENING.value:
                raise errors.ConflictError(message=_('订单不在交易中，订单交易可能已完成或关闭'))
            if order.pay_type != PayType.PREPAID.value:
                raise errors.ConflictError(message=_('不是预付费订单'))

            face_value = order.payable_amount
            if face_value <= Decimal('0'):
                raise errors.ConflictError(message=_('订单应付金额不大于0'))

            service_type_map = {
                ResourceType.VM.value: CouponApply.ServiceType.SERVER.value,
                ResourceType.DISK.value: CouponApply.ServiceType.SERVER.value,
                ResourceType.SCAN.value: CouponApply.ServiceType.SCAN.value
            }
            if order.resource_type not in service_type_map:
                raise errors.ConflictError(message=_('订单订购资源类型不支持资源券申请'))

            service_type = service_type_map[order.resource_type]
            service_id = order.service_id
        except errors.Error as exc:
            return self.exception_response(exc)

        if order.owner_type == OwnerType.VO.value:
            user = request.user
            user_id = user.id
            username = user.username
            vo_id = order.vo_id
            vo_name = order.vo_name
            owner_type = OwnerType.VO.value
        else:
            vo_id = ''
            vo_name = ''
            user_id = order.user_id
            username = order.username
            owner_type = OwnerType.USER.value

        try:
            CouponApplyManager.check_apply_limit(owner_type=owner_type, user_id=user_id, vo_id=vo_id)
            odc, service_id, service_name, service_name_en, pay_service_id = self._get_service_info(
                service_type=service_type, service_id=service_id
            )
            apply = CouponApplyManager.create_apply(
                service_type=service_type, odc=odc, service_id=service_id, service_name=service_name,
                service_name_en=service_name_en, pay_service_id=pay_service_id,
                face_value=face_value, expiration_time=dj_timezone.now() + timedelta(days=30), apply_desc=apply_desc,
                user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type,
                order_id=order_id, contact_info=contact_info
            )
        except errors.Error as exc:
            return self.exception_response(exc)

        try:
            self.email_notify_admin_new_apply(new_apply=apply)
        except Exception as exc:
            pass

        return Response(data=serializers.CouponApplySerializer(apply).data, status=201)

    @staticmethod
    def _get_service_info(service_type: str, service_id: str):
        if service_type == CouponApply.ServiceType.SERVER.value:
            try:
                unit = ServerServiceManager.get_service(service_id=service_id)
            except errors.NotFound:
                raise errors.TargetNotExist(message=_('云主机服务单元不存在'))
            except errors.ServiceStopped:
                raise errors.ConflictError(message=_('云主机服务单元停止服务中'))

            service_name = unit.name
            service_name_en = unit.name_en
            odc = unit.org_data_center
            pay_app_service_id = unit.pay_app_service_id
        elif service_type == CouponApply.ServiceType.STORAGE.value:
            try:
                unit = ObjectsServiceManager.get_service(service_id=service_id)
            except errors.NotFound:
                raise errors.TargetNotExist(message=_('对象存储服务单元不存在'))
            except errors.ServiceStopped:
                raise errors.ConflictError(message=_('对象存储服务单元停止服务中'))

            service_name = unit.name
            service_name_en = unit.name_en
            odc = unit.org_data_center
            pay_app_service_id = unit.pay_app_service_id
        elif service_type == CouponApply.ServiceType.MONITOR_SITE.value:
            ins = MonitorWebsiteVersion.get_instance()
            service_id = str(ins.id)
            service_name = '站点监控服务'
            service_name_en = 'Site Monitoring Service'
            odc = None
            pay_app_service_id = ins.pay_app_service_id
        elif service_type == CouponApply.ServiceType.SCAN.value:
            ins = VtScanService.objects.order_by('-add_time').first()
            if ins is None:
                raise errors.TargetNotExist(message=_('暂未提供安全漏洞扫描服务'))

            if ins.status != VtScanService.Status.ENABLE.value:
                raise errors.ConflictError(message=_('安全漏洞扫描服务停止服务中'))

            service_id = ins.id
            service_name = ins.name
            service_name_en = ins.name_en
            odc = None
            pay_app_service_id = ins.pay_app_service_id
        else:
            raise errors.Error(message=_('无效的服务类型'))

        if not pay_app_service_id or len(pay_app_service_id) < 6:
            raise errors.ConflictError(message=_('指定服务可能未注册钱包结算单元'))

        return odc, service_id, service_name, service_name_en, pay_app_service_id

    @staticmethod
    def email_notify_admin_new_apply(new_apply: CouponApply):
        """
        提交新的券申请，向服务单元管理员发送通知
        """
        CouponApplyEmailNotifier.new_apply_notice(apply=new_apply)

    @staticmethod
    def email_notify_user_apply_status(new_apply: CouponApply):
        """
        券申请审批状态通过或拒绝，向申请者发送通知
        """
        CouponApplyEmailNotifier.new_status_notice(apply=new_apply)

    def _create_validate_params(self, request, serializer):
        data = self._update_validate_params(serializer=serializer)
        vo_id = serializer.validated_data.get('vo_id', None)
        if vo_id:
            if data['service_type'] != CouponApply.ServiceType.SERVER.value:
                raise errors.InvalidArgument(message=_('指定的服务类型，不允许为vo组申请资源券'))

            vo, member = VoManager().get_has_manager_perm_vo(vo_id=vo_id, user=request.user)
        else:
            vo = None

        data['vo'] = vo
        return data

    @staticmethod
    def _update_validate_params(serializer):
        """
        :raises: Error
        """
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            exc = errors.BadRequest(message=msg)
            raise exc

        data = serializer.validated_data
        face_value = data['face_value']
        expiration_time = data['expiration_time']
        apply_desc = data['apply_desc']
        service_type = data['service_type']
        service_id = data.get('service_id', None)
        contact_info = data.get('contact_info', '')

        if face_value < Decimal('0'):
            raise errors.InvalidArgument(message=_('申请金额必须大于0.00'))

        if expiration_time < dj_timezone.now() + timedelta(hours=1):
            raise errors.InvalidArgument(message=_('过期时间距当前时间不足一个小时'))

        if service_type not in CouponApply.ServiceType.values:
            raise errors.InvalidArgument(message=_('申请服务类型无效'))

        if service_type in [CouponApply.ServiceType.SERVER.value, CouponApply.ServiceType.STORAGE.value]:
            if not service_id:
                raise errors.InvalidArgument(message=_('申请服务类型为云主机和对象存储服务时，必须指定申请的服务单元'))

        return {
            'face_value': face_value,
            'expiration_time': expiration_time,
            'apply_desc': apply_desc,
            'service_type': service_type,
            'service_id': service_id if service_id else '',
            'contact_info': contact_info if contact_info else ''
        }

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改资源券申请'),
        responses={
            200: ''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        修改资源券申请

            * 只有云主机服务可以为vo组申请资源券
            * 服务类型为云主机和对象存储时，需要指定服务单元id
            * 为订单提交的申请不允许修改

            http code 201:
            {
                "id": "oft85v49io35e3kmsf2wd1yev",
                "service_type": "server",
                "odc": {                            # 数据中心，站点监控和安全扫描服务时 为 null
                    "id": "of5z7h3pnagywp3f1g05fpx95",
                    "name": "odc1",
                    "name_en": "test_en"
                },
                "service_id": "ofma1ygtqkwpe9vjh43gr769v",  # 对应各服务类型的服务单元id
                "service_name": "server1",
                "service_name_en": "server1 en",
                "face_value": "2000.12",
                "expiration_time": "2024-03-18T06:44:32Z",
                "apply_desc": "申请说明",
                "creation_time": "2024-03-14T02:44:32.576110Z",
                "update_time": "2024-03-14T02:44:32.576110Z",
                "user_id": "of4wiym05t41g7zyov60ifofv",
                "username": "test",
                "vo_id": "",
                "vo_name": "",
                "owner_type": "user",
                "status": "wait",
                "approver": "",
                "reject_reason": "",
                "approved_amount": "0.00",
                "coupon_id": ""
            }

            http code 400, 401, 403, 404, 409:
            {
                "code": "BadRequest",
                "message": "xxx"
            }
            * code
            400：BadRequest、InvalidArgument: 请求有误、参数无效
            403：AccessDenied: 你没有访问权限
            404：TargetNotExist：云主机、对象存储服务单元不存在
            409：Conflict：服务单元停止服务中 / 指定服务可能未注册钱包结算单元
                TooManyApply: 已有多个申请待审批，暂不能提交更多的申请
        """
        try:
            slizer = self.get_serializer(data=request.data)
            data = self._update_validate_params(serializer=slizer)
        except errors.Error as exc:
            return self.exception_response(exc)

        face_value = data['face_value']
        expiration_time = data['expiration_time']
        apply_desc = data['apply_desc']
        service_type = data['service_type']
        service_id = data['service_id']
        contact_info = data['contact_info']

        user = request.user

        try:
            odc, service_id, service_name, service_name_en, pay_service_id = self._get_service_info(
                service_type=service_type, service_id=service_id
            )
            with transaction.atomic():
                apply = CouponApplyManager.get_perm_apply(
                    _id=kwargs[self.lookup_field], user=user, select_for_update=True)
                if apply.status not in [CouponApply.Status.WAIT.value, CouponApply.Status.REJECT.value]:
                    raise errors.ConflictError(message=_('只允许修改“待审批”和“拒绝”状态的申请记录'))

                if apply.order_id:
                    raise errors.ConflictError(message=_('指定订单的申请记录不允许修改'))

                if apply.status == CouponApply.Status.REJECT.value:
                    CouponApplyManager.check_apply_limit(
                        owner_type=apply.owner_type, user_id=apply.user_id, vo_id=apply.vo_id)

                if apply.owner_type == OwnerType.VO.value and service_type != CouponApply.ServiceType.SERVER.value:
                    raise errors.ConflictError(message=_('指定的服务类型，不允许为vo组申请资源券'))

                apply = CouponApplyManager.update_apply(
                    apply=apply, service_type=service_type, odc=odc, service_id=service_id, service_name=service_name,
                    service_name_en=service_name_en, pay_service_id=pay_service_id,
                    face_value=face_value, expiration_time=expiration_time, apply_desc=apply_desc,
                    user_id=user.id, username=user.username, contact_info=contact_info
                )
        except errors.Error as exc:
            return self.exception_response(exc)

        return Response(data=serializers.CouponApplySerializer(apply).data, status=200)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除资源券申请记录'),
        responses={
            204: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        删除资源券申请记录

            http code 204: ok
        """
        try:
            CouponApplyManager.delete_apply(apply_id=kwargs[self.lookup_field], user=request.user)
        except errors.Error as exc:
            return self.exception_response(exc)

        return Response(data=None, status=204)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('取消资源券申请'),
        request_body=no_body,
        responses={
            204: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='cancel', url_name='cancel')
    def cancel_apply(self, request, *args, **kwargs):
        """
        取消资源券申请

            * 已通过状态申请无法取消
            http code 200: ok
        """
        try:
            CouponApplyManager.cancel_apply(apply_id=kwargs[self.lookup_field], user=request.user)
        except errors.Error as exc:
            return self.exception_response(exc)

        return Response(data=None, status=200)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('审批挂起资源券申请'),
        request_body=no_body,
        responses={
            204: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='pending', url_name='pending')
    def pending_apply(self, request, *args, **kwargs):
        """
        审批挂起资源券申请，需要数据中心管理员和联邦管理员权限

            * 只能挂起外审批状态申请
            http code 200: ok
        """
        try:
            CouponApplyManager.pending_apply(apply_id=kwargs[self.lookup_field], admin_user=request.user)
        except errors.Error as exc:
            return self.exception_response(exc)

        return Response(data=None, status=200)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('审批拒绝资源券申请'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='reason',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=gettext_lazy('拒绝原因')
            )
        ],
        responses={
            204: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='reject', url_name='reject')
    def reject_apply(self, request, *args, **kwargs):
        """
        审批拒绝资源券申请，需要数据中心管理员和联邦管理员权限

            * 只能审批挂起状态的申请
            http code 200: ok
        """
        reason = request.query_params.get('reason', '')
        if not reason:
            return self.exception_response(
                errors.InvalidArgument(message=_('请提交拒绝的原因')))

        try:
            apply = CouponApplyManager.reject_apply(
                apply_id=kwargs[self.lookup_field], admin_user=request.user, reject_reason=reason)
        except errors.Error as exc:
            return self.exception_response(exc)

        try:
            self.email_notify_user_apply_status(new_apply=apply)
        except Exception as exc:
            pass

        return Response(data=None, status=200)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('审批通过资源券申请'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='approved_amount',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=gettext_lazy('如果用户申请金额太大，通过此参数指定审批通过的金额，不能大于用户申请金额，格式为1.23')
            )
        ],
        responses={
            204: ''
        }
    )
    @action(methods=['post'], detail=True, url_path='pass', url_name='pass')
    def pass_apply(self, request, *args, **kwargs):
        """
        审批通过资源券申请，需要数据中心管理员和联邦管理员权限

            * 只能审批挂起状态的申请，通过
            * 为订单提交的资源券申请不能审批通过部分金额
            http code 200: ok
        """
        approved_amount = request.query_params.get('approved_amount', None)
        if approved_amount is not None:
            try:
                approved_amount = Decimal(approved_amount)
            except Exception as exc:
                return self.exception_response(errors.InvalidArgument(message=_('金额格式无效')))

            if approved_amount <= Decimal('0'):
                return self.exception_response(errors.InvalidArgument(message=_('金额不能小于0')))

        try:
            apply = CouponApplyManager.pass_apply(
                apply_id=kwargs[self.lookup_field], admin_user=request.user, approved_amount=approved_amount)
        except errors.Error as exc:
            return self.exception_response(exc)

        try:
            self.email_notify_user_apply_status(new_apply=apply)
        except Exception as exc:
            pass

        if not apply.order:
            return Response(data=None, status=200)

        # 申请关联订单，自动支付，交付资源
        try:
            order = apply.order
            subject = order.build_subject()
            order = OrderPaymentManager().pay_order(
                order=order, app_id=site_configs_manager.get_pay_app_id(settings), subject=subject,
                executor=apply.username, remark='',
                coupon_ids=[apply.coupon_id], only_coupon=True,
                required_enough_balance=True
            )
            OrderResourceDeliverer().deliver_order(order=order)
        except Exception as exc:
            try:
                err_msg = f'自动支付订单，交付资源，[{type(exc)}] {str(exc)}'
                method = request.method
                full_path = request.get_full_path()
                ErrorLog.add_log(
                    status_code=0, method=method, full_path=full_path, message=err_msg, username=request.user.username)
            except Exception:
                pass

        return Response(data=None, status=200)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('资源券申请记录详情查询'),
        manual_parameters=NormalGenericViewSet.PARAMETERS_AS_ADMIN,
        responses={
            204: ''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        资源券申请记录详情查询

            http code 200:
            {
                "id": "1spdsf5d4rf48ecpwx82eya23",
                "service_type": "scan",
                "odc": null,
                "service_id": "scan1",
                "service_name": "scan_name1",
                "service_name_en": "scan_name_en1",
                "face_value": "7000.12",
                "expiration_time": "2024-03-15T00:00:00Z",
                "apply_desc": "申请说明",
                "contact_info": "122xx",                    # 联系方式
                "creation_time": "2024-03-09T00:00:00Z",
                "update_time": "2024-03-09T00:00:00Z",
                "user_id": "1snj1fmahymxr60ary3t10gyt",
                "username": "test",
                "vo_id": "",
                "vo_name": "",
                "owner_type": "user",
                "status": "wait",
                "approver": "",
                "reject_reason": "",
                "approved_amount": "0.00",
                "coupon_id": "",
                "order": {          # 关联订单，未关联为 null
                    "id": "2024032107101265626013",
                    "order_type": "new",
                    "status": "unpaid",
                    "total_amount": "333.33",
                    "pay_amount": "0.00",
                    "payable_amount": "220.00",
                    "balance_amount": "0.00",
                    "coupon_amount": "0.00",
                    "service_id": "scan_service_id",
                    "service_name": "scan_service_name",
                    "resource_type": "scan",
                    "instance_config": {
                        "name": "host and web",
                        "host_addr": "10.8.8.6",
                        "web_url": "https://test.cn",
                        "remark": "test remark"
                    },
                    "period": 0,
                    "payment_time": null,
                    "pay_type": "prepaid",
                    "creation_time": "2024-03-21T07:10:12.656447Z",
                    "user_id": "1snj1fmahymxr60ary3t10gyt",
                    "username": "test",
                    "vo_id": "",
                    "vo_name": "",
                    "owner_type": "user",
                    "cancelled_time": null,
                    "app_service_id": "app_service_id",
                    "trading_status": "opening",
                    "number": 1
                }
            }
        """
        apply_id = kwargs[self.lookup_field]
        try:
            if self.is_as_admin_request(request):
                apply = CouponApplyManager.get_admin_perm_apply(
                    _id=apply_id, admin_user=request.user, select_for_update=False)
            else:
                apply = CouponApplyManager.get_perm_apply(
                    _id=apply_id, user=request.user, select_for_update=False)
        except errors.Error as exc:
            return self.exception_response(exc)

        return Response(data=serializers.CouponDetailSerializer(apply).data)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CouponApplySerializer
        elif self.action == 'create':
            return serializers.CouponApplyCreateSerializer
        elif self.action == 'update':
            return serializers.CouponApplyUpdateSerializer
        elif self.action == 'for_order_apply':
            return serializers.OrderCouponApplySerializer

        return Serializer
