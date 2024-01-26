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


class ArrearServerSerializer(serializers.Serializer):
    id = serializers.CharField(label='ID', max_length=36, read_only=True)
    server_id = serializers.CharField(
        label=_('云主机ID'), max_length=36, default='')
    service_id = serializers.CharField(label=_('云主机服务单元ID'), allow_null=True)
    service_name = serializers.CharField(max_length=255, label=_('云主机服务单元'))
    ipv4 = serializers.CharField(max_length=128, label='IPV4', default='')
    vcpus = serializers.IntegerField(label=_('虚拟CPU数'), default=0)
    ram = serializers.IntegerField(label=_('内存GiB'), default=0)
    image = serializers.CharField(max_length=255, label=_('镜像系统名称'), default='')
    pay_type = serializers.CharField(label=_('计费方式'), max_length=16)
    server_creation = serializers.DateTimeField(label=_('云主机创建时间'))
    server_expire = serializers.DateTimeField(label=_('云主机过期时间'), allow_null=True, default=None)
    remarks = serializers.CharField(max_length=255, default='', label=_('云主机备注'))
    user_id = serializers.CharField(label=_('用户ID'), max_length=36, default='')
    username = serializers.CharField(label=_('用户名'), help_text=_('个人云主机的拥有者，或者vo组云主机的创建者'))
    vo_id = serializers.CharField(label=_('VO组ID'), max_length=36, default='')
    vo_name = serializers.CharField(label=_('VO组名'), max_length=256, default='')
    owner_type = serializers.CharField(label=_('所有者类型'), max_length=8)
    balance_amount = serializers.DecimalField(
        label=_('所有者的余额'), max_digits=10, decimal_places=2, help_text=_('用户个人余额，或者VO组余额'))
    date = serializers.DateField(label=_('数据日期'), help_text=_('查询欠费云主机数据采样日期'))
    creation_time = serializers.DateTimeField(label=_('判定为欠费的时间'))
