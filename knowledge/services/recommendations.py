from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta


class RecommendationService:
    """Рекомендации статей по роли/подразделению и виджеты"""

    def get_recommended(self, user, limit=5):
        from knowledge.models import Article
        qs = Article.objects.filter(status='published')

        if hasattr(user, 'department') and user.department:
            dept_cats = user.department.kb_categories.values_list('id', flat=True)
            if dept_cats:
                qs = qs.filter(
                    Q(category_id__in=dept_cats) | Q(article_type='onboarding')
                )

        return qs.order_by('-views_count', '-avg_rating')[:limit]

    def get_popular(self, days=30, limit=10):
        from knowledge.models import Article
        since = timezone.now() - timedelta(days=days)
        return Article.objects.filter(
            status='published',
            published_at__gte=since
        ).order_by('-views_count')[:limit]

    def get_recently_updated(self, limit=10):
        from knowledge.models import Article
        return Article.objects.filter(
            status='published'
        ).order_by('-updated_at')[:limit]

    def get_tag_cloud(self, limit=30):
        from knowledge.models import Tag
        return Tag.objects.filter(
            is_approved=True,
            usage_count__gt=0
        ).order_by('-usage_count')[:limit]
