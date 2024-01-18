import ipaddress

from django.contrib import admin
from django.utils.translation import gettext_lazy
from django.db.models.constants import LOOKUP_SEP
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils.text import smart_split, unescape_string_literal
from django.contrib.admin.utils import lookup_spawns_duplicates

from .models import (
    NetBoxUserRole, OrgVirtualObject, ASN, IPv4Address, IPv4Range, IPv4RangeRecord,
    IPv6Range, IPv6Address, IPv6RangeRecord, ContactPerson,
    LeaseLine, OpticalFiber, DistributionFrame, DistriFramePort, ConnectorBox,
    FiberCable, ElementLink, Element, Link
)


class IPModelAdmin(admin.ModelAdmin):
    def get_search_q_querys(self, request, queryset, search_term):
        """
        return: [Q()], may_have_duplicates
        """
        # Apply keyword searches.
        def construct_search(field_name):
            if field_name.startswith("^"):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith("="):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith("@"):
                return "%s__search" % field_name[1:]
            # Use field_name if it includes a lookup.
            opts = queryset.model._meta
            lookup_fields = field_name.split(LOOKUP_SEP)
            # Go through the fields, following all relations.
            prev_field = None
            for path_part in lookup_fields:
                if path_part == "pk":
                    path_part = opts.pk.name
                try:
                    field = opts.get_field(path_part)
                except FieldDoesNotExist:
                    # Use valid query lookups.
                    if prev_field and prev_field.get_lookup(path_part):
                        return field_name
                else:
                    prev_field = field
                    if hasattr(field, "path_infos"):
                        # Update opts to follow the relation.
                        opts = field.path_infos[-1].to_opts
            # Otherwise, use the field with icontains.
            return "%s__icontains" % field_name

        may_have_duplicates = False
        search_fields = self.get_search_fields(request)
        term_queries = []
        if search_fields and search_term:
            orm_lookups = [
                construct_search(str(search_field)) for search_field in search_fields
            ]
            for bit in smart_split(search_term):
                if bit.startswith(('"', "'")) and bit[0] == bit[-1]:
                    bit = unescape_string_literal(bit)
                or_queries = models.Q.create(
                    [(orm_lookup, bit) for orm_lookup in orm_lookups],
                    connector=models.Q.OR,
                )
                term_queries.append(or_queries)

            may_have_duplicates |= any(
                lookup_spawns_duplicates(self.opts, search_spec)
                for search_spec in orm_lookups
            )
        return term_queries, may_have_duplicates

    @staticmethod
    def get_ip_search_q(search_term):
        return None

    def get_search_results(self, request, queryset, search_term):
        term_queries, may_have_duplicates = self.get_search_q_querys(
            request=request, queryset=queryset, search_term=search_term
        )

        or_ip_querys = self.get_ip_search_q(search_term)
        if or_ip_querys is not None:
            if term_queries:
                term_queries[0] |= or_ip_querys
            else:
                term_queries.append(or_ip_querys)

        if term_queries:
            queryset = queryset.filter(models.Q.create(term_queries))

        return queryset, may_have_duplicates


@admin.register(NetBoxUserRole)
class NetBoxUserRoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'is_ipam_admin', 'is_ipam_readonly', 'is_link_admin', 'is_link_readonly',
                    'creation_time', 'update_time')
    list_select_related = ('user',)
    raw_id_fields = ('user',)
    search_fields = ('user_username',)
    filter_horizontal = ('organizations',)


@admin.register(OrgVirtualObject)
class OrgVirtualObjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'organization', 'creation_time', 'remark')
    list_select_related = ('organization',)
    raw_id_fields = ('organization',)
    search_fields = ('name', 'organization__name', 'remark')
    filter_horizontal = ('contacts',)
    readonly_fields = ('creation_time',)


@admin.register(ContactPerson)
class ContactPersonAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'name', 'telephone', 'email', 'address', 'creation_time', 'remarks')

    search_fields = ('name', 'telephone', 'email', 'address', 'remarks')
    readonly_fields = ('creation_time', 'update_time')


@admin.register(ASN)
class ASNAdmin(admin.ModelAdmin):
    list_display = ('id', 'number', 'name', 'creation_time')
    search_fields = ('name',)


