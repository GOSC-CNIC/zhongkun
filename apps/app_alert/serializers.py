from rest_framework import serializers
from apps.app_alert.models import AlertModel
from apps.app_alert.models import AlertWorkOrder
from apps.app_alert.models import EmailNotification
from apps.app_alert.models import TicketResolutionCategory
from apps.app_alert.models import TicketResolution
from apps.app_alert.models import AlertTicket
from apps.app_alert.utils import errors
from apps.app_alert.utils.utils import DateUtils
from apps.app_alert.handlers.handlers import AlertServerAdapter
from apps.app_alert.models import ServiceAdminUser
from apps.users.models import UserProfile
from apps.app_alert.models import AlertService
from apps.app_alert.models import TicketHandler


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
            # handlers = order.handlers.all()
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


class TicketHandlerSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketHandler
        fields = "__all__"


class TicketHandlerReadOnlySerializer(serializers.ModelSerializer):
    userid = serializers.SerializerMethodField(read_only=True)
    username = serializers.SerializerMethodField(read_only=True)
    fullname = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TicketHandler
        fields = (
            'id',
            'userid',
            'username',
            'fullname',
            'creation',
            'modification',
        )

    def get_userid(self, obj):
        return obj.user.id

    def get_username(self, obj):
        return obj.user.username

    def get_fullname(self, obj):
        return obj.user.get_full_name()


class AlertReadOnlySerializer(serializers.ModelSerializer):
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
            'ticket',
        ]


class AlertTicketCreateSerializer(serializers.ModelSerializer):
    submitter_username = serializers.SerializerMethodField(read_only=True)
    submitter_fullname = serializers.SerializerMethodField(read_only=True)
    handlers = serializers.SerializerMethodField(read_only=True)
    alerts = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AlertTicket
        fields = (
            'id',
            'title',
            'description',
            'service',
            'severity',
            'status',
            'creation',
            'modification',
            'submitter',
            'submitter_username',
            'submitter_fullname',
            'resolution',
            'handlers',
            'alerts',
        )
        extra_kwargs = {
            'submitter': {'read_only': True},
            'service': {'read_only': True},
        }

    def get_handlers(self, obj):
        return TicketHandlerReadOnlySerializer(TicketHandler.objects.filter(ticket=obj).all(), many=True).data

    def get_submitter_username(self, obj):
        if obj.submitter:
            return obj.submitter.username

    def get_submitter_fullname(self, obj):
        if obj.submitter:
            return obj.submitter.get_full_name()

    def get_category_id(self, obj):
        if obj.resolution:
            return obj.resolution.category.id

    def get_category(self, obj):
        if obj.resolution:
            return obj.resolution.category.name

    def get_resolution_id(self, obj):
        if obj.resolution:
            return obj.resolution.id

    def get_resolution(self, obj):
        if obj.resolution:
            return obj.resolution.resolution

    def get_alerts(self, obj):

        return AlertReadOnlySerializer(obj.app_alert_alertmodel_related.all(), many=True).data


class AlertTicketSerializer(serializers.ModelSerializer):
    submitter_username = serializers.SerializerMethodField(read_only=True)
    submitter_fullname = serializers.SerializerMethodField(read_only=True)
    handlers = serializers.SerializerMethodField(read_only=True)
    alerts = serializers.SerializerMethodField(read_only=True)
    category_id = serializers.SerializerMethodField(read_only=True)
    category = serializers.SerializerMethodField(read_only=True)
    resolution_id = serializers.SerializerMethodField(read_only=True)
    resolution = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AlertTicket
        fields = (
            'id',
            'title',
            'description',
            'service',
            'severity',
            'status',
            'creation',
            'modification',
            'submitter',
            'submitter_username',
            'submitter_fullname',
            'category_id',
            'category',
            'resolution_id',
            'resolution',
            'handlers',
            'alerts',
        )
        extra_kwargs = {
            'submitter': {'read_only': True},
            'service': {'read_only': True},
        }

    def get_handlers(self, obj):
        return TicketHandlerReadOnlySerializer(TicketHandler.objects.filter(ticket=obj).all(), many=True).data

    def get_submitter_username(self, obj):
        if obj.submitter:
            return obj.submitter.username

    def get_submitter_fullname(self, obj):
        if obj.submitter:
            return obj.submitter.get_full_name()

    def get_category_id(self, obj):
        if obj.resolution:
            return obj.resolution.category.id

    def get_category(self, obj):
        if obj.resolution:
            return obj.resolution.category.name

    def get_resolution_id(self, obj):
        if obj.resolution:
            return obj.resolution.id

    def get_resolution(self, obj):
        if obj.resolution:
            return obj.resolution.resolution

    def get_alerts(self, obj):

        return AlertReadOnlySerializer(obj.app_alert_alertmodel_related.all(), many=True).data


