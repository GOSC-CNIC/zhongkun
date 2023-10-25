from django.utils.translation import gettext_lazy
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from core import errors
from service.models import DataCenter
from ..paginations import NewPageNumberPagination100
from ..serializers import org_serializers


class OrganizationViewSet(GenericViewSet):
    """
    机构
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination100

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举机构'),
        responses={200: ''}
    )
    def list(self, request, *args, **kwargs):
        """
        列举机构

            Http Code: 状态码200，返回数据：
            {
              "registries": [
                {
                  "id": "9c70cbe2c8009fe2eb10",
                  "name": "网络中心",
                  "name_en": "string",
                  "abbreviation": "xxx"
                  "creation_time": 2021-02-07T06:20:00Z,
                  "desc": "",
                  "longitude": 0,
                  "latitude": 0,
                  "sort_weight": 6                        # 排序值，由小到大
                }
              ]
            }
        """
        try:
            queryset = DataCenter.objects.order_by('-creation_time')
            orgs = self.paginate_queryset(queryset)
            serializer = org_serializers.OrganizationSerializer(orgs, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as exc:
            err = errors.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)
