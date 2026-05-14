import mimetypes

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse, Http404
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Conversation, Message, UserConversation, Attachment

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
                conversation.display_avatar = other_user.avatar if other_user.avatar else None
            else:
                conversation.display_name = "Удалённый пользователь"
                conversation.display_position = ''
                conversation.display_avatar = None
        else:
            conversation.display_name = conversation.name or "Без названия"
            conversation.display_position = ''
            conversation.display_avatar = conversation.avatar
        
        conversations_with_unread.append(conversation)

    return render(request, 'chat/index.html', {
        'conversations': conversations_with_unread
    })


@login_required
def chat_room(request, conversation_id):
    """Страница конкретного чата"""
    from chat.models import OnlineStatus
    
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
        raise Http404("Вы не являетесь участником этого чата")
    
    # Обновляем время последнего прочтения
    user_conversation.mark_as_read()

    # Количество актуальных участников (кто ещё не покинул беседу)
    active_participants_count = UserConversation.objects.filter(
        conversation=conversation,
        left_at__isnull=True,
    ).count()
    
    # Для direct чата - получаем собеседника и его статус
    other_user = None
    other_user_online = False
    if conversation.type == 'direct':
        other_user = conversation.participants.exclude(id=request.user.id).first()
        if other_user:
            try:
                online_status = OnlineStatus.objects.get(user=other_user)
                stale_threshold = timezone.now() - timezone.timedelta(minutes=5)
                other_user_online = (
                    online_status.is_online
                    and online_status.connection_count > 0
                    and online_status.last_activity_at
                    and online_status.last_activity_at > stale_threshold
                )
                if online_status.is_online and not other_user_online:
                    online_status.is_online = False
                    online_status.connection_count = 0
                    online_status.last_seen_at = online_status.last_activity_at
                    online_status.save(update_fields=['is_online', 'connection_count', 'last_seen_at'])
            except OnlineStatus.DoesNotExist:
                other_user_online = False
    
    return render(request, 'chat/room.html', {
        'conversation': conversation,
        'user_conversation': user_conversation,
        'other_user': other_user,
        'other_user_online': other_user_online,
        'active_participants_count': active_participants_count,
    })


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
    
    # Получаем параметры пагинации
    try:
        limit = min(100, max(1, int(request.GET.get('limit', 50))))
    except (ValueError, TypeError):
        limit = 50
    try:
        offset = max(0, int(request.GET.get('offset', 0)))
    except (ValueError, TypeError):
        offset = 0
    
    # Получаем сообщения
    messages = Message.objects.filter(
        conversation_id=conversation_id,
        is_deleted=False
    ).select_related('author', 'reply_to', 'reply_to__author', 'forwarded_from', 'forwarded_from__author'
    ).prefetch_related('attachments').order_by('-created_at')[offset:offset + limit]
    
    messages_data = []
    for msg in reversed(list(messages)):
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
            msg_dict['forwarded_from_author'] = (orig.author.get_full_name() or orig.author.username) if orig.author else 'Система'

        messages_data.append(msg_dict)
    
    from chat.models import MessageStatus
    for msg_dict in messages_data:
        if msg_dict['author_id'] == request.user.id:
            statuses = MessageStatus.objects.filter(message_id=msg_dict['id'])
            total = statuses.count()
            if total == 0:
                msg_dict['is_read'] = False
            else:
                all_read = not statuses.exclude(status='read').exists()
                msg_dict['is_read'] = all_read
        else:
            msg_dict['is_read'] = True

    return JsonResponse({
        'messages': messages_data,
        'has_more': Message.objects.filter(
            conversation_id=conversation_id,
            is_deleted=False
        ).count() > offset + limit
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
    """
    Начать или открыть существующий личный чат с пользователем.
    Если чат уже есть - редирект в него, иначе создаём новый.
    """
    # Нельзя начать чат с самим собой
    if request.user.id == user_id:
        return redirect('chat_index')
    
    # Получаем пользователя
    other_user = get_object_or_404(User, pk=user_id, is_active=True)
    
    # Ищем существующий direct чат между этими пользователями
    existing_conversation = Conversation.objects.filter(
        type='direct',
        is_active=True,
        participants=request.user
    ).filter(
        participants=other_user
    ).first()
    
    if existing_conversation:
        # Чат уже существует - открываем его
        return redirect('chat_room', conversation_id=existing_conversation.id)
    
    # Создаём новый direct чат
    conversation = Conversation.objects.create(
        type='direct',
        created_by=request.user
    )
    
    # Добавляем обоих участников
    UserConversation.objects.create(
        user=request.user,
        conversation=conversation,
        role='member'
    )
    UserConversation.objects.create(
        user=other_user,
        conversation=conversation,
        role='member'
    )
    
    return redirect('chat_room', conversation_id=conversation.id)


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

    DANGEROUS = {'.exe', '.bat', '.cmd', '.com', '.msi', '.scr', '.pif', '.vbs', '.js', '.wsf', '.ps1', '.sh', '.jar'}

    for f in files:
        ext = os.path.splitext(f.name)[1].lower()
        if ext in DANGEROUS:
            return JsonResponse({'error': f'Запрещённый тип файла: {ext}'}, status=400)
        if f.size > 50 * 1024 * 1024:
            return JsonResponse({'error': f'Файл слишком большой: {f.name} (макс. 50 МБ)'}, status=400)

    has_image = any(
        (mimetypes.guess_type(f.name)[0] or '').startswith('image/') for f in files
    )
    has_video = any(
        (mimetypes.guess_type(f.name)[0] or '').startswith('video/') for f in files
    )
    if files:
        msg_type = 'image' if has_image and not has_video else ('video' if has_video else 'file')
    else:
        msg_type = 'text'

    message = Message.objects.create(
        conversation_id=conversation_id,
        author=request.user,
        content=text or (files[0].name if files else ''),
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
            uploaded_by=request.user,
        )
        attachments_data.append({
            'id': att.id,
            'url': att.file.url,
            'name': att.file_name,
            'size': att.file_size,
            'type': att.file_type,
            'mime': att.mime_type,
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
            'avatar': u.avatar.url if u.avatar else None,
            'role': m_uc.role,
        })

    return JsonResponse({
        'id': conv.id,
        'name': conv.name or '',
        'type': conv.type,
        'avatar': conv.avatar.url if conv.avatar else None,
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
