from django.urls import path, include
from rest_framework.routers import SimpleRouter
from apps.app_scan.viewsets import report_views, task_views


app_name = "scan"


no_slash_router = SimpleRouter(trailing_slash=False)

no_slash_router.register(r"task", task_views.ScanTaskViewSet, basename="task")
no_slash_router.register(r"report", report_views.ScanReportViewSet, basename="report")

urlpatterns = [
    path("", include(no_slash_router.urls)),
]
