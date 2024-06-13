from django.utils.translation import gettext_lazy
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema, no_body

from apps.app_probe.serializers import AppProbeSerializer
from apps.app_probe.handlers.handlers import ProbeHandlers
from apps.api.viewsets import NormalGenericViewSet, serializer_error_msg
from apps.app_probe.models import ProbeDetails
from core import errors as exceptions, errors


class ProbeViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = [IsAuthenticated, ]
    pagination_class = None

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询版本信息'),
        request_body=no_body,
        responses={
            200: ''
        }
    )
    @action(methods=['get'], detail=False, url_path='version', url_name='version')
    def version(self, request, *args, **kwargs):
        """
        查询版本信息

            {
              "version": 0,
              "server": "中国科技网"
            }
        """
        obj = ProbeDetails.get_instance()
        data = {'version': obj.version, 'server': obj.get_probe_type_display()}

        return Response(data=data, status=200)

    @swagger_auto_schema(
        operation_summary=gettext_lazy('更新探针服务信息'),
        responses={
            200: ''
        }
    )
    @action(methods=['post'], detail=False, url_path='submit', url_name='sbumit_probe')
    def sbumit_probe_website(self, request, *args, **kwargs):
        """
        通知更新服务配置信息

            {
              "operate": "string",  # 操作 add/update/delete
              "task": {
                "url": "string",    # 网址
                "url_hash": "string",  # 哈希值
                "is_tamper_resistant": false,  # 防篡改
              },
              "version": 0  # 版本号
            }

        """
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid(raise_exception=False):
            msg = serializer_error_msg(serializer.errors)
            exc = exceptions.BadRequest(message=msg)
            raise exc

        data = serializer.validated_data
        operate = data['operate']
        version = data['version']

        probehandler = ProbeHandlers()
        if operate == 'add':
            try:
                probehandler.add_probe_website(task=data['task'])
            except errors.Error as e:
                return self.exception_response(e)

        elif operate == 'update':

            try:
                probehandler.update_probe_website(task=data['task'], newtask=data['newtask'])
            except errors.Error as e:
                return self.exception_response(e)

        elif operate == 'delete':
            try:
                probehandler.delete_probe_website(task=data['task'])
            except errors.Error as e:
                return self.exception_response(e)

        else:
            return self.exception_response(f'operate 只有 add/update/delete ')

        probehandler.update_version(version=version)

        return Response(status=200)

    def get_serializer_class(self):

        if self.action == 'sbumit_probe_website':
            return AppProbeSerializer
        return Serializer
