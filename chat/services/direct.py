"""Личные чаты: поиск, создание, повторное присоединение."""
from django.contrib.auth import get_user_model
from django.db.models import Count

from chat.models import Conversation, UserConversation

User = get_user_model()


def find_direct_conversation(user_a, user_b):
    """Беседа 1:1 между двумя пользователями (включая покинутые)."""
    return (
        Conversation.objects.filter(type='direct', is_active=True)
        .annotate(participant_count=Count('participants', distinct=True))
        .filter(participant_count=2)
        .filter(participants=user_a)
        .filter(participants=user_b)
        .order_by('-updated_at')
        .first()
    )


def ensure_membership(user, conversation, role='member'):
    """Активное участие в беседе (снимает left_at)."""
    uc, _ = UserConversation.objects.get_or_create(
        user=user,
        conversation=conversation,
        defaults={'role': role},
    )
    if uc.left_at is not None:
        uc.left_at = None
        uc.save(update_fields=['left_at'])
    return uc


def get_or_start_direct_conversation(current_user, other_user):
    """
    Открыть существующий личный чат или создать новый.
    Если пользователь ранее «удалил» чат — восстанавливает участие.
    """
    if current_user.id == other_user.id:
        raise ValueError('self_chat')

    conversation = find_direct_conversation(current_user, other_user)
    if conversation:
        ensure_membership(current_user, conversation, role='member')
        ensure_membership(other_user, conversation, role='member')
        return conversation

    conversation = Conversation.objects.create(
        type='direct',
        created_by=current_user,
    )
    ensure_membership(current_user, conversation, role='member')
    ensure_membership(other_user, conversation, role='member')
    return conversation
