from django.urls import path, include
from rest_framework.routers import SimpleRouter

from apps.app_users.api_views import user_views


app_name = 'users'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'user', user_views.UserViewSet, basename='user')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
