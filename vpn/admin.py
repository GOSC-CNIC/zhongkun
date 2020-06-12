from django.contrib import admin

from .models import VPNAuth, Article


@admin.register(VPNAuth)
class VPNAuthAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'user', 'password', 'created_time', 'modified_time')
    list_select_related = ('user',)
    search_fields = ('user__username',)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'title', 'topic', 'lang', 'create_time', 'modify_time')
    list_filter = ('lang', 'topic')
    search_fields = ('title',)
