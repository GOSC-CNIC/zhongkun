from rest_framework import serializers
from apps.app_alert.models import AlertModel
from apps.app_alert.models import AlertWorkOrder
from apps.app_alert.models import EmailNotification
from apps.app_alert.models import TicketResolutionCategory
from apps.app_alert.models import TicketResolution
from apps.app_alert.models import AlertTicket
from apps.app_alert.utils import errors
from apps.app_alert.utils.utils import DateUtils
from apps.app_alert.handlers.ticket import ServerAdapter
from apps.app_alert.models import ServiceAdminUser


class AlertModelSerializer(serializers.ModelSerializer):
    order = serializers.SerializerMethodField(read_only=True)
    end = serializers.SerializerMethodField(read_only=True)
    alertname = serializers.SerializerMethodField(read_only=True)
    alert_type = serializers.SerializerMethodField(read_only=True)
    timestamp = serializers.SerializerMethodField(read_only=True)
    startsAt = serializers.SerializerMethodField(read_only=True)
    monitor_cluster = serializers.SerializerMethodField(read_only=True)

    def get_order(self, obj):
        order = obj.ticket
        if order:
            result = dict()
            result['id'] = order.id
            result['remark'] = order.description
            result['status'] = order.status
            result['creation'] = order.creation
            result['creator_name'] = order.submitter.get_full_name()
            result['creator_email'] = order.submitter.username
            if order.assigned_to:
                result['assigned_to_name'] = order.assigned_to.get_full_name()
                result['assigned_to_email'] = order.assigned_to.username
            else:
                result['assigned_to_name'] = None
                result['assigned_to_email'] = None
            if order.resolution:
                result['resolution'] = order.resolution.resolution
            else:
                result['resolution'] = None

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


class TicketResolutionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketResolutionCategory
        fields = "__all__"

    def validate(self, data):
        obj = TicketResolutionCategory.objects.filter(name=data.get('name'), service=data.get('service')).first()
        if obj:
            raise serializers.ValidationError("please do not resubmit")
        return data


class TicketResolutionReadOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketResolution
        fields = (
            "id",
            "resolution",
            "creation",
            "modification",
        )


class TicketResolutionCategoryRelationSerializer(serializers.ModelSerializer):
    resolutions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TicketResolutionCategory
        fields = [
            'id',
            'name',
            'service',
            'creation',
            'modification',
            'resolutions',

        ]

    def get_resolutions(self, obj):
        return TicketResolutionReadOnlySerializer(obj.resolutions.all(), many=True).data


class TicketResolutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketResolution
        fields = "__all__"

    def validate(self, data):
        resolution = data.get('resolution')
        if not resolution:
            raise serializers.ValidationError("invalid resolution")
        obj = TicketResolution.objects.filter(category=data.get('category'), resolution=data.get('resolution')).first()
        if obj:
            raise serializers.ValidationError("please do not resubmit")
        return data


class AlertTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertTicket
        fields = "__all__"
        extra_kwargs = {
            'submitter': {'read_only': True},
            'service': {'read_only': True},
        }


class BelongedServiceSerializer(serializers.Serializer):
    alerts = serializers.JSONField(required=True)

    def validate_alerts(self, alerts: str):
        if not isinstance(alerts, list):
            raise errors.InvalidArgument("param alerts should be a list")
        service_adapter = ServerAdapter(alerts)
        service_set = service_adapter.get_service_set()
        if not service_set:
            raise errors.InvalidArgument("unknown service")
        if len(service_set) > 1:
            raise errors.InvalidArgument("multi service is not supported")
        return list(service_set)[0]


class ServiceAdminUserSerializer(serializers.ModelSerializer):
    userid = serializers.SerializerMethodField(read_only=True)
    username = serializers.SerializerMethodField(read_only=True)
    fullname = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ServiceAdminUser
        fields = [
            'id',
            'userid',
            'username',
            'fullname',
            'role',
            'join_time',
            'service',
        ]

    def get_userid(self, obj):
        return obj.userprofile.id

    def get_username(self, obj):
        return obj.userprofile.username

    def get_fullname(self, obj):
        return obj.userprofile.get_full_name()
