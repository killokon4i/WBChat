from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from .models import Document, DocumentCategory, DocumentVersion, DocumentViewLog
from .services import DocumentSearchService, DocumentAccessService


search_service = DocumentSearchService()
access_service = DocumentAccessService()


@login_required
def documents_list(request):
    """Список документов с поиском и фильтрацией"""
    query = request.GET.get('q', '')
    doc_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    category_slug = request.GET.get('category', '')
    page = int(request.GET.get('page', 1))
    
    # Базовый queryset
    documents = Document.objects.filter(status='active')
    
    # Применяем фильтры
    filters = {}
    if doc_type:
        filters['document_type'] = doc_type
    if status:
        filters['status'] = status
    if category_slug:
        filters['category_slug'] = category_slug
    
    # Поиск
    if query or filters:
        result = search_service.search(
            query=query,
            user=request.user,
            filters=filters,
            page=page,
            per_page=20
        )
        documents = result['results']
        total_pages = result['pages']
    else:
        # Простой запрос без поиска
        documents = documents.select_related('category', 'author').order_by('-updated_at')
        paginator = Paginator(documents, 20)
        documents = paginator.get_page(page)
        total_pages = paginator.num_pages
    
    # Категории для сайдбара
    categories = DocumentCategory.objects.filter(is_active=True).order_by('order', 'name')
    
    return render(request, 'documents/list.html', {
        'documents': documents,
        'categories': categories,
        'query': query,
        'current_type': doc_type,
        'current_status': status,
        'current_category': category_slug,
        'page': page,
        'pages': total_pages,
        'page_range': range(1, total_pages + 1),
        'total_count': Document.objects.filter(status='active').count(),
    })


@login_required
def document_detail(request, document_id):
    """Детальная страница документа"""
    document = get_object_or_404(
        Document.objects.select_related('category', 'author', 'curator'),
        id=document_id
    )
    
    # Проверка доступа
    if not access_service.check_permission(document, request.user, 'view'):
        return render(request, 'documents/access_denied.html', status=403)
    
    # Логируем просмотр
    DocumentViewLog.objects.create(
        document=document,
        user=request.user,
        version=document.get_current_version(),
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    # Увеличиваем счётчик просмотров
    document.views_count += 1
    document.save(update_fields=['views_count'])
    
    # Версии документа
    versions = document.versions.select_related('uploaded_by').order_by('-version_number')[:10]
    
    # Права пользователя
    permissions = access_service.get_user_permissions(document, request.user)
    
    return render(request, 'documents/detail.html', {
        'document': document,
        'versions': versions,
        'current_version': document.get_current_version(),
        'permissions': permissions,
    })


@login_required
def document_download(request, document_id, version_number=None):
    """Скачивание файла документа"""
    document = get_object_or_404(Document, id=document_id)
    
    # Проверка доступа
    if not access_service.check_permission(document, request.user, 'download'):
        return HttpResponse('Доступ запрещён', status=403)
    
    # Получаем версию
    if version_number:
        version = get_object_or_404(DocumentVersion, document=document, version_number=version_number)
    else:
        version = document.get_current_version()
    
    if not version or not version.file:
        raise Http404("Файл не найден")
    
    # Возвращаем файл
    response = HttpResponse(version.file.read(), content_type=version.mime_type)
    response['Content-Disposition'] = f'attachment; filename="{version.file_name}"'
    return response


@login_required
def document_search_api(request):
    """API для поиска документов (автодополнение)"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    suggestions = search_service.suggest(query, request.user, limit=5)
    return JsonResponse({'results': suggestions})


