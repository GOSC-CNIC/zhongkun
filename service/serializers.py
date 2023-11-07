from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


class OrgDataCenterSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'))
    name = serializers.CharField()
    name_en = serializers.CharField()
    organization = serializers.SerializerMethodField(method_name='get_organization')
    users = serializers.SerializerMethodField(method_name='get_user_list')
    longitude = serializers.FloatField()
    latitude = serializers.FloatField()
    creation_time = serializers.DateTimeField()
    sort_weight = serializers.IntegerField()
    remark = serializers.CharField()

    thanos_endpoint_url = serializers.CharField()
    thanos_username = serializers.CharField()
    thanos_password = serializers.CharField()
    thanos_receive_url = serializers.CharField()
    thanos_remark = serializers.CharField()

    loki_endpoint_url = serializers.CharField()
    loki_username = serializers.CharField()
    loki_password = serializers.CharField()
    loki_receive_url = serializers.CharField()
    loki_remark = serializers.CharField()

    @staticmethod
    def get_user_list(obj):
        user_objs = obj.users.all()
        if user_objs is None:
            return None

        data = []
        for user in user_objs:
            data.append({'id': user.id, 'username': user.username})

        return data

    @staticmethod
    def get_organization(obj):
        organization = obj.organization
        data = []
        if organization:
            data.append({'id': organization.id, 'name': organization.name})
        return data


class OrgDataCenterCreateSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('名称'), max_length=255)
    name_en = serializers.CharField(label=_('英文名称'), max_length=255)
    organization = serializers.CharField(label=_('机构'))
    users = serializers.CharField(label=_('管理员'), required=False, allow_blank=True, default='')
    longitude = serializers.FloatField(label=_('经度'), required=False, default=0)
    latitude = serializers.FloatField(label=_('纬度'), required=False, default=0)
    sort_weight = serializers.IntegerField(label=_('排序值'), required=False, default=0)
    remark = serializers.CharField(label=_('数据中心备注'), max_length=255, required=False, allow_blank=True, default='')

    thanos_endpoint_url = serializers.CharField(label=_('Thanos服务查询接口'), max_length=255, required=False,
                                                allow_blank=True, default='')
    thanos_username = serializers.CharField(label=_('Thanos服务认证用户名'), max_length=128, required=False, allow_blank=True,
                                            default='')
    thanos_password = serializers.CharField(label=_('Thanos服务认证密码'), max_length=255, required=False, allow_blank=True,
                                            default='')
    thanos_receive_url = serializers.CharField(label=_('Thanos服务接收接口'), max_length=255, required=False,
                                               allow_blank=True, default='')
    thanos_remark = serializers.CharField(label=_('Thanos服务备注'), max_length=255, required=False, allow_blank=True,
                                          default='')

    loki_endpoint_url = serializers.CharField(label=_('Loki服务查询接口'), max_length=255, required=False, allow_blank=True,
                                              default='')
    loki_username = serializers.CharField(label=_('Loki服务认证用户名'), max_length=128, required=False, allow_blank=True,
                                          default='')
    loki_password = serializers.CharField(label=_('Loki服务认证密码'), max_length=255, required=False, allow_blank=True,
                                          default='')
    loki_receive_url = serializers.CharField(label=_('Loki服务接收接口'), max_length=255, required=False, allow_blank=True,
                                             default='')
    loki_remark = serializers.CharField(label=_('Loki服务备注'), max_length=255, required=False, allow_blank=True,
                                        default='')
