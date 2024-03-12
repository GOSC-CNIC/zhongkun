from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .api_views import coupon_views


app_name = 'apply'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'coupon', coupon_views.CouponApplyViewSet, basename='coupon')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
