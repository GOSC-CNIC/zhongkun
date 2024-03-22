import ipaddress
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _
from api.viewsets import CustomGenericViewSet, serializer_error_msg
from core import errors
from scan.managers import TaskManager, URLHTTPValidator
from rest_framework.response import Response
from scan.models import VtScanService
from scan.serializers import ScanTaskListSerializer
from order.managers.order import OrderManager
from order.managers.instance_configs import ScanConfig


class TaskType(TextChoices):
    WEB = "web", _("站点")
    HOST = "host", _("主机")


class TaskHandler:
    @staticmethod
    def list_scan_task(view: CustomGenericViewSet, request):
        """
        列举用户扫描任务
        """
        try:
            type = request.query_params.get("type", None)
            if type and type not in TaskType.values:
                raise errors.InvalidArgument(message=_("指定的扫描类型无效"))
            if type == TaskType.HOST:
                queryset = TaskManager.get_user_host_tasks(user_id=request.user.id)
            elif type == TaskType.WEB:
                queryset = TaskManager.get_user_web_tasks(user_id=request.user.id)
            else:
                queryset = TaskManager.get_user_all_tasks(user_id=request.user.id)
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

        do_web_scan = validated_data.get("scheme", False)
        do_host_scan = validated_data.get("ipaddr", False)
        if do_web_scan is None or do_web_scan == "":
            do_web_scan = False
        if do_host_scan is None or do_host_scan == "":
            do_host_scan = False

        validated_data["do_web_scan"] = do_web_scan
        validated_data["do_host_scan"] = do_host_scan
        # 必须指定一种以上扫描方式
        if do_host_scan is False and do_web_scan is False:
            raise errors.BadRequest(
                message=_("未指定安全扫描类型"), code="InvalidScanType"
            )
        if do_web_scan is not False:
            try:
                scheme = validated_data.get("scheme", "")
                hostname = validated_data.get("hostname", "")
                uri = validated_data.get("uri", "")
                full_url = scheme + hostname + uri
                validated_data["web_url"] = full_url
                URLHTTPValidator()(full_url)
            except Exception:
                raise errors.BadRequest(message=_("网址无效"), code="InvalidUrl")
        if do_host_scan is not False:
            try:
                ipaddr = validated_data.get("ipaddr", "")
                ipaddress.IPv4Address(ipaddr)
                if ipaddr == "127.0.0.1":
                    raise errors.BadRequest(
                        message=_("主机IP不能为127.0.0.1"), code="InvalidIp"
                    )
                validated_data["host_addr"] = ipaddr
            except ipaddress.AddressValueError:
                raise errors.BadRequest(message=_("主机IP无效"), code="InvalidIp")
        return validated_data

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
                    message=_("问题相关的服务无效。") + s_errors["remark"][0]
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

            if not pay_app_service_id or len(pay_app_service_id) < 10:
                raise errors.ConflictError(
                    message=_("安全扫描未配置对应的结算系统APP服务id"),
                    code="ServiceNoPayAppServiceId",
                )
                
            # 创建订单
            scanconfig = ScanConfig(name=params["name"], 
                                    host_addr=params.get("host_addr",""), 
                                    web_url=params.get("web_url",""), 
                                    remark=params.get("remark",""))
            omgr = OrderManager()
            order, resources = omgr.create_scan_order(
                service_id=ins.id,
                service_name=ins.name,
                pay_app_service_id=ins.pay_app_service_id,
                instance_config=scanconfig,
                user_id=user.id,
                username=user.username,
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        return Response(data={"order_id": order.id})
