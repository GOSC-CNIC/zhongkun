from api.viewsets import NormalGenericViewSet
from django.utils.translation import gettext_lazy, gettext as _
from api.paginations import NewPageNumberPagination
from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from core import errors
from api.handlers.handlers import serializer_error_msg
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from link.serializers.leaseline_serializers import LeaseLineSerializer
from link.managers import userrole_managers, leaseline_managers

class LeaseLineViewSet(NormalGenericViewSet):
    """
    租用线路视图
    """
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建租用线路'),
        responses={
            200: '''
                {
                    "order_id": "xxx",      # 订单id
                }
            '''
        }
    )
    def create(self, request, *args, **kwargs):
        try:
            data = self._create_validate_params(request=request)
        except Exception as exc:
            return self.exception_response(exc)
        ur_wrapper = userrole_managers.UserRoleWrapper(user=request.user)
        if not ur_wrapper.has_write_permission():
            return self.exception_response(errors.AccessDenied(message=_('你没有科技网链路管理功能的编辑权限')))
        leaseline = leaseline_managers.LeaseLineManager.create_leaseline(
            private_line_number=data['private_line_number'],
            lease_line_code=data['lease_line_code'],
            line_username=data['line_username'],
            endpoint_a=data['endpoint_a'],
            endpoint_z=data['endpoint_z'],
            line_type=data['line_type'],
            cable_type=data['cable_type'],
            bandwidth=data['bandwidth'],
            length=data['length'],
            provider=data['provider'],
            enable_date=data['enable_date'],
            is_whithdrawal=data['is_whithdrawal'],
            money=data['money'],
            remarks=data['remarks']
        )


        return Response(data=LeaseLineSerializer(instance=leaseline).data)


    def _create_validate_params(self, request):
        """
        :raises: Error
        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            raise errors.BadRequest(message=msg)

        data = serializer.validated_data
        return data
    def get_serializer_class(self):
        if self.action in ['create', ]:
            return LeaseLineSerializer

        return Serializer