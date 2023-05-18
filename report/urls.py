from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

app_name = 'report'


urlpatterns = [
    path('monthly', views.monthly_report_view, name='monthly-report'),
]

