from django.contrib import admin
from .models import (
    Category, Tag, Article, ArticleVersion, ArticleAttachment,
    ArticleComment, ArticleRating, FAQ, Snippet, ArticleTemplate,
    ArticleView, Subscription, EditLock, SearchQuery,
    SuggestedEdit, TermRequest, AuditLog,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent', 'level', 'order', 'is_active', 'is_restricted')
    list_filter = ('is_active', 'is_restricted', 'level')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'usage_count', 'is_controlled', 'is_approved')
    list_filter = ('is_controlled', 'is_approved')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'author', 'status', 'article_type', 'views_count', 'avg_rating', 'published_at')
    list_filter = ('status', 'article_type', 'category')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('author',)


@admin.register(ArticleVersion)
class ArticleVersionAdmin(admin.ModelAdmin):
    list_display = ('article', 'version_number', 'author', 'created_at', 'is_rollback')
    list_filter = ('is_rollback',)


@admin.register(ArticleAttachment)
class ArticleAttachmentAdmin(admin.ModelAdmin):
    list_display = ('file_name', 'article', 'mime_type', 'file_size', 'uploaded_by', 'uploaded_at')
    list_filter = ('mime_type',)
    search_fields = ('file_name',)


@admin.register(ArticleRating)
class ArticleRatingAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'score', 'created_at')
    list_filter = ('score',)


@admin.register(ArticleView)
class ArticleViewAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'viewed_at', 'time_spent_seconds')
    list_filter = ('viewed_at',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'tag', 'article', 'created_at')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'helpful_yes', 'helpful_no', 'is_active')
    list_filter = ('is_active', 'category')


@admin.register(Snippet)
class SnippetAdmin(admin.ModelAdmin):
    list_display = ('key', 'title', 'updated_at')
    search_fields = ('key', 'title')


@admin.register(ArticleTemplate)
class ArticleTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'article_type', 'is_active')
    list_filter = ('article_type', 'is_active')


@admin.register(SuggestedEdit)
class SuggestedEditAdmin(admin.ModelAdmin):
    list_display = ('article', 'author', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(TermRequest)
class TermRequestAdmin(admin.ModelAdmin):
    list_display = ('term', 'requested_by', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'action', 'created_at', 'ip_address')
    list_filter = ('action', 'created_at')
    search_fields = ('details',)
    readonly_fields = ('article', 'user', 'action', 'details', 'ip_address', 'created_at')
