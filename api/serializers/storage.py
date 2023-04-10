from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class BucketCreateSerializer(serializers.Serializer):
    service_id = serializers.CharField(label=_('服务单元ID'), max_length=36, required=True)
    name = serializers.CharField(label=_('存储桶名称'), max_length=73, required=True)


class BucketSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('存储桶ID'))
    name = serializers.CharField(label=_('存储桶名称'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    user_id = serializers.CharField(label=_('用户id'))
    username = serializers.SerializerMethodField(method_name='get_username')
    service = serializers.SerializerMethodField(method_name='get_service')

    @staticmethod
    def get_username(obj):
        if obj.user:
            return obj.user.username

        return ''

    @staticmethod
    def get_service(obj):
        if obj.service:
            return {'id': obj.service.id, 'name': obj.service.name, 'name_en': obj.service.name_en}

        return {'id': None, 'name': None, 'name_en': None}


class AdminBucketSerializer(BucketSerializer):
    task_status = serializers.CharField(label='创建状态', max_length=16)
    situation = serializers.CharField(label='过期欠费管控情况', max_length=16, help_text='欠费状态下存储桶读写锁定管控情况')
    situation_time = serializers.DateTimeField(label='管控情况时间', help_text='欠费管控开始时间')


class ObjectsServiceSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('存储桶ID'))
    name = serializers.CharField(label=_('服务名称'))
    name_en = serializers.CharField(label=_('服务英文名称'))
    service_type = serializers.CharField()
    endpoint_url = serializers.CharField(label=_('服务地址url'), help_text='http(s)://{hostname}:{port}/')
    add_time = serializers.DateTimeField(label=_('添加时间'))
    status = serializers.CharField(label=_('服务状态'))
    remarks = serializers.CharField(label=_('备注'))
    provide_ftp = serializers.BooleanField(label=_('是否提供FTP服务'))
    ftp_domains = serializers.SerializerMethodField(method_name='get_ftp_domains')
    longitude = serializers.FloatField(label=_('经度'))
    latitude = serializers.FloatField(label=_('纬度'))
    pay_app_service_id = serializers.CharField(label=_('余额结算APP服务ID'))
    data_center = serializers.SerializerMethodField(method_name='get_data_center')
    sort_weight = serializers.IntegerField(label=_('排序权重'), default=0, help_text=_('值越大排序越靠前'))

    @staticmethod
    def get_ftp_domains(obj):
        return obj.ftp_domains_list()

    @staticmethod
    def get_data_center(obj):
        if obj.data_center:
            return {'id': obj.data_center.id, 'name': obj.data_center.name, 'name_en': obj.data_center.name_en,
                    'sort_weight': obj.data_center.sort_weight}

        return None
