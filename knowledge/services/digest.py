from django.utils import timezone
from datetime import timedelta


class DigestService:
    """Формирование и отправка дайджестов базы знаний"""

    def generate_digest(self, period_days=7):
        """Generate digest data for the last N days."""
        from knowledge.models import Article, FAQ
        since = timezone.now() - timedelta(days=period_days)

        new_articles = Article.objects.filter(
            status='published',
            published_at__gte=since
        ).select_related('category', 'author').order_by('-published_at')[:20]

        updated_articles = Article.objects.filter(
            status='published',
            updated_at__gte=since
        ).exclude(
            published_at__gte=since
        ).select_related('category', 'author').order_by('-updated_at')[:10]

        popular_articles = Article.objects.filter(
            status='published'
        ).order_by('-views_count')[:5]

        new_faqs = FAQ.objects.filter(
            is_active=True,
            created_at__gte=since
        ).select_related('category')[:10]

        return {
            'period_days': period_days,
            'since': since,
            'new_articles': list(new_articles),
            'updated_articles': list(updated_articles),
            'popular_articles': list(popular_articles),
            'new_faqs': list(new_faqs),
        }

    def send_digest_notifications(self, period_days=7):
        """Send digest as in-app notifications to all subscribers."""
        from knowledge.models import Subscription
        from notifications.models import Notification, NotificationType

        digest = self.generate_digest(period_days)
        if not digest['new_articles'] and not digest['updated_articles']:
            return 0

        notif_type, _ = NotificationType.objects.get_or_create(
            code='kb_digest',
            defaults={
                'name': 'Дайджест базы знаний',
                'title_template': 'Дайджест базы знаний за {period}',
                'body_template': '{content}',
                'priority': 'low',
            }
        )

        subscriber_ids = set(
            Subscription.objects.values_list('user_id', flat=True).distinct()
        )
        if not subscriber_ids:
            return 0

        period_label = f'{period_days} дн.' if period_days != 7 else 'неделю'
        lines = []
        if digest['new_articles']:
            lines.append(f"Новых статей: {len(digest['new_articles'])}")
            for a in digest['new_articles'][:5]:
                lines.append(f'  - <a href="/knowledge/article/{a.slug}/">{a.title}</a>')
        if digest['updated_articles']:
            lines.append(f"Обновлённых статей: {len(digest['updated_articles'])}")
            for a in digest['updated_articles'][:5]:
                lines.append(f'  - <a href="/knowledge/article/{a.slug}/">{a.title}</a>')

        content = '<br>'.join(lines)

        notifications = [
            Notification(
                user_id=uid,
                notification_type=notif_type,
                title=f'Дайджест базы знаний за {period_label}',
                content=content,
                link='/knowledge/',
            )
            for uid in subscriber_ids
        ]
        Notification.objects.bulk_create(notifications)
        return len(notifications)

    def send_email_digest(self, period_days=7):
        """Send digest via email to subscribers who have emails."""
        from django.core.mail import send_mass_mail
        from django.contrib.auth import get_user_model
        from knowledge.models import Subscription

        User = get_user_model()
        digest = self.generate_digest(period_days)
        if not digest['new_articles'] and not digest['updated_articles']:
            return 0

        subscriber_ids = set(
            Subscription.objects.values_list('user_id', flat=True).distinct()
        )
        users = User.objects.filter(id__in=subscriber_ids, email__isnull=False).exclude(email='')

        period_label = f'{period_days} дн.' if period_days != 7 else 'неделю'
        subject = f'Дайджест базы знаний за {period_label}'

        lines = []
        if digest['new_articles']:
            lines.append(f"Новых статей: {len(digest['new_articles'])}")
            for a in digest['new_articles'][:10]:
                lines.append(f"  - {a.title}")
        if digest['updated_articles']:
            lines.append(f"\nОбновлённых статей: {len(digest['updated_articles'])}")
            for a in digest['updated_articles'][:10]:
                lines.append(f"  - {a.title}")
        body = '\n'.join(lines)

        messages = []
        for user in users:
            messages.append((subject, body, None, [user.email]))

        if messages:
            try:
                send_mass_mail(messages, fail_silently=True)
            except Exception:
                pass
        return len(messages)
