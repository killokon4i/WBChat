from django.contrib import admin
from .models import (
    NewsCategory,
    News,
    NewsAttachment,
    NewsComment,
    NewsReaction,
    NewsEditLog,
    NewsView
)


@admin.register(NewsCategory)
class NewsCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_official', 'requires_moderation', 'is_active', 'order']
    list_filter = ['is_official', 'requires_moderation', 'is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


class NewsAttachmentInline(admin.TabularInline):
    model = NewsAttachment
    extra = 1
    fields = ['file', 'file_name', 'file_type', 'order']


class NewsCommentInline(admin.TabularInline):
    model = NewsComment
    extra = 0
    readonly_fields = ['author', 'content', 'created_at', 'is_deleted']
    can_delete = False
    max_num = 10
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'author', 'moderation_status',
        'is_pinned', 'is_published', 'views_count', 'comments_count', 'created_at'
    ]
    list_filter = [
        'moderation_status', 'category', 'is_pinned',
        'is_published', 'visibility', 'created_at'
    ]
    search_fields = ['title', 'content', 'author__username']
    raw_id_fields = ['author', 'moderated_by']
    readonly_fields = ['views_count', 'comments_count', 'created_at', 'updated_at', 'published_at']
    date_hierarchy = 'created_at'
    inlines = [NewsAttachmentInline, NewsCommentInline]
    filter_horizontal = ['visible_to_departments', 'visible_to_users']
    
    fieldsets = (
        ('Основное', {
            'fields': ('title', 'slug', 'content', 'excerpt', 'category', 'image', 'author')
        }),
        ('Закрепление', {
            'fields': ('is_pinned', 'pin_until', 'pin_order'),
            'classes': ('collapse',)
        }),
        ('Комментарии', {
            'fields': ('allow_comments', 'comments_count'),
        }),
        ('Видимость', {
            'fields': ('visibility', 'visible_to_departments', 'visible_to_users'),
            'classes': ('collapse',)
        }),
        ('Модерация', {
            'fields': ('moderation_status', 'moderated_by', 'moderated_at', 'moderation_comment'),
        }),
        ('Публикация', {
            'fields': ('is_published', 'published_at', 'schedule_publish_at'),
        }),
        ('Статистика', {
            'fields': ('views_count',),
        }),
        ('Служебное', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['approve_news', 'reject_news', 'pin_news', 'unpin_news']
    
    def approve_news(self, request, queryset):
        queryset.update(moderation_status='approved', moderated_by=request.user)
    approve_news.short_description = 'Одобрить выбранные'
    
    def reject_news(self, request, queryset):
        queryset.update(moderation_status='rejected', moderated_by=request.user)
    reject_news.short_description = 'Отклонить выбранные'
    
    def pin_news(self, request, queryset):
        queryset.update(is_pinned=True)
    pin_news.short_description = 'Закрепить выбранные'
    
    def unpin_news(self, request, queryset):
        queryset.update(is_pinned=False)
    unpin_news.short_description = 'Открепить выбранные'


@admin.register(NewsComment)
class NewsCommentAdmin(admin.ModelAdmin):
    list_display = ['news', 'author', 'content_preview', 'level', 'is_deleted', 'is_hidden', 'created_at']
    list_filter = ['is_deleted', 'is_hidden', 'created_at']
    search_fields = ['content', 'author__username', 'news__title']
    raw_id_fields = ['news', 'author', 'parent']
    readonly_fields = ['created_at', 'updated_at', 'edited_at', 'deleted_at']
    filter_horizontal = ['mentions']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Содержимое'
    
    actions = ['hide_comments', 'unhide_comments', 'delete_comments']
    
    def hide_comments(self, request, queryset):
        queryset.update(is_hidden=True, hidden_reason='Скрыто модератором')
    hide_comments.short_description = 'Скрыть выбранные'
    
    def unhide_comments(self, request, queryset):
        queryset.update(is_hidden=False, hidden_reason='')
    unhide_comments.short_description = 'Показать выбранные'
    
    def delete_comments(self, request, queryset):
        for comment in queryset:
            comment.soft_delete()
    delete_comments.short_description = 'Удалить выбранные (мягко)'


@admin.register(NewsReaction)
class NewsReactionAdmin(admin.ModelAdmin):
    list_display = ['news', 'user', 'emoji', 'created_at']
    list_filter = ['emoji', 'created_at']
    search_fields = ['news__title', 'user__username']
    raw_id_fields = ['news', 'user']


@admin.register(NewsEditLog)
class NewsEditLogAdmin(admin.ModelAdmin):
    list_display = ['news', 'edited_by', 'field_name', 'edited_at']
    list_filter = ['field_name', 'edited_at']
    search_fields = ['news__title', 'edited_by__username']
    raw_id_fields = ['news', 'edited_by']
    readonly_fields = ['edited_at']
    date_hierarchy = 'edited_at'


@admin.register(NewsView)
class NewsViewAdmin(admin.ModelAdmin):
    list_display = ['news', 'user', 'viewed_at']
    list_filter = ['viewed_at']
    search_fields = ['news__title', 'user__username']
    raw_id_fields = ['news', 'user']
    date_hierarchy = 'viewed_at'
