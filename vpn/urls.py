from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views

app_name = "vpn"

urlpatterns = [
    path('service/<int:service_id>/', login_required(views.VPNView.as_view()), name='service-vpn'),
]
