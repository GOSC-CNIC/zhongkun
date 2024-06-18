from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class AppProbeTaskSerializer(serializers.Serializer):
    url = serializers.CharField(label=_('URI'), max_length=1024, required=False)
    url_hash = serializers.CharField(label=_('网址hash值'), max_length=64, required=False)
    is_tamper_resistant = serializers.BooleanField(default=False, required=False)

class AppProbeSerializer(serializers.Serializer):
    operate = serializers.CharField(label=_('操作'))
    version = serializers.IntegerField(label=_('版本号'))
    task = AppProbeTaskSerializer()
    newtask = AppProbeTaskSerializer(required=False)

