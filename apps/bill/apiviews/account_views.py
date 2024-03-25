from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body

from api.viewsets import CustomGenericViewSet
from bill import trade_serializers
from bill.managers import PaymentManager
from core import errors
from vo.managers import VoManager


class BalanceAccountViewSet(CustomGenericViewSet):

    permission_classes = [IsAuthenticated, ]
    pagination_class = None
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询用户自己的余额账户'),
        request_body=no_body,
        manual_parameters=[
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='user', url_name='balance-user')
    def get_user_balance(self, request, *args, **kwargs):
        """
        查询用户自己的余额账户

            http code 200：
            {
              "id": "a2e83c96-b648-11ec-900f-c8009fe2eb10",
              "balance": "-219.15",
              "creation_time": "2022-04-07T07:59:22.867906Z",
              "user": {
                "id": "1"
              }
            }
        """
        account = PaymentManager().get_user_point_account(user_id=request.user.id)
        serializer = self.get_serializer(account)
        return Response(data=serializer.data)

    @action(methods=['get'], detail=False, url_path=r'vo/(?P<vo_id>.+)', url_name='balance-vo')
    def get_vo_balance(self, request, *args, **kwargs):
        """
        查询VO组的余额账户

            http code 200：
            {
              "id": "a2e83c96-b648-11ec-900f-c8009fe2eb10",
              "balance": "-219.15",
              "creation_time": "2022-04-07T07:59:22.867906Z",
              "vo": {
                "id": "1"
              }
            }
        """
        vo_id = kwargs.get('vo_id', None)
        if not vo_id:
            return self.exception_response(errors.InvalidArgument(_('参数vo_id无效')))

        try:
            VoManager().get_has_read_perm_vo(vo_id=vo_id, user=request.user)
        except errors.Error as exc:
            return self.exception_response(exc)

        account = PaymentManager().get_vo_point_account(vo_id=vo_id)
        serializer = self.get_serializer(account)
        return Response(data=serializer.data)

    def get_serializer_class(self):
        if self.action == 'get_vo_balance':
            return trade_serializers.VoPointAccountSerializer
        elif self.action == 'get_user_balance':
            return trade_serializers.UserPointAccountSerializer

        return Serializer
