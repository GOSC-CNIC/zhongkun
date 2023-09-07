from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class BucketStatsMonthlySerializer(serializers.Serializer):
    id = serializers.CharField(label=_('ID'))
    service = serializers.SerializerMethodField(label=_('服务单元'), method_name='get_service')
    bucket_id = serializers.CharField(label=_('存储桶ID'))
    bucket_name = serializers.CharField(label=_('存储桶名称'))
    size_byte = serializers.IntegerField(label=_('存储容量(Byte)'))
    increment_byte = serializers.IntegerField(label=_('存储容量增量(Byte)'))
    object_count = serializers.IntegerField(label=_('桶对象数量'))
    original_amount = serializers.DecimalField(label=_('计费金额'), max_digits=10, decimal_places=2)
    increment_amount = serializers.DecimalField(label=_('计费金额增量'), max_digits=10, decimal_places=2)
    user_id = serializers.CharField(label=_('用户id'))
    username = serializers.CharField(label=_('用户名'))
    date = serializers.SerializerMethodField(label=_('数据日期(月份)'), method_name='get_date')
    creation_time = serializers.DateTimeField(label=_('创建时间'))

    @staticmethod
    def get_service(obj):
        if obj.service:
            return {'id': obj.service.id, 'name': obj.service.name, 'name_en': obj.service.name_en}

        return {'id': None, 'name': None, 'name_en': None}

    @staticmethod
    def get_date(obj):
        val = obj.date
        if not val:
            return None

        return f"{val.year:04}-{val.month:02}"