@admin.register(IPv4Address)
class IPv4AddressAdmin(IPModelAdmin):
    list_display = ('id', 'ip_address', 'display_ip_addr', 'creation_time', 'update_time',
                    'admin_remark', 'remark')
    # list_select_related = ('ip_range',)
    # raw_id_fields = ('ip_range',)
    search_fields = ('admin_remark', 'remark', 'ip_address')

    @staticmethod
    @admin.display(description=gettext_lazy('IP地址'))
    def display_ip_addr(obj: IPv4Address):
        return obj.ip_address_str()

    @staticmethod
    def get_ip_search_q(search_term):
        if not search_term:
            return None

        try:
            ip_int = int(ipaddress.IPv4Address(search_term))
            return models.Q(ip_address=ip_int)
        except ipaddress.AddressValueError:
            return None


@admin.register(IPv4Range)
class IPv4RangeAdmin(IPModelAdmin):
    list_display = ('id', 'name', 'start_address', 'end_address', 'mask_len', 'display_ip_range', 'asn', 'status',
                    'org_virt_obj', 'org_name', 'assigned_time', 'creation_time', 'update_time',
                    'admin_remark', 'remark')
    list_select_related = ('asn', 'org_virt_obj', 'org_virt_obj__organization')
    list_filter = ('status', 'mask_len')
    search_fields = ('name', 'admin_remark', 'remark', 'org_virt_obj__name', 'org_virt_obj__organization__name')
    raw_id_fields = ('org_virt_obj',)

    @staticmethod
    @admin.display(description=gettext_lazy('地址段易读显示'))
    def display_ip_range(obj: IPv4Range):
        return obj.ip_range_display()

    @staticmethod
    @admin.display(description=gettext_lazy('机构'))
    def org_name(obj: IPv4Range):
        if obj.org_virt_obj and obj.org_virt_obj.organization:
            return obj.org_virt_obj.organization.name

        return ''

    @staticmethod
    def get_ip_search_q(search_term):
        if not search_term:
            return None

        try:
            ip_int = int(ipaddress.IPv4Address(search_term))
            return models.Q.create(
                [('start_address__lte', ip_int), ('end_address__gte', ip_int)], connector=models.Q.AND)
        except ipaddress.AddressValueError:
            return None


@admin.register(IPv4RangeRecord)
class IPv4RangeRecordAdmin(IPModelAdmin):
    list_display = ('id', 'start_address', 'end_address', 'mask_len', 'display_ip_range',
                    'org_virt_obj', 'creation_time', 'user', 'remark')
    list_select_related = ('user', 'org_virt_obj')
    raw_id_fields = ('org_virt_obj', 'user')
    search_fields = ('remark',)

    @staticmethod
    def display_ip_range(obj: IPv4RangeRecord):
        return obj.ip_range_display()

    @staticmethod
    def get_ip_search_q(search_term):
        if not search_term:
            return None

        try:
            ip_int = int(ipaddress.IPv4Address(search_term))
            return models.Q.create(
                [('start_address__lte', ip_int), ('end_address__gte', ip_int)], connector=models.Q.AND)
        except ipaddress.AddressValueError:
            return None


@admin.register(IPv6Address)
class IPv6AddressAdmin(IPModelAdmin):
    list_display = ('id', 'display_ip_addr', 'creation_time', 'update_time',
                    'admin_remark', 'remark')
    search_fields = ('admin_remark', 'remark')

    @staticmethod
    @admin.display(description=gettext_lazy('IP地址'))
    def display_ip_addr(obj: IPv6Address):
        return obj.ip_address_str()

    @staticmethod
    def get_ip_search_q(search_term):
        if not search_term:
            return None

        try:
            ip_bytes = ipaddress.IPv6Address(search_term).packed
            return models.Q(ip_address=ip_bytes)
        except ipaddress.AddressValueError:
            return None


