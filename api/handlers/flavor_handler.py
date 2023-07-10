from django.utils.translation import gettext as _
from rest_framework.response import Response

from core import errors as exceptions
from servers.models import Flavor
from api.viewsets import CustomGenericViewSet
from api.serializers import serializers


class FlavorHandler:
    @staticmethod
    def list_flavors(view: CustomGenericViewSet, request, kwargs):
        service_id = request.query_params.get('service_id', None)
        try:
            flavors = Flavor.objects.filter(service_id=service_id, enable=True).order_by('vcpus', 'ram').all()
            serializer = serializers.FlavorSerializer(flavors, many=True)
        except Exception as exc:
            return view.exception_response(
                exceptions.APIException(message=str(exc)))

        return Response(data={"flavors": serializer.data})
