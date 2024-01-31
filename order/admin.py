from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext

from utils.model import BaseModelAdmin
from .models import Order, Resource, Price, Period


@admin.register(Order)
class OrderAdmin(BaseModelAdmin):
    list_display = ('id', 'order_type', 'number', 'status', 'total_amount', 'payable_amount', 'pay_amount',
                    'balance_amount', 'coupon_amount', 'service_name',
                    'resource_type', 'period', 'pay_type', 'payment_time',
                    'creation_time', 'trading_status', 'completion_time', 'deleted',
                    'owner_type', 'username', 'vo_name', 'cancelled_time', 'app_service_id')
    list_display_links = ('id',)
    list_filter = ('owner_type', 'resource_type', 'pay_type', 'status', 'order_type', 'trading_status', 'deleted')
    search_fields = ('id', 'username', 'vo_name')

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Resource)
class ResourceAdmin(BaseModelAdmin):
    list_display = ('id', 'order_id', 'resource_type', 'instance_id', 'instance_status', 'delivered_time',
                    'desc', 'instance_remark', 'creation_time')
    list_display_links = ('id',)
    list_filter = ('resource_type', 'instance_status')
    search_fields = ('order__id', 'instance_id')
    raw_id_fields = ('order',)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Price)
class PriceAdmin(BaseModelAdmin):
    list_display = ('id', 'vm_ram', 'vm_cpu', 'vm_pub_ip', 'vm_disk', 'vm_disk_snap', 'vm_upstream',
                    'vm_downstream', 'disk_size', 'disk_snap', 'obj_size', 'obj_upstream', 'obj_downstream',
                    'obj_replication', 'obj_get_request', 'obj_put_request', 'prepaid_discount',
                    'mntr_site_base', 'mntr_site_tamper', 'mntr_site_security')
    list_display_links = ('id',)


class PeriodModelForm(forms.ModelForm):
    def clean(self):
        data = super().clean()
        period = data['period']
        service = data['service']
        service_id = service.id if service else None
        if not self.instance.id:    # add new
            if service_id:
                if Period.objects.filter(period=period, service_id=service_id).exists():
                    raise ValidationError(message=gettext('服务单元已存在相同月数的时长选项'))

            if Period.objects.filter(period=period, service_id__isnull=True).exists():
                raise ValidationError(message=gettext('已存在相同月数的公共时长选项'))
        else:   # change
            qs = Period.objects.exclude(id=self.instance.id).filter(period=period)
            if service_id:
                qs = qs.filter(service_id=service_id)
            else:
                qs = qs.filter(service_id__isnull=True)

            if qs.exists():
                raise ValidationError(message=gettext('目标服务单元或者公共选项已存在月数相同的时长选项'))

        return data


@admin.register(Period)
class PeriodAdmin(BaseModelAdmin):
    form = PeriodModelForm
    list_display_links = ('id',)
    list_display = ('id', 'period', 'enable', 'service', 'creation_time')
    ordering = ('service', 'period',)
    list_filter = ['service']
