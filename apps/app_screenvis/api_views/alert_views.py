from django.utils.translation import gettext_lazy, gettext as _
from rest_framework.serializers import Serializer

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from apps.app_alert.models import AlertModel, ResolvedAlertModel
from apps.app_screenvis.utils import errors
from apps.app_screenvis.permissions import ScreenAPIIPPermission
from apps.app_screenvis.paginations import AlertPagination
from apps.app_screenvis.serializers import AlertSerializer
from . import NormalGenericViewSet


class AlertViewSet(NormalGenericViewSet):
    queryset = []
    permission_classes = [ScreenAPIIPPermission]
    pagination_class = AlertPagination
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_summary=gettext_lazy('查询告警信息'),
        manual_parameters=[
            openapi.Parameter(
                name='status',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description=_('告警状态筛选，firing(进行中)，resolved(已恢复)')
            )
        ],
        responses={
            200: ''
        }
    )
    def list(self, request, *args, **kwargs):
        """
        查询告警信息

            Http Code 200:
            {
              "has_next": true,                         # 是否有下一页数据
              "next_marker": "cD0xNzE1OTc0NzQ5LjA=",    # 下一页数据开始标记
              "marker": null,                           # 当前页数据开始标记
              "page_size": 100,
              "results": [
                {
                  "id": "q9uwfn6r8q4uqna1db6wfqo9v",
                  "name": "mail_log_mysql",
                  "type": "log",
                  "instance": "159.226.14.40",
                  "port": "",
                  "cluster": "mail_log",
                  "severity": "critical",   # 级别: warning（警告）、error（错误）、 critical（严重错误）
                  "summary": "the message including error tips in plenty of logs",
                  "description": "source: mail_log_mysql level: error content: May 20 09:53:45 159.226.14.40.osmsm session_id: 39244;cmd_time:1716170025;cmd:/home/coremail/bin/mysql_cm;block:0;user:lichaooffice;dev_usr:userb;dev_ip:192.168.0.185;protocol:ssh;risk:1,{\"name\":\"159.226.14.40\"},{\"log_source\":\"alert.log\"}",
                  "start": 1716170048,
                  "end": 1716171249,
                  "status": "firing",   # firing（进行中）、resolved（已恢复）
                  "count": 9,
                  "creation": 1716170049.242474
                }
              ]
            }
        """
        status = request.query_params.get('status', None)

        if status and status not in ['firing', 'resolved']:
            return self.exception_response(errors.InvalidArgument(message=_('查询的告警状态无效')))

        try:
            querysets = self.filter_alert_querysets(status=status)
            paginator = self.paginator
            objs = paginator.paginate_queryset(querysets=querysets, request=request, view=self)
            return paginator.get_paginated_response(data=AlertSerializer(instance=objs, many=True).data)
        except errors.Error as exc:
            return self.exception_response(exc)

    def filter_alert_querysets(self, status: str = None) -> list:
        querysets = [AlertModel.objects.all(), ResolvedAlertModel.objects.all()]

        queryset_list = []
        for qs in querysets:
            queryset_list.append(self._filter_alert_qs(queryset=qs, tags=None, status=status))

        return queryset_list

    @staticmethod
    def _filter_alert_qs(queryset, tags: list, status: str):
        if tags is not None:
            if len(tags) == 0:
                return queryset.none()
            elif len(tags) == 1:
                queryset = queryset.filter(cluster=tags[0])
            else:
                queryset = queryset.filter(cluster__in=tags)

        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_serializer_class(self):
        return Serializer
