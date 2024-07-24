from rest_framework import serializers
from apps.app_net_flow.models import MenuModel
from apps.app_net_flow.models import ChartModel
from apps.app_net_flow.models import Menu2Chart
from apps.app_net_flow.models import Menu2Member
from apps.app_net_flow.models import GlobalAdminModel
from apps.users.models import UserProfile
from apps.app_net_flow.permission import PermissionManager
from apps.users.models import UserProfile
from django.utils.translation import gettext_lazy as _
from apps.app_alert.utils.errors import GroupMemberExistedError


class ChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartModel
        fields = "__all__"


class GlobalAdminSerializer(serializers.ModelSerializer):
    member = serializers.EmailField(required=True, write_only=True, label='用户邮箱')
    username = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GlobalAdminModel

        fields = [
            'id',
            'username',
            'member',
            'role',
            'inviter',
            'creation',
            'modification',
        ]

    def get_username(self, obj):
        return obj.member.username

    def validate_member(self, value):
        user = UserProfile.objects.filter(username=value).first()
        if not user:
            raise serializers.ValidationError(_('用户不存在'))
        return user


class GlobalAdminWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalAdminModel

        fields = [
            'id',
            'role',
        ]

    def get_username(self, obj):
        return obj.member.username


class Menu2MemberSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField(read_only=True)
    member = serializers.EmailField(required=True, write_only=True, label='用户邮箱')

    def validate_member(self, value):
        user_object = UserProfile.objects.filter(username=value).first()
        if not user_object:
            raise serializers.ValidationError(detail=_("无效的用户邮箱"))
        menu = self.initial_data.get('menu')
        menu_object = MenuModel.objects.filter(id=menu).first()
        menu2member_object = Menu2Member.objects.filter(menu=menu_object, member=user_object).first()
        if menu2member_object:
            raise GroupMemberExistedError()
        return user_object

    class Meta:
        model = Menu2Member
        extra_kwargs = {
            'menu': {'write_only': True},
        }
        fields = (
            "id",
            "role",
            "inviter",
            "creation",
            "menu",
            "member",
            "username",
        )

    def get_username(self, obj):
        return obj.member.username


class Menu2MemberWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu2Member
        fields = [
            "id",
            "role",
        ]


class Menu2ChartListSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.perm = PermissionManager(request=self.context.get('request'))

    instance_name = serializers.SerializerMethodField(read_only=True)
    global_title = serializers.SerializerMethodField(read_only=True)
    global_remark = serializers.SerializerMethodField(read_only=True)
    admin_remark = serializers.SerializerMethodField(read_only=True)
    if_alias = serializers.SerializerMethodField(read_only=True)
    if_address = serializers.SerializerMethodField(read_only=True)
    device_ip = serializers.SerializerMethodField(read_only=True)
    port_name = serializers.SerializerMethodField(read_only=True)
    class_uuid = serializers.SerializerMethodField(read_only=True)
    band_width = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Menu2Chart
        extra_kwargs = {
            'menu': {'write_only': True},
            'chart': {'write_only': True}
        }
        fields = [
            "id",
            "instance_name",
            "global_title",
            "global_remark",
            "remark",
            "admin_remark",
            "sort_weight",
            "if_alias",
            "if_address",
            "device_ip",
            "port_name",
            "class_uuid",
            "band_width",
            "menu",
            "chart",
        ]

    def get_global_title(self, obj):
        return obj.chart.title

    def get_global_remark(self, obj):
        return obj.chart.remark

    def get_instance_name(self, obj):
        return obj.chart.instance_name

    def get_if_alias(self, obj):
        return obj.chart.if_alias

    def get_admin_remark(self, obj):
        if self.perm.is_global_super_admin_or_ops_admin():
            return obj.admin_remark
        if self.perm.has_group_admin_permission(obj.menu.id):
            return obj.admin_remark
        return None

    def get_device_ip(self, obj):
        if self.perm.is_global_super_admin_or_ops_admin():
            return obj.chart.device_ip
        if self.perm.has_group_admin_permission(obj.menu.id):
            return obj.chart.device_ip
        return None

    def get_port_name(self, obj):
        if self.perm.is_global_super_admin_or_ops_admin():
            return obj.chart.port_name
        if self.perm.has_group_admin_permission(obj.menu.id):
            return obj.chart.port_name
        return None

    def get_if_address(self, obj):
        return obj.chart.if_address

    def get_class_uuid(self, obj):
        return obj.chart.class_uuid

    def get_band_width(self, obj):
        return obj.chart.band_width


