from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
class ElementBaseSerializer(serializers.Serializer):
    is_linked = serializers.BooleanField(label=_('接入链路'), read_only=True)
    element_id = serializers.CharField(label='网元ID', max_length=36, read_only=True)