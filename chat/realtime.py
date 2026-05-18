"""Real-time inbox / badge updates for chat participants."""

from django.contrib.auth import get_user_model

from chat.models import Conversation, Message, UserConversation
from notifications.realtime import push_user_event

User = get_user_model()


def _message_preview(message):
    content = (message.content or '').strip()
    if content:
        if len(content) > 80:
            return content[:80] + '…'
        return content
    if message.attachments.exists():
        att = message.attachments.first()
        if att:
            variant = getattr(att, 'variant', 'default') or 'default'
            if variant == 'voice':
                return '🎤 Голосовое сообщение'
            if variant == 'video_note':
                return '📹 Видеосообщение'
            return '📎 ' + (att.file_name or 'Файл')
    return 'Новое сообщение'


def get_unread_summary(user):
    from notifications.models import Notification

    notifications_unread = Notification.objects.filter(
        user=user, is_read=False
    ).count()

    conversations = (
        Conversation.objects.filter(
            is_active=True,
            userconversation__user=user,
            userconversation__left_at__isnull=True,
        )
        .distinct()
        .order_by('-updated_at')
    )

    conv_items = []
    messages_unread = 0
    for conv in conversations:
        unread = conv.get_unread_count(user)
        messages_unread += unread
        conv_items.append({'id': conv.id, 'unread_count': unread})

    return {
        'notifications_unread': notifications_unread,
        'messages_unread': messages_unread,
        'conversations': conv_items,
    }


def push_counts_update(user_id):
    user = User.objects.filter(pk=user_id).first()
    if not user:
        return
    push_user_event(user_id, {
        'type': 'counts_update',
        'counts': get_unread_summary(user),
    })


def notify_chat_message_by_id(message_id, sender_id):
    message = (
        Message.objects.select_related('author', 'conversation')
        .prefetch_related('attachments')
        .filter(pk=message_id)
        .first()
    )
    if message:
        notify_chat_message(message, sender_id)


def notify_chat_message(message, sender_id):
    """Notify other participants about a new message (sidebar + badges)."""
    if not message or not message.conversation_id:
        return

    preview = _message_preview(message)
    author_name = ''
    if message.author_id:
        author = message.author
        author_name = author.get_full_name() or author.username

    participant_ids = UserConversation.objects.filter(
        conversation_id=message.conversation_id,
        left_at__isnull=True,
    ).values_list('user_id', flat=True)

    updated_at = message.created_at.isoformat() if message.created_at else None

    for uid in participant_ids:
        if uid == sender_id:
            continue
        user = User.objects.filter(pk=uid).first()
        if not user:
            continue
        unread = message.conversation.get_unread_count(user)
        summary = get_unread_summary(user)
        message_kind = 'text'
        if message.attachments.exists():
            att = message.attachments.first()
            v = getattr(att, 'variant', 'default') or 'default'
            if v == 'voice':
                message_kind = 'voice'
            elif v == 'video_note':
                message_kind = 'video_note'
            else:
                message_kind = 'attachment'

        from chat.message_format import conversation_display_name
        conv_name = conversation_display_name(message.conversation, user)

        push_user_event(uid, {
            'type': 'chat_inbox',
            'conversation_id': message.conversation_id,
            'conversation_name': conv_name,
            'unread_count': unread,
            'preview': preview,
            'author_name': author_name,
            'message_kind': message_kind,
            'sender_id': sender_id,
            'updated_at': updated_at,
            'counts': summary,
        })


def notify_inbox_read(user_id, conversation_id):
    """Refresh badges after user read messages in a chat."""
    push_counts_update(user_id)
    push_user_event(user_id, {
        'type': 'chat_read',
        'conversation_id': conversation_id,
    })
