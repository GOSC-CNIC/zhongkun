from typing import Union
from datetime import datetime

from django.contrib import admin
from django.utils.translation import gettext_lazy
from django.utils import timezone as dj_timezone

from utils.model import BaseModelAdmin
from apps.app_alert.models import ResolvedAlertModel, AlertModel


def ts_to_time_dispaly(ts: Union[int, float]) -> str:
    if ts is None:
        return ''

    try:
        dt = datetime.fromtimestamp(ts, tz=dj_timezone.get_default_timezone())
    except Exception as exc:
        return str(ts)

    return dt.isoformat(sep=' ')


class AlertAdminBase(BaseModelAdmin):
    list_display = ['id', 'name', 'type', 'status', 'severity',
                    'start', 'show_start', 'end', 'show_end', 'show_recovery', 'count',
                    'instance', 'port', 'cluster', 'fingerprint',
                    'show_creation', 'show_first_notification', 'show_last_notification',
                    'summary', 'description'
                    ]
    list_display_links = ('id', 'name')
    search_fields = ('summary', 'description', 'instance', 'cluster')

    @admin.display(description=gettext_lazy("开始时间"))
    def show_start(self, obj):
        return ts_to_time_dispaly(obj.start)

    @admin.display(description=gettext_lazy("结束时间"))
    def show_end(self, obj):
        return ts_to_time_dispaly(obj.end)

    @admin.display(description=gettext_lazy("恢复时间"))
    def show_recovery(self, obj):
        return ts_to_time_dispaly(obj.recovery)

    @admin.display(description=gettext_lazy("创建时间"))
    def show_creation(self, obj):
        return ts_to_time_dispaly(obj.creation)

    @admin.display(description=gettext_lazy("首次通知时间"))
    def show_first_notification(self, obj):
        return ts_to_time_dispaly(obj.first_notification)

    @admin.display(description=gettext_lazy("上次通知时间"))
    def show_last_notification(self, obj):
        return ts_to_time_dispaly(obj.last_notification)


@admin.register(AlertModel)
class AlertModelAdmin(AlertAdminBase):
    pass


@admin.register(ResolvedAlertModel)
class ResolvedAlertModelAdmin(AlertAdminBase):
    pass
