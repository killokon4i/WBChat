from celery import shared_task


@shared_task
def check_review_deadlines():
    """Ежедневная проверка сроков пересмотра статей"""
    from knowledge.services.actualization import ActualizationService

    service = ActualizationService()
    reminders_sent = service.send_review_reminders()
    docs_checked = service.check_related_documents()

    return {
        'reminders_sent': reminders_sent,
        'docs_flagged': docs_checked,
    }


@shared_task
def update_tag_counts():
    """Обновление счётчиков использования тегов"""
    from knowledge.models import Tag
    from django.db.models import Count

    tags = Tag.objects.annotate(real_count=Count('articles'))
    for tag in tags:
        if tag.usage_count != tag.real_count:
            tag.usage_count = tag.real_count
            tag.save(update_fields=['usage_count'])
