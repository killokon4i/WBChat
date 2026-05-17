from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import timedelta


class StatisticsService:
    """Статистика и отчётность по Базе знаний"""

    def get_overview(self):
        from knowledge.models import Article, Category, Tag, FAQ

        total_articles = Article.objects.filter(status='published').count()
        total_drafts = Article.objects.filter(status='draft').count()
        total_categories = Category.objects.filter(is_active=True).count()
        total_tags = Tag.objects.filter(is_approved=True).count()
        total_faqs = FAQ.objects.filter(is_active=True).count()

        needs_review = Article.objects.filter(
            status__in=['needs_review', 'published'],
            next_review_date__lte=timezone.now().date()
        ).count()

        needs_actualization = Article.objects.filter(
            needs_actualization=True, status='published'
        ).count()

        return {
            'total_articles': total_articles,
            'total_drafts': total_drafts,
            'total_categories': total_categories,
            'total_tags': total_tags,
            'total_faqs': total_faqs,
            'needs_review': needs_review,
            'needs_actualization': needs_actualization,
        }

    def get_top_articles(self, limit=10, by='views'):
        from knowledge.models import Article
        qs = Article.objects.filter(status='published').select_related('category', 'author')

        if by == 'views':
            qs = qs.order_by('-views_count')
        elif by == 'rating':
            qs = qs.order_by('-avg_rating')
        elif by == 'comments':
            qs = qs.order_by('-comments_count')

        return qs[:limit]

    def get_category_stats(self):
        from knowledge.models import Category
        return Category.objects.filter(is_active=True).annotate(
            article_count=Count('articles', filter=Q(articles__status='published')),
            avg_rating=Avg('articles__avg_rating', filter=Q(articles__status='published')),
            total_views=Sum('articles__views_count', filter=Q(articles__status='published')),
        ).order_by('-article_count')

    def get_author_stats(self, limit=10):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.annotate(
            articles_count=Count('kb_articles', filter=Q(kb_articles__status='published')),
            avg_article_rating=Avg('kb_articles__avg_rating', filter=Q(kb_articles__status='published')),
        ).filter(articles_count__gt=0).order_by('-articles_count')[:limit]

    def get_search_analytics(self, days=30):
        from knowledge.models import SearchQuery
        since = timezone.now() - timedelta(days=days)

        zero_results = SearchQuery.objects.filter(
            created_at__gte=since, results_count=0
        ).values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:20]

        popular_queries = SearchQuery.objects.filter(
            created_at__gte=since
        ).values('query').annotate(
            count=Count('id')
        ).order_by('-count')[:20]

        return {
            'zero_results': list(zero_results),
            'popular_queries': list(popular_queries),
        }

    def export_articles_data(self, format='csv'):
        from knowledge.models import Article
        articles = Article.objects.filter(
            status='published'
        ).select_related('category', 'author').order_by('-published_at')

        data = []
        for a in articles:
            data.append({
                'title': a.title,
                'type': a.get_article_type_display(),
                'category': a.category.name if a.category else '',
                'author': a.author.get_full_name() if a.author else '',
                'published': a.published_at.strftime('%d.%m.%Y') if a.published_at else '',
                'updated': a.updated_at.strftime('%d.%m.%Y'),
                'views': a.views_count,
                'rating': a.avg_rating,
                'comments': a.comments_count,
                'version': a.current_version,
            })
        return data