class Menu2ChartCreateSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.perm = PermissionManager(request=self.context.get('request'))

    instance_name = serializers.SerializerMethodField(read_only=True)
    global_title = serializers.SerializerMethodField(read_only=True)
    global_remark = serializers.SerializerMethodField(read_only=True)
    if_alias = serializers.SerializerMethodField(read_only=True)
    if_address = serializers.SerializerMethodField(read_only=True)
    device_ip = serializers.SerializerMethodField(read_only=True)
    port_name = serializers.SerializerMethodField(read_only=True)
    class_uuid = serializers.SerializerMethodField(read_only=True)
    band_width = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Menu2Chart
        extra_kwargs = {
            'menu': {'write_only': True},
            'chart': {'write_only': True}
        }
        fields = [
            "id",
            "instance_name",
            "global_title",
            "global_remark",
            "remark",
            "admin_remark",
            "sort_weight",
            "if_alias",
            "if_address",
            "device_ip",
            "port_name",
            "class_uuid",
            "band_width",
            "menu",
            "chart",
        ]

    def get_global_title(self, obj):
        return obj.chart.title

    def get_global_remark(self, obj):
        return obj.chart.remark

    def get_instance_name(self, obj):
        return obj.chart.instance_name

    def get_if_alias(self, obj):
        return obj.chart.if_alias

    def get_device_ip(self, obj):
        if self.perm.is_global_super_admin_or_ops_admin():
            return obj.chart.device_ip
        if self.perm.has_group_admin_permission(obj.menu.id):
            return obj.chart.device_ip
        return None

    def get_port_name(self, obj):
        if self.perm.is_global_super_admin_or_ops_admin():
            return obj.chart.port_name
        if self.perm.has_group_admin_permission(obj.menu.id):
            return obj.chart.port_name
        return None

    def get_if_address(self, obj):
        return obj.chart.if_address

    def get_class_uuid(self, obj):
        return obj.chart.class_uuid

    def get_band_width(self, obj):
        return obj.chart.band_width


class Menu2ChartUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu2Chart
        fields = [
            "id",
            "remark",
            "admin_remark",
            "sort_weight",
        ]


class MenuWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuModel
        fields = [
            "id",
            "name",
            "sort_weight",
            "remark",
        ]


class MenuModelSerializer(serializers.ModelSerializer):
    father_id = serializers.PrimaryKeyRelatedField(  # 只写
        queryset=MenuModel.objects.all(),
        source='father',
        write_only=True,
        default=None
    )

    class Meta:
        model = MenuModel
        fields = (
            'id',
            'name',
            # 'admin',
            'sort_weight',
            'remark',
            'level',
            # 'sub_categories',
            'father_id',
        )
        depth = 0


class CustomSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        self.meta = dict()
        super().__init__(*args, **kwargs)


class TimestampRangeSerializer(CustomSerializer):
    start = serializers.IntegerField(
        label="起始时间戳",
        help_text='起始时间戳',
        required=True,
        error_messages={'required': "起始时间戳start不能为空"}
    )
    end = serializers.IntegerField(
        label="结束时间戳",
        help_text='结束时间戳',
        required=True,
        error_messages={'required': "结束时间戳end不能为空"}
    )

    def validate_start(self, start):
        if not self.s_or_ns(start):
            raise serializers.ValidationError("start仅支持10位或19位.请检查: {}".format(start))
        self.meta["start"] = start
        return start

    def validate_end(self, end):
        if not self.s_or_ns(end):
            raise serializers.ValidationError("end仅支持10位或19位.请检查: {}".format(end))
        self.meta["end"] = end
        if self.meta.get("start") > end:
            raise serializers.ValidationError("start 应小于等于 end")
        return end

    @staticmethod
    def s_or_ns(ts):
        return len(str(ts)) in [10, 19]


class TrafficSerializer(TimestampRangeSerializer):
    chart = serializers.CharField(
        label="元素id",
        help_text='元素id',
        required=True,
        error_messages={'required': "元素id不能为空"}
    )
    metrics_ids = serializers.JSONField(
        label="查询字段",
        help_text='查询字段',
        required=True,
        error_messages={'required': "查询字段不能为空"}
    )

    def validate_chart(self, chart):
        element = Menu2Chart.objects.filter(id=chart).first()
        if not element:
            raise serializers.ValidationError("无效的chart参数")
        return element.chart.id
