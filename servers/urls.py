from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views


app_name = 'servers'

urlpatterns = [
    path('', login_required(views.ServerView.as_view()), name='server-list'),
    path('service/<int:service_id>/', login_required(views.ServerView.as_view()), name='service-server-list'),
    path('create/', login_required(views.ServerCreateView.as_view()), name='create'),
    path('vmware/', login_required(views.VmwareConsoleView.as_view()), name='vmware')

]
