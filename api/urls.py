from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .apiviews import views
from .apiviews import (
    bill_views, account_views, cash_coupon_views,
    trade_test_views, trade_views,
    user_views, app_service_views,
    tradebill_views, recharge_views, email_views,
    portal_views, report_storage_views
)


app_name = 'api'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'media', views.MediaViewSet, basename='media')
no_slash_router.register(r'vpn', views.VPNViewSet, basename='vpn')
no_slash_router.register(r'registry', views.DataCenterViewSet, basename='registry')
no_slash_router.register(r'user', user_views.UserViewSet, basename='user')
no_slash_router.register(r'apply/service', views.ApplyVmServiceViewSet, basename='apply-service')
no_slash_router.register(r'apply/organization', views.ApplyOrganizationViewSet, basename='apply-organization')
no_slash_router.register(r'email', email_views.EmailViewSet, basename='email')

no_slash_router.register(r'payment-history', bill_views.PaymentHistoryViewSet, basename='payment-history')
no_slash_router.register(r'account/balance', account_views.BalanceAccountViewSet, basename='account-balance')
no_slash_router.register(r'cashcoupon', cash_coupon_views.CashCouponViewSet, basename='cashcoupon')
no_slash_router.register(r'trade/test', trade_test_views.TradeTestViewSet, basename='trade-test')
no_slash_router.register(r'trade/query', trade_views.TradeQueryViewSet, basename='trade-query')
no_slash_router.register(r'trade/charge', trade_views.TradeChargeViewSet, basename='trade-charge')
no_slash_router.register(r'trade/sign', trade_views.TradeSignKeyViewSet, basename='trade-signkey')
no_slash_router.register(r'trade/app_service', app_service_views.AppServiceViewSet, basename='app-service')
no_slash_router.register(r'trade/rsakey', app_service_views.AppRSAKeyViewSet, basename='trade-rsakey')
no_slash_router.register(r'trade/refund', trade_views.TradeRefundViewSet, basename='trade-refund')
no_slash_router.register(r'trade/bill/transaction', tradebill_views.AppTradeBillViewSet, basename='app-tradebill')
no_slash_router.register(r'trade/tradebill', tradebill_views.TradeBillViewSet, basename='tradebill')
no_slash_router.register(r'trade/recharge', recharge_views.RechargeViewSet, basename='trade-recharge')
no_slash_router.register(r'admin/cashcoupon', cash_coupon_views.AdminCashCouponViewSet, basename='admin-coupon')
no_slash_router.register(r'admin/trade/tradebill', tradebill_views.AdminTradeBillViewSet, basename='admin-tradebill')
no_slash_router.register(
    r'admin/user/statistics', user_views.AdminUserStatisticsViewSet, basename='admin-user-statistics')

no_slash_router.register(r'portal/service', portal_views.PortalServiceViewSet, basename='portal-service')
no_slash_router.register(r'report/storage/bucket/stats/monthly', report_storage_views.BucketStatsMonthlyViewSet,
                         basename='report-bucket-stats-monthly')
no_slash_router.register(r'report/storage/stats/monthly', report_storage_views.StorageStatsMonthlyViewSet,
                         basename='report-storage-stats-monthly')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
