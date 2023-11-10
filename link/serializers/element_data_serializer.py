from link.serializers.leaseline_serializer import LeaseLineSerializer
from link.serializers.connectorbox_serializer import ConnectorBoxSerializer
from link.serializers.opticalfiber_serializer import OpticalFiberSerializer
from link.serializers.distriframeport_serializer import DistriFramePortSerializer
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

class ElementDataSerializer(serializers.Serializer):
    type = serializers.CharField(max_length=32, label='网元类型', read_only=True)
    lease = LeaseLineSerializer()
    port = DistriFramePortSerializer()
    fiber = OpticalFiberSerializer()
    box = ConnectorBoxSerializer()
