from django.contrib import admin
from .models import *


@admin.register(LinkUserRole)
class LinkUserRoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'is_admin',
                    'is_readonly', 'create_time', 'update_time']
    list_select_related = ['user',]
    raw_id_fields = ['user',]
    search_fields = ['user_username',]


@admin.register(LeaseLine)
class LeaseLineAdmin(admin.ModelAdmin):
    list_display = ['id', 'private_line_number', 'lease_line_code', 'line_username',
                    'endpoint_a', 'endpoint_z', 'line_type', 'cable_type',
                    'bandwidth', 'length', 'provider', 'enable_date', 'is_whithdrawal',
                    'money', 'remarks', 'element', 'create_time', 'update_time']
    search_fields = ['id', 'private_line_number',
                     'lease_line_code', 'line_username']


@admin.register(OpticalFiber)
class OpticalFiberAdmin(admin.ModelAdmin):
    list_display = ['id', 'fiber_cable', 'sequence',
                    'element', 'create_time', 'update_time']
    search_fields = ['id']


@admin.register(DistriFramePort)
class DistriFramePortAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'row', 'col',
                    'distribution_frame', 'element', 'create_time', 'update_time']
    search_fields = ['id', 'number']


@admin.register(ConnectorBox)
class ConnectorBoxAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'place', 'remarks',
                    'location', 'element', 'create_time', 'update_time']
    search_fields = ['id', 'number']


@admin.register(FiberCable)
class FiberCableAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'fiber_count', 'length',
                    'endpoint_1', 'endpoint_2', 'remarks', 'create_time', 'update_time']
    search_fields = ['id', 'number']


@admin.register(DistributionFrame)
class DistributionFrameAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'model_type', 'row_count', 'col_count',
                    'place', 'link_org', 'remarks', 'create_time', 'update_time']
    search_fields = ['id', 'number']

@admin.register(LinkOrg)
class LinkOrgAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'remarks', 'location',
                    'data_center', 'create_time', 'update_time']
    search_fields = ['id', 'name']


@admin.register(ElementLink)
class ElementLinkAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'element_ids', 'remarks',
                    'link_status', 'task', 'create_time', 'update_time']
    search_fields = ['id', 'device_id']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'user', 'endpoint_a', 'endpoint_z',
                    'bandwidth', 'task_description', 'line_type', 'task_person',
                    'build_person', 'task_status', 'create_time', 'update_time']
    search_fields = ['id', 'number', 'user']


@admin.register(Element)
class ElementAdmin(admin.ModelAdmin):
    list_display = ['id', 'object_type',
                    'object_id', 'create_time', 'update_time']
    search_fields = ['id', 'object_id']
    list_filter = ['object_type']

