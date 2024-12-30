from django.urls import path
from django.contrib.auth.decorators import login_required

from . import views


app_name = 'servers'

urlpatterns = [
    path('', login_required(views.ServerView.as_view()), name='server-list'),
    path('create/', login_required(views.ServerCreateView.as_view()), name='create'),
    path('vmware/', login_required(views.VmwareConsoleView.as_view()), name='vmware'),
    path('notice/server/', login_required(views.ServerExpiredEmailView.as_view()),
         name='server-expired-email'),
]
