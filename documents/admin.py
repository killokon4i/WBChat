from django.contrib import admin
from .models import (
    DocumentCategory,
    Document,
    DocumentVersion,
    DocumentAcknowledgement,
    DocumentAccessRule,
    DocumentViewLog
)


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'parent', 'retention_days', 'is_active', 'order']
    list_filter = ['is_active', 'parent']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    readonly_fields = ['version_number', 'file_hash', 'uploaded_at', 'uploaded_by', 'scan_result']
    fields = ['version_number', 'file', 'file_name', 'uploaded_by', 'uploaded_at', 'scan_result', 'comment']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'document_number', 'document_type', 'category',
        'status', 'confidentiality', 'author', 'updated_at'
    ]
    list_filter = ['status', 'document_type', 'category', 'confidentiality', 'is_legal_hold']
    search_fields = ['title', 'document_number', 'description']
    raw_id_fields = ['author', 'curator', 'legal_hold_by']
    readonly_fields = ['created_at', 'updated_at', 'published_at', 'views_count', 'search_vector']
    date_hierarchy = 'created_at'
    inlines = [DocumentVersionInline]
    
    fieldsets = (
        ('Основное', {
            'fields': ('title', 'document_type', 'category', 'description')
        }),
        ('Метаданные НПА', {
            'fields': (
                'document_number', 'document_date',
                'effective_date', 'expiry_date',
                'basis', 'confidentiality'
            )
        }),
        ('Статус и ответственные', {
            'fields': ('status', 'author', 'curator')
        }),
        ('Внешние системы', {
            'fields': ('tezis_link', 'tezis_id'),
            'classes': ('collapse',)
        }),
        ('Legal Hold', {
            'fields': ('is_legal_hold', 'legal_hold_reason', 'legal_hold_until', 'legal_hold_by'),
            'classes': ('collapse',)
        }),
        ('Дополнительно', {
            'fields': ('tags', 'views_count', 'created_at', 'updated_at', 'published_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = [
        'document', 'version_number', 'file_name',
        'file_size', 'scan_result', 'uploaded_by', 'uploaded_at'
    ]
    list_filter = ['scan_result', 'is_scanned', 'uploaded_at']
    search_fields = ['document__title', 'file_name']
    raw_id_fields = ['document', 'uploaded_by']
    readonly_fields = ['file_hash', 'uploaded_at']


@admin.register(DocumentAcknowledgement)
class DocumentAcknowledgementAdmin(admin.ModelAdmin):
    list_display = ['document', 'user', 'required', 'deadline', 'acknowledged_at']
    list_filter = ['required', 'acknowledged_at', 'deadline']
    search_fields = ['document__title', 'user__username']
    raw_id_fields = ['document', 'user', 'acknowledged_version']


@admin.register(DocumentAccessRule)
class DocumentAccessRuleAdmin(admin.ModelAdmin):
    list_display = [
        'get_target', 'get_subject',
        'can_view', 'can_download', 'can_edit', 'can_delete', 'can_publish'
    ]
    list_filter = ['can_view', 'can_edit', 'can_delete', 'can_publish']
    raw_id_fields = ['document', 'category', 'department', 'user', 'created_by']
    
    def get_target(self, obj):
        return obj.document or obj.category or 'Все'
    get_target.short_description = 'Цель'
    
    def get_subject(self, obj):
        return obj.user or obj.department or obj.role or 'Все'
    get_subject.short_description = 'Субъект'


@admin.register(DocumentViewLog)
class DocumentViewLogAdmin(admin.ModelAdmin):
    list_display = ['document', 'user', 'version', 'viewed_at', 'ip_address']
    list_filter = ['viewed_at']
    search_fields = ['document__title', 'user__username']
    raw_id_fields = ['document', 'user', 'version']
    date_hierarchy = 'viewed_at'


