"""
Команда для отправки напоминаний об опросах по полю reminder_days.
Запускать по расписанию (cron) раз в день, например в 9:00.

Пример: python manage.py send_survey_reminders
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from surveys.models import Survey
from surveys.services import send_survey_reminders_for_day


class Command(BaseCommand):
    help = "Отправить напоминания об опросах (по reminder_days до окончания)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Только показать, кому бы отправились напоминания, не создавая уведомления",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now().date()
        total_sent = 0

        # Активные опросы с датой окончания и настроенными напоминаниями
        for survey in Survey.objects.filter(
            status="active", ends_at__isnull=False
        ).exclude(reminder_days=[]):
            reminder_days = survey.reminder_days or []
            if not reminder_days:
                continue
            ends_at_date = survey.ends_at.date()
            for days_left in reminder_days:
                target_date = ends_at_date - timedelta(days=days_left)
                if target_date != now:
                    continue
                if dry_run:
                    from surveys.models import SurveyResponse
                    eligible = list(survey.get_eligible_users())
                    submitted_ids = set(
                        SurveyResponse.objects.filter(
                            survey=survey, submitted_at__isnull=False
                        ).values_list("user_id", flat=True)
                    )
                    count = sum(1 for u in eligible if u.id not in submitted_ids)
                    self.stdout.write(
                        f"[dry-run] Survey #{survey.pk} «{survey.title}»: would send {count} reminders ({days_left} d. before end)"
                    )
                    total_sent += count
                else:
                    count = send_survey_reminders_for_day(survey, days_left)
                    if count:
                        total_sent += count
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Survey #{survey.pk} «{survey.title}»: sent {count} reminders ({days_left} d. before end)"
                            )
                        )

        if dry_run:
            self.stdout.write(f"[dry-run] Total would send: {total_sent}")
        else:
            self.stdout.write(self.style.SUCCESS(f"Total reminders sent: {total_sent}"))
