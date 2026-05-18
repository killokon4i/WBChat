import json
import mimetypes

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse, Http404, FileResponse
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.utils import timezone
from .models import Conversation, Message, UserConversation, Attachment
from .message_format import build_message_dict, conversation_display_name
from .realtime import _message_preview, get_unread_summary
from .services.file_upload import validate_chat_upload_variant
from .services.avatar_display import attach_conversation_display
from .services.presence import (
    get_direct_chat_partner,
    serialize_user_presence,
)
from .services.direct import get_or_start_direct_conversation
from .services.messages_visibility import visible_messages_queryset

User = get_user_model()


@login_required
def chat_index(request):
    """Главная страница чата со списком бесед"""
    conversations = (
        Conversation.objects.filter(
            is_active=True,
            userconversation__user=request.user,
            userconversation__left_at__isnull=True,
        )
        .prefetch_related('participants', 'participants__position')
        .order_by('-updated_at')
        .distinct()
    )

    # Добавляем количество непрочитанных и информацию о собеседнике для direct чатов
    conversations_with_unread = []
    for conversation in conversations:
        conversation.unread_count = conversation.get_unread_count(request.user)
        
        # Для личных чатов - получаем собеседника
        if conversation.type == 'direct':
            other_user = conversation.participants.exclude(id=request.user.id).first()
            if other_user:
                conversation.other_user = other_user
                conversation.display_name = other_user.get_full_name() or other_user.username
                conversation.display_position = other_user.position.name if other_user.position else ''
            else:
                conversation.display_name = "Удалённый пользователь"
                conversation.display_position = ''
        else:
            conversation.display_name = conversation.name or "Без названия"
            conversation.display_position = ''

        attach_conversation_display(conversation, request.user)
        conversations_with_unread.append(conversation)

    active_id = request.GET.get('c') or request.GET.get('chat')
    active_conversation_id = None
    if active_id:
        try:
            active_conversation_id = int(active_id)
        except (TypeError, ValueError):
            active_conversation_id = None

    return render(request, 'chat/index.html', {
        'conversations': conversations_with_unread,
        'active_conversation_id': active_conversation_id,
    })


@login_required
@xframe_options_sameorigin
def chat_room(request, conversation_id):
    """Страница конкретного чата (полная) или панель для split-view (?embed=1)"""
    from django.urls import reverse

    embed = request.GET.get('embed', '').lower() in ('1', 'true', 'yes')
    if not embed:
        return redirect(f"{reverse('chat_index')}?c={conversation_id}")

    # Проверяем, что пользователь имеет доступ к этому чату
    conversation = get_object_or_404(
        Conversation.objects.prefetch_related('participants', 'participants__position'),
        id=conversation_id,
        is_active=True
    )
    
    # Проверяем участие пользователя в чате
    user_conversation = UserConversation.objects.filter(
        user=request.user,
        conversation=conversation,
        left_at__isnull=True
    ).first()
    
    if not user_conversation:
        if embed:
            return render(request, 'chat/embed_left.html')
        raise Http404("Вы не являетесь участником этого чата")
    
    # Обновляем время последнего прочтения
    user_conversation.mark_as_read()

    # Количество актуальных участников (кто ещё не покинул беседу)
    active_participants_count = UserConversation.objects.filter(
        conversation=conversation,
        left_at__isnull=True,
    ).count()
    
    # Для direct чата — собеседник и статус присутствия
    other_user = get_direct_chat_partner(conversation, request.user)
    other_presence = serialize_user_presence(other_user) if other_user else None
    attach_conversation_display(conversation, request.user)

    return render(request, 'chat/room_embed.html', {
        'conversation': conversation,
        'user_conversation': user_conversation,
        'other_user': other_user,
        'other_user_online': other_presence['is_online'] if other_presence else False,
        'other_presence': other_presence,
        'other_presence_json': json.dumps(other_presence) if other_presence else 'null',
        'active_participants_count': active_participants_count,
    })


