from django.urls import path

from . import views

app_name = 'probe'

urlpatterns = [
    path('details/', views.ProbeDetailsViews.as_view(), name='probe-details'),
]
