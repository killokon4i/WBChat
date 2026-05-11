import json
import difflib
import os
import mimetypes
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q, Avg

from .models import (
    Article, Category, Tag, ArticleVersion, ArticleComment,
    ArticleRating, ArticleView, FAQ, Subscription, EditLock, Snippet,
    ArticleAttachment, SuggestedEdit, TermRequest, AuditLog,
)
from .forms import (
    ArticleForm, CommentForm, FAQForm,
    SuggestedEditForm, TermRequestForm, AttachmentForm,
)
from .services import (
    KBSearchService, RecommendationService,
    QualityCheckService, AuditService,
)

search_service = KBSearchService()
rec_service = RecommendationService()
quality_service = QualityCheckService()


# === Notifications helpers ===

def _notify_article_subscribers(article, editor, event='update'):
    from notifications.models import Notification, NotificationType

    code = 'kb_article_updated' if event == 'update' else 'kb_article_created'
    name = 'Обновление статьи базы знаний' if event == 'update' else 'Новая статья базы знаний'

    notif_type, _ = NotificationType.objects.get_or_create(
        code=code,
        defaults={
            'name': name,
            'title_template': 'Статья «{title}»',
            'body_template': '{editor} {action} статью «{title}»',
            'priority': 'normal',
        }
    )

    subscriber_ids = set()
    for sub in Subscription.objects.filter(article=article).select_related('user'):
        subscriber_ids.add(sub.user_id)
    if article.category:
        for sub in Subscription.objects.filter(category=article.category).select_related('user'):
            subscriber_ids.add(sub.user_id)
    for tag in article.tags.all():
        for sub in Subscription.objects.filter(tag=tag).select_related('user'):
            subscriber_ids.add(sub.user_id)
    subscriber_ids.discard(editor.id)
    if not subscriber_ids:
        return

    editor_name = editor.get_full_name() or editor.username
    editor_link = f'<a href="/directory/employee/{editor.id}/">{editor_name}</a>'
    action_text = 'обновил(а)' if event == 'update' else 'опубликовал(а)'
    article_link = f'/knowledge/article/{article.slug}/'

    notifications = [
        Notification(
            user_id=uid,
            notification_type=notif_type,
            title=f'Статья «{article.title}» {"обновлена" if event == "update" else "опубликована"}',
            content=f'{editor_link} {action_text} статью «{article.title}»',
            link=article_link,
        )
        for uid in subscriber_ids
    ]
    Notification.objects.bulk_create(notifications)


def _notify_comment_to_author(comment, article):
    """Notify article author about a new comment."""
    if not article.author or article.author == comment.author:
        return
    from notifications.models import Notification, NotificationType
    notif_type, _ = NotificationType.objects.get_or_create(
        code='kb_new_comment',
        defaults={
            'name': 'Новый комментарий к статье',
            'title_template': 'Комментарий к «{title}»',
            'body_template': '{author} оставил(а) комментарий к статье «{title}»',
            'priority': 'normal',
        }
    )
    commenter = comment.author.get_full_name() or comment.author.username
    commenter_link = f'<a href="/directory/employee/{comment.author.id}/">{commenter}</a>'
    Notification.objects.create(
        user=article.author,
        notification_type=notif_type,
        title=f'Комментарий к «{article.title}»',
        content=f'{commenter_link} оставил(а) комментарий к статье «{article.title}»',
        link=f'/knowledge/article/{article.slug}/',
    )


# === Home ===

@login_required
def knowledge_home(request):
    popular = rec_service.get_popular(days=30, limit=6)
    recent = rec_service.get_recently_updated(limit=6)
    recommended = rec_service.get_recommended(request.user, limit=6)
    tag_cloud = rec_service.get_tag_cloud(limit=30)
    root_categories = Category.objects.filter(
        parent__isnull=True, is_active=True
    ).order_by('order', 'name')
    onboarding_cat = Category.objects.filter(slug='onboarding', is_active=True).first()

    return render(request, 'knowledge/home.html', {
        'popular': popular,
        'recent': recent,
        'recommended': recommended,
        'tag_cloud': tag_cloud,
        'root_categories': root_categories,
        'onboarding_cat': onboarding_cat,
    })


# === Category ===

