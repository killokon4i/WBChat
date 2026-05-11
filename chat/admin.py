from django.contrib import admin
from .models import (
    Conversation,
    UserConversation,
    Message,
    MessageStatus,
    Attachment,
    Reaction,
    TypingIndicator,
    OnlineStatus
)


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'type', 'name', 'created_by', 'created_at', 'is_active']
    list_filter = ['type', 'is_active', 'is_archived', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserConversation)
class UserConversationAdmin(admin.ModelAdmin):
    list_display = ['user', 'conversation', 'role', 'is_pinned', 'is_muted', 'joined_at']
    list_filter = ['role', 'is_pinned', 'is_muted', 'joined_at']
    search_fields = ['user__username', 'conversation__name']
    readonly_fields = ['joined_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'conversation', 'type', 'content_preview', 'created_at', 'is_deleted']
    list_filter = ['type', 'is_deleted', 'is_pinned', 'created_at']
    search_fields = ['content', 'author__username']
    readonly_fields = ['created_at', 'updated_at', 'edited_at', 'deleted_at']
    raw_id_fields = ['conversation', 'author', 'reply_to', 'forwarded_from']

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(MessageStatus)
class MessageStatusAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'status', 'sent_at', 'delivered_at', 'read_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['user__username', 'message__content']
    readonly_fields = ['sent_at', 'delivered_at', 'read_at']
    raw_id_fields = ['message', 'user']


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'file_name', 'file_type', 'file_size_mb', 'uploaded_by', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['file_name', 'uploaded_by__username']
    readonly_fields = ['uploaded_at']
    raw_id_fields = ['message', 'uploaded_by']


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ['message', 'user', 'emoji', 'created_at']
    list_filter = ['emoji', 'created_at']
    search_fields = ['user__username', 'emoji']
    readonly_fields = ['created_at']
    raw_id_fields = ['message', 'user']


@admin.register(TypingIndicator)
class TypingIndicatorAdmin(admin.ModelAdmin):
    list_display = ['user', 'conversation', 'started_at']
    list_filter = ['started_at']
    search_fields = ['user__username', 'conversation__name']
    readonly_fields = ['started_at']
    raw_id_fields = ['conversation', 'user']


@admin.register(OnlineStatus)
class OnlineStatusAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_online', 'last_seen_at', 'last_activity_at', 'connection_count']
    list_filter = ['is_online', 'show_online_status', 'show_last_seen']
    search_fields = ['user__username']
    readonly_fields = ['last_activity_at', 'last_seen_at']
    raw_id_fields = ['current_conversation']
