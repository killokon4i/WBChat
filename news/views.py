import json
import mimetypes
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.utils import timezone
from django.contrib import messages
from .models import News, NewsComment, NewsReaction, NewsAttachment
from .services import MentionService, AutoModerationService

User = get_user_model()
@login_required(login_url='login')
def news_list(request):
    """Список только опубликованных новостей для ленты."""
    news = News.objects.filter(is_published=True).order_by(
        '-published_at',
        '-created_at',
    )
    return render(request, 'news/news_list.html', {'news': news})


@login_required(login_url='login')
def news_personal_dashboard(request):
    """Личный кабинет по новостям (для авторов/модераторов)."""
    if not request.user.isModerator:
        return HttpResponseForbidden("У вас нет прав.")

    my_published = News.objects.filter(author=request.user, is_published=True)
    my_drafts = News.objects.filter(author=request.user, is_published=False).order_by('-updated_at')

    published_count = my_published.count()
    drafts_count = my_drafts.count()
    agg = my_published.aggregate(total_views=Sum('views_count'))
    total_views = agg['total_views'] or 0

    context = {
        'published_count': published_count,
        'drafts_count': drafts_count,
        'total_views': total_views,
        'my_drafts': my_drafts,
    }
    return render(request, 'news/personal_dashboard.html', context)
@login_required(login_url='login')
def news_detail(request, pk):
    news_item = get_object_or_404(News, pk=pk)
    comments = news_item.comments.filter(is_deleted=False, parent__isnull=True).select_related('author').prefetch_related('replies__author')
    
    # Подсветка упоминаний
    mention_service = MentionService()
    
    # Подсветка в тексте новости
    news_item.highlighted_content = mention_service.highlight_mentions(news_item.content)
    
    # Подсветка в комментариях
    for comment in comments:
        comment.highlighted_content = mention_service.highlight_mentions(comment.content)
        # Сохраняем обработанные replies в отдельный атрибут
        comment.processed_replies = []
        for reply in comment.replies.filter(is_deleted=False):
            reply.highlighted_content = mention_service.highlight_mentions(reply.content)
            comment.processed_replies.append(reply)
    
    # Реакции на новость
    reactions = NewsReaction.objects.filter(news=news_item).values('emoji').annotate(
        count=Count('id')
    )
    reaction_counts = {r['emoji']: r['count'] for r in reactions}
    
    # Реакции текущего пользователя
    user_reactions = []
    if request.user.is_authenticated:
        user_reactions = list(NewsReaction.objects.filter(
            news=news_item,
            user=request.user
        ).values_list('emoji', flat=True))
    
    gallery_images = news_item.attachments.filter(file_type='image').order_by('order', 'uploaded_at')

    return render(request, 'news/news_detail.html', {
        'news_item': news_item,
        'comments': comments,
        'reaction_counts_json': json.dumps(reaction_counts),
        'user_reactions_json': json.dumps(user_reactions),
        'gallery_images': gallery_images,
    })


def _handle_news_attachments(request, news_item):
    """Process uploaded files for news attachments (доп. фото/файлы)."""
    files = list(request.FILES.getlist('attachments'))
    # Дополнительные изображения могут прийти во множественном выборе обложки:
    # первый файл = превью, остальные = доп. фото
    image_files = request.FILES.getlist('image')
    if image_files and len(image_files) > 1:
        files.extend(image_files[1:])
    if not files:
        return

    DANGEROUS = {'.exe', '.bat', '.cmd', '.com', '.msi', '.scr', '.pif', '.vbs', '.js', '.wsf', '.ps1', '.sh', '.jar'}
    import os
    for f in files:
        ext = os.path.splitext(f.name)[1].lower()
        if ext in DANGEROUS:
            messages.warning(request, f'Файл {f.name} пропущен: запрещённый тип.')
            continue
        if f.size > 50 * 1024 * 1024:
            messages.warning(request, f'Файл {f.name} пропущен: размер больше 50 МБ.')
            continue
        mime = mimetypes.guess_type(f.name)[0] or ''
        if mime.startswith('image/'):
            file_type = 'image'
        elif mime.startswith('video/'):
            file_type = 'video'
        elif mime.startswith('application/') or mime.startswith('text/'):
            file_type = 'document'
        else:
            file_type = 'other'
        NewsAttachment.objects.create(
            news=news_item,
            file=f,
            file_name=f.name,
            file_type=file_type,
            file_size=f.size,
        )
