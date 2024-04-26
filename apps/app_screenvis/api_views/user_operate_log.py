from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.api.paginations import DefaultPageNumberPagination
from apps.app_screenvis.utils import errors
from apps.app_screenvis.models import  ServerServiceLog, ObjectServiceLog
from apps.app_screenvis.permissions import ScreenAPIIPPermission
from . import NormalGenericViewSet
from ..serializers import ServiceUserOperateLogSerializer


class UserOperateLogViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = [ScreenAPIIPPermission]
    pagination_class = DefaultPageNumberPagination

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询云主机服务单元/对象存储服务单元用户操作日志信息'),
        manual_parameters=[
            openapi.Parameter(
                name='server_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"iharbor:对象存储；evcloud:云服务单元;",
                enum=['iharbor', 'evcloud',]
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询云主机服务单元/对象存储服务单元用户操作日志信息

        """

        server_type = request.query_params.get('server_type', None)

        if not server_type:
            return self.exception_response(errors.BadRequest(message=_('请指定查询服务类型')))


        if server_type == 'evcloud':
            queryset = ServerServiceLog.objects.all()

        else:
            queryset = ObjectServiceLog.objects.all()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=200)


    def get_serializer_class(self):
        if self.action == 'list':
            return ServiceUserOperateLogSerializer
        return Serializer
