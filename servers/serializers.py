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


class FlavorCreateSerializer(serializers.Serializer):
    service_id = serializers.CharField(label=_('服务单元id'), required=True)
    vcpus = serializers.IntegerField(label=_('CPU数'), required=True)
    ram = serializers.IntegerField(label=_('内存GiB'), required=True)
    enable = serializers.BooleanField(label=_('是否启用'), required=True)


class ImageSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    release = serializers.CharField()
    version = serializers.CharField()
    architecture = serializers.CharField()
    system_type = serializers.CharField()
    creation_time = serializers.DateTimeField()
    desc = serializers.CharField()
    default_user = serializers.CharField()
    default_password = serializers.CharField()
    min_sys_disk_gb = serializers.IntegerField()
    min_ram_mb = serializers.IntegerField()


class ImageOldSerializer(ImageSerializer):
    system = serializers.SerializerMethodField(method_name='get_system')

    @staticmethod
    def get_system(obj):
        return obj.release


class NetworkSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    public = serializers.BooleanField()
    segment = serializers.CharField()


class AvailabilityZoneSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('可用区ID'))
    name = serializers.CharField(label=_('可用区名称'))
    available = serializers.BooleanField(label=_('是否可用'))
