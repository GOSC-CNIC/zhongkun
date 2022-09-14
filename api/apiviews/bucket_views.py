from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from api.viewsets import StorageGenericViewSet
from api.paginations import PageNumberPagination
from api.serializers import storage as storage_serializers
from api.handlers import BucketHandler


class BucketViewSet(StorageGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = PageNumberPagination
    lookup_field = 'bucket_name'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('指定服务单元创建一个存储桶'),
        responses={
            200: ''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        指定服务单元创建一个存储桶

            http code 200：
            {
                "id": "264add9c-3348-11ed-b732-c8009fe2ebbc",
                "name": "string",
                "creation_time": "2022-09-13T09:40:49.144926Z",
                "user_id": "1",
                "service": {
                    "id": "4fa94896-29a6-11ed-861f-c8009fe2ebbc",
                    "name": "test iharbor",
                    "name_en": "en iharbor"
                }
            }
        """
        return BucketHandler().create_bucket(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'create':
            return storage_serializers.BucketCreateSerializer

        return Serializer
