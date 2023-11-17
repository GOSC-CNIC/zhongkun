from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class ODCSimpleSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'))
    name = serializers.CharField()
    name_en = serializers.CharField()
    organization = serializers.SerializerMethodField(method_name='get_organization')
    longitude = serializers.FloatField()
    latitude = serializers.FloatField()
    creation_time = serializers.DateTimeField()
    sort_weight = serializers.IntegerField()
    remark = serializers.CharField()

    @staticmethod
    def get_organization(obj):
        organization = obj.organization
        if organization is None:
            return None

        return {'id': organization.id, 'name': organization.name, 'name_en': organization.name_en}


class OrgDataCenterSerializer(ODCSimpleSerializer):
    thanos_endpoint_url = serializers.CharField()
    thanos_username = serializers.CharField()
    thanos_password = serializers.SerializerMethodField(method_name='get_thanos_password')
    thanos_receive_url = serializers.CharField()
    thanos_remark = serializers.CharField()

    loki_endpoint_url = serializers.CharField()
    loki_username = serializers.CharField()
    loki_password = serializers.SerializerMethodField(method_name='get_loki_password')
    loki_receive_url = serializers.CharField()
    loki_remark = serializers.CharField()

    @staticmethod
    def get_thanos_password(obj):
        return obj.raw_thanos_password

    @staticmethod
    def get_loki_password(obj):
        return obj.raw_loki_password


class OrgDataCenterDetailSerializer(OrgDataCenterSerializer):
    users = serializers.SerializerMethodField(method_name='get_users')

    @staticmethod
    def get_users(obj):
        user_objs = obj.users.all()
        data = []
        for user in user_objs:
            data.append({'id': user.id, 'username': user.username})

        return data


class OrgDataCenterCreateSerializer(serializers.Serializer):
    name = serializers.CharField(label=_('名称'), max_length=255)
    name_en = serializers.CharField(label=_('英文名称'), max_length=255)
    organization_id = serializers.CharField(label=_('机构'))
    longitude = serializers.FloatField(label=_('经度'), required=False, default=0, min_value=-120, max_value=120)
    latitude = serializers.FloatField(label=_('纬度'), required=False, default=0, min_value=-90, max_value=90)
    sort_weight = serializers.IntegerField(label=_('排序值'), required=False, default=0)
    remark = serializers.CharField(label=_('数据中心备注'), max_length=255, required=False, allow_blank=True, default='')

    thanos_endpoint_url = serializers.URLField(
        label=_('Thanos服务查询接口'), max_length=255, required=False, allow_blank=True, default='')
    thanos_username = serializers.CharField(
        label=_('Thanos服务认证用户名'), max_length=128, required=False, allow_blank=True, default='')
    thanos_password = serializers.CharField(
        label=_('Thanos服务认证密码'), max_length=255, required=False, allow_blank=True, default='')
    thanos_receive_url = serializers.URLField(
        label=_('Thanos服务接收接口'), max_length=255, required=False, allow_blank=True, default='')
    thanos_remark = serializers.CharField(
        label=_('Thanos服务备注'), max_length=255, required=False, allow_blank=True, default='')

    loki_endpoint_url = serializers.URLField(
        label=_('Loki服务查询接口'), max_length=255, required=False, allow_blank=True, default='')
    loki_username = serializers.CharField(
        label=_('Loki服务认证用户名'), max_length=128, required=False, allow_blank=True, default='')
    loki_password = serializers.CharField(
        label=_('Loki服务认证密码'), max_length=255, required=False, allow_blank=True, default='')
    loki_receive_url = serializers.URLField(
        label=_('Loki服务接收接口'), max_length=255, required=False, allow_blank=True, default='')
    loki_remark = serializers.CharField(
        label=_('Loki服务备注'), max_length=255, required=False, allow_blank=True, default='')


class UsernamesBodySerializer(serializers.Serializer):
    usernames = serializers.ListField(
        label=_('用户名'), max_length=1024, required=True, allow_null=False, allow_empty=False)
