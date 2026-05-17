from django.db.models import Q
from knowledge.models import Article, Tag, SearchQuery as SearchQueryLog


class KBSearchService:
    """Полнотекстовый поиск по Базе знаний (PostgreSQL FTS)"""

    def search(self, query, user, filters=None, page=1, per_page=20):
        filters = filters or {}
        qs = Article.objects.filter(status='published').select_related('category', 'author')

        if query:
            # Поиск по подстроке: "пер", "первы", "первый" находят "Первый день на работе"
            qs = qs.filter(
                Q(title__icontains=query) |
                Q(content__icontains=query) |
                Q(excerpt__icontains=query)
            )

            # Расширяем поиск синонимами
            try:
                synonyms = Tag.objects.filter(
                    Q(name__icontains=query) | Q(synonyms__contains=[query])
                ).values_list('name', flat=True)
                if synonyms:
                    tag_q = Q()
                    for syn in synonyms:
                        tag_q |= Q(tags__name__icontains=syn)
                    qs = qs | Article.objects.filter(
                        status='published'
                    ).filter(tag_q).distinct()
            except Exception:
                pass

        if filters.get('category_id'):
            qs = qs.filter(category_id=filters['category_id'])
        if filters.get('tag_slug'):
            qs = qs.filter(tags__slug=filters['tag_slug'])
        if filters.get('author_id'):
            qs = qs.filter(author_id=filters['author_id'])
        if filters.get('article_type'):
            qs = qs.filter(article_type=filters['article_type'])

        # Security trimming
        qs = self._apply_access_filter(qs, user)

        total = qs.count()
        start = (page - 1) * per_page
        results = qs.distinct()[start:start + per_page]

        # Логируем запрос
        if query:
            try:
                SearchQueryLog.objects.create(
                    query=query, user=user, results_count=total
                )
            except Exception:
                pass

        return {
            'results': results,
            'total': total,
            'page': page,
            'pages': max(1, (total + per_page - 1) // per_page),
        }

    def suggest(self, query, user, limit=5):
        """Подсказки «возможно вы имели в виду» — без pg_trgm, только icontains."""
        qs = Article.objects.filter(
            status='published', title__icontains=query
        ).values('id', 'title', 'slug')[:limit]
        return [{'id': a['id'], 'title': a['title'], 'slug': a['slug']} for a in qs]

    def _apply_access_filter(self, qs, user):
        if user.is_superuser or getattr(user, 'is_admin_portal', False):
            return qs
        restricted_cats = []
        from knowledge.models import Category
        for cat in Category.objects.filter(is_restricted=True):
            if not cat.is_visible_to(user):
                restricted_cats.append(cat.id)
        if restricted_cats:
            qs = qs.exclude(category_id__in=restricted_cats)
        return qs
