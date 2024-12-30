import ipaddress

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from apps.api.viewsets import CustomGenericViewSet, serializer_error_msg
from core import errors
from apps.app_order.managers.order import OrderManager
from apps.app_order.managers.instance_configs import ScanConfig
from apps.app_scan.managers import TaskManager, URLHTTPValidator
from apps.app_scan.models import VtScanService, VtTask


class TaskHandler:
    @staticmethod
    def list_scan_task(view: CustomGenericViewSet, request):
        """
        列举用户扫描任务
        """
        try:
            _type = request.query_params.get("type", None)
            if _type and _type not in VtTask.TaskType.values:
                raise errors.InvalidArgument(message=_("指定的扫描类型无效"))

            queryset = TaskManager.filter_task_queryset(user_id=request.user.id, _type=_type)
            tasks = view.paginate_queryset(queryset=queryset)
        except Exception as exc:
            return view.exception_response(exc)

        data = view.get_serializer(instance=tasks, many=True).data
        return view.get_paginated_response(data=data)

    @staticmethod
    def _create_task_order_validate_params(view, request):
        validated_data = TaskHandler._post_task_order_validate_params(
            view=view, request=request
        )

        web_url = ''
        scheme = validated_data.get("scheme", "")
        if scheme:
            try:
                hostname = validated_data.get("hostname", "")
                uri = validated_data.get("uri", "")
                web_url = scheme + hostname + uri
                URLHTTPValidator()(web_url)
            except Exception:
                raise errors.BadRequest(message=_("网址无效"), code="InvalidUrl")

        host_addr = validated_data.get("ipaddr", '') or ''
        if host_addr:
            try:
                ipaddress.IPv4Address(host_addr)
                if host_addr in ["127.0.0.1", "0.0.0.0"]:
                    raise errors.BadRequest(
                        message=_("主机IP不能为127.0.0.1和0.0.0.0"), code="InvalidIp"
                    )
            except ipaddress.AddressValueError:
                raise errors.BadRequest(message=_("主机IP无效"), code="InvalidIp")

        if not web_url and not host_addr:
            raise errors.BadRequest(
                message=_("必须提交一个安全扫描任务"), code="InvalidScanType"
            )

        return {
            'name': validated_data['name'],
            'remark': validated_data.get('remark', ''),
            'web_url': web_url,
            'host_addr': host_addr
        }

    @staticmethod
    def _post_task_order_validate_params(view, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if "name" in s_errors:
                exc = errors.BadRequest(
                    message=_("无效的监控任务名称。") + s_errors["name"][0]
                )
            elif "scheme" in s_errors:
                exc = errors.BadRequest(
                    message=_("无效的站点协议。") + s_errors["scheme"][0],
                    code="InvalidScheme",
                )
            elif "hostname" in s_errors:
                exc = errors.BadRequest(
                    message=_("无效的站点域名。") + s_errors["hostname"][0],
                    code="InvalidHostname",
                )
            elif "remark" in s_errors:
                exc = errors.BadRequest(
                    message=_("备注无效。") + s_errors["remark"][0]
                )
            elif "uri" in s_errors:
                exc = errors.BadRequest(
                    message=_("无效的站点URI。") + s_errors["uri"][0], code="InvalidUri"
                )
            elif "ipaddr" in s_errors:
                exc = errors.BadRequest(
                    message=_("无效的主机ip。") + s_errors["ipaddr"][0],
                    code="InvalidIp",
                )
            else:
                msg = serializer_error_msg(serializer.errors)
                exc = errors.BadRequest(message=msg)

            raise exc

        return serializer.validated_data

    @staticmethod
    def create_scan_task_order(view: CustomGenericViewSet, request):
        """
        创建扫描任务，需要同时执行域名的检查以及资源券的扣费
        """
        try:
            params = TaskHandler._create_task_order_validate_params(
                view=view, request=request
            )
            user = request.user

            ins = VtScanService.get_instance()
            pay_app_service_id = ins.pay_app_service_id

            if ins.status != VtScanService.Status.ENABLE.value:
                raise errors.ConflictError(
                    message=_("安全扫描服务不在服务中")
                )

            if not pay_app_service_id or len(pay_app_service_id) < 10:
                raise errors.ConflictError(
                    message=_("安全扫描未配置对应的结算系统APP服务id"),
                    code="ServiceNoPayAppServiceId",
                )

            # 创建订单
            scanconfig = ScanConfig(
                name=params["name"],
                host_addr=params["host_addr"],
                web_url=params["web_url"],
                remark=params["remark"]
            )
            order, resources = OrderManager().create_scan_order(
                service_id=ins.id,
                service_name=ins.name,
                pay_app_service_id=pay_app_service_id,
                instance_config=scanconfig,
                user_id=user.id,
                username=user.username,
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data={"order_id": order.id})
