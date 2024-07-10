from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.app_screenvis.managers import ScreenWebMonitorManager, WebQueryChoices
from apps.app_screenvis.utils import errors
from apps.app_screenvis.permissions import ScreenAPIIPPermission
from apps.app_screenvis.models import WebsiteMonitorTask
from . import NormalGenericViewSet


class WebsiteMonitorViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = [ScreenAPIIPPermission]
    pagination_class = None
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询站点监控实时信息'),
        manual_parameters=[
            openapi.Parameter(
                name='query',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description=f"{WebQueryChoices.choices}",
                enum=WebQueryChoices.values
            )
        ],
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='query', url_name='query')
    def query(self, request, *args, **kwargs):
        """
        查询站点监控实时信息

            Http Code: 状态码200，返回数据格式最外层key-value格式，key是查询指标参数值，value是单个查询指标的数据：
            {
                "tasks": [      # url监控任务列表
                    {
                      "id": "3i2o4ouiei72p871uqtshh4io",
                      "name": "test1",
                      "url": "https://tes6t2.com",
                      "url_hash": "72564636674e26802b61e5ec4893a5e40bd698f0",
                      "is_tamper_resistant": true
                    }
                ],
                "http_duration_seconds": [     # 数组，可能为空，单项，多项
                    {"metric": {}, "value": [1718864229.841, "0.150246683"]},   # 一个url http请求过程中单个细分过程耗时
                ],
                'duration_seconds' [
                    {"metric": {}, "value": [1718864229.841, "0.150246683"]},   # 一个url http请求总耗时
                ]
            }
        """
        query = request.query_params.get('query', None)

        if query is None:
            return self.exception_response(errors.BadRequest(message=_('必须指定查询指标')))

        if query not in WebQueryChoices.values:
            return self.exception_response(errors.InvalidArgument(message=_('指定查询指标无效')))

        try:
            data = ScreenWebMonitorManager().query(tag=query)
        except errors.Error as exc:
            return self.exception_response(exc)

        ret_data = data
        tasks = WebsiteMonitorTask.objects.all().values('id', 'name', 'url', 'url_hash', 'is_tamper_resistant')
        ret_data['tasks'] = list(tasks)
        return Response(data=ret_data, status=200)

    def get_serializer_class(self):
        return Serializer
