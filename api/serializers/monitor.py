from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class MonitorOrganizationSimpleSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('监控机构id'))
    name = serializers.CharField(label=_('监控机构名称'), max_length=255, default='')
    name_en = serializers.CharField(label=_('监控机构英文名称'), max_length=255, default='')
    abbreviation = serializers.CharField(label=_('简称'), max_length=64, default='')
    sort_weight = serializers.IntegerField(label=_('排序权重'), help_text=_('值越大排序越靠前'))
    creation = serializers.DateTimeField(label=_('创建时间'))


class MonitorOrganizationSerializer(MonitorOrganizationSimpleSerializer):
    country = serializers.CharField(label=_('国家/地区'), max_length=128, default='')
    city = serializers.CharField(label=_('城市'), max_length=128, default='')
    postal_code = serializers.CharField(label=_('邮政编码'), max_length=32, default='')
    address = serializers.CharField(label=_('单位地址'), max_length=256, default='')
    longitude = serializers.FloatField(label=_('经度'), default=0)
    latitude = serializers.FloatField(label=_('纬度'), default=0)
    modification = serializers.DateTimeField(label=_('修改时间'))
    remark = serializers.CharField(label=_('备注'), default='')


class MonitorJobCephSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('监控单元id'))
    name = serializers.CharField(label=_('监控的CEPH集群名称'), max_length=255, default='')
    name_en = serializers.CharField(label=_('监控的CEPH集群英文名称'), max_length=255, default='')
    job_tag = serializers.CharField(label=_('CEPH集群标签名称'), max_length=255, default='')
    creation = serializers.DateTimeField(label=_('创建时间'))


class MonitorUnitCephSerializer(MonitorJobCephSerializer):
    """ceph监控单元"""
    remark = serializers.CharField(label=_('备注'))
    sort_weight = serializers.IntegerField(label=_('排序权重'), default=0, help_text=_('值越大排序越靠前'))
    grafana_url = serializers.CharField(label=_('Grafana连接'), max_length=255)
    dashboard_url = serializers.CharField(label=_('Dashboard连接'), max_length=255)
    organization = MonitorOrganizationSimpleSerializer(required=False)


class MonitorJobServerSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('监控单元id'))
    name = serializers.CharField(label=_('监控的主机集群'), max_length=255, default='')
    name_en = serializers.CharField(label=_('监控的主机集群英文名'), max_length=255, default='')
    job_tag = serializers.CharField(label=_('主机集群的标签名称'), max_length=255, default='')
    creation = serializers.DateTimeField(label=_('创建时间'))


class MonitorUnitServerSerializer(MonitorJobServerSerializer):
    """server监控单元"""
    remark = serializers.CharField(label=_('备注'))
    sort_weight = serializers.IntegerField(label=_('排序权重'), default=0, help_text=_('值越大排序越靠前'))
    grafana_url = serializers.CharField(label=_('Grafana连接'), max_length=255)
    dashboard_url = serializers.CharField(label=_('Dashboard连接'), max_length=255)


class MonitorJobVideoMeetingSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('科技云会服务节点院所名称'), max_length=255, default='')
    name_en = serializers.CharField(label=_('科技云会服务节点院所英名称'), max_length=255, default='')
    job_tag = serializers.CharField(label=_('视频会议节点的标签名称'), max_length=255, default='')
    creation = serializers.DateTimeField(label=_('创建时间'))
    longitude = serializers.FloatField(label=_('经度'))
    latitude = serializers.FloatField(label=_('纬度'))


class MonitorWebsiteSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'), read_only=True)

    name = serializers.CharField(label=_('网站名称'), max_length=255, required=True)
    url = serializers.URLField(label=_('要监控的网址'), max_length=2048, required=True, help_text='http(s)://xxx.xxx')
    remark = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, default='')

    url_hash = serializers.CharField(label=_('网址hash值'), max_length=64, read_only=True)
    creation = serializers.DateTimeField(label=_('创建时间'), read_only=True)


class MonitorWebsiteWithUserSerializer(MonitorWebsiteSerializer):
    user = serializers.SerializerMethodField(method_name='get_user', read_only=True)

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {'id': user.id, 'username': user.username}

        return {'id': '', 'username': ''}


class MonitorWebsiteTaskSerializer(serializers.Serializer):
    # id = serializers.CharField(label=_('ID'), read_only=True)
    url = serializers.URLField(label=_('要监控的网址'), max_length=2048, required=True, help_text='http(s)://xxx.xxx')
    url_hash = serializers.CharField(label=_('网址hash值'), max_length=64, read_only=True)
    creation = serializers.DateTimeField(label=_('创建时间'), read_only=True)
