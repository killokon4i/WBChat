"""
Сервис уведомлений опросов: приглашения при запуске и напоминания по reminder_days.
"""
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from notifications.models import Notification, NotificationType


def get_or_create_survey_invitation_type():
    """Тип уведомления «Приглашение пройти опрос»."""
    return NotificationType.objects.get_or_create(
        code="survey_invitation",
        defaults={
            "name": "Приглашение пройти опрос",
            "title_template": "Новый опрос: {title}",
            "body_template": "{description}",
            "priority": "normal",
        },
    )[0]


def get_or_create_survey_reminder_type():
    """Тип уведомления «Напоминание об опросе»."""
    return NotificationType.objects.get_or_create(
        code="survey_reminder",
        defaults={
            "name": "Напоминание об опросе",
            "title_template": "Напоминание: опрос «{title}» заканчивается через {days_left} дн.",
            "body_template": "{description}",
            "priority": "high",
        },
    )[0]


def send_survey_invitations(survey):
    """
    Отправить приглашения пройти опрос всем пользователям из целевой аудитории.
    Вызывается при запуске опроса (survey_launch).
    """
    from .models import Survey

    if not isinstance(survey, Survey):
        survey = Survey.objects.get(pk=survey)

    notif_type = get_or_create_survey_invitation_type()
    content_type = ContentType.objects.get_for_model(survey)
    users = survey.get_eligible_users()
    take_url = f"/surveys/{survey.pk}/take/"
    description = (survey.description or survey.title)[:500]

    notifications = [
        Notification(
            user=user,
            notification_type=notif_type,
            title=f"Новый опрос: {survey.title}",
            content=description,
            link=take_url,
            content_type=content_type,
            object_id=survey.pk,
        )
        for user in users
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)
    return len(notifications)


def send_survey_reminders_for_day(survey, days_left):
    """
    Отправить напоминание об опросе пользователям, которые ещё не прошли опрос.
    days_left — за сколько дней до окончания (число из reminder_days).
    """
    from .models import Survey, SurveyResponse

    if not isinstance(survey, Survey):
        survey = Survey.objects.get(pk=survey)

    reminder_days = survey.reminder_days or []
    if days_left not in reminder_days:
        return 0

    notif_type = get_or_create_survey_reminder_type()
    content_type = ContentType.objects.get_for_model(survey)
    eligible = survey.get_eligible_users()
    submitted_user_ids = set(
        SurveyResponse.objects.filter(
            survey=survey, submitted_at__isnull=False
        ).values_list("user_id", flat=True)
    )
    # Анонимные ответы не имеют user_id; считаем только по user
    to_notify = [u for u in eligible if u.id not in submitted_user_ids]
    take_url = f"/surveys/{survey.pk}/take/"
    description = (survey.description or survey.title)[:500]
    days_label = {1: "1 день", 2: "2 дня", 3: "3 дня"}.get(days_left, f"{days_left} дн.")

    notifications = [
        Notification(
            user=user,
            notification_type=notif_type,
            title=f"Напоминание: опрос «{survey.title}» заканчивается через {days_label}",
            content=description,
            link=take_url,
            content_type=content_type,
            object_id=survey.pk,
            priority="high",
        )
        for user in to_notify
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)
    return len(notifications)
