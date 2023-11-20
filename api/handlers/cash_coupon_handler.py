import math

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.utils.translation import gettext as _
from django.db.models import TextChoices, Count, Sum, Q
from rest_framework.response import Response

from users.managers import get_user_by_name
from users.models import UserProfile
from vo.models import VirtualOrganization
from vo.managers import VoManager
from core import errors
from api.viewsets import CustomGenericViewSet
from api.serializers.serializers import AdminCashCouponSerializer
from bill.managers import CashCouponManager
from bill.managers.cash_coupon import get_app_service_by_admin
from bill.models import CashCoupon, PayAppService, CashCouponPaymentHistory
from utils.report_file import CSVFileInMemory, wrap_csv_file_response
from utils.time import iso_utc_to_datetime
from utils import rand_utils
from utils.decimal_utils import quantize_10_2
from utils.model import OwnerType
from .handlers import serializer_error_msg


class QueryCouponValidChoices(TextChoices):
    NOT_YET = 'notyet', '未起效'
    VALID = 'valid', '有效期内'
    EXPIRED = 'expired', '已过期'


class CashCouponHandler:
    def list_cash_coupon(self, view: CustomGenericViewSet, request):
        try:
            data = self.list_cash_coupon_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        vo_id = data['vo_id']
        valid = data['valid']
        app_service_id = data['app_service_id']
        app_service_category = data['app_service_category']

        mgr = CashCouponManager()
        if vo_id:
            queryset = mgr.get_vo_cash_coupon_queryset(
                user=request.user, vo_id=vo_id, valid=valid, app_service_id=app_service_id,
                app_service_category=app_service_category
            )
        else:
            queryset = mgr.get_user_cash_coupon_queryset(
                user_id=request.user.id, valid=valid, app_service_id=app_service_id,
                app_service_category=app_service_category
            )

        try:
            coupons = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=coupons, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(errors.convert_to_error(exc))

    @staticmethod
    def list_cash_coupon_validate_params(request):
        vo_id = request.query_params.get('vo_id', None)
        valid = request.query_params.get('valid', None)
        app_service_id = request.query_params.get('app_service_id', None)
        app_service_category = request.query_params.get('app_service_category', None)

        if vo_id == '':
            raise errors.BadRequest(message=_('参数“vo_id”值无效'), code='InvalidVoId')

        if app_service_category and app_service_category not in PayAppService.Category.values:
            raise errors.InvalidArgument(message=_('参数“app_service_category”值无效'), code='InvalidAppServiceCategory')

        if isinstance(valid, str):
            valid = valid.lower()
            if valid not in QueryCouponValidChoices.values:
                raise errors.InvalidArgument(message=_('参数“valid”值无效'), code='InvalidValid')
        else:
            valid = None

        return {
            'vo_id': vo_id,
            'valid': valid,
            'app_service_id': app_service_id,
            'app_service_category': app_service_category
        }

    def draw_cash_coupon(self, view: CustomGenericViewSet, request):
        try:
            coupon_id, coupon_code, vo_id = self.draw_cash_coupon_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            coupon = CashCouponManager().draw_cash_coupon(
                coupon_id=coupon_id, coupon_code=coupon_code, user=request.user, vo_id=vo_id
            )
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={'id': coupon.id})

    @staticmethod
    def draw_cash_coupon_validate_params(request) -> tuple:
        coupon_id = request.query_params.get('id', None)
        coupon_code = request.query_params.get('coupon_code', None)
        vo_id = request.query_params.get('vo_id', None)

        if coupon_id is None:
            raise errors.BadRequest(message=_('参数“id”必须指定'), code='MissingID')

        if not coupon_id:
            raise errors.BadRequest(message=_('参数“id”值无效'), code='InvalidID')

        if coupon_code is None:
            raise errors.BadRequest(message=_('参数“coupon_code”必须指定'), code='MissingCouponCode')

        if not coupon_code:
            raise errors.BadRequest(message=_('参数“coupon_code”值无效'), code='InvalidCouponCode')

        if vo_id is not None and not vo_id:
            raise errors.BadRequest(message=_('参数“vo_id”值无效'), code='InvalidVoId')

        return coupon_id, coupon_code, vo_id

    @staticmethod
    def delete_cash_coupon(view: CustomGenericViewSet, request, kwargs):
        coupon_id = kwargs.get(view.lookup_field, None)
        force = request.query_params.get('force', None)
        force = force is not None

        try:
            CashCouponManager().delete_cash_coupon(coupon_id=coupon_id, user=request.user, force=force)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)

    @staticmethod
    def list_cash_coupon_payment(view: CustomGenericViewSet, request, kwargs):
        """
        列举券支付记录
        """
        coupon_id = kwargs.get(view.lookup_field)
        try:
            queryset = CashCouponManager().get_cash_coupon_payment_queryset(coupon_id=coupon_id, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        try:
            coupons = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=coupons, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(errors.convert_to_error(exc))

    def admin_list_cash_coupon(self, view: CustomGenericViewSet, request):
        try:
            data = self._admin_list_cash_coupon_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        template_id = data['template_id']
        status = data['status']
        app_service_id = data['app_service_id']
        valid = data['valid']
        redeemer = data['redeemer']
        issuer = data['issuer']
        download = data['download']
        time_start = data['time_start']
        time_end = data['time_end']

        try:
            queryset = CashCouponManager().admin_list_coupon_queryset(
                user=request.user, template_id=template_id, app_service_id=app_service_id, status=status, valid=valid,
                issuer=issuer, redeemer=redeemer, createtime_start=time_start, createtime_end=time_end,
                coupon_id=data['id']
            )

            if download:
                return self.admin_list_coupon_download(queryset=queryset)

            coupons = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=coupons, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(errors.convert_to_error(exc))

    @staticmethod
    def _admin_list_cash_coupon_validate_params(request):
        c_id = request.query_params.get('id', None)
        template_id = request.query_params.get('template_id', None)
        status = request.query_params.get('status', None)
        app_service_id = request.query_params.get('app_service_id', None)
        valid_status = request.query_params.get('valid_status', None)
        redeemer = request.query_params.get('redeemer', None)
        issuer = request.query_params.get('issuer', None)
        download = request.query_params.get('download', None)
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)

        if issuer is not None and not issuer:
            raise errors.InvalidArgument(message=_('指定的发放人不能为空'))

        if redeemer is not None and not redeemer:
            raise errors.InvalidArgument(message=_('指定的兑换人不能为空'))

        if status and status not in CashCoupon.Status.values:
            raise errors.InvalidArgument(message=_('参数“status”的值无效'))

        if isinstance(valid_status, str):
            valid = valid_status.lower()
            if valid not in QueryCouponValidChoices.values:
                raise errors.InvalidArgument(message=_('参数“valid”值无效'), code='InvalidValid')
        else:
            valid = None

        if time_start is not None:
            time_start = iso_utc_to_datetime(time_start)
            if time_start is None:
                raise errors.InvalidArgument(message=_('参数“time_start”的值无效的时间格式'))

        if time_end is not None:
            time_end = iso_utc_to_datetime(time_end)
            if time_end is None:
                raise errors.InvalidArgument(message=_('参数“time_end”的值无效的时间格式'))

        if time_start and time_end:
            if time_start >= time_end:
                raise errors.InvalidArgument(message=_('参数“time_start”时间必须超前“time_end”时间'))

        return {
            'template_id': template_id,
            'status': status,
            'valid': valid,
            'app_service_id': app_service_id,
            'issuer': issuer,
            'redeemer': redeemer,
            'download': download is not None,
            'time_start': time_start,
            'time_end': time_end,
            'id': c_id
        }

    @staticmethod
    def admin_list_coupon_download(queryset):
        count = queryset.count()
        if count > 100000:
            exc = errors.ConflictError(message=_('数据量太多'), code='TooManyData')
            return Response(data=exc.err_data(), status=exc.status_code)

        filename = rand_utils.timestamp14_sn()
        csv_file = CSVFileInMemory(filename=filename)
        csv_file.writerow(['#' + _('资源券明细')])
        csv_file.writerow(['#--------------' + _('数据明细列表') + '---------------'])
        csv_file.writerow([
            _('资源券编号'), _('面额'), _('余额'), _('服务单元'), _('创建日期'), _('生效日期'), _('过期时间'),
            _('状态'), _('券模板'), _('兑换码'), _('所有者类型'), _('用户'), _('VO组名')
        ])
        per_page = 1000
        is_end_page = False
        for number in range(1, math.ceil(count / per_page) + 1):
            bottom = (number - 1) * per_page
            top = bottom + per_page
            if top >= count:
                top = count
                is_end_page = True

            coupons = queryset[bottom:top]
            rows = []
            for c in coupons:
                c: CashCoupon
                app_service_name = c.app_service.name if c.app_service else "空"
                tpl_name = c.activity.name if c.activity else "空"
                username = c.user.username if c.user else '空'
                voname = c.vo.name if c.vo else '空'

                line_items = [
                    str(c.id), str(quantize_10_2(c.face_value)), str(quantize_10_2(c.balance)),
                    str(app_service_name), c.creation_time.isoformat(), c.effective_time.isoformat(),
                    c.expiration_time.isoformat(), str(c.get_status_display()),
                    tpl_name, c.one_exchange_code, str(c.owner_type), username, voname
                ]
                rows.append(line_items)

            csv_file.writerows(rows)
            if is_end_page:
                break

        csv_file.writerow(['#--------------' + _('数据明细列表结束') + '---------------'])
        csv_file.writerow(['#' + _('数据总数') + f': {count}'])
        csv_file.writerow(['#' + _('下载时间') + f': {timezone.now()}'])

        filename = csv_file.filename
        data = csv_file.to_bytes()
        csv_file.close()
        return wrap_csv_file_response(filename=filename, data=data)

    def exchange_cash_coupon(self, view: CustomGenericViewSet, request):
        """兑换码兑换资源券"""
        try:
            code, vo_id = self._exchange_cash_coupon_validate_params(request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        coupon_id, coupon_code = CashCoupon.parse_exchange_code(code=code)

        try:
            coupon = CashCouponManager().draw_cash_coupon(
                coupon_id=coupon_id, coupon_code=coupon_code, user=request.user, vo_id=vo_id
            )
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={'id': coupon.id})

    @staticmethod
    def _exchange_cash_coupon_validate_params(request) -> tuple:
        code = request.query_params.get('code', None)
        vo_id = request.query_params.get('vo_id', None)

        if code is None:
            raise errors.BadRequest(message=_('参数“code”必须指定'), code='MissingCode')

        if not code:
            raise errors.BadRequest(message=_('参数“code”值无效'), code='InvalidCode')

        if len(code) < 10:
            raise errors.BadRequest(message=_('参数“code”值无效'), code='InvalidCode')

        if vo_id is not None and not vo_id:
            raise errors.BadRequest(message=_('参数“vo_id”值无效'), code='InvalidVoId')

        return code, vo_id

    @staticmethod
    def admin_create_cash_coupon(view: CustomGenericViewSet, request):
        """
        App服务单元管理员创建一个资源券，可直接发放给指定用户或vo
        """
        try:
            data = CashCouponHandler._admin_create_cash_coupon_validate_params(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        face_value = data['face_value']
        effective_time = data['effective_time']
        expiration_time = data['expiration_time']
        app_service = data['app_service']
        to_user = data['user']
        vo = data['vo']
        remark = data['remark']

        try:
            if to_user is not None:
                coupon = CashCouponManager().create_one_coupon_to_user_or_vo(
                    user=to_user, vo=None, app_service_id=app_service.id,
                    face_value=face_value, effective_time=effective_time, expiration_time=expiration_time,
                    issuer=request.user.username, remark=remark
                )
            elif vo is not None:
                coupon = CashCouponManager().create_one_coupon_to_user_or_vo(
                    user=request.user, vo=vo, app_service_id=app_service.id,
                    face_value=face_value, effective_time=effective_time, expiration_time=expiration_time,
                    issuer=request.user.username, remark=remark
                )
            else:
                coupon, coupon_num = CashCouponManager().create_wait_draw_coupon(
                    app_service_id=app_service.id,
                    face_value=face_value,
                    effective_time=effective_time,
                    expiration_time=expiration_time,
                    coupon_num=0,
                    issuer=request.user.username,
                    remark=remark
                )

        except Exception as exc:
            return view.exception_response(exc)

        return Response(data=AdminCashCouponSerializer(instance=coupon).data)

    @staticmethod
    def _admin_create_cash_coupon_validate_params(view: CustomGenericViewSet, request):
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            s_errors = serializer.errors
            if 'face_value' in s_errors:
                exc = errors.BadRequest(
                    message=_('资源券面额无效。') + s_errors['face_value'][0], code='InvalidFaceValue')
            elif 'effective_time' in s_errors:
                exc = errors.BadRequest(
                    message=_('资源券生效时间无效。') + s_errors['effective_time'][0], code='InvalidEffectiveTime')
            elif 'expiration_time' in s_errors:
                exc = errors.BadRequest(
                    message=_('资源券过期时间无效。') + s_errors['expiration_time'][0], code='InvalidExpirationTime')
            else:
                msg = serializer_error_msg(serializer.errors)
                exc = errors.BadRequest(message=msg)

            raise exc

        data = serializer.validated_data
        face_value = data['face_value']
        effective_time = data['effective_time']
        expiration_time = data['expiration_time']
        app_service_id = data['app_service_id']
        username = data.get('username', None)
        vo_id = data.get('vo_id', None)
        remark = data.get('remark')

        if face_value < 0 or face_value > 100000:
            raise errors.BadRequest(message=_('资源券面额必须大于0，不得大于100000'), code='InvalidFaceValue')

        now_time = timezone.now()
        if (expiration_time - now_time) < timedelta(hours=1):
            raise errors.BadRequest(message=_('资源券的过期时间与当前时间的时间差必须大于1小时'), code='InvalidExpirationTime')

        if effective_time:
            if (expiration_time - effective_time) < timedelta(hours=1):
                raise errors.BadRequest(
                    message=_('资源券的过期时间与生效时间的时间差必须大于1小时'), code='InvalidExpirationTime')
        else:
            effective_time = now_time

        if username and vo_id:
            raise errors.InvalidArgument(message=_('不能同时指定用户和项目组'))

        # AppServiceNotExist, AccessDenied
        app_service = get_app_service_by_admin(_id=app_service_id, user=request.user)

        if username:
            user = get_user_by_name(username=username)      # UserNotExist
        else:
            user = None

        if vo_id:
            vo = VoManager.get_vo_by_id(vo_id=vo_id)
            if vo is None:
                raise errors.VoNotExist(message=_('项目组不存在'))
        else:
            vo = None

        return {
            'face_value': face_value,
            'effective_time': effective_time,
            'expiration_time': expiration_time,
            'app_service': app_service,
            'user': user,
            'vo': vo,
            'remark': remark if remark else ''
        }

    @staticmethod
    def detail_cash_coupon(view: CustomGenericViewSet, request, kwargs):
        """
        查询资源券详情
        """
        coupon_id = kwargs.get(view.lookup_field)

        ccmgr = CashCouponManager()
        try:
            coupon = ccmgr.get_cash_coupon(
                coupon_id=coupon_id, select_for_update=False,
                related_fields=['vo', 'user', 'activity', 'app_service']
            )
            ccmgr.has_read_perm_cash_coupon(coupon=coupon, user=request.user)
            serializer = view.get_serializer(instance=coupon)
            return Response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def admin_detail_cash_coupon(view: CustomGenericViewSet, request, kwargs):
        """
        管理员查询资源券详情
        """
        coupon_id = kwargs.get(view.lookup_field)

        ccmgr = CashCouponManager()
        try:
            coupon = ccmgr.get_cash_coupon(
                coupon_id=coupon_id, select_for_update=False,
                related_fields=['vo', 'user', 'activity', 'app_service']
            )
            ccmgr.has_admin_perm_cash_coupon(coupon=coupon, user=request.user)
            serializer = view.get_serializer(instance=coupon)
            return Response(data=serializer.data)
        except Exception as exc:
            return view.exception_response(exc)

    @staticmethod
    def admin_delete_cash_coupon(view: CustomGenericViewSet, request, kwargs):
        coupon_id = kwargs.get(view.lookup_field, None)

        try:
            CashCouponManager().admin_delete_cash_coupon(coupon_id=coupon_id, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        return Response(status=204)

    @staticmethod
    def admin_list_cash_coupon_payment(view: CustomGenericViewSet, request, kwargs):
        """
        列举券支付记录
        """
        coupon_id = kwargs.get(view.lookup_field)
        try:
            queryset = CashCouponManager().admin_get_cash_coupon_payment_queryset(
                coupon_id=coupon_id, user=request.user)
        except Exception as exc:
            return view.exception_response(exc)

        try:
            coupons = view.paginate_queryset(queryset)
            serializer = view.get_serializer(instance=coupons, many=True)
            return view.get_paginated_response(serializer.data)
        except Exception as exc:
            return view.exception_response(errors.convert_to_error(exc))

    @staticmethod
    def admin_cash_coupon_statistics(view: CustomGenericViewSet, request, kwargs):
        """
        联邦管理员查询券统计信息
        """
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)
        app_service_id = request.query_params.get('app_service_id', None)

        try:
            time_start, time_end = CashCouponHandler._validate_time_start_end(time_start=time_start, time_end=time_end)
        except Exception as exc:
            return view.exception_response(exc)

        try:
            if not request.user.is_federal_admin():
                raise errors.AccessDenied(message=_('你没有联邦管理员权限。'))

            lookups = {}
            if time_start:
                lookups['creation_time__gte'] = time_start
            if time_end:
                lookups['creation_time__lte'] = time_end
            if app_service_id:
                lookups['app_service_id'] = app_service_id

            r = CashCoupon.objects.filter(**lookups).aggregate(
                total_count=Count('id', distinct=True),
                total_face_value=Sum('face_value')
            )
            total_count = r['total_count']
            total_face_value = r['total_face_value'] if r['total_face_value'] else Decimal(0.00)

            # 兑换券数量
            redeem_count = CashCoupon.objects.filter(**lookups).exclude(status=CashCoupon.Status.WAIT.value).count()
            # 当前有效券数量
            available_count = CashCoupon.objects.filter(
                expiration_time__gt=timezone.now(), status=CashCoupon.Status.AVAILABLE.value, **lookups).count()

            # 券总消费点数，时间段参数无效
            lookups = {}
            if time_start:
                lookups['creation_time__gte'] = time_start
            if time_end:
                lookups['creation_time__lte'] = time_end
            if app_service_id:
                lookups['cash_coupon__app_service_id'] = app_service_id
            r = CashCouponPaymentHistory.objects.filter(**lookups).aggregate(
                coupon_pay_amounts=Sum('amounts'))
            coupon_pay_amounts = r['coupon_pay_amounts'] if r['coupon_pay_amounts'] else Decimal('0.00')
            coupon_pay_amounts = -coupon_pay_amounts

            # 有效券总余额，时间段参数无效
            lookups = {}
            if app_service_id:
                lookups['app_service_id'] = app_service_id
            r = CashCoupon.objects.filter(
                **lookups, expiration_time__gt=timezone.now(),
                status=CashCoupon.Status.AVAILABLE.value
            ).aggregate(total_balance=Sum('balance'))
            total_balance = r['total_balance'] if r['total_balance'] else Decimal('0.00')
        except Exception as exc:
            return view.exception_response(exc)

        return Response(data={
            'total_face_value': total_face_value,
            'total_count': total_count,
            'redeem_count': redeem_count,
            'available_count': available_count,
            'coupon_pay_amounts': coupon_pay_amounts,
            'total_balance': total_balance,
        })

    @staticmethod
    def admin_coupon_issue_statistics(view: CustomGenericViewSet, request, kwargs):
        """
        联邦管理员查询券发放统计信息
        """
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)
        issuer = request.query_params.get('issuer', None)

        try:
            time_start, time_end = CashCouponHandler._validate_time_start_end(time_start=time_start, time_end=time_end)
            if not request.user.is_federal_admin():
                raise errors.AccessDenied(message=_('你没有联邦管理员权限。'))
        except Exception as exc:
            return view.exception_response(exc)

        lookups = {}
        if time_start:
            lookups['creation_time__gte'] = time_start
        if time_end:
            lookups['creation_time__lte'] = time_end
        if issuer:
            lookups['issuer'] = issuer

        queryset = CashCoupon.objects.filter(**lookups).values('issuer').annotate(
            total_face_value=Sum('face_value'),
            total_count=Count('id', distinct=True)
        ).order_by('issuer')

        try:
            page = view.paginate_queryset(queryset)
            return view.get_paginated_response(page)
        except Exception as exc:
            return view.exception_response(errors.convert_to_error(exc))

    @staticmethod
    def admin_coupon_user_statistics(view: CustomGenericViewSet, request, kwargs):
        """
        联邦管理员查询用户资源券统计信息
        """
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)
        username = request.query_params.get('username', None)

        try:
            time_start, time_end = CashCouponHandler._validate_time_start_end(time_start=time_start, time_end=time_end)
            if not request.user.is_federal_admin():
                raise errors.AccessDenied(message=_('你没有联邦管理员权限。'))
        except Exception as exc:
            return view.exception_response(exc)

        lookups = {}
        if time_start:
            lookups['creation_time__gte'] = time_start
        if time_end:
            lookups['creation_time__lte'] = time_end
        if username:
            lookups['user__username'] = username

        queryset = CashCoupon.objects.filter(
            owner_type=OwnerType.USER.value, **lookups).values('user_id').annotate(
            total_face_value=Sum('face_value'),
            total_balance=Sum('balance'),
            total_count=Count('id', distinct=True),
            total_valid_count=Count(
                'id', distinct=True, filter=Q(
                    status=CashCoupon.Status.AVAILABLE.value, expiration_time__gt=timezone.now())),
        ).order_by('user_id')

        try:
            page = view.paginate_queryset(queryset)
            CashCouponHandler._mixin_username(page)
            return view.get_paginated_response(page)
        except Exception as exc:
            return view.exception_response(errors.convert_to_error(exc))

    @staticmethod
    def _mixin_username(data: list):
        user_ids = [i['user_id'] for i in data]
        users = UserProfile.objects.filter(id__in=user_ids).values('id', 'username')
        users_map = {i['id']: i['username'] for i in users}
        for i in data:
            i['username'] = users_map.get(i['user_id'], '')

        return data

    @staticmethod
    def _mixin_voname(data: list):
        vo_ids = [i['vo_id'] for i in data]
        vos = VirtualOrganization.objects.filter(id__in=vo_ids).values('id', 'name')
        users_map = {i['id']: i['name'] for i in vos}
        for i in data:
            i['name'] = users_map.get(i['vo_id'], '')

        return data

    @staticmethod
    def _validate_time_start_end(time_start: str, time_end: str):
        """
        :raises: Error
        """
        if time_start is not None:
            time_start = iso_utc_to_datetime(time_start)
            if time_start is None:
                raise errors.InvalidArgument(message=_('参数“time_start”的值无效的时间格式'))

        if time_end is not None:
            time_end = iso_utc_to_datetime(time_end)
            if time_end is None:
                raise errors.InvalidArgument(message=_('参数“time_end”的值无效的时间格式'))

        if time_start and time_end:
            if time_start >= time_end:
                raise errors.InvalidArgument(message=_('参数“time_start”时间必须超前“time_end”时间'))

        return time_start, time_end

    @staticmethod
    def admin_coupon_vo_statistics(view: CustomGenericViewSet, request, kwargs):
        """
        联邦管理员查询用户资源券统计信息
        """
        time_start = request.query_params.get('time_start', None)
        time_end = request.query_params.get('time_end', None)
        voname = request.query_params.get('voname', None)

        try:
            time_start, time_end = CashCouponHandler._validate_time_start_end(time_start=time_start, time_end=time_end)
            if not request.user.is_federal_admin():
                raise errors.AccessDenied(message=_('你没有联邦管理员权限。'))
        except Exception as exc:
            return view.exception_response(exc)

        lookups = {}
        if time_start:
            lookups['creation_time__gte'] = time_start
        if time_end:
            lookups['creation_time__lte'] = time_end
        if voname:
            lookups['vo__name'] = voname

        queryset = CashCoupon.objects.filter(
            owner_type=OwnerType.VO.value, **lookups).values('vo_id').annotate(
            total_face_value=Sum('face_value'),
            total_balance=Sum('balance'),
            total_count=Count('id', distinct=True),
            total_valid_count=Count(
                'id', distinct=True, filter=Q(
                    status=CashCoupon.Status.AVAILABLE.value, expiration_time__gt=timezone.now())),
        ).order_by('vo_id')

        try:
            page = view.paginate_queryset(queryset)
            CashCouponHandler._mixin_voname(page)
            return view.get_paginated_response(page)
        except Exception as exc:
            return view.exception_response(errors.convert_to_error(exc))

    @staticmethod
    def admin_change_coupon_remark(view: CustomGenericViewSet, request, kwargs):
        """
        管理员修改资源券备注信息
        """
        coupon_id = kwargs.get(view.lookup_field)
        remark = request.query_params.get('remark')

        ccmgr = CashCouponManager()
        try:
            if not remark:
                raise errors.InvalidArgument(message=_('必须指定新的备注信息'))

            coupon = ccmgr.get_cash_coupon(
                coupon_id=coupon_id, select_for_update=False,
                related_fields=['app_service']
            )
            ccmgr.has_admin_perm_cash_coupon(coupon=coupon, user=request.user)
            if coupon.remark != remark:
                coupon: CashCoupon
                coupon.remark = remark
                coupon.save(update_fields=['remark'])

            return Response(data={'remark': coupon.remark})
        except Exception as exc:
            return view.exception_response(exc)