@login_required
def category_view(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    if not category.is_visible_to(request.user):
        return HttpResponseForbidden('Доступ ограничен')

    children = category.children.filter(is_active=True).order_by('order', 'name')
    articles = Article.objects.filter(
        Q(category=category) | Q(categories=category),
        status='published'
    ).distinct().select_related('author').order_by('-is_pinned', '-published_at')

    sort = request.GET.get('sort', 'date')
    if sort == 'rating':
        articles = articles.order_by('-avg_rating')
    elif sort == 'views':
        articles = articles.order_by('-views_count')

    is_subscribed = Subscription.objects.filter(
        user=request.user, category=category
    ).exists()

    return render(request, 'knowledge/category.html', {
        'category': category,
        'children': children,
        'articles': articles,
        'breadcrumbs': category.get_breadcrumbs(),
        'is_subscribed': is_subscribed,
        'current_sort': sort,
    })


# === Article detail ===

@login_required
def article_detail(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if not article.can_view(request.user):
        return HttpResponseForbidden('Доступ ограничен')

    ArticleView.objects.create(
        article=article, user=request.user,
        ip_address=request.META.get('REMOTE_ADDR')
    )
    Article.objects.filter(pk=article.pk).update(views_count=article.views_count + 1)
    AuditService.log(article, request.user, 'view', ip_address=request.META.get('REMOTE_ADDR'))

    comments = article.article_comments.filter(
        is_deleted=False, parent__isnull=True
    ).select_related('author').prefetch_related('replies__author')
    for comment in comments:
        comment.processed_replies = list(
            comment.replies.filter(is_deleted=False).select_related('author')
        )

    user_rating = None
    if request.user.is_authenticated:
        user_rating = ArticleRating.objects.filter(article=article, user=request.user).first()

    is_subscribed = Subscription.objects.filter(user=request.user, article=article).exists()
    toc = article.generate_toc()
    content = article.content_with_anchors()
    related_docs = article.related_documents.filter(status='active')
    can_edit = article.can_edit(request.user)
    attachments = article.attachments.all()

    return render(request, 'knowledge/article_detail.html', {
        'article': article,
        'content': content,
        'toc': toc,
        'comments': comments,
        'comment_form': CommentForm(),
        'user_rating': user_rating,
        'is_subscribed': is_subscribed,
        'breadcrumbs': article.get_breadcrumbs(),
        'related_docs': related_docs,
        'can_edit': can_edit,
        'attachments': attachments,
    })


# === Article CRUD ===

@login_required
def article_create(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            action = request.POST.get('action', 'draft')
            article.status = 'published' if action == 'publish' else 'draft'
            if article.status == 'published':
                article.published_at = article.published_at or timezone.now()
            tpl = form.cleaned_data.get('template_id')
            if tpl:
                article.template = tpl
            article.save()
            form._save_tags(article)
            article.categories.set(form.cleaned_data.get('extra_categories', []))

            ArticleVersion.objects.create(
                article=article, version_number=1,
                title=article.title, content=article.content,
                author=request.user, comment='Создание статьи'
            )
            AuditService.log(article, request.user, 'publish', 'Создание статьи',
                             request.META.get('REMOTE_ADDR'))

            if article.status == 'published':
                _notify_article_subscribers(article, request.user, event='create')

            _handle_attachments(request, article)
            messages.success(request, 'Статья успешно создана!')
            return redirect('kb_article_detail', slug=article.slug)
    else:
        form = ArticleForm()

    templates = list(
        __import__('knowledge.models', fromlist=['ArticleTemplate']).ArticleTemplate
        .objects.filter(is_active=True).values('id', 'name', 'article_type', 'content_template')
    )
    return render(request, 'knowledge/article_form.html', {
        'form': form, 'is_edit': False,
        'article_templates_json': json.dumps(templates, ensure_ascii=False, default=str),
    })


@login_required
def article_edit(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if not article.can_edit(request.user):
        return HttpResponseForbidden('Нет прав на редактирование')

    lock, acquired = EditLock.acquire(article, request.user)
    lock_warning = None
    if not acquired:
        lock_warning = f'Статью редактирует {lock.user.get_full_name() or lock.user.username} с {lock.locked_at.strftime("%H:%M")}'

    if request.method == 'POST':
        old_content = article.content
        old_title = article.title
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            article = form.save(commit=False)
            action = request.POST.get('action', 'save')
            if action == 'publish':
                article.status = 'published'
                if not article.published_at:
                    article.published_at = timezone.now()
            elif action == 'draft':
                article.status = 'draft'
            article.save()
            form._save_tags(article)
            article.categories.set(form.cleaned_data.get('extra_categories', []))

            changed = old_content != article.content or old_title != article.title
            if changed:
                article.current_version += 1
                article.save(update_fields=['current_version'])
                ArticleVersion.objects.create(
                    article=article,
                    version_number=article.current_version,
                    title=article.title, content=article.content,
                    author=request.user,
                    comment=request.POST.get('version_comment', '')
                )
                _notify_article_subscribers(article, request.user)
                AuditService.log(article, request.user, 'edit',
                                 f'v{article.current_version}',
                                 request.META.get('REMOTE_ADDR'))

            _handle_attachments(request, article)
            EditLock.release(article, request.user)
            messages.success(request, 'Изменения внесены успешно!')
            return redirect('kb_article_detail', slug=article.slug)
    else:
        form = ArticleForm(instance=article)

    templates = list(
        __import__('knowledge.models', fromlist=['ArticleTemplate']).ArticleTemplate
        .objects.filter(is_active=True).values('id', 'name', 'article_type', 'content_template')
    )
    return render(request, 'knowledge/article_form.html', {
        'form': form, 'article': article, 'is_edit': True,
        'lock_warning': lock_warning,
        'article_templates_json': json.dumps(templates, ensure_ascii=False, default=str),
    })


def _handle_attachments(request, article):
    """Process uploaded files for article."""
    files = request.FILES.getlist('attachments')
    for f in files:
        errors = quality_service.validate_attachment(f)
        if errors:
            messages.warning(request, f'Файл {f.name}: {"; ".join(errors)}')
            continue
        mime = mimetypes.guess_type(f.name)[0] or ''
        ArticleAttachment.objects.create(
            article=article, file=f, file_name=f.name,
            file_size=f.size, mime_type=mime,
            uploaded_by=request.user,
        )


@login_required
def article_delete(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if not article.can_edit(request.user):
        return HttpResponseForbidden('Нет прав')

    is_admin = request.user.is_superuser or getattr(request.user, 'isModerator', False) or getattr(request.user, 'is_admin_portal', False)

    if request.method == 'POST':
        action = request.POST.get('action', 'archive')
        if action == 'permanent' and is_admin:
            title = article.title
            AuditService.log(article, request.user, 'delete',
                             f'Полное удаление: {title}', request.META.get('REMOTE_ADDR'))
            article.delete()
            messages.success(request, f'Статья «{title}» полностью удалена.')
        else:
            article.status = 'archived'
            article.save(update_fields=['status'])
            AuditService.log(article, request.user, 'delete',
                             'Архивирование', request.META.get('REMOTE_ADDR'))
            messages.success(request, 'Статья перемещена в архив.')

        # Если действие инициировано из личного кабинета модератора, возвращаем туда
        referer = request.META.get('HTTP_REFERER', '')
        if '/knowledge/dashboard' in referer:
            return redirect('kb_personal_dashboard')
        return redirect('kb_home')

    return render(request, 'knowledge/article_confirm_delete.html', {
        'article': article,
        'is_admin': is_admin,
    })


@login_required
def article_unarchive(request, slug):
    """Вернуть архивную статью в черновики (для модераторов/админов)."""
    article = get_object_or_404(Article, slug=slug, status='archived')
    is_admin = (
        request.user.is_superuser
        or getattr(request.user, 'isModerator', False)
        or getattr(request.user, 'is_admin_portal', False)
    )
    if not is_admin:
        return HttpResponseForbidden('Нет прав')
    if request.method != 'POST':
        return JsonResponse({'error': 'POST only'}, status=405)

    article.status = 'draft'
    article.save(update_fields=['status'])
    AuditService.log(
        article, request.user, 'rollback',
        'Разархивирование в черновик',
        request.META.get('REMOTE_ADDR'),
    )
    messages.success(request, f'Статья «{article.title}» возвращена в черновики.')
    return redirect('kb_personal_dashboard')


# === Versions ===

@login_required
def article_versions(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if not article.can_edit(request.user):
        return HttpResponseForbidden('Нет прав')
    versions = article.versions.select_related('author').order_by('-version_number')
    return render(request, 'knowledge/article_versions.html', {
        'article': article, 'versions': versions,
    })


@login_required
def article_diff(request, slug, v1, v2):
    article = get_object_or_404(Article, slug=slug)
    if not article.can_edit(request.user):
        return HttpResponseForbidden('Нет прав')
    ver1 = get_object_or_404(ArticleVersion, article=article, version_number=v1)
    ver2 = get_object_or_404(ArticleVersion, article=article, version_number=v2)
    diff_html = difflib.HtmlDiff(wrapcolumn=80).make_table(
        ver1.content.splitlines(), ver2.content.splitlines(),
        fromdesc=f'v{v1} ({ver1.created_at.strftime("%d.%m.%Y %H:%M")})',
        todesc=f'v{v2} ({ver2.created_at.strftime("%d.%m.%Y %H:%M")})',
    )
    return render(request, 'knowledge/article_diff.html', {
        'article': article, 'ver1': ver1, 'ver2': ver2, 'diff_html': diff_html,
    })


@login_required
def article_rollback(request, slug, version_number):
    article = get_object_or_404(Article, slug=slug)
    if not article.can_edit(request.user):
        return HttpResponseForbidden('Нет прав')
    version = get_object_or_404(ArticleVersion, article=article, version_number=version_number)
    if request.method == 'POST':
        article.current_version += 1
        article.title = version.title
        article.content = version.content
        article.save(update_fields=['title', 'content', 'current_version', 'updated_at'])
        ArticleVersion.objects.create(
            article=article, version_number=article.current_version,
            title=version.title, content=version.content,
            author=request.user, comment=f'Откат к версии {version_number}',
            is_rollback=True
        )
        AuditService.log(article, request.user, 'rollback',
                         f'Откат к v{version_number}', request.META.get('REMOTE_ADDR'))
        return redirect('kb_article_detail', slug=article.slug)
    return render(request, 'knowledge/article_rollback.html', {
        'article': article, 'version': version,
    })


@login_required
def article_publish(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if not article.can_edit(request.user):
        return HttpResponseForbidden('Нет прав')
    if request.method == 'POST':
        new_status = request.POST.get('status', 'published')
        if new_status in dict(Article.STATUS_CHOICES):
            article.status = new_status
            if new_status == 'published' and not article.published_at:
                article.published_at = timezone.now()
            article.save()
            AuditService.log(article, request.user, 'publish',
                             f'Статус -> {new_status}', request.META.get('REMOTE_ADDR'))
            if new_status == 'published':
                _notify_article_subscribers(article, request.user, event='create')
        return redirect('kb_article_detail', slug=article.slug)
    return JsonResponse({'error': 'POST only'}, status=405)


# === Preview ===

@login_required
def article_preview(request):
    """AJAX preview of article content."""
    content = request.POST.get('content', '')
    title = request.POST.get('title', 'Предпросмотр')
    return render(request, 'knowledge/article_preview.html', {
        'title': title, 'content': content,
    })


# === Autosave ===

@login_required
@require_POST
def article_autosave(request, slug):
    """AJAX autosave draft."""
    article = get_object_or_404(Article, slug=slug)
    if not article.can_edit(request.user):
        return JsonResponse({'error': 'Нет прав'}, status=403)
    content = request.POST.get('content', '')
    title = request.POST.get('title', '')
    if title:
        article.title = title
    if content:
        article.content = content
    article.save(update_fields=['title', 'content', 'updated_at'])
    return JsonResponse({'success': True, 'saved_at': timezone.now().strftime('%H:%M:%S')})


# === Quality check ===

@login_required
def article_quality_check(request, slug):
    """AJAX quality check for article."""
    article = get_object_or_404(Article, slug=slug)
    issues = quality_service.check_article(article)
    return JsonResponse({'issues': issues})


# === Attachments ===

@login_required
@require_POST
def upload_attachment(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if not article.can_edit(request.user):
        return JsonResponse({'error': 'Нет прав'}, status=403)
    f = request.FILES.get('file')
    if not f:
        return JsonResponse({'error': 'Файл не выбран'}, status=400)
    errors = quality_service.validate_attachment(f)
    if errors:
        return JsonResponse({'error': '; '.join(errors)}, status=400)
    mime = mimetypes.guess_type(f.name)[0] or ''
    att = ArticleAttachment.objects.create(
        article=article, file=f, file_name=f.name,
        file_size=f.size, mime_type=mime, uploaded_by=request.user,
    )
    AuditService.log(article, request.user, 'edit',
                     f'Загружен файл: {f.name}', request.META.get('REMOTE_ADDR'))
    return JsonResponse({
        'success': True,
        'attachment': {
            'id': att.id, 'name': att.file_name,
            'size': att.file_size, 'url': att.file.url,
        }
    })


@login_required
@require_POST
def delete_attachment(request, slug, attachment_id):
    article = get_object_or_404(Article, slug=slug)
    if not article.can_edit(request.user):
        return JsonResponse({'error': 'Нет прав'}, status=403)
    att = get_object_or_404(ArticleAttachment, id=attachment_id, article=article)
    att.file.delete(save=False)
    att.delete()
    return JsonResponse({'success': True})


# === Comments ===

@login_required
@require_POST
def add_comment(request, slug):
    article = get_object_or_404(Article, slug=slug)
    content = request.POST.get('content', '').strip()
    parent_id = request.POST.get('parent_id')
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if not content:
        if is_ajax:
            return JsonResponse({'error': 'Пустой комментарий'}, status=400)
        return redirect('kb_article_detail', slug=slug)

    try:
        from news.services import AutoModerationService
        automod = AutoModerationService()
        mod_result = automod.process_comment(request.user, content)
        if not mod_result['allowed']:
            if is_ajax:
                return JsonResponse({
                    'error': mod_result['message'],
                    'warning_number': mod_result.get('warning_number'),
                    'is_banned': mod_result.get('is_banned', False),
                }, status=403)
            messages.error(request, mod_result['message'])
            return redirect('kb_article_detail', slug=slug)
    except ImportError:
        pass

    # Process @mentions
    import re
    mentioned_usernames = re.findall(r'@(\w+)', content)
    if mentioned_usernames:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        from notifications.models import Notification, NotificationType
        notif_type, _ = NotificationType.objects.get_or_create(
            code='kb_mention',
            defaults={
                'name': 'Упоминание в комментарии БЗ',
                'title_template': 'Вас упомянули в комментарии',
                'body_template': '{author} упомянул(а) вас в комментарии к статье «{title}»',
                'priority': 'normal',
            }
        )
        commenter = request.user.get_full_name() or request.user.username
        for uname in set(mentioned_usernames):
            mentioned_user = User.objects.filter(username=uname).first()
            if mentioned_user and mentioned_user != request.user:
                Notification.objects.create(
                    user=mentioned_user,
                    notification_type=notif_type,
                    title=f'Вас упомянули в комментарии',
                    content=f'<a href="/directory/employee/{request.user.id}/">{commenter}</a> упомянул(а) вас в комментарии к статье «{article.title}»',
                    link=f'/knowledge/article/{article.slug}/',
                )

    parent = None
    if parent_id:
        parent = ArticleComment.objects.filter(id=parent_id, article=article).first()

    comment = ArticleComment.objects.create(
        article=article, author=request.user, content=content, parent=parent,
    )
    Article.objects.filter(pk=article.pk).update(
        comments_count=article.article_comments.filter(is_deleted=False).count()
    )
    _notify_comment_to_author(comment, article)

    if is_ajax:
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'author': comment.author.get_full_name() or comment.author.username,
                'content': comment.content,
                'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M'),
            }
        })
    return redirect('kb_article_detail', slug=slug)


@login_required
@require_POST
def delete_comment(request, slug, comment_id):
    comment = get_object_or_404(ArticleComment, id=comment_id, article__slug=slug)
    if comment.author != request.user and not getattr(request.user, 'isModerator', False):
        return HttpResponseForbidden('Нет прав')
    comment.is_deleted = True
    comment.save(update_fields=['is_deleted'])
    return redirect('kb_article_detail', slug=slug)


@login_required
@require_POST
def edit_comment(request, slug, comment_id):
    comment = get_object_or_404(ArticleComment, id=comment_id, article__slug=slug)
    if comment.author != request.user:
        return JsonResponse({'error': 'Нет прав'}, status=403)
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'error': 'Комментарий не может быть пустым'}, status=400)
    comment.content = content
    comment.is_edited = True
    comment.save(update_fields=['content', 'is_edited'])
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'content': comment.content})
    return redirect('kb_article_detail', slug=slug)


