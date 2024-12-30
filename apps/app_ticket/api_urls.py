from django.urls import path, include
from rest_framework.routers import SimpleRouter

from . import ticket_views


app_name = 'ticket'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'support/ticket', ticket_views.TicketViewSet, basename='support-ticket')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
