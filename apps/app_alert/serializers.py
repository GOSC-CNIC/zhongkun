from rest_framework import serializers
from apps.app_alert.models import ResolvedAlertModel
from apps.app_alert.models import AlertWorkOrder
from apps.app_alert.models import EmailNotification


class ResolvedAlertModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResolvedAlertModel
        exclude = ["first_notification", "last_notification", ]


class NotificationModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailNotification
        fields = "__all__"


class WorkOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertWorkOrder
        fields = "__all__"
        read_only_fields = ["creator"]
