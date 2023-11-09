from django.urls import path, include
from rest_framework.routers import SimpleRouter

from .apiviews import views
from .apiviews import (
    service_quota_views,
    azone_views, order_views, org_views,
    metering_views, bill_views, account_views, cash_coupon_views,
    trade_test_views, trade_views, bucket_views, storage_views,
    ticket_views, storage_metering_views, user_views, app_service_views,
    tradebill_views, recharge_views, email_views, disk_views, flavor_views,
    portal_views, report_storage_views, monitor_metering_views
)
from monitor import monitor_views, log_views
from ipam.viewsets import ipv4_views
from link.viewsets import (
    leaseline_views, fibercable_views, distriframe_views,
    connectorbox_views, task_views, elementlink_views,
    opticalfiber_views, distriframeport_views, linkorg_views,
    linkuserrole_views
    )
from service.viewsets import org_data_center_views

app_name = 'api'


no_slash_router = SimpleRouter(trailing_slash=False)
no_slash_router.register(r'media', views.MediaViewSet, basename='media')
no_slash_router.register(r'server', views.ServersViewSet, basename='servers')
no_slash_router.register(r'server-archive', views.ServerArchiveViewSet, basename='server-archive')
no_slash_router.register(r'image', views.ImageViewSet, basename='images')
no_slash_router.register(r'network', views.NetworkViewSet, basename='networks')
no_slash_router.register(r'vpn', views.VPNViewSet, basename='vpn')
no_slash_router.register(r'flavor', flavor_views.FlavorViewSet, basename='flavor')
no_slash_router.register(r'service', views.ServiceViewSet, basename='service')
no_slash_router.register(r'registry', views.DataCenterViewSet, basename='registry')
no_slash_router.register(r'organization', org_views.OrganizationViewSet, basename='organization')
no_slash_router.register(r'odc', org_data_center_views.OrgDataCenterViewSet, basename='odc')
no_slash_router.register(r'user', user_views.UserViewSet, basename='user')
no_slash_router.register(r'apply/service', views.ApplyVmServiceViewSet, basename='apply-service')
no_slash_router.register(r'apply/organization', views.ApplyOrganizationViewSet, basename='apply-organization')
no_slash_router.register(r'vo', views.VOViewSet, basename='vo')
no_slash_router.register(r'email', email_views.EmailViewSet, basename='email')
no_slash_router.register(r'disk', disk_views.DisksViewSet, basename='disks')

no_slash_router.register(r'monitor/unit/ceph', monitor_views.MonitorUnitCephViewSet, basename='monitor-unit-ceph')
no_slash_router.register(r'monitor/unit/server', monitor_views.MonitorUnitServerViewSet, basename='monitor-unit-server')
no_slash_router.register(r'monitor/unit/tidb', monitor_views.MonitorUnitTiDBViewSet, basename='monitor-unit-tidb')
no_slash_router.register(r'monitor/ceph/query', monitor_views.MonitorCephQueryViewSet, basename='monitor-ceph-query')
no_slash_router.register(r'monitor/server/query', monitor_views.MonitorServerQueryViewSet,
                         basename='monitor-server-query')
no_slash_router.register(r'monitor/video-meeting/query', monitor_views.MonitorVideoMeetingQueryViewSet,
                         basename='monitor-video-meeting-query')
no_slash_router.register(r'monitor/website', monitor_views.MonitorWebsiteViewSet,
                         basename='monitor-website')
no_slash_router.register(r'monitor/website-task', monitor_views.MonitorWebsiteTaskViewSet,
                         basename='monitor-website-task')
no_slash_router.register(r'monitor/tidb/query', monitor_views.MonitorTiDBQueryViewSet, basename='monitor-tidb-query')
no_slash_router.register(r'monitor/log/site', log_views.LogSiteViewSet, basename='monitor-log-site')

no_slash_router.register(r'vms/service/p-quota', service_quota_views.ServivePrivateQuotaViewSet,
                         basename='vms-service-p-quota')
no_slash_router.register(r'vms/service/s-quota', service_quota_views.ServiveShareQuotaViewSet,
                         basename='vms-service-s-quota')
no_slash_router.register(r'azone', azone_views.AvailabilityZoneViewSet, basename='availability-zone')
no_slash_router.register(r'describe-price', order_views.PriceViewSet, basename='describe-price')
no_slash_router.register(r'order', order_views.OrderViewSet, basename='order')
no_slash_router.register(r'period', order_views.PeriodViewSet, basename='period')
no_slash_router.register(r'metering/server', metering_views.MeteringServerViewSet, basename='metering-server')
no_slash_router.register(r'metering/disk', metering_views.MeteringDiskViewSet, basename='metering-disk')
no_slash_router.register(
    r'metering/storage', storage_metering_views.MeteringStorageViewSet, basename='metering-storage')
