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


class DailyStatementDiskSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('日结算单编号'))
    original_amount = serializers.DecimalField(label=_('计费金额'), max_digits=10, decimal_places=2, default=0.0)
    payable_amount = serializers.DecimalField(label=_('应付金额'), max_digits=10, decimal_places=2, default=0.0)
    trade_amount = serializers.DecimalField(label=_('实付金额'), max_digits=10, decimal_places=2, default=0.0)
    payment_status = serializers.CharField(label=_('支付状态'), max_length=16)
    payment_history_id = serializers.CharField(label=_('支付记录ID'), max_length=36)
    service_id = serializers.CharField(label=_('服务id'), max_length=36)
    date = serializers.DateField(label=_('日结算单日期'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    user_id = serializers.CharField(label=_('用户ID'), max_length=36)
    username = serializers.CharField(label=_('用户名'), max_length=64)
    vo_id = serializers.CharField(label=_('VO组ID'), max_length=36)
    vo_name = serializers.CharField(label=_('VO组名'), max_length=256)
    owner_type = serializers.CharField(label=_('所有者类型'), max_length=8)


class DailyStatementDiskDetailSerializer(DailyStatementDiskSerializer):
    service = serializers.SerializerMethodField(method_name='get_service')

    @staticmethod
    def get_service(obj):
        service = obj.service
        if service:
            return {
                'id': service.id,
                'name': service.name,
                'name_en': service.name_en,
                'service_type': service.service_type
            }

        return None


class MeteringMonitorSiteSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('编号'))
    original_amount = serializers.DecimalField(label=_('计费金额'), max_digits=10, decimal_places=2)
    trade_amount = serializers.DecimalField(label=_('应付金额'), max_digits=10, decimal_places=2)
    daily_statement_id = serializers.CharField(label=_('日结算单ID'))
    website_id = serializers.CharField(label=_('监控站点ID'), max_length=36)
    website_name = serializers.CharField(label=_('监控站点名称'), max_length=255)
    user_id = serializers.CharField(label=_('用户ID'), max_length=36)
    username = serializers.CharField(label=_('用户名'), max_length=128)
    date = serializers.DateField(label=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    hours = serializers.FloatField(label=_('监控小时数'), help_text=_('小时数'))
    # detection_count = serializers.IntegerField(label=_('探测次数'), default=0)
    tamper_resistant_count = serializers.IntegerField(
        label=_('是否防篡改'), default=0, help_text=_('防篡改探测次数，记录站点监控是否设置防篡改监控服务'))
    # security_count = serializers.IntegerField(
    #     label=_('是否安全扫描'), default=0, help_text=_('安全扫描次数，记录站点监控是否设置安全扫描服务'))
