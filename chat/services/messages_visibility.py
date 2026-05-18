"""Фильтрация сообщений с учётом «очистки истории» у пользователя."""
from chat.models import Message, UserConversation


def filter_messages_for_user(qs, user_conversation):
    if user_conversation and user_conversation.history_cleared_at:
        return qs.filter(created_at__gt=user_conversation.history_cleared_at)
    return qs


def get_user_conversation(user, conversation_id):
    return UserConversation.objects.filter(
        user=user,
        conversation_id=conversation_id,
        left_at__isnull=True,
    ).first()


def visible_messages_queryset(user, conversation_id, *, user_conversation=None):
    uc = user_conversation or get_user_conversation(user, conversation_id)
    if not uc:
        return Message.objects.none()
    qs = Message.objects.filter(
        conversation_id=conversation_id,
        is_deleted=False,
    )
    return filter_messages_for_user(qs, uc)