@login_required
def api_presence(request, conversation_id):
    """Статус собеседника в личном чате (для polling)."""
    user_conversation = UserConversation.objects.filter(
        user=request.user,
        conversation_id=conversation_id,
        left_at__isnull=True,
    ).first()
    if not user_conversation:
        return JsonResponse({'error': 'Нет доступа'}, status=403)

    conversation = get_object_or_404(Conversation, id=conversation_id, is_active=True)
    partner = get_direct_chat_partner(conversation, request.user)
    if not partner:
        return JsonResponse({'error': 'Только для личных чатов'}, status=400)

    return JsonResponse(serialize_user_presence(partner))


@login_required
def get_messages(request, conversation_id):
    """API для получения истории сообщений"""
    # Проверяем доступ
    user_conversation = UserConversation.objects.filter(
        user=request.user,
        conversation_id=conversation_id,
        left_at__isnull=True
    ).first()
    
    if not user_conversation:
        return JsonResponse({'error': 'Access denied'}, status=403)

    since_id = request.GET.get('since_id')
    if since_id:
        try:
            since_id = int(since_id)
        except (TypeError, ValueError):
            since_id = None
    if since_id:
        new_messages = visible_messages_queryset(
            request.user, conversation_id, user_conversation=user_conversation,
        ).filter(
            id__gt=since_id,
        ).select_related(
            'author', 'reply_to', 'reply_to__author', 'forwarded_from', 'forwarded_from__author'
        ).prefetch_related('attachments').order_by('created_at')[:100]
        return JsonResponse({
            'messages': [build_message_dict(m, request.user) for m in new_messages],
            'has_more': False,
        })
    
    # Получаем параметры пагинации
    try:
        limit = min(100, max(1, int(request.GET.get('limit', 50))))
    except (ValueError, TypeError):
        limit = 50
    try:
        offset = max(0, int(request.GET.get('offset', 0)))
    except (ValueError, TypeError):
        offset = 0
    
    visible_qs = visible_messages_queryset(
        request.user, conversation_id, user_conversation=user_conversation,
    )
    messages = visible_qs.select_related(
        'author', 'reply_to', 'reply_to__author', 'forwarded_from', 'forwarded_from__author',
    ).prefetch_related('attachments').order_by('-created_at')[offset:offset + limit]

    messages_data = [build_message_dict(msg, request.user) for msg in reversed(list(messages))]
    total_visible = visible_qs.count()

    return JsonResponse({
        'messages': messages_data,
        'has_more': total_visible > offset + limit,
    })