class AlertServiceSerializer(serializers.Serializer):
    alerts = serializers.JSONField(required=True)

    def validate_alerts(self, alerts: str):
        if not isinstance(alerts, list):
            raise errors.InvalidArgument("param alerts should be a list")
        alert_object_list = list()
        for alert in alerts:
            alert_obj = AlertModel.objects.filter(id=alert).first()
            if not alert_obj:
                raise errors.InvalidArgument(f"unknown alert:`{alert}`")
            alert_object_list.append(alert_obj)
        return alert_object_list


class TicketCustomSerializer(serializers.Serializer):
    service = serializers.CharField(required=True)
    alerts = serializers.JSONField(required=True)
    handlers = serializers.JSONField(required=True)

    def validate_alerts(self, alerts: str):
        if not isinstance(alerts, list):
            raise errors.InvalidArgument("param alerts should be a list")
        alert_object_list = list()
        for alert in alerts:
            alert_obj = AlertModel.objects.filter(id=alert).first()
            if not alert_obj:
                raise errors.InvalidArgument(f"unknown alert:`{alert}`")
            alert_object_list.append(alert_obj)
        return alert_object_list

    def validate_service(self, service: str):
        service_object = AlertService.objects.filter(name_en=service).first()
        if not service_object:
            raise errors.InvalidArgument(f"unknown service:`{service}`")
        return service

    def validate(self, data):
        service_adapter = AlertServerAdapter(data.get('alerts'))
        service = service_adapter.get_service_set()
        if service.name_en != data.get('service'):
            raise errors.InvalidArgument('alerts and service mismatch')
        handlers = data.get('handlers')
        for user in handlers:
            if not service.users.filter(id=user.id).first():
                raise errors.InvalidArgument(f"`{user.id}` does not have permission")
        return data

    def validate_handlers(self, handlers: str):
        if not isinstance(handlers, list):
            raise errors.InvalidArgument("param handlers should be a list")
        user_object_list = list()
        for user in handlers:
            user_object = UserProfile.objects.filter(id=user).first()
            if not user_object:
                raise errors.InvalidArgument(f"unknown user:`{user}`")
            user_object_list.append(user_object)
        return user_object_list


class TicketUpdateSerializer(serializers.ModelSerializer):
    submitter_username = serializers.SerializerMethodField(read_only=True)
    submitter_fullname = serializers.SerializerMethodField(read_only=True)
    handlers = serializers.SerializerMethodField(read_only=True)
    alerts = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AlertTicket
        fields = (
            'id',
            'title',
            'description',
            'service',
            'severity',
            'status',
            'creation',
            'modification',
            'submitter',
            'submitter_username',
            'submitter_fullname',
            'resolution',
            'handlers',
            'alerts',
        )
        extra_kwargs = {
            'submitter': {'read_only': True},
            'service': {'read_only': True},
        }

    def get_handlers(self, obj):
        return TicketHandlerReadOnlySerializer(TicketHandler.objects.filter(ticket=obj).all(), many=True).data

    def get_submitter_username(self, obj):
        if obj.submitter:
            return obj.submitter.username

    def get_submitter_fullname(self, obj):
        if obj.submitter:
            return obj.submitter.get_full_name()

    def get_alerts(self, obj):

        return AlertReadOnlySerializer(obj.app_alert_alertmodel_related.all(), many=True).data


class TicketUpdateHandlersSerializer(serializers.Serializer):
    service = serializers.CharField(required=True)
    handlers = serializers.JSONField(required=True)

    def validate_service(self, service: str):
        service_object = AlertService.objects.filter(name_en=service).first()
        if not service_object:
            raise errors.InvalidArgument(f"unknown service:`{service}`")
        return service

    def validate(self, data):
        service = data.get('service')
        service = AlertService.objects.filter(name_en=service).first()
        handlers = data.get('handlers')
        for user in handlers:
            if not service.users.filter(id=user.id).first():
                raise errors.InvalidArgument(f"`{user.id}` does not have permission")
        return data

    def validate_handlers(self, handlers: str):
        if not isinstance(handlers, list):
            raise errors.InvalidArgument("param handlers should be a list")
        user_object_list = list()
        for user in handlers:
            user_object = UserProfile.objects.filter(id=user).first()
            if not user_object:
                raise errors.InvalidArgument(f"unknown user:`{user}`")
            user_object_list.append(user_object)
        return user_object_list


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
