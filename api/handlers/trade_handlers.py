from decimal import Decimal

from django.utils.translation import gettext as _

from rest_framework.response import Response

from core import errors
from core.jwt.authentication import CreateUserJWTAuthentication
from api.viewsets import PaySignGenericViewSet
from api.handlers import serializer_error_msg
from api.serializers.serializers import PaymentHistorySerializer
from bill.managers.payment import PaymentManager
from core.jwt.jwt import JWTInvalidError


class TradeHandler:
    @staticmethod
    def trade_pay(view: PaySignGenericViewSet, request, kwargs):
        """
        扣费

        :return: Response()
        """
        try:
            app = view.check_request_sign(request)
        except errors.Error as exc:
            return view.exception_response(exc)

        try:
            data = TradeHandler._trade_pay_validate(view=view, request=request)
        except errors.Error as exc:
            return view.exception_response(exc)

        subject = data.get('subject')
        order_id = data.get('order_id')
        amounts = data.get('amounts')
        app_service_id = data.get('app_service_id')
        user = data.get('user')
        remark = data.get('remark')

        try:
            history = PaymentManager().pay_by_user(
                user_id=user.id,
                app_id=app.id,
                subject=subject,
                amounts=amounts,
                executor='',
                remark=remark,
                order_id=order_id,
                app_service_id=app_service_id,
                resource_type='',
                instance_id=''
            )
        except errors.Error as exc:
            return view.exception_response(exc)

        s = PaymentHistorySerializer(instance=history)
        return Response(data=s.data)

    @staticmethod
    def _trade_pay_validate(view, request):
        """
        :raises: Error
        """
        serializer = view.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise errors.BadRequest(msg)

        data = serializer.validated_data
        amounts = data.get('amounts')
        aai_jwt = data.get('aai_jwt')

        if amounts <= Decimal('0'):
            raise errors.BadRequest(message=_('交易金额必须大于0'))

        try:
            auth = CreateUserJWTAuthentication()
            token = auth.get_validated_token(raw_token=aai_jwt)
            user = auth.get_user(validated_token=token)
        except JWTInvalidError as exc:
            raise errors.BadRequest(message=exc.message, code=exc.code)
        except Exception as exc:
            raise errors.Error.from_error(exc)

        data['user'] = user
        return data
