from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


from service.models import OrgDataCenter


def get_org_data_center_dict(odc: OrgDataCenter):
    if odc is None:
        return None

    data = {
        'id': odc.id, 'name': odc.name, 'name_en': odc.name_en, 'sort_weight': odc.sort_weight
    }
    org = odc.organization
    if org is None:
        data['organization'] = None
    else:
        data['organization'] = {
            'id': org.id, 'name': org.name, 'name_en': org.name_en, 'sort_weight': odc.sort_weight
        }

    return data


# class MonitorOrganizationSimpleSerializer(serializers.Serializer):
#     id = serializers.CharField(label=_('监控机构id'))
#     name = serializers.CharField(label=_('监控机构名称'), max_length=255, default='')
#     name_en = serializers.CharField(label=_('监控机构英文名称'), max_length=255, default='')
#     abbreviation = serializers.CharField(label=_('简称'), max_length=64, default='')
#     sort_weight = serializers.IntegerField(label=_('排序权重'), help_text=_('值越大排序越靠前'))
#     creation_time = serializers.DateTimeField(label=_('创建时间'))


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
    org_data_center = serializers.SerializerMethodField(label=_('机构数据中心'), method_name='get_org_data_center')

    @staticmethod
    def get_org_data_center(obj):
        return get_org_data_center_dict(obj.org_data_center)


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
    org_data_center = serializers.SerializerMethodField(label=_('机构数据中心'), method_name='get_org_data_center')

    @staticmethod
    def get_org_data_center(obj):
        return get_org_data_center_dict(obj.org_data_center)


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
    scheme = serializers.CharField(label=_('协议'), max_length=32, required=True, help_text='https|tcp://')
    hostname = serializers.CharField(label=_('域名'), max_length=255, required=True, help_text='hostname:8000')
    uri = serializers.CharField(label=_('URI'), max_length=1024, required=True, help_text='/a/b?query=123#test')
    is_tamper_resistant = serializers.BooleanField(
        label=_('防篡改'), required=False, allow_null=True, default=None, help_text='tcp监控不支持防篡改监控')
    remark = serializers.CharField(label=_('备注'), max_length=255, allow_blank=True, default='')

    url_hash = serializers.CharField(label=_('网址hash值'), max_length=64, read_only=True)
    creation = serializers.DateTimeField(label=_('创建时间'), read_only=True)
    modification = serializers.DateTimeField(label=_('修改时间'), read_only=True)
    is_attention = serializers.BooleanField(label=_('特别关注'), read_only=True)
    url = serializers.SerializerMethodField(label=_('要监控的网址'), read_only=True, method_name='get_url')

    @staticmethod
    def get_url(obj):
        return obj.full_url


class MonitorWebsiteWithUserSerializer(MonitorWebsiteSerializer):
    user = serializers.SerializerMethodField(method_name='get_user', read_only=True)
    odc = serializers.SerializerMethodField(method_name='get_odc', read_only=True)

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {'id': user.id, 'username': user.username}

        return {'id': '', 'username': ''}

    @staticmethod
    def get_odc(obj):
        odc = obj.odc
        if odc:
            return {'id': odc.id, 'name': odc.name, 'name_en': odc.name_en}

        return None


class MonitorWebsiteTaskSerializer(serializers.Serializer):
    # id = serializers.CharField(label=_('ID'), read_only=True)
    url = serializers.URLField(label=_('要监控的网址'), max_length=2048, required=True, help_text='http(s)://xxx.xxx')
    url_hash = serializers.CharField(label=_('网址hash值'), max_length=64, read_only=True)
    creation = serializers.DateTimeField(label=_('创建时间'), read_only=True)
    is_tamper_resistant = serializers.BooleanField(label=_('防篡改'))


class MonitorWebsiteDetectionPointSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'), read_only=True)
    name = serializers.CharField(label=_('监控探测点名称'), max_length=128)
    name_en = serializers.CharField(label=_('监控探测点英文名称'), max_length=128)
    creation = serializers.DateTimeField(label=_('创建时间'))
    modification = serializers.DateTimeField(label=_('修改时间'))
    remark = serializers.CharField(label=_('备注'), max_length=255)
    enable = serializers.BooleanField(label=_('使用启用'))


class MonitorJobTiDBSimpleSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('监控单元id'))
    name = serializers.CharField(label=_('监控的TiDB集群'), max_length=255, default='')
    name_en = serializers.CharField(label=_('监控的TiDB集群英文名'), max_length=255, default='')
    job_tag = serializers.CharField(label=_('TiDB集群的标签名称'), max_length=255, default='')
    creation = serializers.DateTimeField(label=_('创建时间'))


class MonitorUnitTiDBSerializer(MonitorJobTiDBSimpleSerializer):
    """TiDB监控单元"""
    remark = serializers.CharField(label=_('备注'))
    sort_weight = serializers.IntegerField(label=_('排序权重'), default=0, help_text=_('值越大排序越靠前'))
    grafana_url = serializers.CharField(label=_('Grafana连接'), max_length=255)
    dashboard_url = serializers.CharField(label=_('Dashboard连接'), max_length=255)
    version = serializers.CharField(label=_('TiDB版本'), max_length=32, help_text='xx.xx.xx')
    org_data_center = serializers.SerializerMethodField(label=_('机构数据中心'), method_name='get_org_data_center')

    @staticmethod
    def get_org_data_center(obj):
        return get_org_data_center_dict(obj.org_data_center)


class LogSiteTypeSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField(label="日志网站类别名称")
    name_en = serializers.CharField(label=_('英文名称'))
    sort_weight = serializers.IntegerField(label='排序值', help_text='值越小排序越靠前')
    desc = serializers.CharField(label="备注")


class LogSiteSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField(label="日志单元名称")
    name_en = serializers.CharField(label=_('日志单元英文名称'))
    log_type = serializers.CharField(label="日志类型")
    job_tag = serializers.CharField(label=_('网站日志单元标识'))
    sort_weight = serializers.IntegerField(label='排序值', help_text='值越小排序越靠前')
    desc = serializers.CharField(label="备注")
    creation = serializers.DateTimeField(label='创建时间')
    site_type = LogSiteTypeSerializer(allow_null=True)
    org_data_center = serializers.SerializerMethodField(label=_('机构数据中心'), method_name='get_org_data_center')

    @staticmethod
    def get_org_data_center(obj):
        return get_org_data_center_dict(obj.org_data_center)
