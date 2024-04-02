from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .apiviews import (
    bill_views, account_views, cash_coupon_views, tradebill_views, trade_test_views,
    trade_views, recharge_views, app_service_views
)


app_name = 'wallet'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'admin/trade/tradebill', tradebill_views.AdminTradeBillViewSet, basename='admin-tradebill')
no_slash_router.register(r'admin/cashcoupon', cash_coupon_views.AdminCashCouponViewSet, basename='admin-coupon')
no_slash_router.register(r'payment-history', bill_views.PaymentHistoryViewSet, basename='payment-history')
no_slash_router.register(r'account/balance', account_views.BalanceAccountViewSet, basename='account-balance')
no_slash_router.register(r'cashcoupon', cash_coupon_views.CashCouponViewSet, basename='cashcoupon')

no_slash_router.register(r'trade/test', trade_test_views.TradeTestViewSet, basename='trade-test')
no_slash_router.register(r'trade/query', trade_views.TradeQueryViewSet, basename='trade-query')
no_slash_router.register(r'trade/charge', trade_views.TradeChargeViewSet, basename='trade-charge')
no_slash_router.register(r'trade/refund', trade_views.TradeRefundViewSet, basename='trade-refund')
no_slash_router.register(r'trade/recharge', recharge_views.RechargeViewSet, basename='trade-recharge')
no_slash_router.register(r'trade/sign', trade_views.TradeSignKeyViewSet, basename='trade-signkey')
no_slash_router.register(r'trade/rsakey', app_service_views.AppRSAKeyViewSet, basename='trade-rsakey')
no_slash_router.register(r'trade/app_service', app_service_views.AppServiceViewSet, basename='app-service')
no_slash_router.register(r'trade/bill/transaction', tradebill_views.AppTradeBillViewSet, basename='app-tradebill')
no_slash_router.register(r'trade/tradebill', tradebill_views.TradeBillViewSet, basename='tradebill')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
