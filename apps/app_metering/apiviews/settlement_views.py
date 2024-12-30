from datetime import timedelta

from django.utils.translation import gettext_lazy, gettext as _
from django.utils import timezone as dj_timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from core import errors
from utils.model import PayType
from apps.api.viewsets import CustomGenericViewSet
from apps.api.paginations import NewPageNumberPagination
from apps.app_servers.managers import ServerManager
from apps.app_servers.serializers import ServerSerializer
from apps.app_metering import metering_serializers
from apps.app_metering.models import MeteringServer, DailyStatementServer
from apps.app_wallet.models import PaymentHistory, CashCouponPaymentHistory
from apps.app_wallet import trade_serializers
from apps.app_order.models import Resource, Order
from apps.app_order.serializers import OrderSerializer


def previous_days_dates(days: int = 10):
    """
    前面几天的日期
    """
    today = dj_timezone.now().date()
    return [today - timedelta(days=x) for x in range(days)]


class ServerSettlementViewSet(CustomGenericViewSet):
    """
    云主机结算信息
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'server_id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询云主机最近一次的结算信息'),
        manual_parameters=CustomGenericViewSet.PARAMETERS_AS_ADMIN,
        responses={
            200: ''''''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询云主机最近一次的结算信息

            http Code 200 Ok:
                {
                    "server": {
                        "id": "18fohiypbvd1xn3zvj0b1p2wx-i",
                        "name": "54fda185c32648c385b0348765ac1fa3",
                        "vcpus": 8,
                        "ram": 32,
                        "ram_gib": 32,
                        "ipv4": "223.193.36.182",
                        "public_ip": true,
                        "image": "CentOS-7",
                        "creation_time": "2024-07-25T02:24:39.711051Z",
                        "expiration_time": null,
                        "remarks": "zzh-node02",
                        "classification": "vo",
                        "image_id": "13",
                        "image_desc": "-",
                        "default_user": "cnic",
                        "default_password": "cnic.cn",
                        "pay_type": "postpaid",
                        "img_sys_type": "Linux",
                        "img_sys_arch": "x86-64",
                        "img_release": "CentOS",
                        "img_release_version": "CentOS-7-x86_64-Everything-2207-",
                        "service": {
                            "id": "04a9ee9c-2cf6-11ed-8bc0-c8009fe2eb03",
                            "name": "AIOPS 大数据平台",
                            "name_en": "AIOPS of CSTCloud",
                            "service_type": "evcloud"
                        },
                        "center_quota": 1,
                        "vo_id": "n0o6b3o3g28y93tocm6uap9i5",
                        "vo": {
                            "id": "n0o6b3o3g28y93tocm6uap9i5",
                            "name": "高通量NFV服务及试验平台项目"
                        },
                        "user": {
                            "id": "834f54b72a220ca1fa54edc24b4a9e46",
                            "username": "zhengzihao23@mails.ucas.ac.cn"
                        },
                        "lock": "lock-operation"
                    },
                    "settlement": {                         # 结算信息
                        "metering": {                       # 计量单，可能为null，只在按量付费云主机时存在
                            "id": "s6gncworpej3z3wcrkqgwvbic0",
                            "original_amount": "38.05",
                            "trade_amount": "38.05",
                            "daily_statement_id": "s6vkhu4tt0wa2bgpijfs1xrtdk",
                            "service_id": "04a9ee9c-2cf6-11ed-8bc0-c8009fe2eb03",
                            "server_id": "18fohiypbvd1xn3zvj0b1p2wx-i",
                            "date": "2024-09-19",
                            "creation_time": "2024-09-20T07:30:31.767075Z",
                            "user_id": "",
                            "username": "",
                            "vo_id": "n0o6b3o3g28y93tocm6uap9i5",
                            "vo_name": "高通量NFV服务及试验平台项目",
                            "owner_type": "vo",
                            "cpu_hours": 192,
                            "ram_hours": 768,
                            "disk_hours": 1200,
                            "public_ip_hours": 24,
                            "snapshot_hours": 0,
                            "upstream": 0,
                            "downstream": 0,
                            "pay_type": "postpaid"
                        },
                        "daily_statement": {                    # 日结算单，可能为null，只在按量付费云主机时存在
                            "id": "s6vkhu4tt0wa2bgpijfs1xrtdk",
                            "original_amount": "304.40",
                            "payable_amount": "304.40",
                            "trade_amount": "304.40",
                            "payment_status": "paid",
                            "payment_history_id": "202409200730400861453691",
                            "service_id": "04a9ee9c-2cf6-11ed-8bc0-c8009fe2eb03",
                            "date": "2024-09-19",
                            "creation_time": "2024-09-20T07:30:37.510954Z",
                            "user_id": "",
                            "username": "",
                            "vo_id": "n0o6b3o3g28y93tocm6uap9i5",
                            "vo_name": "高通量NFV服务及试验平台项目",
                            "owner_type": "vo",
                            "service": {
                                "id": "s20220905770015",
                                "name": "AIOPS 大数据平台",
                                "name_en": "AIOPS of CSTCloud"
                            }
                        },
                        "order": {                          # 订单，可能为null，只在预付费云主机时存在
                            "id": "2023072805405925081458",
                            "order_type": "new",
                            "status": "paid",
                            "total_amount": "13524.28",
                            "pay_amount": "13524.28",
                            "payable_amount": "13524.28",
                            "balance_amount": "0.00",
                            "coupon_amount": "13524.28",
                            "service_id": "04a9ee9c-2cf6-11ed-8bc0-c8009fe2eb03",
                            "service_name": "AIOPS 大数据平台",
                            "resource_type": "vm",
                            "instance_config": {},
                            "period": 12,
                            "period_unit": "month",
                            "start_time": "2023-07-28T05:43:45.324602Z",
                            "end_time": "2024-07-22T05:43:45.324602Z",
                            "payment_time": "2023-07-28T05:43:42.736800Z",
                            "pay_type": "prepaid",
                            "creation_time": "2023-07-28T05:40:59.252059Z",
                            "user_id": "8",
                            "username": "wangyushun@cnic.cn",
                            "vo_id": "",
                            "vo_name": "",
                            "owner_type": "user",
                            "cancelled_time": null,
                            "app_service_id": "s20220905770015",
                            "trading_status": "completed",
                            "number": 1
                        },
                        "payment": {                        # 支付记录，可能为null
                            "id": "202409200730400861453691",
                            "subject": "云服务器按量计费",
                            "payment_method": "coupon",
                            "executor": "metering",
                            "payer_id": "n0o6b3o3g28y93tocm6uap9i5",
                            "payer_name": "高通量NFV服务及试验平台项目",
                            "payer_type": "vo",
                            "payable_amounts": "304.40",
                            "amounts": "0.00",
                            "coupon_amount": "-304.40",
                            "creation_time": "2024-09-20T07:30:40.086121Z",
                            "payment_time": "2024-09-20T07:30:40.086123Z",
                            "remark": "server, 2024-09-19",
                            "status": "success",
                            "status_desc": "支付成功",
                            "order_id": "s6vkhu4tt0wa2bgpijfs1xrtdk",
                            "app_id": "20220615085209",
                            "app_service_id": "s20220905770015",
                            "coupon_historys": [        # 资源券支付记录
                                {
                                    "cash_coupon_id": "230915000002",
                                    "amounts": "-304.40",
                                    "before_payment": "97911.46",
                                    "after_payment": "97607.06",
                                    "creation_time": "2024-09-20T07:30:40.087076Z",
                                    "cash_coupon": {
                                        "id": "230915000002",
                                        "face_value": "100000.00",
                                        "creation_time": "2023-09-15T09:13:17.697853Z",
                                        "effective_time": "2023-09-14T16:00:00Z",
                                        "expiration_time": "2024-10-14T16:00:00Z",
                                        "balance": "97603.61",
                                        "status": "available",
                                        "granted_time": "2023-09-15T09:13:17.707176Z",
                                        "owner_type": "vo",
                                        "app_service": {
                                            "id": "s20220905770015",
                                            "name": "AIOPS 大数据平台",
                                            "name_en": "AIOPS of CSTCloud",
                                            "category": "vms-server",
                                            "service_id": "04a9ee9c-2cf6-11ed-8bc0-c8009fe2eb03"
                                        },
                                        "user": {
                                            "id": "8",
                                            "username": "wangyushun@cnic.cn"
                                        },
                                        "vo": {
                                            "id": "n0o6b3o3g28y93tocm6uap9i5",
                                            "name": "高通量NFV服务及试验平台项目"
                                        },
                                        "activity": null,
                                        "issuer": "wangyushun@cnic.cn",
                                        "remark": ""
                                    }
                                }
                            ]
                        }
                    }
                }

            Http Code 400, 404, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                403:
                AccessDenied: 你不是组管理员，没有组管理权限

                500:
                InternalError: xxx
        """
        server_id = kwargs.get(self.lookup_field)
        user = request.user

        try:
            if self.is_as_admin_request(request=request):
                server = ServerManager().get_read_perm_server(
                    server_id=server_id, user=user, related_fields=['vo'], as_admin=True)
            else:
                server = ServerManager().get_read_perm_server(
                    server_id=server_id, user=user, related_fields=['vo'], as_admin=False)
        except errors.Error as exc:
            return self.exception_response(exc=exc)

        # 预付费，订单
        settlement_data = {}
        if server.pay_type == PayType.PREPAID.value:
            settlement = self.get_order_payment(server_id=server_id)
            order = settlement.get('order')
            settlement_data['order'] = OrderSerializer(order, allow_null=True).data
        else:
            settlement = self.get_metering_statement_payment(server_id=server_id)
            metering = settlement.get('metering', None)
            daily_statement = settlement.get('daily_statement', None)
            settlement_data['metering'] = metering_serializers.MeteringServerSerializer(metering, allow_null=True).data
            settlement_data['daily_statement'] = metering_serializers.DailyStatementServerDetailSerializer(
                daily_statement, allow_null=True).data

        payment = settlement.get('payment', None)
        coupon_historys = settlement.get('coupon_payments', [])
        if payment:
            payment_data = trade_serializers.PaymentHistorySerializer(payment).data
            coupon_historys_data = []
            if coupon_historys:
                for ch in coupon_historys:
                    ch_data = trade_serializers.BaseCashCouponPaymentSerializer(instance=ch).data
                    coupon_data = trade_serializers.CashCouponSerializer(ch.cash_coupon).data
                    ch_data['cash_coupon'] = coupon_data
                    coupon_historys_data.append(ch_data)

            payment_data['coupon_historys'] = coupon_historys_data
            settlement_data['payment'] = payment_data
        else:
            settlement_data['payment'] = None

        return Response(data={
            'server': ServerSerializer(server).data,
            'settlement': settlement_data
        })

    @staticmethod
    def get_metering_statement_payment(server_id):
        """
        云主机计量单，结算单，支付记录

        :return: {  # 各项都有可能不存在
            'metering': MeteringServer,                 # 计量单
            'daily_statement': DailyStatementServer,    # 结算单
            'payment': PaymentHistory,                  # 支付记录
            'coupon_payments': list[                    # 资源券支付记录
                CashCouponPaymentHistory
            ]
        }
        """
        pre_days_date = previous_days_dates(days=10)
        data = {}
        metering = MeteringServer.objects.filter(server_id=server_id, date__in=pre_days_date).order_by('-date').first()
        if metering is None or not metering.daily_statement_id:
            return data

        data['metering'] = metering
        daily_state = DailyStatementServer.objects.select_related('service').filter(
            id=metering.daily_statement_id).first()
        if daily_state is None or not daily_state.payment_history_id:
            return data

        data['daily_statement'] = daily_state
        payment = PaymentHistory.objects.filter(id=daily_state.payment_history_id).first()
        if payment is None:
            return data

        data['payment'] = payment
        if payment.payment_method != PaymentHistory.PaymentMethod.BALANCE.value:
            coupon_payment_qs = CashCouponPaymentHistory.objects.select_related(
                'cash_coupon', 'cash_coupon__user', 'cash_coupon__vo', 'cash_coupon__app_service'
            ).filter(payment_history_id=payment.id).all()
            data['coupon_payments'] = list(coupon_payment_qs)

        return data

    @staticmethod
    def get_order_payment(server_id):
        """
        云主机订单，支付记录

        :return: {  # 各项都有可能不存在
            'order': Order,             # 订单
            'payment': PaymentHistory,  # 支付记录
            'coupon_payments': list[    # 资源券支付记录
                CashCouponPaymentHistory
            ]
        }
        """
        data = {}
        resource = Resource.objects.filter(
            instance_id=server_id, order__status=Order.Status.PAID.value
        ).select_related('order').order_by('creation_time').first()
        if resource is None or resource.order is None:
            return data

        order = resource.order
        data['order'] = resource.order
        if not order.payment_history_id:
            return data

        payment = PaymentHistory.objects.filter(id=order.payment_history_id).first()
        if payment is None:
            return data

        data['payment'] = payment
        if payment.payment_method != PaymentHistory.PaymentMethod.BALANCE.value:
            coupon_payment_qs = CashCouponPaymentHistory.objects.select_related(
                'cash_coupon', 'cash_coupon__user', 'cash_coupon__vo', 'cash_coupon__app_service'
            ).filter(payment_history_id=payment.id).all()
            data['coupon_payments'] = list(coupon_payment_qs)

        return data
