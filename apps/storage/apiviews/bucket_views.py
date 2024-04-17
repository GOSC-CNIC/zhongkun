from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from apps.api.viewsets import StorageGenericViewSet
from apps.api.paginations import DefaultPageNumberPagination
from apps.storage.bucket_handler import BucketHandler
from apps.storage import serializers as storage_serializers


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
                BalanceNotEnough: 创建存储桶要求余额或资源券余额大于100
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

            http code 204：无响应数据
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
                  },
                  "storage_size": 66347638,
                  "object_count": 456,
                  "stats_time": "2022-10-27T08:09:26.911670Z"
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


class AdminBucketViewSet(StorageGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = DefaultPageNumberPagination
    lookup_field = 'bucket_name'
    # lookup_value_regex = '[^/]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员列举存储桶'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                required=False,
                type=openapi.TYPE_STRING,
                description=gettext_lazy('对象存储服务单元ID')
            ),
            openapi.Parameter(
                name='user_id',
                in_=openapi.IN_QUERY,
                required=False,
                type=openapi.TYPE_STRING,
                description=gettext_lazy('查询指定用户的桶')
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        管理员列举存储桶

            {
              "count": 1,
              "next": null,
              "previous": null,
              "results": [
                {
                  "id": "3a642594-59be-11ed-83d1-c8009fe2ebbc",
                  "name": "test2",
                  "creation_time": "2022-10-27T08:09:26.911670Z",
                  "user_id": "1",
                  "username": "shun",
                  "service": {
                    "id": "2cd1d0a8-388e-11ed-bbc7-c8009fe2ebbc",
                    "name": "开发环境",
                    "name_en": "dev"
                  },
                  "task_status": "created", # created:创建成功; creating:正在创建中; failed:创建失败
                  "situation": "normal",    # normal(正常), arrearage(欠费), arrears-lock(欠费锁定读写), lock(锁定读写), lock-write(锁定写（只读）)
                  "situation_time": null,
                  "storage_size": 66347638, # byte
                  "object_count": 456,
                  "stats_time": "2022-10-27T08:09:26.911670Z"
                }
              ]
            }
        """
        return BucketHandler.admin_list_bucket(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员查询存储桶统计信息'),
        responses={
            200: ''
        }
    )
    @action(methods=['GET'], detail=True, url_path=r'stats/service/(?P<service_id>[^/]+)', url_name='stats-bucket')
    def stats_bucket(self, request, *args, **kwargs):
        """
        管理员查询存储桶统计信息

            {
              "bucket": {
                "id": "3a642594-59be-11ed-83d1-c8009fe2ebbc",
                "name": "test2",
                "service_id": "2cd1d0a8-388e-11ed-bbc7-c8009fe2ebbc",
                "service_name": "开发环境"
              },
              "stats": {
                "objects_count": 2,
                "bucket_size_byte": 72975,
                "stats_time": "2023-04-13T15:33:59.615146+08:00"
              }
            }
        """
        return BucketHandler.admin_stats_bucket(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员删除存储桶'),
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='存储服务单元id'
            )
        ],
        responses={
            204: ''
        }
    )
    def destroy(self, request, *args, **kwargs):
        """
        管理员删除存储桶

            http code 204：无响应数据
            http code 400, 403, 404, 500：
            {
                "code": "BucketNotExist",
                "message": "存储桶不存在"
            }

            * code:
            400：
                InvalidArgument： 存储服务单元id未指定。
            403：
                AccessDenied：没有存储桶的管理权限
            404：
                BucketNotExist：存储桶不存在
            500：
                Adapter.AuthenticationFailed：请求服务单元时身份认证失败
                Adapter.AccessDenied: 请求服务单元时无权限
                Adapter.BadRequest: 请求服务单元时请求有误
        """
        return BucketHandler.admin_delete_bucket(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('管理员加锁或解锁存储桶'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='存储服务单元id'
            ),
            openapi.Parameter(
                name='action',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f'{BucketHandler.LockActionChoices.choices}'
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['POST'], detail=True, url_path='lock', url_name='lock')
    def bucket_lock(self, request, *args, **kwargs):
        """
        管理员加锁或解锁存储桶

            http code 204：无响应数据
            http code 400, 403, 404, 500：
            {
                "code": "BucketNotExist",
                "message": "存储桶不存在"
            }

            * code:
            400：
                MissingParam：存储服务单元id未指定 / 必须指定操作选项 /
                InvalidArgument：操作选项无效
            403：
                AccessDenied：没有存储桶的管理权限
            404：
                BucketNotExist：存储桶不存在
            500：
                Adapter.AuthenticationFailed：请求服务单元时身份认证失败
                Adapter.AccessDenied: 请求服务单元时无权限
                Adapter.BadRequest: 请求服务单元时请求有误
        """
        return BucketHandler.admin_lock_bucket(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return storage_serializers.AdminBucketSerializer

        return Serializer
