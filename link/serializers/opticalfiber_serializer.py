from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from link.serializers.element_serializer import ElementBaseSerializer

class OpticalFiberSerializer(ElementBaseSerializer):
    id = serializers.CharField(label='ID', max_length=36, read_only=True)
    sequence = serializers.IntegerField(label=_('纤序'), read_only=True)
    fiber_cable = serializers.SerializerMethodField(label=_('光缆'), method_name='get_fibercable')

    @staticmethod
    def get_fibercable(obj):
        fibercable = obj.fiber_cable
        if fibercable is not None:
            return {'id': fibercable.id, 'number': fibercable.number}

        return None