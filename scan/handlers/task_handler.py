from decimal import Decimal
import ipaddress
from django.conf import settings
from django.db.models import TextChoices
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from api.viewsets import CustomGenericViewSet, serializer_error_msg
from core import errors
from scan.managers import TaskManager, URLHTTPValidator
from bill.managers.payment import PaymentManager
from rest_framework.response import Response
from scan.models import VtScanService
from scan.serializers import ScanTaskListSerializer


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
    def _create_task_validate_params(view, request):
        validated_data = TaskHandler._post_task_validate_params(
            view=view, request=request
        )

        do_web_scan = validated_data.get("scheme", False)
        do_host_scan = validated_data.get("ipaddr", False)
        validated_data['do_web_scan'] = do_web_scan
        validated_data['do_host_scan'] = do_host_scan
        # 必须指定一种以上扫描方式
        if do_host_scan is False and do_web_scan is False:
            raise errors.BadRequest(
                message=_("未指定安全扫描类型"), code="InvalidScanType"
            )

        if do_web_scan is not False:
            scheme = validated_data.get("scheme", "")
            hostname = validated_data.get("hostname", "")
            uri = validated_data.get("uri", "")
            full_url = scheme + hostname + uri
            try:
                URLHTTPValidator()(full_url)
                validated_data["url"] = full_url
            except Exception:
                raise errors.BadRequest(message=_("网址无效"), code="InvalidUrl")

        if do_host_scan is not False:
            try:
                ipaddr = validated_data.get("ipaddr", "")
                ipaddress.IPv4Address(ipaddr)
                if ipaddr == '127.0.0.1':
                    raise errors.BadRequest(message=_("主机IP不能为127.0.0.1"), code="InvalidIp")
            except ipaddress.AddressValueError:
                raise errors.BadRequest(message=_("主机IP无效"), code="InvalidIp")

        # 检查指定的资源券
        coupon_ids = request.query_params.getlist("coupon_ids", [])
        if coupon_ids == []:
            raise errors.BadRequest(
                message=_("安全扫描服务必须指定资源券"), code="MissingCouponIDs"
            )
        if coupon_ids:
            coupon_set = set(coupon_ids)
            if not all(coupon_set):
                raise errors.BadRequest(
                    message=_("参数“coupon_ids”的值不能为空"), code="InvalidCouponIDs"
                )

            if len(coupon_ids) > 5:
                raise errors.BadRequest(
                    message=_("最多可以指定使用5个资源券"), code="TooManyCouponIDs"
                )

            if len(coupon_set) != len(coupon_ids):
                raise errors.BadRequest(
                    message=_("指定的资源券有重复"), code="DuplicateCouponIDExist"
                )
        validated_data["coupon_ids"] = coupon_ids

        return validated_data

    @staticmethod
    def _post_task_validate_params(view, request):
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
    def __pay_price_create_task(app_service_id: str, user, price: Decimal, params):
        """
        扣除券并创建任务

        :raises: Error, BalanceNotEnough
        """
        # 扣券与创建任务需要做一个事务
        try:
            with transaction.atomic():
                # 创建任务
                tasks = []
                if params["do_web_scan"] is not False:
                    tasks.append(
                        TaskManager.create_task(
                            user_id=user.id,
                            name=params["name"],
                            type=TaskType.WEB,
                            target=params["url"],
                            remark=params["remark"],
                        )
                    )
                if params["do_host_scan"] is not False:
                    tasks.append(
                        TaskManager.create_task(
                            user_id=user.id,
                            name=params["name"],
                            type=TaskType.HOST,
                            target=params["ipaddr"],
                            remark=params["remark"],
                        )
                    )
                # 扣券
                pay_history = PaymentManager().pay_by_user(
                    user_id=user.id,
                    app_id=settings.PAYMENT_BALANCE["app_id"],
                    subject="安全扫描计费",
                    amounts=price,
                    executor=user.username,
                    remark="",
                    order_id=tasks[0].id,
                    app_service_id=app_service_id,
                    instance_id="",
                    required_enough_balance=True,
                    coupon_ids=params["coupon_ids"],
                    only_coupon=True,
                )
                for task in tasks:
                    TaskManager.set_task_payment_id(
                        task=task, payment_history_id=pay_history.id
                    )
                return tasks
        except errors.Error as exc:
            raise exc
        except Exception as exc:
            raise errors.Error.from_error(exc)

    @staticmethod
    def create_scan_task(view: CustomGenericViewSet, request):
        """
        创建扫描任务，需要同时执行域名的检查以及资源券的扣费
        """
        try:
            params = TaskHandler._create_task_validate_params(
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
            price = 0
            if params["do_web_scan"] is not False:
                price += ins.web_scan_price
            if params["do_host_scan"] is not False:
                price += ins.host_scan_price
            # 扣余额券以及创建任务
            tasks = TaskHandler.__pay_price_create_task(
                app_service_id=pay_app_service_id, user=user, price=price, params=params
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        data = ScanTaskListSerializer(instance=tasks, many=True).data
        return Response(data=data)
