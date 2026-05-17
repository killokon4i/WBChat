from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification
from .realtime import push_user_event


@receiver(post_save, sender=Notification)
def notification_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from chat.realtime import get_unread_summary

        counts = get_unread_summary(instance.user)
    except Exception:
        counts = None

    push_user_event(instance.user_id, {
        'type': 'notification',
        'notification': {
            'id': instance.id,
            'title': instance.title,
            'content': instance.content,
            'link': instance.link or '',
            'is_read': instance.is_read,
            'created_at': instance.created_at.isoformat() if instance.created_at else None,
        },
        'counts': counts,
    })
