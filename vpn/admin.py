from django.contrib import admin

from .models import Article


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display_links = ('id',)
    list_display = ('id', 'title', 'topic', 'lang', 'create_time', 'modify_time')
    list_filter = ('lang', 'topic')
    search_fields = ('title',)
