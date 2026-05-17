"""Push real-time events to the user's notification WebSocket group."""


def push_user_event(user_id, payload):
    if not user_id:
        return
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f'notifications_{user_id}',
            {'type': 'user_event', 'payload': payload},
        )
    except Exception:
        pass
