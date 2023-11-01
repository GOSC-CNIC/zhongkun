from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

class ElementLinkSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=64, label=_('链路编号'), allow_blank=False, allow_null=False, required=True)
    remarks = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, allow_null=True, required=False, default='')
    link_status = serializers.CharField(label=_('链路状态'), max_length=16, allow_blank=True, allow_null=True, required=False, default='')
    task = serializers.SerializerMethodField(label=_('业务'), method_name='get_task', read_only=True)
    element_id_list = serializers.SerializerMethodField(label=_('链路网元ID'), method_name='get_element_id_list', read_only=True)

    @staticmethod
    def get_task(obj):
        task = obj.task
        if task is not None:
            return {'id': task.id, 'number': task.number, 'user': task.user}
        return None

    @staticmethod
    def get_element_id_list(obj):
        return obj.element_id_list()