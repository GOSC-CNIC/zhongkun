from django.contrib import admin

from .models import (
    Ticket, TicketChange, FollowUp, TicketRating
)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'service_type', 'severity', 'submitter', 'submit_time',
                    'contact', 'assigned_to')
    list_display_links = ('id', 'title')
    list_filter = ('service_type', 'status', 'severity')
    search_fields = ('title',)
    list_select_related = ('submitter', 'assigned_to')


@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket', 'user', 'submit_time', 'fu_type', 'title', 'ticket_change')
    list_display_links = ('id',)
    list_filter = ('fu_type', )
    search_fields = ('title', 'ticket__id')
    list_select_related = ('user', 'ticket_change')


@admin.register(TicketChange)
class TicketChangeAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket_field', 'display')
    list_display_links = ('id',)
    search_fields = ('id',)


@admin.register(TicketRating)
class TicketRatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket_id', 'score', 'submit_time', 'username', 'is_sys_submit')
    list_display_links = ('id',)
    search_fields = ('id', 'ticket_id')
    list_filter = ('is_sys_submit',)
