from rest_framework import serializers
from apps.app_alert.models import AlertModel
from apps.app_alert.models import EmailNotification

from apps.app_alert.utils.utils import DateUtils


class AlertModelSerializer(serializers.ModelSerializer):
    end = serializers.SerializerMethodField(read_only=True)
    alertname = serializers.SerializerMethodField(read_only=True)
    alert_type = serializers.SerializerMethodField(read_only=True)
    timestamp = serializers.SerializerMethodField(read_only=True)
    startsAt = serializers.SerializerMethodField(read_only=True)
    monitor_cluster = serializers.SerializerMethodField(read_only=True)

    def get_end(self, obj):
        if obj.recovery:
            return obj.recovery
        else:
            return obj.end

    def get_alertname(self, obj):
        return obj.name

    def get_alert_type(self, obj):
        return obj.type

    def get_timestamp(self, obj):
        return obj.start

    def get_startsAt(self, obj):
        return DateUtils.ts_to_date(obj.start)

    def get_monitor_cluster(self, obj):
        return obj.cluster

    class Meta:
        model = AlertModel
        exclude = [
            'first_notification',
            'last_notification',
            'recovery',
        ]


class NotificationModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailNotification
        fields = "__all__"