@login_required(login_url='login')
def edit_news(request, pk):
    news_item = get_object_or_404(News, pk=pk)

    if not request.user.is_authenticated or not request.user.isModerator:
        return HttpResponseForbidden("У вас нет прав.")

    if request.method == 'POST':
        news_item.title = request.POST.get('title', '').strip()
        news_item.content = request.POST.get('content', '').strip()
        news_item.excerpt = request.POST.get('excerpt', '').strip()

        category_id = request.POST.get('category')
        if category_id:
            try:
                news_item.category_id = int(category_id)
            except (TypeError, ValueError):
                pass

        # Обложка: первый файл из списка image (если несколько — первый = превью,
        # остальные попадут в _handle_news_attachments как доп. фото)
        image_files = request.FILES.getlist('image')
        if image_files:
            news_item.image = image_files[0]

        news_item.save()
        _handle_news_attachments(request, news_item)
        return redirect('news_detail', pk=news_item.pk)

    from .models import NewsCategory
    categories = NewsCategory.objects.filter(is_active=True).order_by('order', 'name')
    return render(request, 'news/edit_news.html', {
        'news_item': news_item,
        'categories': categories,
    })
@login_required(login_url='login')
def delete_news(request, pk):
    news_item = get_object_or_404(News, pk=pk)

    if not request.user.is_authenticated or not request.user.isModerator:
        return HttpResponseForbidden("У вас нет прав.")

    news_item.delete()
    return redirect('news_list')


@login_required(login_url='login')
@require_POST
def delete_news_attachment(request, pk, attachment_id):
    news_item = get_object_or_404(News, pk=pk)
    if not request.user.isModerator:
        return HttpResponseForbidden("У вас нет прав.")
    att = get_object_or_404(NewsAttachment, pk=attachment_id, news=news_item)
    name = att.file_name
    att.delete()
    messages.success(request, f'Вложение «{name}» удалено.')
    return redirect('news_edit', pk=news_item.pk)


@login_required(login_url='login')
@require_POST
def news_autosave(request, pk):
    """Autosave draft of an existing news item."""
    news_item = get_object_or_404(News, pk=pk)
    if not request.user.isModerator:
        return JsonResponse({'error': 'Нет прав'}, status=403)

    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    excerpt = request.POST.get('excerpt', '').strip()

    if title:
        news_item.title = title
    if content:
        news_item.content = content
    if excerpt:
        news_item.excerpt = excerpt

    news_item.save()
    return JsonResponse({'success': True, 'saved_at': timezone.now().strftime('%H:%M:%S')})


@login_required(login_url='login')
def news_preview(request):
    if request.method != 'POST':
        return HttpResponseForbidden('POST only')
    title = request.POST.get('title', 'Предпросмотр новости')
    content = request.POST.get('content', '')
    excerpt = request.POST.get('excerpt', '')
    return render(request, 'news/news_preview.html', {
        'title': title,
        'content': content,
        'excerpt': excerpt,
    })
@login_required(login_url='login')
def create_news(request):
    if not request.user.is_authenticated or not request.user.isModerator:
        return HttpResponseForbidden("У вас нет прав.")

    from .models import NewsCategory
    categories = NewsCategory.objects.filter(is_active=True).order_by('order', 'name')

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        content = request.POST.get("content", "").strip()
        image_files = request.FILES.getlist("image")
        image = image_files[0] if image_files else None
        excerpt = request.POST.get("excerpt", "").strip()
        category_id = request.POST.get("category")
        action = request.POST.get("action", "publish")

        is_published = action == "publish"

        news_item = News(
            title=title,
            content=content,
            author=request.user,
            image=image,
            is_published=is_published,
            moderation_status='approved',
        )
        if excerpt:
            news_item.excerpt = excerpt
        if is_published:
            news_item.published_at = timezone.now()
        if category_id:
            try:
                news_item.category_id = int(category_id)
            except (TypeError, ValueError):
                pass

        news_item.save()
        _handle_news_attachments(request, news_item)
        return redirect('news_detail', pk=news_item.pk)

    return render(request, "news/create_news.html", {
        'categories': categories,
    })


def _user_avatar_url(user):
    if not user or not getattr(user, 'avatar', None):
        return None
    try:
        return user.avatar.url
    except (ValueError, OSError):
        return None


