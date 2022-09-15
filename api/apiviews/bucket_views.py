from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.viewsets import StorageGenericViewSet
from api.paginations import DefaultPageNumberPagination
from api.serializers import storage as storage_serializers
from api.handlers import BucketHandler


class BucketViewSet(StorageGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'bucket_name'
    # lookup_value_regex = '[^/]+'

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
                "username": "shun",
                "service": {
                    "id": "4fa94896-29a6-11ed-861f-c8009fe2ebbc",
                    "name": "test iharbor",
                    "name_en": "en iharbor"
                }
            }
            http code 400, 404, 409, 500：
            {
                "code": "BucketAlreadyExists",
                "message": "存储桶已存在，请更换另一个存储桶名程后再重试。"
            }

            * code:
            400：
                InvalidName: 无效的存储桶名
            404：
                ServiceNotExist： 资源提供者服务单元不存在。
            409：
                BucketAlreadyExists：存储桶已存在，请更换另一个存储桶名程后再重试。
                BalanceNotEnough: 创建存储桶要求余额或代金券余额大于100
                ServiceStopped: 资源提供者服务单元暂停服务
            500：
                Adapter.AuthenticationFailed：请求服务单元时身份认证失败
                Adapter.AccessDenied: 请求服务单元时无权限
                Adapter.BadRequest: 请求服务单元时请求有误
                Adapter.BucketAlreadyExists: 存储桶已存在，请更换另一个存储桶名程后再重试。
        """
        return BucketHandler().create_bucket(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('删除指定服务单元中的一个存储桶'),
        responses={
            200: ''
        }
    )
    @action(methods=['DELETE'], detail=True, url_path=r'service/(?P<service_id>[^/]+)', url_name='delete-bucket')
    def delete_bucket(self, request, *args, **kwargs):
        """
        删除指定服务单元中的一个存储桶

            http code 204：
            {}
            http code 400, 404, 409, 500：
            {
                "code": "BucketNotExist",
                "message": "存储桶不存在"
            }

            * code:
            404：
                ServiceNotExist： 资源提供者服务单元不存在。
            409：
                BucketNotExist：存储桶不存在
                ServiceStopped: 资源提供者服务单元暂停服务
            500：
                Adapter.AuthenticationFailed：请求服务单元时身份认证失败
                Adapter.AccessDenied: 请求服务单元时无权限
                Adapter.BadRequest: 请求服务单元时请求有误
        """
        return BucketHandler().delete_bucket(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举存储桶'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                required=False,
                type=openapi.TYPE_STRING,
                description=gettext_lazy('对象存储服务单元ID')
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举存储桶

            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "2b03fd40-33cb-11ed-aec0-c8009fe2ebbc",
                  "name": "string1",
                  "creation_time": "2022-09-14T01:18:40.166221Z",
                  "user_id": "1",
                  "username": "shun",
                  "service": {
                    "id": "4fa94896-29a6-11ed-861f-c8009fe2ebbc",
                    "name": "test iharbor",
                    "name_en": "en iharbor"
                  }
                }
              ]
            }
        """
        return BucketHandler.list_bucket(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return storage_serializers.BucketSerializer
        elif self.action == 'create':
            return storage_serializers.BucketCreateSerializer

        return Serializer
