from django.contrib import admin
from . import models


@admin.register(models.LinkUserRole)
class LinkUserRoleAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'is_admin',
                    'is_readonly', 'create_time', 'update_time']
    list_select_related = ['user',]
    raw_id_fields = ['user',]
    search_fields = ['user_username',]


@admin.register(models.LeaseLine)
class LeaseLineAdmin(admin.ModelAdmin):
    list_display = ['id', 'private_line_number', 'lease_line_code', 'line_username',
                    'endpoint_a', 'endpoint_z', 'line_type', 'cable_type',
                    'bandwidth', 'length', 'provider', 'enable_date', 'is_whithdrawal',
                    'money', 'remarks', 'element', 'create_time', 'update_time']
    search_fields = ['id', 'private_line_number', 'lease_line_code', 'line_username', 'remarks']
    raw_id_fields = ('element',)


@admin.register(models.OpticalFiber)
class OpticalFiberAdmin(admin.ModelAdmin):
    list_display = ['id', 'fiber_cable', 'sequence',
                    'element', 'create_time', 'update_time']
    search_fields = ['id']
    raw_id_fields = ('element', 'fiber_cable')


@admin.register(models.DistriFramePort)
class DistriFramePortAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'row', 'col',
                    'distribution_frame', 'element', 'create_time', 'update_time']
    search_fields = ['id', 'number']
    raw_id_fields = ('distribution_frame', 'element')


@admin.register(models.ConnectorBox)
class ConnectorBoxAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'place', 'remarks',
                    'location', 'element', 'create_time', 'update_time']
    search_fields = ['id', 'number']
    raw_id_fields = ('element',)


@admin.register(models.FiberCable)
class FiberCableAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'fiber_count', 'length',
                    'endpoint_1', 'endpoint_2', 'remarks', 'create_time', 'update_time']
    search_fields = ['id', 'number']


@admin.register(models.DistributionFrame)
class DistributionFrameAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'model_type', 'row_count', 'col_count',
                    'place', 'link_org', 'remarks', 'create_time', 'update_time']
    search_fields = ['id', 'number', 'remarks']
    raw_id_fields = ('link_org',)


@admin.register(models.ElementLink)
class ElementLinkAdmin(admin.ModelAdmin):
    list_display = ['id', 'element_id', 'link_id', 'index', 'sub_index']
    search_fields = ['id', 'element_id', 'link_id']
    raw_id_fields = ('element', 'link')


@admin.register(models.Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'user', 'endpoint_a', 'endpoint_z',
                    'bandwidth', 'description', 'line_type', 'business_person',
                    'build_person', 'link_status', 'remarks', 'enable_date', 
                    'create_time', 'update_time']
    search_fields = ['id', 'number', 'user']


@admin.register(models.Element)
class ElementAdmin(admin.ModelAdmin):
    list_display = ['id', 'object_type',
                    'object_id', 'create_time', 'update_time']
    search_fields = ['id', 'object_id']
    list_filter = ['object_type']