@login_required(login_url='login')
@require_POST
def add_comment(request, pk):
    """Добавить комментарий к новости"""
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    def json_error(message, status=400, **extra):
        payload = {'success': False, 'error': message, **extra}
        return JsonResponse(payload, status=status)

    try:
        news_item = get_object_or_404(News, pk=pk)

        if not news_item.allow_comments:
            return json_error('Комментарии отключены', status=403)

        content = request.POST.get('content', '').strip()
        parent_id = request.POST.get('parent_id')

        if not content:
            return json_error('Комментарий не может быть пустым', status=400)

        automod = AutoModerationService()
        moderation_result = automod.process_comment(request.user, content)

        if not moderation_result['allowed']:
            if is_ajax:
                return json_error(
                    moderation_result['message'],
                    status=403,
                    is_banned=moderation_result['is_banned'],
                    warning_number=moderation_result['warning_number'],
                )
            messages.error(request, moderation_result['message'])
            return redirect('news_detail', pk=pk)

        parent_comment = None
        if parent_id:
            parent_comment = NewsComment.objects.filter(pk=parent_id, news=news_item).first()

        comment = NewsComment.objects.create(
            news=news_item,
            author=request.user,
            content=content,
            parent=parent_comment,
        )
        news_item.recompute_comments_count()

        mention_service = MentionService()
        try:
            mentioned_users = mention_service.process_comment(comment)
        except Exception:
            mentioned_users = []

        if parent_comment and parent_comment.author_id != request.user.id:
            try:
                from notifications.models import Notification, NotificationType

                notification_type, _ = NotificationType.objects.get_or_create(
                    code='comment_reply',
                    defaults={
                        'name': 'Ответ на комментарий',
                        'title_template': '{author} ответил на ваш комментарий',
                        'body_template': '{content}',
                        'priority': 'normal',
                    },
                )
                Notification.objects.create(
                    user=parent_comment.author,
                    notification_type=notification_type,
                    title=f'{request.user.get_full_name() or request.user.username} ответил на ваш комментарий',
                    content=content[:200],
                    link=f'/news/{news_item.id}/#comment-{comment.id}',
                )
            except Exception:
                pass

        if is_ajax:
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'author': comment.author.get_full_name() or comment.author.username,
                    'author_avatar': _user_avatar_url(comment.author),
                    'content': mention_service.highlight_mentions(comment.content),
                    'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M'),
                    'mentioned_count': len(mentioned_users),
                },
            })

        return redirect('news_detail', pk=pk)

    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception('add_comment failed: %s', exc)
        if is_ajax:
            return json_error(
                'Не удалось сохранить комментарий. Попробуйте ещё раз или обновите страницу.',
                status=500,
            )
        messages.error(request, 'Не удалось сохранить комментарий.')
        return redirect('news_detail', pk=pk)


@login_required(login_url='login')
@require_POST
def delete_comment(request, pk, comment_id):
    """Удалить комментарий (мягкое удаление)"""
    comment = get_object_or_404(NewsComment, pk=comment_id, news_id=pk)
    
    # Только автор или модератор может удалить
    if comment.author != request.user and not request.user.isModerator:
        return JsonResponse({'error': 'Нет прав'}, status=403)
    
    comment.is_deleted = True
    comment.save(update_fields=['is_deleted'])
    # После мягкого удаления пересчитываем количество комментариев
    if comment.news_id:
        comment.news.recompute_comments_count()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    return redirect('news_detail', pk=pk)


@login_required(login_url='login')
@require_POST
def edit_comment(request, pk, comment_id):
    """Редактировать комментарий"""
    comment = get_object_or_404(NewsComment, pk=comment_id, news_id=pk)
    
    # Только автор может редактировать
    if comment.author != request.user:
        return JsonResponse({'error': 'Нет прав'}, status=403)
    
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Комментарий не может быть пустым'}, status=400)
    
    comment.content = content
    comment.is_edited = True
    comment.save()
    
    # Обрабатываем упоминания
    mention_service = MentionService()
    mention_service.process_comment(comment)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'highlighted_content': mention_service.highlight_mentions(comment.content)
        })
    
    return redirect('news_detail', pk=pk)


