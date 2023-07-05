from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class MeteringDiskSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('编号'))
    original_amount = serializers.DecimalField(label=_('计费金额'), max_digits=10, decimal_places=2)
    trade_amount = serializers.DecimalField(label=_('交易金额'), max_digits=10, decimal_places=2)
    daily_statement_id = serializers.CharField(label=_('日结算单ID'))
    service_id = serializers.CharField(label=_('服务'))
    disk_id = serializers.CharField(label=_('云硬盘ID'), max_length=36)
    date = serializers.DateField(label=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    user_id = serializers.CharField(label=_('用户ID'), max_length=36)
    username = serializers.CharField(label=_('用户名'), max_length=128)
    vo_id = serializers.CharField(label=_('VO组ID'), max_length=36)
    vo_name = serializers.CharField(label=_('vo组名'), max_length=255)
    owner_type = serializers.CharField(label=_('所有者类型'), max_length=8)
    size_hours = serializers.FloatField(label=_('云硬盘容量GiB Hour'), help_text=_('云硬盘容量的CPU Hour数'))
    pay_type = serializers.CharField(label=_('云服务器付费方式'), max_length=16)
