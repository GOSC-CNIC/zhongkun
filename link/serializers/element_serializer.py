from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
class ElementBaseSerializer(serializers.Serializer):
    is_linked = serializers.BooleanField(label=_('接入链路'), read_only=True)
    element_id = serializers.CharField(label=_('网元ID'), max_length=36, read_only=True)
    link_id = serializers.ListField(label=_('链路ID数组'), read_only=True, child=serializers.CharField(label=_('链路ID'), max_length=36))
    @staticmethod
    def get_link_id(obj):

        return None
