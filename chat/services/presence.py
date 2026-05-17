"""Онлайн-статус и форматирование «был(а) в сети»."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from chat.models import Conversation, OnlineStatus, UserConversation

User = get_user_model()

PRESENCE_STALE_MINUTES = 5


def _stale_threshold():
    return timezone.now() - timedelta(minutes=PRESENCE_STALE_MINUTES)


def is_user_online(status):
    """Пользователь считается в сети при активном соединении и недавней активности."""
    if not status:
        return False
    if not status.is_online or status.connection_count <= 0:
        return False
    if not status.last_activity_at:
        return False
    return status.last_activity_at > _stale_threshold()


def reconcile_stale_status(status):
    """Сбросить зависший «онлайн» после таймаута."""
    if not status or not status.is_online:
        return status
    if is_user_online(status):
        return status
    status.is_online = False
    status.connection_count = 0
    if status.last_activity_at and not status.last_seen_at:
        status.last_seen_at = status.last_activity_at
    elif not status.last_seen_at:
        status.last_seen_at = timezone.now()
    status.save(update_fields=['is_online', 'connection_count', 'last_seen_at'])
    return status


def format_time_hm(dt):
    return dt.strftime('%H:%M')


def format_last_seen_label(dt, online=False):
    """
    Подпись как в Telegram: в сети / был(а) только что / вчера в … / дата.
    """
    if online:
        return 'в сети'

    if not dt:
        return 'не в сети'

    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())

    now = timezone.localtime(timezone.now())
    seen = timezone.localtime(dt)
    delta = now - seen

    if delta.total_seconds() < 60:
        return 'был(а) только что'
    if delta.total_seconds() < 3600:
        mins = max(1, int(delta.total_seconds() // 60))
        return f'был(а) {mins} мин. назад'

    same_day = (
        seen.year == now.year
        and seen.month == now.month
        and seen.day == now.day
    )
    yesterday = now.date() - timedelta(days=1)
    is_yesterday = seen.date() == yesterday

    t = format_time_hm(seen)
    if same_day:
        return f'был(а) в {t}'
    if is_yesterday:
        return f'был(а) вчера в {t}'

    if seen.year == now.year:
        months_ru = (
            '', 'янв.', 'февр.', 'мар.', 'апр.', 'мая', 'июн.',
            'июл.', 'авг.', 'сент.', 'окт.', 'нояб.', 'дек.',
        )
        month = f'{seen.day} {months_ru[seen.month]}'
        if (now.date() - seen.date()).days < 7:
            weekdays = (
                'понедельник', 'вторник', 'среда', 'четверг',
                'пятница', 'суббота', 'воскресенье',
            )
            return f'был(а) в {weekdays[seen.weekday()]} в {t}'
        return f'был(а) {month} в {t}'

    return f'был(а) {seen.strftime("%d.%m.%Y")}'


def serialize_user_presence(user):
    """Словарь для API / WebSocket."""
    try:
        status = OnlineStatus.objects.get(user=user)
    except OnlineStatus.DoesNotExist:
        return {
            'user_id': user.id,
            'is_online': False,
            'label': 'не в сети',
            'last_seen_at': None,
        }

    status = reconcile_stale_status(status)
    online = is_user_online(status)
    last_seen = status.last_seen_at or status.last_activity_at
    label = format_last_seen_label(last_seen, online=online)
    if online:
        label = 'в сети'

    return {
        'user_id': user.id,
        'is_online': online,
        'label': label,
        'last_seen_at': last_seen.isoformat() if last_seen else None,
    }


def get_direct_chat_partner(conversation, viewer):
    if conversation.type != 'direct':
        return None
    return conversation.participants.exclude(id=viewer.id).first()


def notify_presence_changed(user_id):
    """Уведомить собеседников в личных чатах об изменении статуса."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    payload = serialize_user_presence(user)
    payload['type'] = 'presence_update'

    conv_ids = Conversation.objects.filter(
        type='direct',
        participants=user,
        is_active=True,
    ).values_list('id', flat=True)

    other_ids = (
        UserConversation.objects.filter(
            conversation_id__in=conv_ids,
            left_at__isnull=True,
        )
        .exclude(user_id=user_id)
        .values_list('user_id', flat=True)
        .distinct()
    )

    from notifications.realtime import push_user_event

    for oid in other_ids:
        push_user_event(oid, payload)
