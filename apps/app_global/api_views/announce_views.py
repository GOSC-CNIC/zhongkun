from django.utils.translation import gettext_lazy
from django.utils import timezone as dj_timezone
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema

from apps.api.viewsets import NormalGenericViewSet
from apps.api.paginations import NewPageNumberPagination100
from apps.app_global.models import Announcement
from apps.app_global import serializers


class AnnouncementViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举站内公告'),
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举站内公告

            http Code 200 Ok:
                {
                  "count": 1,
                  "page_num": 1,
                  "page_size": 100,
                  "results": [
                    {
                      "id": "dckfik4mnp2iwaefey42bup0s",
                      "name": "测试",
                      "name_en": "test",
                      "status": "publish",
                      "content": "这是测试\r\n\r\n佛山v参数V刹v我",
                      "creation_time": "2024-12-02T03:06:39.086033Z",
                      "update_time": "2024-12-02T06:06:21.123351Z",
                      "expire_time": null,
                      "publisher": {
                        "id": "8",
                        "username": "test@cnic.cn"
                      }
                    }
                  ]
                }
        """
        now_time = dj_timezone.now()
        qs = Announcement.objects.select_related('publisher').filter(
            status=Announcement.Status.PUBLISH.value
        ).filter(
            Q(expire_time__gt=now_time) | Q(expire_time__isnull=True)
        ).order_by('-creation_time')
        objs = self.paginate_queryset(queryset=qs)
        data = self.get_serializer(objs, many=True).data
        return self.get_paginated_response(data=data)

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.AnnouncementSerializer

        return Serializer
