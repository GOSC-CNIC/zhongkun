from django.utils.translation import gettext_lazy
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi

from core import errors
from api.viewsets import CustomGenericViewSet
from api import serializers
from adapters import inputs


class AvailabilityZoneViewSet(CustomGenericViewSet):

    permission_classes = [IsAuthenticated, ]
    pagination_class = None
    lookup_field = 'id'
    # lookup_value_regex = '[0-9a-z-]+'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('列举服务的可用区'),
        request_body=no_body,
        manual_parameters=[
            openapi.Parameter(
                name='service_id',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=True,
                description='服务端点id'
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        统计已发放的待使用的用户资源配额

            http code 200：
            {
              "zones": [
                {
                  "id": "nova",
                  "name": "nova"
                }
              ]
            }
        """
        try:
            service = self.get_service(request)
        except errors.APIException as exc:
            return Response(exc.err_data(), status=exc.status_code)

        params = inputs.ListImageInput(region_id=service.region_id)
        try:
            r = self.request_service(service, method='list_availability_zones', params=params)
        except errors.AuthenticationFailed as exc:
            return Response(data=exc.err_data(), status=500)
        except errors.APIException as exc:
            return Response(data=exc.err_data(), status=exc.status_code)

        serializer = serializers.AvailabilityZoneSerializer(r.zones, many=True)
        return Response(data={'zones': serializer.data})
