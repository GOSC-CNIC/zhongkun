from rest_framework import serializers
from apps.app_alert.models import AlertModel
from apps.app_alert.models import AlertWorkOrder
from apps.app_alert.models import EmailNotification
from apps.app_alert.utils.utils import DateUtils


class AlertModelSerializer(serializers.ModelSerializer):
    order = serializers.SerializerMethodField(read_only=True)
    end = serializers.SerializerMethodField(read_only=True)
    alertname = serializers.SerializerMethodField(read_only=True)
    alert_type = serializers.SerializerMethodField(read_only=True)
    timestamp = serializers.SerializerMethodField(read_only=True)
    startsAt = serializers.SerializerMethodField(read_only=True)

    def get_order(self, obj):
        order = obj.order
        if order:
            result = dict()
            result['id'] = order.id
            result['remark'] = order.remark
            result['status'] = order.status
            result['creation'] = order.creation
            result['creator_name'] = order.creator.last_name + order.creator.first_name
            result['creator_email'] = order.creator.email
            return result
        else:
            return {}

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


class WorkOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertWorkOrder
        fields = [
            'id',
            'status',
            'remark',
            'creator',
        ]
        extra_kwargs = {
            'creator': {'read_only': True},
        }
        # read_only_fields = ["creator"]
