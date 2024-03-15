from datetime import datetime, timedelta
from decimal import Decimal

from django.utils import timezone as dj_timezone
from django.utils.translation import gettext_lazy, gettext as _
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from core import errors
from utils.time import iso_to_datetime
from utils.model import OwnerType
from api.viewsets import NormalGenericViewSet, serializer_error_msg
from api.paginations import NewPageNumberPagination100
from vo.managers import VoManager
from servers.managers import ServiceManager as ServerServiceManager
from storage.managers import ObjectsServiceManager
from monitor.models import MonitorWebsiteVersion
from scan.models import VtScanService
from apply import serializers
from apply.models import CouponApply
from apply.managers.coupon import CouponApplyManager


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
                        "coupon_id": ""
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
            403：AccessDenied: 你不是组管理员，没有组管理权限
            404：
                VoNotExist：项目组不存在
                TargetNotExist：云主机、对象存储服务单元不存在
            409：Conflict：服务单元停止服务中 / 指定服务可能未注册钱包结算单元
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
            odc, service_id, service_name, service_name_en, pay_service_id = self._get_service_info(
                service_type=service_type, service_id=service_id
            )
            apply = CouponApplyManager.create_apply(
                service_type=service_type, odc=odc, service_id=service_id, service_name=service_name,
                service_name_en=service_name_en, pay_service_id=pay_service_id,
                face_value=face_value, expiration_time=expiration_time, apply_desc=apply_desc,
                user_id=user_id, username=username, vo_id=vo_id, vo_name=vo_name, owner_type=owner_type
            )
        except errors.Error as exc:
            return self.exception_response(exc)

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
            'service_id': service_id if service_id else ''
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

                if apply.owner_type == OwnerType.VO.value and service_type != CouponApply.ServiceType.SERVER.value:
                    raise errors.ConflictError(message=_('指定的服务类型，不允许为vo组申请资源券'))

                apply = CouponApplyManager.update_apply(
                    apply=apply, service_type=service_type, odc=odc, service_id=service_id, service_name=service_name,
                    service_name_en=service_name_en, pay_service_id=pay_service_id,
                    face_value=face_value, expiration_time=expiration_time, apply_desc=apply_desc,
                    user_id=user.id, username=user.username
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

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CouponApplySerializer
        elif self.action == 'create':
            return serializers.CouponApplyCreateSerializer
        elif self.action == 'update':
            return serializers.CouponApplyUpdateSerializer

        return Serializer
