import copy
from django.contrib import admin
from apps.app_net_flow.models import MenuModel
from apps.app_net_flow.models import ChartModel
from apps.app_net_flow.models import Menu2Chart
from apps.app_net_flow.models import GlobalAdminModel
from apps.app_net_flow.models import Menu2Member
from utils.model import BaseModelAdmin
from apps.app_net_flow.handlers.logentry import NetflowLogEntry
from django.core.exceptions import PermissionDenied
from django.contrib.admin.options import TO_FIELD_VAR
from django.contrib.admin.options import IS_POPUP_VAR
from django.utils.translation import gettext as _
from django.contrib.admin import helpers
from django.contrib.admin.exceptions import DisallowedModelAdminToField
from django.contrib.admin.utils import unquote
from django.contrib.admin.utils import flatten_fieldsets
from django.forms.formsets import all_valid


# Register your models here.
class NetflowLogEntryBaseModelAdmin(BaseModelAdmin):

    def log_addition(self, request, obj, message):
        return NetflowLogEntry().log_addition(request=request, obj=obj)

    def log_change(self, request, old_object, new_object):
        NetflowLogEntry().log_change(request=request, old=old_object, new=new_object)

    def log_deletion(self, request, obj, object_repr):
        NetflowLogEntry().log_deletion(request=request, obj=obj)

    def _changeform_view(self, request, object_id, form_url, extra_context):
        to_field = request.POST.get(TO_FIELD_VAR, request.GET.get(TO_FIELD_VAR))
        if to_field and not self.to_field_allowed(request, to_field):
            raise DisallowedModelAdminToField(
                "The field %s cannot be referenced." % to_field
            )

        if request.method == "POST" and "_saveasnew" in request.POST:
            object_id = None

        add = object_id is None

        if add:
            if not self.has_add_permission(request):
                raise PermissionDenied
            obj = None

        else:
            obj = self.get_object(request, unquote(object_id), to_field)

            if request.method == "POST":
                if not self.has_change_permission(request, obj):
                    raise PermissionDenied
            else:
                if not self.has_view_or_change_permission(request, obj):
                    raise PermissionDenied

            if obj is None:
                return self._get_obj_does_not_exist_redirect(
                    request, self.opts, object_id
                )

        old_object = copy.deepcopy(obj)
        fieldsets = self.get_fieldsets(request, obj)
        ModelForm = self.get_form(
            request, obj, change=not add, fields=flatten_fieldsets(fieldsets)
        )
        if request.method == "POST":
            form = ModelForm(request.POST, request.FILES, instance=obj)
            formsets, inline_instances = self._create_formsets(
                request,
                form.instance,
                change=not add,
            )
            form_validated = form.is_valid()
            if form_validated:
                new_object = self.save_form(request, form, change=not add)
            else:
                new_object = form.instance
            if all_valid(formsets) and form_validated:
                self.save_model(request, new_object, form, not add)
                self.save_related(request, form, formsets, not add)
                change_message = self.construct_change_message(
                    request, form, formsets, add
                )
                if add:
                    self.log_addition(request, new_object, change_message)
                    return self.response_add(request, new_object)
                else:
                    self.log_change(request, old_object, new_object)
                    return self.response_change(request, new_object)
            else:
                form_validated = False
        else:
            if add:
                initial = self.get_changeform_initial_data(request)
                form = ModelForm(initial=initial)
                formsets, inline_instances = self._create_formsets(
                    request, form.instance, change=False
                )
            else:
                form = ModelForm(instance=obj)
                formsets, inline_instances = self._create_formsets(
                    request, obj, change=True
                )

        if not add and not self.has_change_permission(request, obj):
            readonly_fields = flatten_fieldsets(fieldsets)
        else:
            readonly_fields = self.get_readonly_fields(request, obj)
        admin_form = helpers.AdminForm(
            form,
            list(fieldsets),
            # Clear prepopulated fields on a view-only form to avoid a crash.
            self.get_prepopulated_fields(request, obj)
            if add or self.has_change_permission(request, obj)
            else {},
            readonly_fields,
            model_admin=self,
        )
        media = self.media + admin_form.media

        inline_formsets = self.get_inline_formsets(
            request, formsets, inline_instances, obj
        )
        for inline_formset in inline_formsets:
            media += inline_formset.media

        if add:
            title = _("Add %s")
        elif self.has_change_permission(request, obj):
            title = _("Change %s")
        else:
            title = _("View %s")
        context = {
            **self.admin_site.each_context(request),
            "title": title % self.opts.verbose_name,
            "subtitle": str(obj) if obj else None,
            "adminform": admin_form,
            "object_id": object_id,
            "original": obj,
            "is_popup": IS_POPUP_VAR in request.POST or IS_POPUP_VAR in request.GET,
            "to_field": to_field,
            "media": media,
            "inline_admin_formsets": inline_formsets,
            "errors": helpers.AdminErrorList(form, formsets),
            "preserved_filters": self.get_preserved_filters(request),
        }

        # Hide the "Save" and "Save and continue" buttons if "Save as New" was
        # previously chosen to prevent the interface from getting confusing.
        if (
                request.method == "POST"
                and not form_validated
                and "_saveasnew" in request.POST
        ):
            context["show_save"] = False
            context["show_save_and_continue"] = False
            # Use the change template instead of the add template.
            add = False

        context.update(extra_context or {})

        return self.render_change_form(
            request, context, add=add, change=not add, obj=obj, form_url=form_url
        )


@admin.register(MenuModel)
class MenuAdmin(NetflowLogEntryBaseModelAdmin):
    list_display = [
        'id',
        'name',
        'level',
        'father',
        'sort_weight',
        'remark',
    ]
    list_display_links = ('id',)
    search_fields = ('id', 'name')  # 搜索字段


@admin.register(ChartModel)
class ChartAdmin(BaseModelAdmin):
    list_display = [
        'id',
        'instance_name',
        'if_alias',
        'if_address',
        'device_ip',
        'port_name',
        'class_uuid',
        'band_width',
        'sort_weight',

    ]
    list_display_links = ('id',)
    search_fields = ('id', 'instance_name', 'if_alias', 'device_ip', 'port_name')  # 搜索字段


@admin.register(Menu2Chart)
class Menu2ChartAdmin(NetflowLogEntryBaseModelAdmin):
    list_display = [
        'id',
        'menu',
        'chart',
        'title',
        'sort_weight',

    ]
    list_display_links = ('id',)
    raw_id_fields = ('menu', 'chart')
    search_fields = (
        'id', 'menu__name', 'menu__id', 'chart__id',
        'chart__instance_name', 'chart__device_ip', 'title'
    )  # 搜索字段


@admin.register(Menu2Member)
class Menu2MemberAdmin(NetflowLogEntryBaseModelAdmin):
    list_display = [
        'id',
        'menu',
        'member',
        'role',
        'inviter',

    ]
    list_display_links = ('id',)
    raw_id_fields = ('menu', 'member')
    search_fields = ('id', 'menu__id', 'menu__name', 'member__email', 'member__username', 'title')  # 搜索字段

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        obj.inviter = request.user.username
        obj.save()


@admin.register(GlobalAdminModel)
class GlobalAdministratorAdmin(NetflowLogEntryBaseModelAdmin):
    list_display = [
        'id',
        'member',
        'role',
        'inviter',
        'creation',
    ]
    list_display_links = ('id',)
    raw_id_fields = ('member',)
    search_fields = ('id', 'member__email', 'member__username', 'role',)  # 搜索字段

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        obj.inviter = request.user.username
        obj.save()
