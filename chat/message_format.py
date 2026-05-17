"""Serialize chat messages for API / polling."""

from chat.models import Message, MessageStatus


def conversation_display_name(conversation, viewer):
    if conversation.type == 'direct':
        other = conversation.participants.exclude(id=viewer.id).first()
        if other:
            return other.get_full_name() or other.username
        return 'Удалённый пользователь'
    return conversation.name or 'Без названия'


def build_message_dict(msg, viewer):
    msg_dict = {
        'id': msg.id,
        'author_id': msg.author.id if msg.author else None,
        'author_username': msg.author.get_full_name() or msg.author.username if msg.author else 'Система',
        'content': msg.content,
        'type': msg.type,
        'created_at': msg.created_at.isoformat(),
        'is_edited': msg.is_edited,
        'edited_at': msg.edited_at.isoformat() if msg.edited_at else None,
        'reply_to_id': msg.reply_to_id,
        'is_pinned': msg.is_pinned,
        'forwarded_from_id': msg.forwarded_from_id,
    }

    atts = list(msg.attachments.all())
    if atts:
        msg_dict['attachments'] = [{
            'id': a.id,
            'url': a.file.url,
            'download_url': f'/chat/api/attachment/{a.id}/download/',
            'name': a.file_name,
            'size': a.file_size,
            'type': a.file_type,
            'mime': a.mime_type,
        } for a in atts]

    if msg.reply_to:
        orig = msg.reply_to
        msg_dict['reply_to_preview'] = {
            'author': (orig.author.get_full_name() or orig.author.username) if orig.author else 'Система',
            'content': (orig.content[:80] + '...') if len(orig.content) > 80 else orig.content,
        }
    if msg.forwarded_from:
        orig = msg.forwarded_from
        msg_dict['forwarded_from_author'] = (
            (orig.author.get_full_name() or orig.author.username) if orig.author else 'Система'
        )

    if msg_dict['author_id'] == viewer.id:
        statuses = MessageStatus.objects.filter(message_id=msg.id)
        total = statuses.count()
        if total == 0:
            msg_dict['is_read'] = False
        else:
            msg_dict['is_read'] = not statuses.exclude(status='read').exists()
    else:
        msg_dict['is_read'] = True

    return msg_dict
