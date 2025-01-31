from django.contrib import admin, messages
from django.contrib.admin.filters import SimpleListFilter
from django.utils.translation import gettext, gettext_lazy as _
from django import forms

from utils.model import NoDeleteSelectModelAdmin, BaseModelAdmin
from .models import (
    PaymentHistory, UserPointAccount, VoPointAccount, PayApp, CashCouponActivity, CashCoupon,
    PayAppService, TransactionBill, RefundRecord, Recharge, CashCouponPaymentHistory
)
from .managers import CashCouponActivityManager


class PayAppForm(forms.ModelForm):
    class Meta:
        widgets = {
            'rsa_public_key': forms.Textarea(attrs={'cols': 80, 'rows': 6}),
        }


@admin.register(PaymentHistory)
class PaymentHistoryAdmin(BaseModelAdmin):
    list_display = ('id', 'subject', 'payment_method', 'payable_amounts', 'amounts', 'coupon_amount',
                    'creation_time', 'payment_time', 'status', 'status_desc', 'app_id',
                    'payer_type', 'payer_id', 'payer_name', 'payment_account', 'executor')
    list_display_links = ('id',)
    list_filter = ('status', 'payer_type')
    search_fields = ('id', 'payer_id', 'payer_name')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CashCouponPaymentHistory)
class CashCouponPaymentHistoryAdmin(BaseModelAdmin):
    list_display = ('id', 'cash_coupon', 'amounts', 'before_payment', 'after_payment',
                    'payment_history', 'refund_history', 'creation_time')
    list_display_links = ('id',)
    list_select_related = ('payment_history', 'cash_coupon', 'refund_history')
    search_fields = ('id', 'cash_coupon__id', 'payment_history__id', 'refund_history__id')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(UserPointAccount)
class UserPointAccountAdmin(NoDeleteSelectModelAdmin):
    list_display = ('id', 'balance', 'user',)
    list_display_links = ('id',)
    list_select_related = ('user',)
    readonly_fields = ('balance',)
    search_fields = ('user__username',)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        """
        Given a model instance delete it from the database.
        """
        raise Exception(_('不允许从后台删除。'))


@admin.register(VoPointAccount)
class VoPointAccountAdmin(NoDeleteSelectModelAdmin):
    list_display = ('id', 'balance', 'vo')
    list_display_links = ('id',)
    list_select_related = ('vo',)
    readonly_fields = ('balance',)
    search_fields = ('vo__name',)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        """
        Given a model instance delete it from the database.
        """
        raise Exception(gettext('不允许从后台删除。'))


@admin.register(PayApp)
class PayAppAdmin(NoDeleteSelectModelAdmin):
    form = PayAppForm
    list_display = ('id', 'name', 'status', 'creation_time', 'app_url')
    list_display_links = ('id',)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CashCouponActivity)
class CashCouponActivityAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'face_value', 'effective_time', 'expiration_time',
                    'app_service', 'grant_total', 'granted_count',
                    'grant_status', 'creation_time', 'desc')
    list_display_links = ('name',)
    list_select_related = ('app_service',)
    actions = ['create_coupon_for_activity']

    @admin.action(description=_('为券模板/活动生成券'))
    def create_coupon_for_activity(self, request, queryset):
        length = len(queryset)
        if length == 0:
            self.message_user(request=request, message=gettext('你没有选中任何一个券模板/活动'), level=messages.ERROR)
            return
        if length > 1:
            self.message_user(request=request, message=gettext('每次只能选中一个券模板/活动'), level=messages.ERROR)
            return

        obj = queryset[0]
        try:
            ay, count, err = CashCouponActivityManager().create_coupons_for_template(
                activity_id=obj.id, user=request.user, max_count=50
            )
            if err is not None:
                msg = gettext('为券模板/活动生成券错误（%(error)s），本次成功生成券数量:%(count)d个。') % {
                    'error': str(err), 'count': count
                }
                self.message_user(request=request, message=msg, level=messages.ERROR)
                return
        except Exception as e:
            self.message_user(request=request,
                              message=gettext('为券模板/活动生成券错误') + f': {str(e)}', level=messages.ERROR)
            return

        self.message_user(request=request, message=gettext('成功生成券') + f':{count}', level=messages.SUCCESS)


