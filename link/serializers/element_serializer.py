from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from link.models import ElementLink
from link.managers.element_manager import ElementManager
class ElementBaseSerializer(serializers.Serializer):
    is_linked = serializers.SerializerMethodField(label=_('接入链路'), method_name='get_is_linked', read_only=True)
    element_id = serializers.CharField(label='网元ID', max_length=36, read_only=True)
    @staticmethod
    def get_is_linked(obj):
        return ElementManager.is_linked(obj.element_id)