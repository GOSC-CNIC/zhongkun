from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class ScanTaskOrderCreateSerializer(serializers.Serializer):
    """创建安全扫描任务序列化器"""

    name = serializers.CharField(label=_("任务名称"), max_length=255, required=True)
    # 站点扫描目标信息
    scheme = serializers.CharField(label=_("协议"), max_length=32, allow_blank=True, default=None, help_text="https|http://")
    hostname = serializers.CharField(label=_("域名"), max_length=255, allow_blank=True, default=None, help_text="hostname:8000")
    uri = serializers.CharField(label=_("URI"), max_length=1024, allow_blank=True, default=None, help_text="/a/b?query=123#test")
    # 主机扫描目标信息
    ipaddr = serializers.CharField(label=_("IP地址"), max_length=16, allow_blank=True, default=None, help_text="1.1.1.1")
    remark = serializers.CharField(label=_("备注"), max_length=255, allow_blank=True, default="")


class ScanTaskListSerializer(serializers.Serializer):
    """任务列表序列化器"""

    id = serializers.CharField(label=_("任务ID"))
    name = serializers.CharField(label=_("任务名称"))
    target = serializers.CharField(label=_("任务目标"))
    type = serializers.CharField(label=_("任务类型"))
    task_status = serializers.CharField(label=_("任务状态"))
    user = serializers.SerializerMethodField(method_name="get_user")
    create_time = serializers.DateTimeField(label=_("创建时间"))
    finish_time = serializers.DateTimeField(label=_("完成时间"))
    update_time = serializers.DateTimeField(label=_("更新时间"))
    remark = serializers.CharField(label=_("备注"), default="")

    @staticmethod
    def get_user(obj):
        user = obj.user
        if user:
            return {"id": user.id, "username": user.username}

        return {"id": "", "username": ""}
