"""Данные для отображения аватара в списке чатов и шапке."""
from accounts.avatar_utils import file_field_has_image, initials_from_name
from chat.services.presence import get_direct_chat_partner


def attach_conversation_display(conversation, viewer):
    """Заполняет display_has_avatar, display_avatar_url, display_initials."""
    if conversation.type == 'direct':
        other = get_direct_chat_partner(conversation, viewer)
        if other:
            conversation.display_has_avatar = other.has_avatar
            conversation.display_avatar_url = (
                other.avatar.url if other.has_avatar else ''
            )
            conversation.display_initials = other.get_avatar_initials()
        else:
            conversation.display_has_avatar = False
            conversation.display_avatar_url = ''
            conversation.display_initials = '?'
        return

    conversation.display_has_avatar = file_field_has_image(conversation.avatar)
    conversation.display_avatar_url = (
        conversation.avatar.url if conversation.display_has_avatar else ''
    )
    conversation.display_initials = initials_from_name(
        conversation.name or 'Группа'
    )
