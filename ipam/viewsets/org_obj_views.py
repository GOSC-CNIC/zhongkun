from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from api.paginations import NewPageNumberPagination100
from api.viewsets import NormalGenericViewSet
from ..handlers.org_obj_handlers import OrgVirtObjHandler, ContactsHandler
from .. import serializers


class OrgObjViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建一个机构二级对象'),
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建一个机构二级对象，需要有IP或者链路管理员权限

            http Code 200 Ok:
                {
                    'id': 'djb42nk0q43g8vkqiqnvx3cd2',
                    'name': 'test测试',
                    'creation_time': '2023-11-27T02:12:45.958061Z',
                    'remark': '备注test',
                    'organization': {
                        'id': 'diu63qgib1vzvur3dye7n4dah',
                        'name': 'test',
                        'name_en': 'test_en'
                    }
                }

            Http Code 400, 403, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                InvalidArgument: 参数无效

                403:
                AccessDenied: 你没有科技网IP管理功能的管理员权限
        """
        return OrgVirtObjHandler().add_org_virt_obj(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举机构二级对象'),
        manual_parameters=[
            openapi.Parameter(
                name='org_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='机构id'
            ),
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='关键字查询，查询名称和备注'
            ),
        ],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举机构二级对象，需要有IP或者链路管理员读权限

            http Code 200 Ok:
                {
                    "count": 1,
                    "page_num": 1,
                    "page_size": 100,
                    "results": [
                        {
                            "id": "djb42nk0q43g8vkqiqnvx3cd2",
                            "name": "test测试",
                            "creation_time": "2023-11-27T02:12:45.958061Z",
                            "remark": "备注test",
                            "organization": {
                                "id": "diu63qgib1vzvur3dye7n4dah",
                                "name": "test",
                                "name_en": "test_en"
                            }
                        }
                    ]
                }

            Http Code 403:
                {
                    "code": "AccessDenied",
                    "message": "你没有科技网IP管理功能的管理员权限"
                }
        """
        return OrgVirtObjHandler.list_org_virt_obj(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改一个机构二级对象'),
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        修改一个机构二级对象，需要有IP或者链路管理员权限

            http Code 200 Ok:
                {
                    'id': 'djb42nk0q43g8vkqiqnvx3cd2',
                    'name': 'test测试',
                    'creation_time': '2023-11-27T02:12:45.958061Z',
                    'remark': '备注test',
                    'organization': {
                        'id': 'diu63qgib1vzvur3dye7n4dah',
                        'name': 'test',
                        'name_en': 'test_en'
                    }
                }

            Http Code 400, 403, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                InvalidArgument: 参数无效

                403:
                AccessDenied: 你没有科技网IP管理功能的管理员权限
        """
        return OrgVirtObjHandler().update_org_virt_obj(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return serializers.OrgVirtObjCreateSerializer

        return Serializer


class ContactPersonViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('创建一个机构二级联系人'),
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def create(self, request, *args, **kwargs):
        """
        创建一个机构二级联系人，需要有IP或者链路管理员权限

            http Code 200 Ok:
                {
                  "id": "hw1gxxrk4xxuhh0reh22r3ns4",
                  "name": "张三",
                  "telephone": "xxx",
                  "email": "xxx",
                  "address": "xxx",
                  "remarks": "xxx",
                  "creation_time": "2024-01-11T08:37:05.653346Z",
                  "update_time": "2024-01-11T08:37:05.653346Z"
                }

            Http Code 400, 403, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                InvalidArgument: 参数无效

                403:
                AccessDenied: 你没有IP或者链路的管理员权限
        """
        return ContactsHandler().add_contact_person(view=self, request=request)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('修改一个机构二级联系人'),
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def update(self, request, *args, **kwargs):
        """
        修改一个机构二级联系人，需要有IP或者链路管理员权限

            http Code 200 Ok:
                {
                  "id": "hw1gxxrk4xxuhh0reh22r3ns4",
                  "name": "张三",
                  "telephone": "xxx",
                  "email": "xxx",
                  "address": "xxx",
                  "remarks": "xxx",
                  "creation_time": "2024-01-11T08:37:05.653346Z",
                  "update_time": "2024-01-11T08:37:05.653346Z"
                }

            Http Code 400, 403, 500:
                {
                    "code": "BadRequest",
                    "message": "xxxx"
                }

                可能的错误码：
                400:
                InvalidArgument: 参数无效

                403:
                AccessDenied: 你没有IP或者链路的管理员权限
        """
        return ContactsHandler().update_contact_person(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return serializers.ContactPersonSerializer

        return Serializer