@login_required(login_url='login')
def mention_autocomplete(request):
    """API для автокомплита @упоминаний"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'users': []})
    
    users = User.objects.filter(
        is_active=True,
        is_archived=False
    ).filter(
        # Поиск по username, имени или фамилии
        username__icontains=query
    ) | User.objects.filter(
        is_active=True,
        is_archived=False,
        first_name__icontains=query
    ) | User.objects.filter(
        is_active=True,
        is_archived=False,
        last_name__icontains=query
    )
    
    users = users.distinct()[:10]
    
    return JsonResponse({
        'users': [
            {
                'username': u.username,
                'full_name': u.get_full_name() or u.username,
                'avatar': u.avatar.url if u.avatar else None,
                'position': u.position.name if u.position else '',
            }
            for u in users
        ]
    })


@login_required(login_url='login')
@require_POST
def toggle_reaction(request, pk):
    """Добавить/убрать реакцию на новость (один юзер = одна реакция)"""
    news_item = get_object_or_404(News, pk=pk)
    emoji = request.POST.get('emoji', '').strip()
    
    # Поддерживаемые реакции
    ALLOWED_EMOJIS = ['👍', '❤️', '🔥', '😂', '😮', '😢']
    
    if emoji not in ALLOWED_EMOJIS:
        return JsonResponse({'error': 'Недопустимая реакция'}, status=400)
    
    # Проверяем существующую реакцию пользователя (любую)
    existing = NewsReaction.objects.filter(
        news=news_item,
        user=request.user
    ).first()
    
    if existing:
        if existing.emoji == emoji:
            # Та же реакция — убираем
            existing.delete()
            action = 'removed'
        else:
            # Другая реакция — меняем
            existing.emoji = emoji
            existing.save()
            action = 'changed'
    else:
        # Нет реакции — добавляем
        NewsReaction.objects.create(
            news=news_item,
            user=request.user,
            emoji=emoji
        )
        action = 'added'
    
    # Получаем обновлённые счётчики
    reactions = NewsReaction.objects.filter(news=news_item).values('emoji').annotate(
        count=Count('id')
    )
    
    reaction_counts = {r['emoji']: r['count'] for r in reactions}
    
    # Реакция текущего пользователя (теперь максимум одна)
    user_reaction = NewsReaction.objects.filter(
        news=news_item,
        user=request.user
    ).values_list('emoji', flat=True).first()
    
    return JsonResponse({
        'success': True,
        'action': action,
        'reactions': reaction_counts,
        'user_reactions': [user_reaction] if user_reaction else [],
        'total': sum(reaction_counts.values()),
    })


@login_required(login_url='login')
def share_conversations(request):
    from chat.models import Conversation, UserConversation
    uc_ids = UserConversation.objects.filter(user=request.user).values_list('conversation_id', flat=True)
    convs = Conversation.objects.filter(id__in=uc_ids).order_by('-updated_at')[:30]
    result = []
    for c in convs:
        name = c.name or 'Без названия'
        if c.type == 'direct':
            other = c.participants.exclude(id=request.user.id).first()
            if other:
                name = f"{other.last_name} {other.first_name}".strip() or other.username
        result.append({'id': c.id, 'name': name, 'type': c.type})
    return JsonResponse({'conversations': result})


@login_required(login_url='login')
@require_POST
def share_news(request, pk):
    import re as _re
    from django.utils import timezone
    from chat.models import Conversation, UserConversation, Message

    news_item = get_object_or_404(News, pk=pk)
    conversation_id = request.POST.get('conversation_id')
    if not conversation_id:
        return JsonResponse({'error': 'conversation_id required'}, status=400)

    uc = UserConversation.objects.filter(user=request.user, conversation_id=conversation_id).first()
    if not uc:
        return JsonResponse({'error': 'Нет доступа к чату'}, status=403)

    news_url = f'/news/{news_item.pk}/'
    clean_excerpt = _re.sub(r'<[^>]+>', '', news_item.excerpt or news_item.content or '')
    preview = clean_excerpt[:150].strip()
    if len(clean_excerpt) > 150:
        preview += '...'
    payload = json.dumps({
        'title': news_item.title,
        'excerpt': preview,
        'type': news_item.category.name if news_item.category else 'Новость',
        'url': news_url,
        'source': 'news',
    }, ensure_ascii=False)
    msg_text = f'[link_card]{payload}'
    Message.objects.create(
        conversation_id=conversation_id,
        author=request.user,
        content=msg_text,
        type='text',
    )
    Conversation.objects.filter(id=conversation_id).update(updated_at=timezone.now())
    return JsonResponse({'success': True})