@admin.register(IPv6Range)
class IPv6RangeAdmin(IPModelAdmin):
    list_display = ('id', 'name', 'prefixlen', 'display_ip_range', 'asn', 'status',
                    'org_virt_obj', 'org_name', 'assigned_time', 'creation_time', 'update_time',
                    'admin_remark', 'remark')
    list_select_related = ('asn', 'org_virt_obj', 'org_virt_obj__organization')
    list_filter = ('status', 'prefixlen')
    search_fields = ('name', 'admin_remark', 'remark', 'org_virt_obj__name', 'org_virt_obj__organization__name')
    raw_id_fields = ('org_virt_obj',)

    @staticmethod
    @admin.display(description=gettext_lazy('地址段易读显示'))
    def display_ip_range(obj: IPv4Range):
        return obj.ip_range_display()

    @staticmethod
    @admin.display(description=gettext_lazy('机构'))
    def org_name(obj: IPv4Range):
        if obj.org_virt_obj and obj.org_virt_obj.organization:
            return obj.org_virt_obj.organization.name

        return ''

    @staticmethod
    def get_ip_search_q(search_term):
        if not search_term:
            return None

        try:
            ip_bytes = ipaddress.IPv6Address(search_term).packed
            return models.Q.create(
                [('start_address__lte', ip_bytes), ('end_address__gte', ip_bytes)], connector=models.Q.AND)
        except ipaddress.AddressValueError:
            return None


@admin.register(IPv6RangeRecord)
class IPv6RangeRecordAdmin(IPModelAdmin):
    list_display = ('id', 'prefixlen', 'display_ip_range',
                    'org_virt_obj', 'creation_time', 'user', 'remark')
    list_select_related = ('user', 'org_virt_obj')
    raw_id_fields = ('org_virt_obj', 'user')
    search_fields = ('remark',)

    @staticmethod
    def display_ip_range(obj: IPv6RangeRecord):
        return obj.ip_range_display()

    @staticmethod
    def get_ip_search_q(search_term):
        if not search_term:
            return None

        try:
            ip_bytes = ipaddress.IPv6Address(search_term).packed
            return models.Q.create(
                [('start_address__lte', ip_bytes), ('end_address__gte', ip_bytes)], connector=models.Q.AND)
        except ipaddress.AddressValueError:
            return None


@admin.register(LeaseLine)
class LeaseLineAdmin(admin.ModelAdmin):
    list_display = ['id', 'private_line_number', 'lease_line_code', 'line_username',
                    'endpoint_a', 'endpoint_z', 'line_type', 'cable_type',
                    'bandwidth', 'length', 'provider', 'enable_date', 'is_whithdrawal',
                    'money', 'remarks', 'element', 'create_time', 'update_time']
    search_fields = ['id', 'private_line_number', 'lease_line_code', 'line_username', 'remarks']
    raw_id_fields = ('element',)


@admin.register(OpticalFiber)
class OpticalFiberAdmin(admin.ModelAdmin):
    list_display = ['id', 'fiber_cable', 'sequence',
                    'element', 'create_time', 'update_time']
    search_fields = ['id']
    raw_id_fields = ('element', 'fiber_cable')


@admin.register(DistriFramePort)
class DistriFramePortAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'row', 'col',
                    'distribution_frame', 'element', 'create_time', 'update_time']
    search_fields = ['id', 'number']
    raw_id_fields = ('distribution_frame', 'element')


@admin.register(ConnectorBox)
class ConnectorBoxAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'place', 'remarks',
                    'location', 'element', 'create_time', 'update_time']
    search_fields = ['id', 'number']
    raw_id_fields = ('element',)


@admin.register(FiberCable)
class FiberCableAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'fiber_count', 'length',
                    'endpoint_1', 'endpoint_2', 'remarks', 'create_time', 'update_time']
    search_fields = ['id', 'number']


@admin.register(DistributionFrame)
class DistributionFrameAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'model_type', 'row_count', 'col_count',
                    'place', 'link_org', 'remarks', 'create_time', 'update_time']
    search_fields = ['id', 'number', 'remarks']
    raw_id_fields = ('link_org',)


@admin.register(ElementLink)
class ElementLinkAdmin(admin.ModelAdmin):
    list_display = ['id', 'element_id', 'link_id', 'index', 'sub_index']
    search_fields = ['id', 'element_id', 'link_id']
    raw_id_fields = ('element', 'link')


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ['id', 'number', 'user', 'endpoint_a', 'endpoint_z',
                    'bandwidth', 'description', 'line_type', 'business_person',
                    'build_person', 'link_status', 'remarks', 'enable_date',
                    'create_time', 'update_time']
    search_fields = ['id', 'number', 'user']


@admin.register(Element)
class ElementAdmin(admin.ModelAdmin):
    list_display = ['id', 'object_type',
                    'object_id', 'create_time', 'update_time']
    search_fields = ['id', 'object_id']
    list_filter = ['object_type']
