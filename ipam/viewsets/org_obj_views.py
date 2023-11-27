from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from drf_yasg.utils import swagger_auto_schema

from api.paginations import NewPageNumberPagination
from api.viewsets import NormalGenericViewSet
from ..handlers.org_obj_handlers import OrgVirtObjHandler
from .. import serializers


class OrgObjViewSet(NormalGenericViewSet):
    permission_classes = [IsAuthenticated, ]
    pagination_class = NewPageNumberPagination
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
        创建一个机构二级对象，需要有科技网管理员权限

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

    def get_serializer_class(self):
        if self.action == 'create':
            return serializers.OrgVirtObjCreateSerializer

        return Serializer
