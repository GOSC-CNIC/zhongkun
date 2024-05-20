from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.app_screenvis.paginations import NewPageNumberPagination100
from apps.app_screenvis.utils import errors
from apps.app_screenvis.models import ServerServiceLog, ObjectServiceLog
from apps.app_screenvis.permissions import ScreenAPIIPPermission
from . import NormalGenericViewSet
from ..serializers import ServiceUserOperateLogSerializer


class UserOperateLogViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = [ScreenAPIIPPermission]
    pagination_class = NewPageNumberPagination100

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询云主机服务单元/对象存储服务单元用户操作日志信息'),
        manual_parameters=[
            openapi.Parameter(
                name='server_type',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description="object:对象存储；server:云主机服务单元;",
                enum=['server', 'object']
            ),
            openapi.Parameter(
                name='dc_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description=gettext_lazy('数据中心id')
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询云主机服务单元/对象存储服务单元用户操作日志信息

            200 ok:
            {
                "count": 2,
                "page_num": 1,
                "page_size": 100,
                "results": [
                    {
                        "creation_time": "2024-05-14T08:48:08.646606Z",
                        "username": "user2",
                        "content": "test serfver2"
                    }
                ]
            }
        """
        server_type = request.query_params.get('server_type', None)
        dc_id = request.query_params.get('dc_id', None)

        if not server_type:
            return self.exception_response(errors.BadRequest(message=_('请指定查询服务类型')))

        if server_type not in ['object', 'server']:
            return self.exception_response(errors.InvalidArgument(message=_('指定查询服务类型无效')))

        if dc_id:
            try:
                dc_id = int(dc_id)
            except ValueError:
                return self.exception_response(errors.InvalidArgument(message=_('数据中心无效')))

        if server_type == 'server':
            queryset = ServerServiceLog.objects.order_by('-creation_time').all()
            if dc_id:
                queryset = queryset.filter(service_cell__data_center_id=dc_id)
        else:
            queryset = ObjectServiceLog.objects.order_by('-creation_time').all()
            if dc_id:
                queryset = queryset.filter(service_cell__data_center_id=dc_id)

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
