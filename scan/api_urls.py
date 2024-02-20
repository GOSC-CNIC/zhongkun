from django.urls import path, include
from rest_framework.routers import SimpleRouter
from scan.viewsets import report_views, task_views, price_view


app_name = "scan"


no_slash_router = SimpleRouter(trailing_slash=False)

no_slash_router.register(r"task", task_views.ScanTaskViewSet, basename="task")
no_slash_router.register(r"report", report_views.ScanReportViewSet, basename="report")
no_slash_router.register(r"price", price_view.ScanPriceViewSet, basename="price")

urlpatterns = [
    path("", include(no_slash_router.urls)),
]
