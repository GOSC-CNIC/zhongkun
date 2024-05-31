from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.response import Response
from rest_framework.decorators import action
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from utils.paginators import NoPaginatorInspector
from apps.api.paginations import NewPageNumberPagination100
from apps.api.viewsets import NormalGenericViewSet
from apps.app_netbox.serializers import common as common_serializers
from apps.app_netbox.handlers.common_handlers import OrgVirtObjHandler, ContactsHandler
from apps.app_net_ipam.managers import NetIPamUserRoleWrapper
from apps.app_net_link.managers import NetLinkUserRoleWrapper
from apps.app_net_ipam.serializers import NetIPamUserRoleSerializer


class NetBoxUserRoleViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询用户在netbox中用户角色和权限'),
        paginator_inspectors=[NoPaginatorInspector],
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询用户在netbox中用户角色和权限

            http Code 200 Ok:
                {
                  "id": "c89od410t7hwsejr11tyv52w9",
                  "is_ipam_admin": false,
                  "is_ipam_readonly": true,
                  "is_link_admin": "false",
                  "is_link_readonly": true,
                  "creation_time": "2023-10-18T06:13:00Z",
                  "update_time": "2023-10-18T06:13:00Z",
                  "user": {
                    "id": "1",
                    "username": "shun"
                  },
                  "organizations": [    # 有ipam管理权限的 机构
                    {
                      "id": "b75r1144s5ucku15p6shp9zgf",
                      "name": "中国科学院计算机网络信息中心",
                      "name_en": "中国科学院计算机网络信息中心"
                    }
                  ]
                }
        """
        urw = NetIPamUserRoleWrapper(user=request.user)
        user_role = urw.user_role
        data = NetIPamUserRoleSerializer(instance=user_role).data
        orgs = user_role.organizations.all().values('id', 'name', 'name_en')
        data['organizations'] = orgs
        link_urw = NetLinkUserRoleWrapper(user=request.user)
        data['is_link_admin'] = link_urw.user_role.is_link_admin
        data['is_link_readonly'] = link_urw.user_role.is_link_readonly
        return Response(data=data)

    def get_serializer_class(self):
        return Serializer


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

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询一个机构二级对象详情'),
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """
        查询一个机构二级对象详情，需要有IP或者链路管理员权限

            http Code 200 Ok:
                {
                  "id": "s627ofyoeez9x0sacuj1hetj4",
                  "name": "北京天文馆",
                  "creation_time": "2023-11-29T03:18:05.437407Z",
                  "remark": "",
                  "organization": {
                    "id": "s620vv6s7rwioxjc5nxfftxx4",
                    "name": "北京天文馆",
                    "name_en": "北京天文馆"
                  },
                  "contacts": [     # 联系人列表
                    {
                      "id": "piwja1h9z6v0tuubu8auu7y4z",
                      "name": "李四",
                      "telephone": "123456",
                      "email": "zhangsan@cnic.cn",
                      "address": "中国广东省广州市越秀区先烈中路100号",
                      "remarks": "",
                      "creation_time": "2024-01-12T01:20:51.091027Z",
                      "update_time": "2024-01-12T01:20:51.091027Z"
                    }
                  ]
                }

            Http Code 401, 403, 500:
                {
                    "code": "AccessDenied",
                    "message": "你没有科技网IP管理功能的管理员权限"
                }
        """
        return OrgVirtObjHandler().detail_org_virt_obj(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('机构二级添加联系人'),
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='add/contacts', url_name='add-contacts')
    def add_contacts(self, request, *args, **kwargs):
        """
        机构二级添加联系人，需要有IP或者链路管理员权限

            http code 200:
                {
                  "id": "s627ofyoeez9x0sacuj1hetj4",
                  "name": "北京天文馆",
                  "creation_time": "2023-11-29T03:18:05.437407Z",
                  "remark": "",
                  "organization": {
                    "id": "s620vv6s7rwioxjc5nxfftxx4",
                    "name": "北京天文馆",
                    "name_en": "北京天文馆"
                  },
                  "contacts": [     # 联系人列表
                    {
                      "id": "piwja1h9z6v0tuubu8auu7y4z",
                      "name": "李四",
                      "telephone": "123456",
                      "email": "zhangsan@cnic.cn",
                      "address": "中国广东省广州市越秀区先烈中路100号",
                      "remarks": "",
                      "creation_time": "2024-01-12T01:20:51.091027Z",
                      "update_time": "2024-01-12T01:20:51.091027Z"
                    }
                  ]
                }

            http code 400, 401, 404：
            {
                "code": "BadRequest",
                "message": ""
            }
        """
        return OrgVirtObjHandler().add_contacts(view=self, request=request, kwargs=kwargs)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('机构二级移除联系人'),
        manual_parameters=[],
        responses={
            200: ''''''
        }
    )
    @action(methods=['POST'], detail=True, url_path='remove/contacts', url_name='remove-contacts')
    def remove_contacts(self, request, *args, **kwargs):
        """
        机构二级移除联系人，需要有IP或者链路管理员权限

            http code 200


            http code 400, 401, 404：
            {
                "code": "BadRequest",
                "message": ""
            }
        """
        return OrgVirtObjHandler().remove_contacts(view=self, request=request, kwargs=kwargs)

    def get_serializer_class(self):
        if self.action in ['create', 'update']:
            return common_serializers.OrgVirtObjCreateSerializer
        elif self.action in ['add_contacts', 'remove_contacts']:
            return common_serializers.OrgVOContactsPostSerializer

        return Serializer


class ContactPersonViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination100
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举机构二级联系人'),
        manual_parameters=[
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='关键字查询，查询姓名、电话、邮箱'
            ),
        ],
        responses={
            200: ''''''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        列举机构二级联系人，需要有IP或者链路管理员权限

            http Code 200 Ok:
                {
                    "count": 1,
                    "page_num": 1,
                    "page_size": 100,
                    "results": [
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
                    ]
                }

            Http Code 401, 403, 500:
                {
                    "code": "AccessDenied",
                    "message": "你没有IP或者链路的管理员权限"
                }
        """
        return ContactsHandler().list_contact_person(view=self, request=request)

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
        if self.action in ['create', 'update', 'list']:
            return common_serializers.ContactPersonSerializer

        return Serializer
