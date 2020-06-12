from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views


app_name = 'servers'

urlpatterns = [
    path('', login_required(views.index), name='index'),
    path('create', login_required(views.ServerCreateView.as_view()), name='create')
]
