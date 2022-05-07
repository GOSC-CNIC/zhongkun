from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors
from api.viewsets import CustomGenericViewSet
from activity.managers import CashCouponManager


class CashCouponHandler:
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
