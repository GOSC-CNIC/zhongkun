from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views


app_name = 'service'

urlpatterns = [
    path('', login_required(views.home), name='index'),
    path('<int:service_id>/', login_required(views.home), name='home'),
]
