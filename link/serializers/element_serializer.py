from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from link.models import ElementLink

class ElementBaseSerializer(serializers.Serializer):
    is_linked = serializers.SerializerMethodField(label=_('接入链路'), method_name='get_is_linked', read_only=True)

    @staticmethod
    def get_is_linked(obj):
        if obj.element_id is not None:
            elementLink = ElementLink.objects.filter(element_ids__icontains=obj.element_id)
            return elementLink.exists()
        return False