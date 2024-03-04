from django.urls import path, include
from rest_framework.routers import SimpleRouter

from order.apiviews import order_views, refund_views


app_name = 'order'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'describe-price', order_views.PriceViewSet, basename='describe-price')
no_slash_router.register(r'order', order_views.OrderViewSet, basename='order')
no_slash_router.register(r'period', order_views.PeriodViewSet, basename='period')
no_slash_router.register(r'order-refund', refund_views.RefundViewSet, basename='order-refund')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