# === Rating ===

@login_required
@require_POST
def rate_article(request, slug):
    article = get_object_or_404(Article, slug=slug)
    try:
        score = int(request.POST.get('score', 0))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Неверная оценка'}, status=400)
    if score < 1 or score > 5:
        return JsonResponse({'error': 'Оценка от 1 до 5'}, status=400)
    ArticleRating.objects.update_or_create(
        article=article, user=request.user, defaults={'score': score}
    )
    agg = ArticleRating.objects.filter(article=article).aggregate(avg=Avg('score'))
    cnt = ArticleRating.objects.filter(article=article).count()
    article.avg_rating = round(agg['avg'] or 0, 1)
    article.ratings_count = cnt
    article.save(update_fields=['avg_rating', 'ratings_count'])
    return JsonResponse({
        'success': True, 'avg_rating': article.avg_rating,
        'ratings_count': article.ratings_count, 'user_score': score,
    })


# === Subscriptions ===

@login_required
@require_POST
def toggle_subscription(request, target_type, target_id):
    kwargs = {'user': request.user}
    if target_type == 'category':
        kwargs['category_id'] = target_id
    elif target_type == 'tag':
        kwargs['tag_id'] = target_id
    elif target_type == 'article':
        kwargs['article_id'] = target_id
    else:
        return JsonResponse({'error': 'Invalid type'}, status=400)
    sub = Subscription.objects.filter(**kwargs).first()
    if sub:
        sub.delete()
        return JsonResponse({'subscribed': False})
    Subscription.objects.create(**kwargs)
    return JsonResponse({'subscribed': True})


