from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.core.validators import MinValueValidator

class TaskSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=36, label='ID', read_only=True)
    number = serializers.CharField(max_length=128, label=_('业务编号'), allow_blank=False, allow_null=False, required=True)
    endpoint_a = serializers.CharField(max_length=255, label=_('A端'), allow_blank=False, allow_null=False, required=True)
    endpoint_z = serializers.CharField(max_length=255, label=_('Z端'), allow_blank=False, allow_null=False, required=True)
    bandwidth = serializers.IntegerField(label=_('带宽'), validators=(MinValueValidator(0),), default=None, allow_null=True, required=False)
    task_description = serializers.CharField(max_length=255, label=_('业务描述'), allow_blank=False, allow_null=False, required=True)
    line_type = serializers.CharField(max_length=36, label=_('线路类型'), allow_blank=False, allow_null=False, required=True)
    task_person = serializers.CharField(max_length=36, label=_('商务对接'), allow_blank=False, allow_null=False, required=True)
    build_person = serializers.CharField(max_length=36, label=_('线路搭建'), allow_blank=False, allow_null=False, required=True)
    task_status = serializers.CharField(max_length=16, label=_('业务状态'), allow_blank=False, allow_null=False, required=True)
