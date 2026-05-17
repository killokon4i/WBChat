"""
Сервис полнотекстового поиска документов.
Использует PostgreSQL Full-Text Search для эффективного поиска.
"""
from typing import Optional, List, Dict, Any
from django.db.models import Q, QuerySet
from django.contrib.postgres.search import (
    SearchQuery, SearchRank, SearchVector, TrigramSimilarity
)
from django.conf import settings

from ..models import Document, DocumentCategory


class DocumentSearchService:
    """
    Сервис поиска документов с поддержкой:
    - Полнотекстового поиска (PostgreSQL FTS)
    - Security trimming (фильтрация по правам)
    - Фасетного поиска (по категориям, типам и т.д.)
    """

    def __init__(self, search_config: str = 'russian'):
        self.search_config = search_config

    def search(
        self,
        query: str,
        user,
        filters: Optional[Dict[str, Any]] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Поиск документов с учётом прав доступа.
        
        Args:
            query: Поисковый запрос
            user: Пользователь, выполняющий поиск
            filters: Дополнительные фильтры
            page: Номер страницы
            per_page: Количество результатов на странице
            
        Returns:
            Словарь с результатами и метаданными поиска
        """
        # Базовый queryset
        qs = Document.objects.filter(status='active')
        
        # Применяем полнотекстовый поиск
        if query:
            search_query = SearchQuery(query, config=self.search_config)
            
            # Поиск по search_vector (если настроен) или по полям
            qs = qs.annotate(
                rank=SearchRank('search_vector', search_query)
            ).filter(
                Q(search_vector=search_query) |
                Q(title__icontains=query) |
                Q(document_number__icontains=query)
            )
        
        # Security trimming - фильтрация по правам
        qs = self._apply_access_filter(qs, user)
        
        # Применяем дополнительные фильтры
        if filters:
            qs = self._apply_filters(qs, filters)
        
        # Сортировка
        if query:
            qs = qs.order_by('-rank', '-updated_at')
        else:
            qs = qs.order_by('-updated_at')
        
        # Пагинация
        total = qs.count()
        offset = (page - 1) * per_page
        results = list(qs[offset:offset + per_page])
        
        # Фасеты
        facets = self._calculate_facets(qs)
        
        return {
            'results': results,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page,
            'facets': facets,
            'query': query,
        }

    def _apply_access_filter(self, qs: QuerySet, user) -> QuerySet:
        """
        Фильтрация результатов по правам доступа (Security Trimming).
        
        Пользователь видит документ если:
        1. Документ публичный (public)
        2. У пользователя есть прямой доступ
        3. У подразделения пользователя есть доступ
        4. У роли пользователя есть доступ
        5. Пользователь - автор или куратор документа
        """
        from ..models import DocumentAccessRule
        
        # Суперпользователь видит всё
        if user.is_superuser:
            return qs
        
        # Публичные документы
        public_q = Q(confidentiality='public')
        
        # Документы пользователя
        author_q = Q(author=user) | Q(curator=user)
        
        # Документы с прямым доступом
        user_access = DocumentAccessRule.objects.filter(
            user=user,
            can_view=True
        ).values_list('document_id', flat=True)
        direct_access_q = Q(id__in=user_access)
        
        # Документы по подразделению
        if user.department:
            dept_access = DocumentAccessRule.objects.filter(
                department=user.department,
                can_view=True
            ).values_list('document_id', flat=True)
            dept_q = Q(id__in=dept_access)
        else:
            dept_q = Q(pk__isnull=True)  # Никогда не совпадёт
        
        # Документы по категории с доступом
        category_access = DocumentAccessRule.objects.filter(
            Q(user=user) | Q(department=user.department) if user.department else Q(user=user),
            document__isnull=True,
            category__isnull=False,
            can_view=True
        ).values_list('category_id', flat=True)
        category_q = Q(category_id__in=category_access)
        
        return qs.filter(public_q | author_q | direct_access_q | dept_q | category_q)

    def _apply_filters(self, qs: QuerySet, filters: Dict[str, Any]) -> QuerySet:
        """Применение дополнительных фильтров"""
        
        if 'document_type' in filters:
            qs = qs.filter(document_type=filters['document_type'])
        
        if 'category' in filters:
            qs = qs.filter(category_id=filters['category'])
        
        if 'category_slug' in filters:
            qs = qs.filter(category__slug=filters['category_slug'])
        
        if 'confidentiality' in filters:
            qs = qs.filter(confidentiality=filters['confidentiality'])
        
        if 'date_from' in filters:
            qs = qs.filter(document_date__gte=filters['date_from'])
        
        if 'date_to' in filters:
            qs = qs.filter(document_date__lte=filters['date_to'])
        
        if 'author' in filters:
            qs = qs.filter(author_id=filters['author'])
        
        if 'tags' in filters:
            # JSON contains для PostgreSQL
            for tag in filters['tags']:
                qs = qs.filter(tags__contains=[tag])
        
        return qs

    def _calculate_facets(self, qs: QuerySet) -> Dict[str, List[Dict]]:
        """Расчёт фасетов для фильтрации"""
        from django.db.models import Count
        
        facets = {}
        
        # По типу документа
        type_facets = qs.values('document_type').annotate(
            count=Count('id')
        ).order_by('-count')
        facets['document_type'] = [
            {'value': f['document_type'], 'count': f['count']}
            for f in type_facets
        ]
        
        # По категории
        category_facets = qs.values('category__name', 'category__slug').annotate(
            count=Count('id')
        ).order_by('-count')
        facets['category'] = [
            {'name': f['category__name'], 'slug': f['category__slug'], 'count': f['count']}
            for f in category_facets if f['category__name']
        ]
        
        # По грифу конфиденциальности
        conf_facets = qs.values('confidentiality').annotate(
            count=Count('id')
        ).order_by('-count')
        facets['confidentiality'] = [
            {'value': f['confidentiality'], 'count': f['count']}
            for f in conf_facets
        ]
        
        return facets

    def suggest(self, query: str, user, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Автодополнение при вводе поискового запроса.
        Использует триграммное сходство для fuzzy matching.
        """
        if len(query) < 2:
            return []
        
        qs = Document.objects.filter(status='active')
        qs = self._apply_access_filter(qs, user)
        
        # Поиск по похожести названия
        qs = qs.annotate(
            similarity=TrigramSimilarity('title', query)
        ).filter(
            similarity__gt=0.1
        ).order_by('-similarity')[:limit]
        
        return [
            {
                'id': doc.id,
                'title': doc.title,
                'document_number': doc.document_number,
                'document_type': doc.document_type,
            }
            for doc in qs
        ]

    @staticmethod
    def update_search_vector(document: Document):
        """
        Обновить поисковый вектор документа.
        Вызывается при создании/обновлении документа.
        """
        document.search_vector = (
            SearchVector('title', weight='A', config='russian') +
            SearchVector('description', weight='B', config='russian') +
            SearchVector('document_number', weight='A', config='russian')
        )
        document.save(update_fields=['search_vector'])


