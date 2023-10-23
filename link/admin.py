from django.contrib import admin
from .models import *


@admin.register(LinkUserRole)
class LinkUserRoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'is_admin', 'is_readonly', 'create_time', 'update_time']
    list_select_related = ['user',]
    raw_id_fields = ['user',]
    search_fields = ['user_username',]
    
@admin.register(LeaseLine)
class LeaseLineAdmin(admin.ModelAdmin):
    list_display = ['id', 'private_line_number', 'lease_line_code', 'line_username', 'endpoint_a', 'endpoint_z',
                    'line_type', 'cable_type', 'bandwidth', 'length', 'provider', 'enable_date',
                    'is_whithdrawal', 'money', 'remarks', 'element_link_id', 'create_time', 'update_time']
    search_fields = ['private_line_number', 'lease_line_code', 'line_username']

@admin.register(OpticalFiber)
class OpticalFiberAdmin(admin.ModelAdmin):
    list_display = ['id', 'fiber_cable_id', 'sequence', 'element_link_id', 'create_time', 'update_time']
    search_fields = ['fiber_cable_id']

@admin.register(Port)
class PortAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'model_type', 'detail', 'distribution_frame_id', 'element_link_id'
                    , 'create_time', 'update_time']
    search_fields = ['number']

@admin.register(ConnectorBox)
class ConnectorBoxAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'place', 'remarks', 'location', 'element_link_id', 'create_time', 'update_time']
    search_fields = ['number']

@admin.register(FiberCable)
class FiberCableAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'fiber_count', 'length', 'endpoint_1', 'endpoint_2',
                    'remarks', 'fiber_ids', 'create_time', 'update_time']
    search_fields = ['number']

@admin.register(DistributionFrame)
class DistributionFrameAdmin(admin.ModelAdmin):
    list_display = ['id', 'device_id', 'model_type', 'size', 'place', 'institution_id', 'remarks', 'create_time', 'update_time']
    search_fields = ['device_id']

@admin.register(LinkOrg)
class LinkOrgAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'remarks', 'location', 'organization', 'create_time', 'update_time']
    search_fields = ['device_id']
    list_select_related = ('organization',)
    raw_id_fields = ('organization',)

@admin.register(ElementLink)
class ElementLinkAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'serials', 'remarks', 'link_status', 'task_id', 'create_time', 'update_time']
    search_fields = ['device_id']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'user', 'endpoint_a', 'endpoint_z', 'bandwidth', 'task_description',
                    'line_type', 'task_person', 'build_person', 'task_status', 'create_time', 'update_time']
    search_fields = ['number', 'user']