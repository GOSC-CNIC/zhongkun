from django.urls import path, include
from rest_framework.routers import SimpleRouter


app_name = 'scan'


no_slash_router = SimpleRouter(trailing_slash=False)


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
