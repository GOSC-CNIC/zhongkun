from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views


app_name = 'service'

urlpatterns = [
    path('resources/', login_required(views.resources), name='resources'),
    path('resources/<int:service_id>/', login_required(views.resources), name='service-resources'),
]
