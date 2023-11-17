from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema

from core import errors
from service.models import DataCenter as Organization
from ..paginations import NewPageNumberPagination100
from ..serializers import org_serializers


class OrganizationViewSet(GenericViewSet):
    """
    机构
    """
    queryset = []
    permission_classes = [IsAuthenticated]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举机构'),
        responses={200: ''}
    )
    def list(self, request, *args, **kwargs):
        """
        列举机构

            Http Code: 状态码200，返回数据：
            {
              "count": 266,
              "page_num": 1,
              "page_size": 100,
              "results": [
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
            queryset = Organization.objects.order_by('-creation_time')
            orgs = self.paginate_queryset(queryset)
            serializer = org_serializers.OrganizationSerializer(orgs, many=True)
            return self.get_paginated_response(serializer.data)
        except Exception as exc:
            err = errors.APIException(message=str(exc))
            return Response(err.err_data(), status=err.status_code)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询机构详细信息'),
        responses={200: ''}
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询机构详细信息，暂时只允许联邦管理员访问

            http code 200:
            {
              "id": "e96de454-a342-11ec-992b-c8009fe2eb03",
              "name": "中科院空天院",
              "name_en": "National Space Science Center (NSSC)",
              "abbreviation": "中科院空天院",
              "creation_time": "2023-10-25T08:05:00Z",
              "desc": "",
              "longitude": 0,
              "latitude": 0,
              "sort_weight": 0,
              "contacts": [
                {
                  "id": "9csaaucjc00h57jo7u751rqqm",
                  "name": "张三",
                  "telephone": "123456",
                  "email": "zhangsan@cnic.cn",
                  "address": "中国广东省广州市越秀区先烈中路100号",
                  "creation_time": "2023-10-25T08:34:00Z",
                  "update_time": "2023-10-25T08:34:00Z",
                  "remarks": ""
                }
              ]
            }
        """
        if not request.user.is_federal_admin():
            exc = errors.AccessDenied(message=_('只允许联邦管理员访问'))
            return Response(data=exc.err_data(), status=exc.status_code)

        org = Organization.objects.filter(id=kwargs[self.lookup_field]).first()
        if org is None:
            exc = errors.TargetNotExist(message=_('未找到指定的机构'))
            return Response(data=exc.err_data(), status=exc.status_code)

        data = org_serializers.OrganizationSerializer(instance=org).data
        contacts_qs = org.contacts.all()
        contacts = org_serializers.ContactSerializer(instance=contacts_qs, many=True).data
        data['contacts'] = contacts
        return Response(data=data)
