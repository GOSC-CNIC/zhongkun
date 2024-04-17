from django.utils.translation import gettext_lazy
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from drf_yasg.utils import swagger_auto_schema
from apps.api.viewsets import NormalGenericViewSet
from apps.app_probe.models import ProbeDetails


class ProbeViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = []

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询版本信息'),
        manual_parameters=[],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        obj = ProbeDetails.get_instance()

        data = {'version': obj.version, 'server': obj.get_probe_type_display()}

        return Response(data=data, status=200)

    def get_serializer_class(self):
        return Serializer
