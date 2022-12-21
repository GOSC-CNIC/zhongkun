from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .apiviews import views
from .apiviews import (
    monitor_views, service_quota_views,
    azone_views, order_views,
    metering_views, bill_views, account_views, cash_coupon_views,
    trade_test_views, trade_views, bucket_views, storage_views,
    ticket_views, storage_metering_views, user_views, app_service_views,
    tradebill_views
)

app_name = 'api'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'media', views.MediaViewSet, basename='media')
no_slash_router.register(r'server', views.ServersViewSet, basename='servers')
no_slash_router.register(r'server-archive', views.ServerArchiveViewSet, basename='server-archive')
no_slash_router.register(r'image', views.ImageViewSet, basename='images')
no_slash_router.register(r'network', views.NetworkViewSet, basename='networks')
no_slash_router.register(r'vpn', views.VPNViewSet, basename='vpn')
no_slash_router.register(r'flavor', views.FlavorViewSet, basename='flavor')
no_slash_router.register(r'service', views.ServiceViewSet, basename='service')
no_slash_router.register(r'registry', views.DataCenterViewSet, basename='registry')
no_slash_router.register(r'user', user_views.UserViewSet, basename='user')
no_slash_router.register(r'apply/service', views.ApplyVmServiceViewSet, basename='apply-service')
no_slash_router.register(r'apply/organization', views.ApplyOrganizationViewSet, basename='apply-organization')
no_slash_router.register(r'vo', views.VOViewSet, basename='vo')

no_slash_router.register(r'monitor/unit/ceph', monitor_views.MonitorUnitCephViewSet, basename='monitor-unit-ceph')
no_slash_router.register(r'monitor/unit/server', monitor_views.MonitorUnitServerViewSet, basename='monitor-unit-server')
no_slash_router.register(r'monitor/ceph/query', monitor_views.MonitorCephQueryViewSet, basename='monitor-ceph-query')
no_slash_router.register(r'monitor/server/query', monitor_views.MonitorServerQueryViewSet,
                         basename='monitor-server-query')
no_slash_router.register(r'monitor/video-meeting/query', monitor_views.MonitorVideoMeetingQueryViewSet,
                         basename='monitor-video-meeting-query')
no_slash_router.register(r'vms/service/p-quota', service_quota_views.ServivePrivateQuotaViewSet,
                         basename='vms-service-p-quota')
no_slash_router.register(r'vms/service/s-quota', service_quota_views.ServiveShareQuotaViewSet,
                         basename='vms-service-s-quota')
no_slash_router.register(r'azone', azone_views.AvailabilityZoneViewSet, basename='availability-zone')
no_slash_router.register(r'describe-price', order_views.PriceViewSet, basename='describe-price')
no_slash_router.register(r'order', order_views.OrderViewSet, basename='order')
no_slash_router.register(r'metering/server', metering_views.MeteringServerViewSet, basename='metering-server')
no_slash_router.register(
    r'metering/storage', storage_metering_views.MeteringStorageViewSet, basename='metering-storage')
no_slash_router.register(r'statement/server', metering_views.StatementServerViewSet, basename='statement-server')
no_slash_router.register(
    r'statement/storage', storage_metering_views.StatementStorageViewSet, basename='statement-storage')
no_slash_router.register(r'payment-history', bill_views.PaymentHistoryViewSet, basename='payment-history')
no_slash_router.register(r'account/balance', account_views.BalanceAccountViewSet, basename='account-balance')
no_slash_router.register(r'cashcoupon', cash_coupon_views.CashCouponViewSet, basename='cashcoupon')
no_slash_router.register(r'admin/cashcoupon', cash_coupon_views.AdminCashCouponViewSet, basename='admin-coupon')
no_slash_router.register(r'trade/test', trade_test_views.TradeTestViewSet, basename='trade-test')
no_slash_router.register(r'trade/query', trade_views.TradeQueryViewSet, basename='trade-query')
no_slash_router.register(r'trade/charge', trade_views.TradeChargeViewSet, basename='trade-charge')
no_slash_router.register(r'trade/sign', trade_views.TradeSignKeyViewSet, basename='trade-signkey')
no_slash_router.register(r'trade/app_service', app_service_views.AppServiceViewSet, basename='app-service')
no_slash_router.register(r'trade/rsakey', app_service_views.AppRSAKeyViewSet, basename='trade-rsakey')
no_slash_router.register(r'trade/refund', trade_views.TradeRefundViewSet, basename='trade-refund')
no_slash_router.register(r'trade/tradebill', tradebill_views.TradeBillViewSet, basename='tradebill')

no_slash_router.register(r'storage/bucket', bucket_views.BucketViewSet, basename='bucket')
no_slash_router.register(r'storage/service', storage_views.ObjectsServiceViewSet, basename='storage-service')
no_slash_router.register(r'support/ticket', ticket_views.TicketViewSet, basename='support-ticket')

urlpatterns = [
    path('', include(no_slash_router.urls)),
]
