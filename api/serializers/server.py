from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class PeriodSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'))
    period = serializers.IntegerField(label=_('月数'))
    enable = serializers.BooleanField(label='启用')
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    service_id = serializers.CharField(label=_('服务单元ID'), max_length=36, required=True)


class FlavorSerializer(serializers.Serializer):
    id = serializers.CharField()
    flavor_id = serializers.CharField(label=_('服务端规格ID'))
    vcpus = serializers.IntegerField(label=_('虚拟CPU数'))
    ram = serializers.IntegerField(label=_('内存GiB'))
    disk = serializers.IntegerField(label=_('硬盘GB'))
    service_id = serializers.CharField(label=_('服务单元id'))
    enable = serializers.BooleanField(label='启用')
    ram_gib = serializers.SerializerMethodField(method_name='get_ram_gib', label=_('内存GiB'))

    @staticmethod
    def get_ram_gib(obj):
        return obj.ram

    @staticmethod
    def get_ram_mib(obj):
        return obj.ram_mib


class FlavorCreateSerializer(serializers.Serializer):
    service_id = serializers.CharField(label=_('服务单元id'), required=True)
    vcpus = serializers.IntegerField(label=_('CPU数'), required=True)
    ram = serializers.IntegerField(label=_('内存GiB'), required=True)
    enable = serializers.BooleanField(label=_('是否启用'), required=True)

