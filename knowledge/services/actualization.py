from django.utils import timezone
from datetime import timedelta


class ActualizationService:
    """Управление сроками пересмотра и актуализацией контента"""

    def get_articles_needing_review(self, author_id=None, category_id=None):
        from knowledge.models import Article
        qs = Article.objects.filter(
            status='published',
            next_review_date__lte=timezone.now().date()
        ).select_related('category', 'author')

        if author_id:
            qs = qs.filter(author_id=author_id)
        if category_id:
            qs = qs.filter(category_id=category_id)

        return qs.order_by('next_review_date')

    def get_stale_articles(self, months=12):
        cutoff = timezone.now() - timedelta(days=30 * months)
        from knowledge.models import Article
        return Article.objects.filter(
            status='published',
            updated_at__lt=cutoff
        ).select_related('category', 'author').order_by('updated_at')

    def mark_needs_review(self, article):
        article.status = 'needs_review'
        article.save(update_fields=['status'])

    def mark_reviewed(self, article, user):
        article.status = 'published'
        article.last_reviewed_at = timezone.now()
        article.last_reviewed_by = user
        article.needs_actualization = False
        if article.review_period_months:
            article.next_review_date = (
                timezone.now() + timedelta(days=30 * article.review_period_months)
            ).date()
        article.save(update_fields=[
            'status', 'last_reviewed_at', 'last_reviewed_by',
            'needs_actualization', 'next_review_date'
        ])

    def check_related_documents(self):
        """Проверить связанные НПА — если НПА устарел, пометить статью"""
        from knowledge.models import Article
        from documents.models import Document

        outdated_doc_ids = Document.objects.filter(
            status__in=['outdated', 'archived']
        ).values_list('id', flat=True)

        if outdated_doc_ids:
            articles = Article.objects.filter(
                related_documents__id__in=outdated_doc_ids,
                needs_actualization=False,
                status='published'
            ).distinct()

            updated_count = articles.update(needs_actualization=True)
            return updated_count
        return 0

    def send_review_reminders(self):
        """Отправить уведомления авторам о просроченном пересмотре"""
        from knowledge.models import Article
        from notifications.models import Notification, NotificationType

        articles = self.get_articles_needing_review()
        notification_type = NotificationType.objects.filter(
            code='kb_review_reminder'
        ).first()

        if not notification_type:
            return 0

        count = 0
        for article in articles:
            if not article.author:
                continue
            already_sent = Notification.objects.filter(
                user=article.author,
                notification_type=notification_type,
                object_id=article.id,
                is_read=False
            ).exists()
            if already_sent:
                continue

            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(article)
            Notification.objects.create(
                user=article.author,
                notification_type=notification_type,
                title=f'Статья требует пересмотра: {article.title}',
                content=f'Срок пересмотра статьи "{article.title}" истёк. Проверьте и обновите материал.',
                link=f'/knowledge/article/{article.slug}/',
                content_type=ct,
                object_id=article.id,
            )
            count += 1

        return count