@admin.register(CashCoupon)
class CashCouponAdmin(BaseModelAdmin):
    list_display = ('id', 'activity', 'face_value', 'balance', 'effective_time', 'expiration_time', 'status',
                    'app_service', 'user', 'vo', 'owner_type', 'issuer', 'granted_time', 'use_scope', 'order_id',
                    'derive_type', 'exchange_code', 'creation_time', 'balance_notice_time', 'expire_notice_time', 'remark')
    list_display_links = ('id',)
    list_select_related = ('app_service', 'user', 'vo', 'activity')
    raw_id_fields = ('activity', 'user', 'vo')
    readonly_fields = ('_coupon_code',)
    list_filter = ('app_service', 'app_service__category', 'owner_type', 'use_scope', 'derive_type')
    search_fields = ('id', 'order_id', 'user__username', 'remark')

    @admin.display(description=_('兑换码'))
    def exchange_code(self, obj):
        return obj.one_exchange_code


# @admin.register(PayOrgnazition)
# class PayOrgnazitionAdmin(BaseModelAdmin):
#     list_display = ('id', 'name', 'name_en', 'abbreviation', 'independent_legal_person', 'country',
#                     'city', 'postal_code', 'address', 'creation_time', 'desc')
#     list_display_links = ('id',)
#     raw_id_fields = ('user',)


class PayServiceOrgFilter(SimpleListFilter):
    title = _("机构")
    parameter_name = 'org_id'

    def lookups(self, request, model_admin):
        r = PayAppService.objects.values_list(
            'orgnazition_id', 'orgnazition__name'
        )
        d = {i[0]: i[1] for i in r if i[0]}
        return [(k, v) for k, v in d.items()]

    def queryset(self, request, queryset):
        org_id = request.GET.get(self.parameter_name)
        if org_id:
            return queryset.filter(orgnazition_id=org_id)


@admin.register(PayAppService)
class PayAppServiceAdmin(NoDeleteSelectModelAdmin):
    list_display = ('id', 'name', 'name_en', 'category', 'app', 'orgnazition', 'creation_time', 'status', 'service_id',
                    'resources', 'contact_person', 'contact_email', 'contact_telephone', 'desc')
    list_display_links = ('id',)
    list_select_related = ('orgnazition', 'app',)
    list_filter = ('category', 'status', PayServiceOrgFilter)
    filter_horizontal = ('users',)
    # raw_id_fields = ('users',)
    raw_id_fields = ('orgnazition',)
    search_fields = ('name', 'name_en')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TransactionBill)
class TransactionBillAdmin(NoDeleteSelectModelAdmin):
    list_display = ('id', 'subject', 'trade_type', 'trade_id', 'out_trade_no',
                    'trade_amounts', 'amounts', 'coupon_amount',
                    'after_balance', 'creation_time', 'app_id',
                    'owner_type', 'owner_id', 'owner_name', 'operator', 'app_service_id')
    list_display_links = ('id',)
    list_filter = ('trade_type', 'owner_type')
    search_fields = ('id', 'owner_id', 'owner_name', 'trade_id')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def delete_model(self, request, obj):
        """
        Given a model instance delete it from the database.
        """
        raise Exception(gettext('不允许从后台删除。'))


@admin.register(RefundRecord)
class RefundRecordAdmin(BaseModelAdmin):
    list_display = ('id', 'trade_id', 'out_order_id', 'out_refund_id', 'refund_reason',
                    'total_amounts', 'refund_amounts', 'real_refund', 'coupon_refund',
                    'status', 'status_desc', 'app_id', 'creation_time', 'success_time',
                    'owner_id', 'owner_name', 'owner_type', 'in_account', 'operator')
    list_display_links = ('id',)
    list_filter = ('status', 'owner_type')
    search_fields = ('id', 'owner_id', 'owner_name', 'out_order_id', 'out_refund_id', 'trade_id')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Recharge)
class RechargeAdmin(BaseModelAdmin):
    list_display = ('id', 'total_amount', 'receipt_amount', 'creation_time', 'status',
                    'trade_channel', 'out_trade_no', 'channel_account',
                    'channel_fee', 'owner_type', 'owner_id', 'owner_name', 'executor', 'in_account')
    list_display_links = ('id',)
    list_filter = ('status', 'owner_type', 'trade_channel')
    search_fields = ('id', 'owner_id', 'owner_name', 'out_trade_no')

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False
