from drf_yasg.utils import swagger_auto_schema
from rest_framework.permissions import IsAuthenticated
from django.utils.translation import gettext_lazy
from apps.api.viewsets import CustomGenericViewSet
from apps.app_scan.handlers.report_handler import ReportHandler


class ScanReportViewSet(CustomGenericViewSet):
    queryset = []
    permission_classes = [IsAuthenticated]
    lookup_field = "task_id"

    @swagger_auto_schema(
        operation_summary=gettext_lazy("下载任务报告"),
        manual_parameters=[],
        responses={200: ""},
    )
    def retrieve(self, request, *args, **kwargs):
        """
        下载安全扫描任务报告
        """
        return ReportHandler.download_task_report(
            view=self, request=request, kwargs=kwargs
        )
