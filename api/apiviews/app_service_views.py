from django.utils.translation import gettext_lazy
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import CustomGenericViewSet
from api.paginations import NewPageNumberPagination
from api.serializers import trade as trade_serializers
from bill.models import PayAppService


class AppServiceViewSet(CustomGenericViewSet):
    """
    app子服务
    """
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举app子服务'),
        manual_parameters=[
            openapi.Parameter(
                name='app_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='查询指定app的子服务'
            ),
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举有管理权限的 app子服务

            http code 200：
            {
              "count": 1,
              "page_num": 1,
              "page_size": 20,
              "results": [
                {
                  "id": "s20220623023119",
                  "name": "怀柔204机房研发测试",
                  "name_en": "怀柔204机房研发测试",
                  "resources": "云主机，云硬盘",
                  "desc": "",
                  "creation_time": "2022-06-23T07:35:44.784474Z",
                  "status": "normal",
                  "contact_person": "",
                  "contact_email": "",
                  "contact_telephone": "",
                  "contact_fixed_phone": "",
                  "contact_address": "",
                  "longitude": 0,
                  "latitude": 0,
                  "category": "vms-server",
                  "orgnazition": {
                    "id": "o20220623073034",
                    "name": "网络中心",
                    "name_en": "cnic"
                  },
                  "app_id": "20220622082141"
                }
              ]
            }
        """
        app_id = request.query_params.get('app_id', None)

        lookups = {}
        if app_id:
            lookups['app_id'] = app_id

        user_id = request.user.id
        queryset = PayAppService.objects.select_related(
            'orgnazition'
        ).filter(**lookups).filter(Q(user_id=user_id) | Q(service__users__id=user_id))

        try:
            tickets = self.paginate_queryset(queryset=queryset)
            serializer = self.get_serializer(tickets, many=True)
            return self.get_paginated_response(data=serializer.data)
        except Exception as exc:
            return self.exception_response(exc)

    def get_serializer_class(self):
        if self.action == 'list':
            return trade_serializers.AppServiceSerializer

        return Serializer
