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
    username = serializers.CharField(label=_('用户名'), max_length=128)
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


class StatementMonitorSiteSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('日结算单编号'))
    original_amount = serializers.DecimalField(label=_('计费金额'), max_digits=10, decimal_places=2, default=0.0)
    payable_amount = serializers.DecimalField(label=_('应付金额'), max_digits=10, decimal_places=2, default=0.0)
    trade_amount = serializers.DecimalField(label=_('实付金额'), max_digits=10, decimal_places=2, default=0.0)
    payment_status = serializers.CharField(label=_('支付状态'), max_length=16)
    payment_history_id = serializers.CharField(label=_('支付记录ID'), max_length=36)
    date = serializers.DateField(label=_('日结算单日期'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    user_id = serializers.CharField(label=_('用户ID'), max_length=36)
    username = serializers.CharField(label=_('用户名'), max_length=128)


class MeteringServerSerializer(serializers.Serializer):
    id = serializers.CharField(label=_('订单编号'))
    original_amount = serializers.DecimalField(label=_('计费金额'), max_digits=10, decimal_places=2)
    trade_amount = serializers.DecimalField(label=_('交易金额'), max_digits=10, decimal_places=2)
    daily_statement_id = serializers.CharField(label=_('日结算单ID'))
    service_id = serializers.CharField(label=_('服务'))
    server_id = serializers.CharField(label=_('云服务器ID'), max_length=36)
    date = serializers.DateField(label=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    user_id = serializers.CharField(label=_('用户ID'), max_length=36)
    username = serializers.CharField(label=_('用户名'), max_length=128)
    vo_id = serializers.CharField(label=_('VO组ID'), max_length=36)
    vo_name = serializers.CharField(label=_('vo组名'), max_length=255)
    owner_type = serializers.CharField(label=_('所有者类型'), max_length=8)
    cpu_hours = serializers.FloatField(label=_('CPU Hour'), help_text=_('云服务器的CPU Hour数'))
    ram_hours = serializers.FloatField(label=_('内存GiB Hour'), help_text=_('云服务器的内存Gib Hour数'))
    disk_hours = serializers.FloatField(label=_('系统盘GiB Hour'), help_text=_('云服务器的系统盘Gib Hour数'))
    public_ip_hours = serializers.FloatField(label=_('IP Hour'), help_text=_('云服务器的公网IP Hour数'))
    snapshot_hours = serializers.FloatField(label=_('快照GiB Hour'), help_text=_('云服务器的快照小时数'))
    upstream = serializers.FloatField(label=_('上行流量GiB'), help_text=_('云服务器的上行流量Gib'))
    downstream = serializers.FloatField(label=_('下行流量GiB'), help_text=_('云服务器的下行流量Gib'))
    pay_type = serializers.CharField(label=_('云服务器付费方式'), max_length=16)


class DailyStatementServerSerializer(serializers.Serializer):
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


class DailyStatementStorageSerializer(serializers.Serializer):
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


class DailyStatementServerDetailSerializer(DailyStatementServerSerializer):
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


class DailyStatementStorageDetailSerializer(DailyStatementStorageSerializer):
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


class MeteringStorageSimpleSerializer(serializers.Serializer):
    """
    对象存储序列化器
    """
    id = serializers.CharField(label=_('订单编号'))
    original_amount = serializers.DecimalField(label=_('计费金额'), max_digits=10, decimal_places=2)
    trade_amount = serializers.DecimalField(label=_('交易金额'), max_digits=10, decimal_places=2)
    daily_statement_id = serializers.CharField(label=_('日结算单ID'))
    service_id = serializers.CharField(label=_('服务'))
    bucket_name = serializers.CharField(label=_('存储桶名字'))
    storage_bucket_id = serializers.CharField(label=_('存储桶ID'), max_length=36)
    date = serializers.DateField(label=_('日期'), help_text=_('计量的资源使用量的所属日期'))
    creation_time = serializers.DateTimeField(label=_('创建时间'))
    user_id = serializers.CharField(label=_('用户ID'), max_length=36)
    username = serializers.CharField(label=_('用户名'), max_length=128)
    storage = serializers.FloatField(label=_('存储容量GiB'), help_text=_('存储桶中使用的容量'))
    downstream = serializers.FloatField(label=_('下行流量GiB'), help_text=_('存储桶的下行流量GiB'))
    replication = serializers.FloatField(label=_('下行流量GiB'), help_text=_('存储桶的同步流量GiB'))
    get_request = serializers.IntegerField(label=_('同步流量GiB'), help_text=_('存储桶的get请求次数'))
    put_request = serializers.IntegerField(label=_('put请求次数'), help_text=_('存储桶的put请求次数'))
    billed_network_flow = serializers.FloatField(label=_('计费流量GiB'), help_text=_('存储桶的计费流量GiB'))
    unbilled_network_flow = serializers.FloatField(label=_('非计费流量GiB'), help_text=_('存储桶的非计费流量GiB'))


class MeteringStorageSerializer(MeteringStorageSimpleSerializer):
    """
    对象存储序列化器
    """
    service = serializers.SerializerMethodField(label=_('服务'), method_name='get_service')

    @staticmethod
    def get_service(obj):
        if obj.service:
            return {'id': obj.service.id, 'name': obj.service.name, 'name_en': obj.service.name_en}

        return None
