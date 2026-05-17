"""
Context processors для передачи данных во все шаблоны.
"""


def notifications_count(request):
    """Добавляет количество непрочитанных уведомлений + сообщений в контекст."""
    if request.user.is_authenticated:
        from notifications.models import Notification
        from chat.models import Conversation
        
        # Непрочитанные уведомления
        notifications_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Непрочитанные сообщения в чатах
        messages_count = 0
        conversations = Conversation.objects.filter(
            participants=request.user,
            is_active=True
        )
        for conv in conversations:
            messages_count += conv.get_unread_count(request.user)
        
        return {
            'unread_notifications_count': notifications_count,
            'unread_notifications_only': notifications_count,
            'unread_messages_count': messages_count,
        }
    return {
        'unread_notifications_count': 0,
        'unread_notifications_only': 0,
        'unread_messages_count': 0,
    }

