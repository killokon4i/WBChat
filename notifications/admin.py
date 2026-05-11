from django.contrib import admin
from .models import (
    NotificationChannel,
    NotificationType,
    Notification,
    UserNotificationSettings,
    NotificationDeliveryLog
)


@admin.register(NotificationChannel)
class NotificationChannelAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active', 'requires_confirmation', 'order']
    list_filter = ['is_active', 'requires_confirmation']
    search_fields = ['code', 'name']
    ordering = ['order', 'name']


@admin.register(NotificationType)
class NotificationTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'priority', 'is_active', 'can_be_disabled']
    list_filter = ['is_active', 'category', 'priority', 'can_be_disabled']
    search_fields = ['code', 'name', 'description']
    filter_horizontal = ['default_channels']


class NotificationDeliveryLogInline(admin.TabularInline):
    model = NotificationDeliveryLog
    extra = 0
    readonly_fields = ['channel', 'status', 'sent_at', 'delivered_at', 'error_message']
    can_delete = False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'priority', 'is_read', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read', 'created_at']
    search_fields = ['title', 'content', 'user__username']
    raw_id_fields = ['user', 'notification_type', 'content_type']
    readonly_fields = ['created_at', 'read_at']
    date_hierarchy = 'created_at'
    inlines = [NotificationDeliveryLogInline]
    
    fieldsets = (
        ('Основное', {
            'fields': ('user', 'notification_type', 'priority')
        }),
        ('Содержимое', {
            'fields': ('title', 'content', 'link')
        }),
        ('Связанный объект', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('Статусы', {
            'fields': ('is_read', 'read_at', 'is_sent_email', 'is_sent_push')
        }),
        ('Группировка', {
            'fields': ('group_key', 'grouped_count'),
            'classes': ('collapse',)
        }),
        ('Служебное', {
            'fields': ('created_at', 'expires_at')
        }),
    )


@admin.register(UserNotificationSettings)
class UserNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'notification_type',
        'in_app_enabled', 'email_enabled', 'push_enabled',
        'email_frequency'
    ]
    list_filter = ['notification_type', 'in_app_enabled', 'email_enabled', 'email_frequency']
    search_fields = ['user__username', 'notification_type__name']
    raw_id_fields = ['user', 'notification_type']


@admin.register(NotificationDeliveryLog)
class NotificationDeliveryLogAdmin(admin.ModelAdmin):
    list_display = ['notification', 'channel', 'status', 'sent_at', 'delivered_at', 'attempts']
    list_filter = ['channel', 'status', 'sent_at']
    search_fields = ['notification__title', 'notification__user__username']
    raw_id_fields = ['notification', 'channel']
    date_hierarchy = 'sent_at'