@login_required
def create_conversation(request):
    """API для создания нового чата"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    import json
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    conversation_type = data.get('type', 'direct')
    name = data.get('name', '')
    participant_ids = data.get('participants', [])
    
    # Создаём беседу
    conversation = Conversation.objects.create(
        type=conversation_type,
        name=name if conversation_type != 'direct' else None,
        created_by=request.user
    )
    
    # Добавляем создателя как владельца
    UserConversation.objects.create(
        user=request.user,
        conversation=conversation,
        role='owner'
    )
    
    # Добавляем участников
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    for user_id in participant_ids:
        try:
            user = User.objects.get(id=user_id)
            UserConversation.objects.create(
                user=user,
                conversation=conversation,
                role='member'
            )
        except User.DoesNotExist:
            pass
    
    return JsonResponse({
        'id': conversation.id,
        'name': conversation.name,
        'type': conversation.type
    })


@login_required
def start_chat(request, user_id):
    """Начать или открыть личный чат (GET-редирект)."""
    from django.urls import reverse

    if request.user.id == user_id:
        return redirect('chat_index')

    other_user = get_object_or_404(User, pk=user_id, is_active=True)
    try:
        conversation = get_or_start_direct_conversation(request.user, other_user)
    except ValueError:
        return redirect('chat_index')

    return redirect(f"{reverse('chat_index')}?c={conversation.id}")


@login_required
@require_POST
def api_start_direct(request, user_id):
    """Создать / открыть личный чат (JSON для модалки «Новый чат»)."""
    if request.user.id == user_id:
        return JsonResponse({'error': 'Нельзя написать самому себе'}, status=400)

    other_user = User.objects.filter(pk=user_id, is_active=True).first()
    if not other_user:
        return JsonResponse({'error': 'Пользователь не найден'}, status=404)

    try:
        conversation = get_or_start_direct_conversation(request.user, other_user)
    except ValueError:
        return JsonResponse({'error': 'Нельзя написать самому себе'}, status=400)

    return JsonResponse({
        'success': True,
        'conversation_id': conversation.id,
    })


@login_required
@require_POST
def upload_attachment(request, conversation_id):
    """Send a message with text and/or multiple file attachments."""
    import os
    uc = UserConversation.objects.filter(
        user=request.user, conversation_id=conversation_id, left_at__isnull=True
    ).first()
    if not uc:
        return JsonResponse({'error': 'Нет доступа'}, status=403)

    files = request.FILES.getlist('files')
    text = request.POST.get('text', '').strip()
    variant = (request.POST.get('variant') or 'default').strip().lower()
    if variant not in ('default', 'voice', 'video_note'):
        variant = 'default'
    try:
        duration_sec = int(request.POST.get('duration') or 0) or None
    except (TypeError, ValueError):
        duration_sec = None
    reply_to_id = request.POST.get('reply_to') or None
    if reply_to_id is not None:
        try:
            reply_to_id = int(reply_to_id)
            reply_msg = Message.objects.filter(
                id=reply_to_id, conversation_id=conversation_id, is_deleted=False
            ).first()
            if not reply_msg:
                reply_to_id = None
        except (ValueError, TypeError):
            reply_to_id = None

    if not files and not text:
        return JsonResponse({'error': 'Нет содержимого'}, status=400)

    if variant in ('voice', 'video_note'):
        if len(files) != 1:
            return JsonResponse({'error': 'Одна запись за раз'}, status=400)
        if text:
            text = ''

    for f in files:
        mime = mimetypes.guess_type(f.name)[0]
        err = validate_chat_upload_variant(
            f.name, f.size, mime, variant=variant, duration_sec=duration_sec,
        )
        if err:
            return JsonResponse({'error': err}, status=400)

    has_image = any(
        (mimetypes.guess_type(f.name)[0] or '').startswith('image/') for f in files
    )
    has_video = any(
        (mimetypes.guess_type(f.name)[0] or '').startswith('video/') for f in files
    )
    if variant == 'voice':
        msg_type = 'audio'
        default_content = '🎤 Голосовое сообщение'
    elif variant == 'video_note':
        msg_type = 'video'
        default_content = '📹 Видеосообщение'
    elif files:
        msg_type = 'image' if has_image and not has_video else ('video' if has_video else 'file')
        default_content = files[0].name
    else:
        msg_type = 'text'
        default_content = ''

    message = Message.objects.create(
        conversation_id=conversation_id,
        author=request.user,
        content=text or default_content,
        type=msg_type,
        reply_to_id=reply_to_id,
    )

    attachments_data = []
    for f in files:
        mime = mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
        if mime.startswith('image/'):
            file_type = 'image'
        elif mime.startswith('video/'):
            file_type = 'video'
        elif mime.startswith('audio/'):
            file_type = 'audio'
        else:
            file_type = 'document'
        att = Attachment.objects.create(
            message=message,
            file=f,
            file_name=f.name,
            file_size=f.size,
            file_type=file_type,
            mime_type=mime,
            variant=variant if variant in ('voice', 'video_note') else 'default',
            duration=duration_sec,
            uploaded_by=request.user,
        )
        attachments_data.append({
            'id': att.id,
            'url': att.file.url,
            'name': att.file_name,
            'size': att.file_size,
            'type': att.file_type,
            'mime': att.mime_type,
            'variant': att.variant,
            'duration': att.duration,
        })

    Conversation.objects.filter(id=conversation_id).update(updated_at=timezone.now())

    from chat.models import MessageStatus
    other_participants = UserConversation.objects.filter(
        conversation_id=conversation_id, left_at__isnull=True
    ).exclude(user=request.user)
    MessageStatus.objects.bulk_create([
        MessageStatus(message=message, user=p.user, status='sent')
        for p in other_participants
    ])

    reply_preview = None
    if message.reply_to_id:
        try:
            orig = Message.objects.select_related('author').get(pk=message.reply_to_id)
            reply_preview = {
                'author': (orig.author.get_full_name() or orig.author.username) if orig.author else 'Система',
                'content': (orig.content[:80] + '...') if len(orig.content) > 80 else orig.content,
            }
        except Message.DoesNotExist:
            pass

    message_payload = {
        'id': message.id,
        'author_id': request.user.id,
        'author_username': request.user.get_full_name() or request.user.username,
        'content': message.content,
        'type': message.type,
        'created_at': message.created_at.isoformat(),
        'is_edited': False,
        'is_pinned': False,
        'reply_to_id': message.reply_to_id,
        'reply_to_preview': reply_preview,
        'forwarded_from_id': None,
        'attachments': attachments_data,
    }

    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{conversation_id}',
        {'type': 'chat_message', 'message': message_payload},
    )

    from chat.realtime import notify_chat_message_by_id
    notify_chat_message_by_id(message.id, request.user.id)

    return JsonResponse({
        'success': True,
        'message': message_payload,
    })


@login_required
@require_POST
def pin_message(request, conversation_id, message_id):
    """Toggle pin on a message."""
    uc = UserConversation.objects.filter(
        user=request.user, conversation_id=conversation_id, left_at__isnull=True
    ).first()
    if not uc:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    msg = Message.objects.filter(id=message_id, conversation_id=conversation_id).first()
    if not msg:
        return JsonResponse({'error': 'Сообщение не найдено'}, status=404)
    
    msg.is_pinned = not msg.is_pinned
    msg.save(update_fields=['is_pinned'])
    return JsonResponse({'success': True, 'is_pinned': msg.is_pinned})


@login_required
def api_conversations_list(request):
    """Список чатов пользователя (для пересылки и др.)."""
    conversations = (
        Conversation.objects.filter(
            is_active=True,
            userconversation__user=request.user,
            userconversation__left_at__isnull=True,
        )
        .prefetch_related('participants')
        .order_by('-updated_at')
        .distinct()
    )
    items = []
    for conversation in conversations:
        items.append({
            'id': conversation.id,
            'name': conversation_display_name(conversation, request.user),
            'type': conversation.type,
        })
    return JsonResponse({'success': True, 'conversations': items})


@login_required
def api_inbox_sync(request):
    """Синхронизация списка чатов (polling / real-time fallback)."""
    conversations = (
        Conversation.objects.filter(
            is_active=True,
            userconversation__user=request.user,
            userconversation__left_at__isnull=True,
        )
        .prefetch_related('participants')
        .order_by('-updated_at')
        .distinct()
    )
    items = []
    for conversation in conversations:
        uc = UserConversation.objects.filter(
            user=request.user,
            conversation=conversation,
        ).first()
        last_msg_qs = Message.objects.filter(conversation=conversation, is_deleted=False)
        if uc and uc.history_cleared_at:
            last_msg_qs = last_msg_qs.filter(created_at__gt=uc.history_cleared_at)
        last_msg = (
            last_msg_qs
            .select_related('author')
            .prefetch_related('attachments')
            .order_by('-created_at')
            .first()
        )
        preview = _message_preview(last_msg) if last_msg else ''
        if last_msg and last_msg.author_id != request.user.id:
            author = last_msg.author.get_full_name() or last_msg.author.username if last_msg.author else ''
            if author:
                preview = f'{author}: {preview}'
        items.append({
            'id': conversation.id,
            'name': conversation_display_name(conversation, request.user),
            'type': conversation.type,
            'unread_count': conversation.get_unread_count(request.user),
            'updated_at': conversation.updated_at.isoformat() if conversation.updated_at else None,
            'preview': preview,
            'last_message_id': last_msg.id if last_msg else None,
        })
    return JsonResponse({
        'success': True,
        'conversations': items,
        'counts': get_unread_summary(request.user),
    })


@login_required
def download_attachment(request, attachment_id):
    """Скачать вложение из чата."""
    attachment = get_object_or_404(
        Attachment.objects.select_related('message__conversation'),
        pk=attachment_id,
    )
    has_access = UserConversation.objects.filter(
        user=request.user,
        conversation=attachment.message.conversation_id,
        left_at__isnull=True,
    ).exists()
    if not has_access:
        raise Http404
    if not attachment.file:
        raise Http404
    response = FileResponse(
        attachment.file.open('rb'),
        as_attachment=True,
        filename=attachment.file_name or 'download',
    )
    if attachment.mime_type:
        response['Content-Type'] = attachment.mime_type
    return response


@login_required
@require_POST
def forward_message(request, conversation_id, message_id):
    """Forward a message to another conversation."""
    import json as _json
    uc = UserConversation.objects.filter(
        user=request.user, conversation_id=conversation_id, left_at__isnull=True
    ).first()
    if not uc:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    original = Message.objects.filter(id=message_id, conversation_id=conversation_id).first()
    if not original:
        return JsonResponse({'error': 'Сообщение не найдено'}, status=404)
    
    target_id = request.POST.get('target_conversation_id')
    if not target_id:
        try:
            body = _json.loads(request.body)
            target_id = body.get('target_conversation_id')
        except Exception:
            pass
    if not target_id:
        return JsonResponse({'error': 'Чат не выбран'}, status=400)
    
    target_uc = UserConversation.objects.filter(
        user=request.user, conversation_id=target_id, left_at__isnull=True
    ).first()
    if not target_uc:
        return JsonResponse({'error': 'Нет доступа к целевому чату'}, status=403)
    
    fwd = Message.objects.create(
        conversation_id=target_id,
        author=request.user,
        content=original.content,
        type=original.type,
        forwarded_from=original,
    )
    from django.core.files.base import ContentFile
    for orig_att in Attachment.objects.filter(message=original):
        new_file = ContentFile(orig_att.file.read())
        new_file.name = orig_att.file_name
        Attachment.objects.create(
            message=fwd,
            file=new_file,
            file_name=orig_att.file_name,
            file_size=orig_att.file_size,
            file_type=orig_att.file_type,
            mime_type=orig_att.mime_type,
            uploaded_by=request.user,
        )
    Conversation.objects.filter(id=target_id).update(updated_at=timezone.now())

    from chat.realtime import notify_chat_message_by_id
    notify_chat_message_by_id(fwd.id, request.user.id)

    return JsonResponse({'success': True, 'message_id': fwd.id})


@login_required
@require_POST
def mark_read(request, conversation_id):
    """Mark all messages in conversation as read."""
    from chat.models import MessageStatus
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    uc = UserConversation.objects.filter(
        user=request.user, conversation_id=conversation_id, left_at__isnull=True
    ).first()
    if not uc:
        return JsonResponse({'error': 'Нет доступа'}, status=403)

    statuses_qs = MessageStatus.objects.filter(
        message__conversation_id=conversation_id,
        user=request.user,
    ).exclude(status='read')
    message_ids = list(statuses_qs.values_list('message_id', flat=True))
    statuses_qs.update(status='read', read_at=timezone.now())
    
    uc.last_read_at = timezone.now()
    uc.save(update_fields=['last_read_at'])

    # Push real-time read receipts so sender indicators update immediately.
    if message_ids:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'chat_{conversation_id}',
            {
                'type': 'read_receipt',
                'user_id': request.user.id,
                'message_ids': message_ids,
            }
        )

    from chat.realtime import notify_inbox_read
    notify_inbox_read(request.user.id, conversation_id)

    return JsonResponse({'success': True, 'updated': len(message_ids)})


@login_required
@require_POST
def create_group(request):
    """Create a group conversation with avatar and name."""
    name = request.POST.get('name', '').strip()
    if not name:
        return JsonResponse({'error': 'Укажите название беседы'}, status=400)
    
    participant_ids = list(dict.fromkeys(request.POST.getlist('participants')))
    
    conversation = Conversation.objects.create(
        type='group',
        name=name,
        created_by=request.user,
    )
    
    if request.FILES.get('avatar'):
        conversation.avatar = request.FILES['avatar']
        conversation.save(update_fields=['avatar'])
    
    UserConversation.objects.create(
        user=request.user,
        conversation=conversation,
        role='owner',
        can_add_members=True,
    )
    
    for uid in participant_ids:
        try:
            user = User.objects.get(id=int(uid), is_active=True)
            if user != request.user:
                UserConversation.objects.create(
                    user=user,
                    conversation=conversation,
                    role='member',
                )
        except (User.DoesNotExist, ValueError):
            pass
    
    return JsonResponse({
        'success': True,
        'conversation_id': conversation.id,
        'name': conversation.name,
    })


@login_required
def chat_info(request, conversation_id):
    """API: get conversation info with participants."""
    uc = UserConversation.objects.filter(
        user=request.user, conversation_id=conversation_id, left_at__isnull=True
    ).first()
    if not uc:
        return JsonResponse({'error': 'Нет доступа'}, status=403)

    conv = Conversation.objects.prefetch_related('participants', 'participants__position').get(id=conversation_id)
    members = []
    for m_uc in UserConversation.objects.filter(conversation=conv, left_at__isnull=True).select_related('user', 'user__position'):
        u = m_uc.user
        members.append({
            'id': u.id,
            'name': u.get_full_name() or u.username,
            'position': u.position.name if u.position else '',
            'has_avatar': u.has_avatar,
            'avatar': u.avatar.url if u.has_avatar else None,
            'initials': u.get_avatar_initials(),
            'role': m_uc.role,
        })

    from accounts.avatar_utils import file_field_has_image, initials_from_name
    conv_has_avatar = file_field_has_image(conv.avatar)

    return JsonResponse({
        'id': conv.id,
        'name': conv.name or '',
        'type': conv.type,
        'has_avatar': conv_has_avatar,
        'avatar': conv.avatar.url if conv_has_avatar else None,
        'initials': initials_from_name(conv.name or 'Группа'),
        'created_by_id': conv.created_by_id,
        'members': members,
        'my_role': uc.role,
    })


@login_required
@require_POST
def chat_update(request, conversation_id):
    """API: update conversation name / avatar. Only owner/admin."""
    uc = UserConversation.objects.filter(
        user=request.user, conversation_id=conversation_id, left_at__isnull=True
    ).first()
    if not uc or uc.role not in ('owner', 'admin'):
        return JsonResponse({'error': 'Нет прав'}, status=403)

    conv = Conversation.objects.get(id=conversation_id)
    update_fields = []
    if 'name' in request.POST:
        conv.name = request.POST.get('name', '').strip()
        update_fields.append('name')
    if request.FILES.get('avatar'):
        conv.avatar = request.FILES['avatar']
        update_fields.append('avatar')
    if update_fields:
        conv.save(update_fields=update_fields)
    return JsonResponse({'success': True, 'name': conv.name, 'avatar': conv.avatar.url if conv.avatar else None})


@login_required
@require_POST
def chat_add_member(request, conversation_id):
    """API: add member to group chat. Only owner/admin."""
    import json as _json
    uc = UserConversation.objects.filter(
        user=request.user, conversation_id=conversation_id, left_at__isnull=True
    ).first()
    if not uc or uc.role not in ('owner', 'admin'):
        return JsonResponse({'error': 'Нет прав'}, status=403)

    try:
        body = _json.loads(request.body)
        user_id = body.get('user_id')
    except Exception:
        user_id = request.POST.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'user_id required'}, status=400)

    target = User.objects.filter(id=int(user_id), is_active=True).first()
    if not target:
        return JsonResponse({'error': 'Пользователь не найден'}, status=404)

    existing = UserConversation.objects.filter(user=target, conversation_id=conversation_id).first()
    if existing:
        if existing.left_at:
            existing.left_at = None
            existing.save(update_fields=['left_at'])
            return JsonResponse({'success': True})
        return JsonResponse({'error': 'Уже участник'}, status=400)

    UserConversation.objects.create(user=target, conversation_id=conversation_id, role='member')
    return JsonResponse({'success': True})


@login_required
@require_POST
def chat_remove_member(request, conversation_id):
    """API: remove member from group chat. Only owner/admin."""
    import json as _json
    uc = UserConversation.objects.filter(
        user=request.user, conversation_id=conversation_id, left_at__isnull=True
    ).first()
    if not uc or uc.role not in ('owner', 'admin'):
        return JsonResponse({'error': 'Нет прав'}, status=403)

    try:
        body = _json.loads(request.body)
        user_id = body.get('user_id')
    except Exception:
        user_id = request.POST.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'user_id required'}, status=400)

    target_uc = UserConversation.objects.filter(
        user_id=int(user_id), conversation_id=conversation_id, left_at__isnull=True
    ).first()
    if not target_uc:
        return JsonResponse({'error': 'Участник не найден'}, status=404)
    if target_uc.role == 'owner':
        return JsonResponse({'error': 'Нельзя удалить создателя'}, status=400)

    target_uc.left_at = timezone.now()
    target_uc.save(update_fields=['left_at'])
    return JsonResponse({'success': True})