no_slash_router.register(
    r'metering/admin/storage', storage_metering_views.AdminMeteringStorageViewSet, basename='admin-metering-storage')
no_slash_router.register(
    r'metering/monitor/site', monitor_metering_views.MeteringMonitorSiteViewSet, basename='metering-monitor-site')
no_slash_router.register(r'statement/server', metering_views.StatementServerViewSet, basename='statement-server')
no_slash_router.register(r'statement/disk', metering_views.StatementDiskViewSet, basename='statement-disk')
no_slash_router.register(
    r'statement/storage', storage_metering_views.StatementStorageViewSet, basename='statement-storage')
no_slash_router.register(
    r'statement/monitor/site', monitor_metering_views.StatementMonitorSiteViewSet, basename='statement-monitor-site')
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

no_slash_router.register(r'storage/bucket', bucket_views.BucketViewSet, basename='bucket')
no_slash_router.register(r'storage/service', storage_views.ObjectsServiceViewSet, basename='storage-service')
no_slash_router.register(r'support/ticket', ticket_views.TicketViewSet, basename='support-ticket')

no_slash_router.register(r'admin/cashcoupon', cash_coupon_views.AdminCashCouponViewSet, basename='admin-coupon')
no_slash_router.register(r'admin/storage/bucket', bucket_views.AdminBucketViewSet, basename='admin-bucket')
no_slash_router.register(
    r'admin/storage/statistics', storage_views.StorageStatisticsViewSet, basename='admin-storage-statistics')
no_slash_router.register(r'admin/trade/tradebill', tradebill_views.AdminTradeBillViewSet, basename='admin-tradebill')
no_slash_router.register(
    r'admin/metering/storage/statistics', storage_metering_views.AdminMeteringStorageStatisticsViewSet,
    basename='admin-metering-storage-statistics')
no_slash_router.register(
    r'admin/user/statistics', user_views.AdminUserStatisticsViewSet, basename='admin-user-statistics')
no_slash_router.register(
    r'admin/metering/server/statistics', metering_views.AdminMeteringServerStatisticsViewSet,
    basename='admin-metering-server-statistics')
no_slash_router.register(r'admin/flavor', flavor_views.AdminFlavorViewSet, basename='admin-flavor')
no_slash_router.register(r'admin/odc', org_data_center_views.AdminOrgDataCenterViewSet, basename='admin-odc')

no_slash_router.register(r'portal/service', portal_views.PortalServiceViewSet, basename='portal-service')
no_slash_router.register(r'report/storage/bucket/stats/monthly', report_storage_views.BucketStatsMonthlyViewSet,
                         basename='report-bucket-stats-monthly')
no_slash_router.register(r'report/storage/stats/monthly', report_storage_views.StorageStatsMonthlyViewSet,
                         basename='report-storage-stats-monthly')

no_slash_router.register(r'ipam/ipv4range', ipv4_views.IPv4RangeViewSet, basename='ipam-ipv4range')
no_slash_router.register(r'ipam/user/role', ipv4_views.IPAMUserRoleViewSet, basename='ipam-userrole')

no_slash_router.register(r'link/leaseline', leaseline_views.LeaseLineViewSet, basename='link-leaseline')
no_slash_router.register(r'link/fibercable', fibercable_views.FiberCableViewSet, basename='link-fibercable')
no_slash_router.register(r'link/distributionframe', distriframe_views.DistriFrameViewSet, basename='link-distributionframe')
no_slash_router.register(r'link/connectorbox', connectorbox_views.ConnectorBoxViewSet, basename='link-connectorbox')
no_slash_router.register(r'link/task', task_views.TaskViewSet, basename='link-task')
no_slash_router.register(r'link/elementlink', elementlink_views.ElementLinkViewSet, basename='link-elementlink')
no_slash_router.register(r'link/opticalfiber', opticalfiber_views.OpticalFiberViewSet, basename='link-opticalfiber')
no_slash_router.register(r'link/distriframeport', distriframeport_views.DistriFramePortViewSet, basename='link-distriframeport')
no_slash_router.register(r'link/linkorg', linkorg_views.linkOrgViewSet, basename='link-linkorg')
no_slash_router.register(r'link/user/role', linkuserrole_views.LinkUserRoleViewSet, basename='link-userrole')


urlpatterns = [
    path('', include(no_slash_router.urls)),
]
