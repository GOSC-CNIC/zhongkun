from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.request import Request
from rest_framework.response import Response
from django.http.request import HttpRequest
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import PaySignGenericViewSet
from api.paginations import NewPageNumberPagination
from core import errors


class TradeTestViewSet(PaySignGenericViewSet):
    """
    支付交易test视图
    """
    permission_classes = []
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('加签验签测试'),
        manual_parameters=[
            openapi.Parameter(
                name='param1',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='param1'
            ),
            openapi.Parameter(
                name='param2',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='param2'
            )
        ],
        responses={
            200: ''
        }
    )
    def create(self, request: Request, *args, **kwargs):
        """
        加签验签测试

            http code 200：
            {
                "xxx": "xxx",
                ...
            }
        """
        try:
            self.check_request_sign(request)
        except errors.Error as exc:
            return self.exception_response(exc)

        return Response(data=request.data)

    def get_serializer_class(self):
        return Serializer