# === Search ===

@login_required
def search(request):
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category')
    tag_slug = request.GET.get('tag')
    article_type = request.GET.get('type')
    author_id = request.GET.get('author')
    try:
        page = max(1, int(request.GET.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    filters = {}
    if category_id:
        try:
            filters['category_id'] = int(category_id)
        except (ValueError, TypeError):
            pass
    if tag_slug:
        filters['tag_slug'] = tag_slug
    if article_type:
        filters['article_type'] = article_type
    if author_id:
        try:
            filters['author_id'] = int(author_id)
        except (ValueError, TypeError):
            pass

    try:
        results = search_service.search(query, request.user, filters, page)
    except Exception:
        import logging
        logging.getLogger(__name__).exception('KB search failed')
        results = {'results': [], 'total': 0, 'page': page, 'pages': 0}
        messages.error(request, 'Ошибка поиска. Попробуйте другой запрос.')

    categories = Category.objects.filter(is_active=True, parent__isnull=True)
    tags = Tag.objects.filter(is_approved=True).order_by('-usage_count')[:20]
    article_types = Article.TYPE_CHOICES

    did_you_mean = None
    if query and results['total'] == 0:
        suggestions = search_service.suggest(query, request.user, limit=1)
        if suggestions:
            did_you_mean = suggestions[0]['title']

    return render(request, 'knowledge/search.html', {
        'query': query,
        'results': results['results'],
        'total': results['total'],
        'page': results['page'],
        'pages': results['pages'],
        'categories': categories,
        'tags': tags,
        'article_types': article_types,
        'current_filters': filters,
        'did_you_mean': did_you_mean,
    })


@login_required
def search_suggest(request):
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    suggestions = search_service.suggest(query, request.user, limit=5)
    return JsonResponse({'results': suggestions})


@login_required
def tags_autocomplete(request):
    query = request.GET.get('q', '').strip()
    if len(query) < 1:
        return JsonResponse({'tags': []})
    tags = Tag.objects.filter(
        Q(name__icontains=query) | Q(synonyms__icontains=query), is_approved=True
    ).values_list('name', flat=True)[:10]
    return JsonResponse({'tags': list(tags)})


# === FAQ ===

@login_required
def faq_list(request):
    category_slug = request.GET.get('category', '')
    faqs = FAQ.objects.filter(is_active=True).select_related('category', 'related_article')
    if category_slug:
        faqs = faqs.filter(category__slug=category_slug)
    categories = Category.objects.filter(is_active=True, faqs__isnull=False).distinct()
    return render(request, 'knowledge/faq.html', {
        'faqs': faqs, 'categories': categories, 'current_category': category_slug,
    })


@login_required
@require_POST
def faq_helpful(request, faq_id):
    faq = get_object_or_404(FAQ, id=faq_id, is_active=True)
    helpful = request.POST.get('helpful') == 'yes'
    if helpful:
        FAQ.objects.filter(pk=faq.pk).update(helpful_yes=faq.helpful_yes + 1)
    else:
        FAQ.objects.filter(pk=faq.pk).update(helpful_no=faq.helpful_no + 1)
    return JsonResponse({'success': True, 'helpful': helpful})


@login_required
@require_POST
def faq_escalate(request, faq_id):
    """Escalation: FAQ answer didn't help — notify author."""
    faq = get_object_or_404(FAQ, id=faq_id, is_active=True)
    feedback = request.POST.get('feedback', '').strip()

    if faq.author:
        from notifications.models import Notification, NotificationType
        notif_type, _ = NotificationType.objects.get_or_create(
            code='kb_faq_escalation',
            defaults={
                'name': 'Эскалация FAQ',
                'title_template': 'FAQ не помог: {question}',
                'body_template': '{feedback}',
                'priority': 'high',
            }
        )
        user_name = request.user.get_full_name() or request.user.username
        Notification.objects.create(
            user=faq.author,
            notification_type=notif_type,
            title=f'FAQ не помог: {faq.question[:60]}',
            content=f'<a href="/directory/employee/{request.user.id}/">{user_name}</a> сообщает, что ответ на вопрос «{faq.question[:80]}» не помог. {("Комментарий: " + feedback) if feedback else ""}',
            link='/knowledge/faq/',
        )
    return JsonResponse({'success': True})


# === Edit Lock API ===

@login_required
@require_POST
def extend_lock(request, slug):
    article = get_object_or_404(Article, slug=slug)
    lock, acquired = EditLock.acquire(article, request.user, duration_minutes=15)
    return JsonResponse({'extended': acquired})


@login_required
@require_POST
def release_lock(request, slug):
    article = get_object_or_404(Article, slug=slug)
    EditLock.release(article, request.user)
    return JsonResponse({'released': True})


# === Tags ===

@login_required
def tag_view(request, slug):
    tag = get_object_or_404(Tag, slug=slug, is_approved=True)
    articles = Article.objects.filter(
        tags=tag, status='published'
    ).select_related('category', 'author').order_by('-published_at')
    is_subscribed = Subscription.objects.filter(user=request.user, tag=tag).exists()
    return render(request, 'knowledge/tag.html', {
        'tag': tag, 'articles': articles, 'is_subscribed': is_subscribed,
    })


@login_required
@require_POST
def tag_delete(request, slug):
    if not (request.user.is_superuser or getattr(request.user, 'isModerator', False)
            or getattr(request.user, 'is_admin_portal', False)):
        return HttpResponseForbidden('Только для администраторов')
    tag = get_object_or_404(Tag, slug=slug)
    name = tag.name
    tag.delete()
    messages.success(request, f'Тег «{name}» удалён.')
    referer = request.META.get('HTTP_REFERER', '')
    if '/knowledge/dashboard' in referer:
        return redirect('kb_personal_dashboard')
    return redirect('kb_home')


# === Suggested edits ===

@login_required
def suggest_edit(request, slug):
    article = get_object_or_404(Article, slug=slug, status='published')
    if request.method == 'POST':
        form = SuggestedEditForm(request.POST)
        if form.is_valid():
            se = form.save(commit=False)
            se.article = article
            se.author = request.user
            if not se.title:
                se.title = article.title
            se.save()
            _notify_suggested_edit(se, article)
            messages.success(request, 'Предложение отправлено на рассмотрение!')
            return redirect('kb_article_detail', slug=slug)
    else:
        form = SuggestedEditForm(initial={
            'title': article.title, 'content': article.content,
        })
    return render(request, 'knowledge/suggest_edit.html', {
        'form': form, 'article': article,
    })


def _notify_suggested_edit(suggested_edit, article):
    """Notify article author and editors about a new suggested edit."""
    from notifications.models import Notification, NotificationType
    notif_type, _ = NotificationType.objects.get_or_create(
        code='kb_suggested_edit',
        defaults={
            'name': 'Предложена правка к статье',
            'title_template': 'Предложена правка к «{title}»',
            'body_template': '{author} предложил(а) правку к статье «{title}»',
            'priority': 'normal',
        }
    )
    se_author = suggested_edit.author
    se_author_name = se_author.get_full_name() or se_author.username
    se_author_link = f'<a href="/directory/employee/{se_author.id}/">{se_author_name}</a>'
    article_link = f'/knowledge/article/{article.slug}/suggested-edits/'

    recipient_ids = set()
    if article.author_id:
        recipient_ids.add(article.author_id)
    for editor_id in article.editors.values_list('id', flat=True):
        recipient_ids.add(editor_id)
    recipient_ids.discard(se_author.id)

    if not recipient_ids:
        return
    comment_text = f' Комментарий: «{suggested_edit.comment}»' if suggested_edit.comment else ''
    notifications = [
        Notification(
            user_id=uid,
            notification_type=notif_type,
            title=f'Предложена правка к «{article.title}»',
            content=f'{se_author_link} предложил(а) правку к статье «{article.title}».{comment_text}',
            link=article_link,
        )
        for uid in recipient_ids
    ]
    Notification.objects.bulk_create(notifications)


@login_required
def suggested_edits_list(request, slug):
    article = get_object_or_404(Article, slug=slug)
    if not article.can_edit(request.user):
        return HttpResponseForbidden('Нет прав')
    edits = article.suggested_edits.select_related('author').order_by('-created_at')

    import re
    clean_tag = re.compile(r'<[^>]+>')
    for edit in edits:
        original_lines = clean_tag.sub('', article.content).splitlines()
        suggested_lines = clean_tag.sub('', edit.content).splitlines()
        edit.diff_html = difflib.HtmlDiff(wrapcolumn=80).make_table(
            original_lines,
            suggested_lines,
            fromdesc='Текущая версия',
            todesc=f'Предложение от {edit.author.get_full_name() or edit.author.username}',
        )

    return render(request, 'knowledge/suggested_edits.html', {
        'article': article, 'edits': edits,
    })


@login_required
@require_POST
def review_suggested_edit(request, slug, edit_id):
    article = get_object_or_404(Article, slug=slug)
    if not article.can_edit(request.user):
        return HttpResponseForbidden('Нет прав')
    se = get_object_or_404(SuggestedEdit, id=edit_id, article=article)
    action = request.POST.get('action')
    if action == 'accept':
        article.content = se.content
        if se.title:
            article.title = se.title
        article.current_version += 1
        article.save(update_fields=['title', 'content', 'current_version', 'updated_at'])
        ArticleVersion.objects.create(
            article=article, version_number=article.current_version,
            title=article.title, content=article.content,
            author=request.user,
            comment=f'Принята правка от {se.author.get_full_name() or se.author.username}'
        )
        se.status = 'accepted'
    elif action == 'reject':
        se.status = 'rejected'
    se.reviewed_by = request.user
    se.review_comment = request.POST.get('review_comment', '')
    se.reviewed_at = timezone.now()
    se.save()
    messages.success(request, 'Предложение обработано.')
    return redirect('kb_suggested_edits', slug=slug)


# === Term requests ===

@login_required
def request_term(request):
    if request.method == 'POST':
        form = TermRequestForm(request.POST)
        if form.is_valid():
            TermRequest.objects.create(
                term=form.cleaned_data['term'],
                description=form.cleaned_data['description'],
                synonyms=form.cleaned_data['synonyms'],
                requested_by=request.user,
            )
            messages.success(request, 'Заявка на термин отправлена!')
            referer = request.META.get('HTTP_REFERER', '')
            if '/knowledge/dashboard' in referer:
                return redirect('kb_personal_dashboard')
            return redirect('kb_home')
    else:
        form = TermRequestForm()
    return render(request, 'knowledge/term_request.html', {'form': form})


@login_required
def term_requests_list(request):
    if not (request.user.is_superuser or getattr(request.user, 'isModerator', False)):
        return HttpResponseForbidden('Только для модераторов')
    requests_qs = TermRequest.objects.select_related('requested_by', 'reviewed_by').order_by('-created_at')
    return render(request, 'knowledge/term_requests.html', {'term_requests': requests_qs})


@login_required
@require_POST
def review_term_request(request, request_id):
    if not (request.user.is_superuser or getattr(request.user, 'isModerator', False)):
        return HttpResponseForbidden('Только для модераторов')
    tr = get_object_or_404(TermRequest, id=request_id)
    action = request.POST.get('action')
    if action == 'approve':
        from django.utils.text import slugify
        slug = slugify(tr.term, allow_unicode=True) or tr.term.lower().replace(' ', '-')
        tag = Tag.objects.filter(slug=slug).first()
        if not tag:
            synonyms_list = [s.strip() for s in tr.synonyms.split(',') if s.strip()] if tr.synonyms else None
            tag = Tag.objects.create(
                name=tr.term, slug=slug,
                description=tr.description,
                synonyms=synonyms_list,
                is_controlled=True, is_approved=True,
            )
        tr.status = 'approved'
        tr.created_tag = tag
    elif action == 'reject':
        tr.status = 'rejected'
    tr.reviewed_by = request.user
    tr.reviewed_at = timezone.now()
    tr.save()
    messages.success(request, f'Заявка на термин «{tr.term}» обработана.')
    return redirect('kb_term_requests')


# === Time tracking ===

@login_required
@require_POST
def track_time(request, slug):
    """AJAX endpoint to record time spent on article."""
    article = get_object_or_404(Article, slug=slug)
    try:
        seconds = int(request.POST.get('seconds', 0))
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid'}, status=400)
    if seconds > 0:
        last_view = ArticleView.objects.filter(
            article=article, user=request.user
        ).order_by('-viewed_at').first()
        if last_view:
            last_view.time_spent_seconds = seconds
            last_view.save(update_fields=['time_spent_seconds'])
    return JsonResponse({'success': True})


# === Statistics and export ===

@login_required
def statistics_view(request):
    if not (request.user.is_superuser or getattr(request.user, 'isModerator', False)
            or getattr(request.user, 'is_admin_portal', False)):
        return HttpResponseForbidden('Только для модераторов')

    from .services import StatisticsService, ActualizationService
    stats_service = StatisticsService()
    act_service = ActualizationService()

    overview = stats_service.get_overview()
    top_by_views = stats_service.get_top_articles(limit=10, by='views')
    top_by_rating = stats_service.get_top_articles(limit=10, by='rating')
    category_stats = stats_service.get_category_stats()
    author_stats = stats_service.get_author_stats(limit=10)
    search_analytics = stats_service.get_search_analytics(days=30)
    needs_review_list = act_service.get_articles_needing_review()[:20]
    stale_articles = act_service.get_stale_articles(months=12)[:20]

    avg_time = ArticleView.objects.filter(
        time_spent_seconds__gt=0
    ).aggregate(avg=Avg('time_spent_seconds'))

    total_published = Article.objects.filter(status='published').count()
    needs_update_count = Article.objects.filter(
        Q(needs_actualization=True) | Q(status='needs_review'),
        status__in=['published', 'needs_review']
    ).distinct().count()
    update_ratio = round(needs_update_count / total_published * 100, 1) if total_published else 0

    pending_suggestions = SuggestedEdit.objects.filter(status='pending').count()
    pending_terms = TermRequest.objects.filter(status='pending').count()

    return render(request, 'knowledge/statistics.html', {
        'overview': overview,
        'top_by_views': top_by_views,
        'top_by_rating': top_by_rating,
        'category_stats': category_stats,
        'author_stats': author_stats,
        'search_analytics': search_analytics,
        'needs_review_list': needs_review_list,
        'stale_articles': stale_articles,
        'avg_reading_time': avg_time.get('avg', 0),
        'update_ratio': update_ratio,
        'pending_suggestions': pending_suggestions,
        'pending_terms': pending_terms,
    })


@login_required
def personal_dashboard(request):
    """Personal KB dashboard for article authors."""
    my_articles = Article.objects.filter(author=request.user).select_related('category')
    my_articles_published = my_articles.filter(status='published')
    my_drafts = my_articles.filter(status='draft')
    my_needs_review = my_articles.filter(
        Q(needs_actualization=True) | Q(next_review_date__lte=timezone.now().date()),
        status__in=['published', 'needs_review']
    )
    my_suggestions = SuggestedEdit.objects.filter(
        article__author=request.user, status='pending'
    ).select_related('article', 'author')

    total_views = sum(a.views_count for a in my_articles_published)
    avg_rating = my_articles_published.aggregate(avg=Avg('avg_rating'))['avg'] or 0

    is_moderator = (
        request.user.is_superuser
        or getattr(request.user, 'isModerator', False)
        or getattr(request.user, 'is_admin_portal', False)
    )
    archived_articles = Article.objects.filter(status='archived').select_related(
        'category', 'author'
    ).order_by('-updated_at') if is_moderator else Article.objects.none()

    current_tab = request.GET.get('tab') or 'author'
    if current_tab not in ('author', 'archive'):
        current_tab = 'author'

    return render(request, 'knowledge/personal_dashboard.html', {
        'my_articles': my_articles,
        'my_drafts': my_drafts,
        'my_needs_review': my_needs_review,
        'my_suggestions': my_suggestions,
        'total_views': total_views,
        'avg_rating': round(avg_rating, 1),
        'published_count': my_articles_published.count(),
        'is_moderator': is_moderator,
        'archived_articles': archived_articles,
        'current_tab': current_tab,
    })


@login_required
def export_articles(request):
    fmt = request.GET.get('format', 'csv')
    if not (request.user.is_superuser or getattr(request.user, 'isModerator', False)):
        return HttpResponseForbidden('Только для модераторов')

    from .services import StatisticsService
    data = StatisticsService().export_articles_data()

    if fmt == 'csv':
        import csv
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="kb_articles.csv"'
        response.write('\ufeff')
        writer = csv.DictWriter(response, fieldnames=[
            'title', 'type', 'category', 'author', 'published',
            'updated', 'views', 'rating', 'comments', 'version'
        ])
        writer.writeheader()
        writer.writerows(data)
        return response
    elif fmt == 'xlsx':
        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Статьи БЗ'
            headers = ['Заголовок', 'Тип', 'Рубрика', 'Автор', 'Опубликовано',
                        'Обновлено', 'Просмотры', 'Рейтинг', 'Комментарии', 'Версия']
            ws.append(headers)
            for row in data:
                ws.append([
                    row['title'], row['type'], row['category'], row['author'],
                    row['published'], row['updated'], row['views'],
                    row['rating'], row['comments'], row['version']
                ])
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename="kb_articles.xlsx"'
            wb.save(response)
            return response
        except ImportError:
            messages.warning(request, 'Для XLSX экспорта установите openpyxl')
            return redirect('kb_statistics')

    return redirect('kb_statistics')


# === Global search API ===

@login_required
def global_search_api(request):
    """API endpoint for global portal search — returns KB results."""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    results = search_service.search(query, request.user, filters={}, page=1, per_page=5)
    items = [{
        'title': a.title,
        'url': f'/knowledge/article/{a.slug}/',
        'type': a.get_article_type_display(),
        'category': a.category.name if a.category else '',
        'module': 'knowledge',
    } for a in results['results']]
    return JsonResponse({'results': items})


# === Share ===

@login_required
def share_conversations(request):
    from chat.models import Conversation, UserConversation
    user_convs = UserConversation.objects.filter(
        user=request.user, left_at__isnull=True
    ).select_related('conversation').order_by('-conversation__updated_at')[:20]
    results = []
    for uc in user_convs:
        conv = uc.conversation
        if conv.type == 'direct':
            other = conv.participants.exclude(id=request.user.id).first()
            name = other.get_full_name() or other.username if other else 'Чат'
        else:
            name = conv.name or f'{conv.get_type_display()} #{conv.id}'
        results.append({'id': conv.id, 'name': name, 'type': conv.type})
    return JsonResponse({'conversations': results})


@login_required
@require_POST
def share_article(request, slug):
    from chat.models import Conversation, UserConversation, Message
    article = get_object_or_404(Article, slug=slug)
    conversation_id = request.POST.get('conversation_id')
    if not conversation_id:
        return JsonResponse({'error': 'Чат не выбран'}, status=400)
    uc = UserConversation.objects.filter(
        user=request.user, conversation_id=conversation_id, left_at__isnull=True
    ).first()
    if not uc:
        return JsonResponse({'error': 'Нет доступа к чату'}, status=403)

    import re as _re
    article_url = f'/knowledge/article/{article.slug}/'
    clean_excerpt = _re.sub(r'<[^>]+>', '', article.excerpt or article.content or '')
    preview = clean_excerpt[:150].strip()
    if len(clean_excerpt) > 150:
        preview += '...'
    payload = json.dumps({
        'title': article.title, 'excerpt': preview,
        'type': article.get_article_type_display(),
        'url': article_url, 'source': 'knowledge',
    }, ensure_ascii=False)
    msg_text = f'[link_card]{payload}'
    Message.objects.create(
        conversation_id=conversation_id, author=request.user,
        content=msg_text, type='text',
    )
    Conversation.objects.filter(id=conversation_id).update(updated_at=timezone.now())
    return JsonResponse({'success': True})


# === Category reorder (drag & drop) ===

@login_required
@require_POST
def reorder_categories(request):
    """AJAX endpoint for drag & drop category reordering."""
    if not (request.user.is_superuser or getattr(request.user, 'isModerator', False)):
        return JsonResponse({'error': 'Нет прав'}, status=403)
    try:
        order_data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    for item in order_data:
        cat_id = item.get('id')
        new_order = item.get('order', 0)
        new_parent_id = item.get('parent_id')
        if cat_id:
            Category.objects.filter(id=cat_id).update(
                order=new_order,
                parent_id=new_parent_id if new_parent_id else None
            )
            cat = Category.objects.filter(id=cat_id).first()
            if cat:
                cat.save()
    return JsonResponse({'success': True})


# === Mention autocomplete ===

@login_required
def mention_autocomplete(request):
    """Autocomplete for @mentions in comments."""
    q = request.GET.get('q', '').strip()
    if len(q) < 1:
        return JsonResponse({'users': []})
    from django.contrib.auth import get_user_model
    User = get_user_model()
    users = User.objects.filter(
        Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
    ).values('id', 'username', 'first_name', 'last_name')[:10]
    result = []
    for u in users:
        name = f"{u['last_name']} {u['first_name']}".strip()
        result.append({'username': u['username'], 'name': name or u['username'], 'id': u['id']})
    return JsonResponse({'users': result})
