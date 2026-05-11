from django.core.management.base import BaseCommand

from surveys.models import SurveyTag


class Command(BaseCommand):
    help = "Создать базовый набор тегов опросов по ТЗ"

    DEFAULT_TAGS = [
        {
            "name": "eNPS / вовлечённость",
            "slug": "enps-engagement",
        },
        {
            "name": "Пульс-опрос",
            "slug": "pulse",
        },
        {
            "name": "Корпоративная культура",
            "slug": "culture",
        },
        {
            "name": "Онбординг (адаптация)",
            "slug": "onboarding",
        },
        {
            "name": "Exit-интервью",
            "slug": "exit-interview",
        },
        {
            "name": "Оценка обучения",
            "slug": "training-feedback",
        },
        {
            "name": "IT и сервисы",
            "slug": "it-services",
        },
        {
            "name": "HR-процессы",
            "slug": "hr-processes",
        },
        {
            "name": "Удовлетворённость сервисами",
            "slug": "services-satisfaction",
        },
        {
            "name": "Безопасность и комплаенс",
            "slug": "compliance",
        },
    ]

    def handle(self, *args, **options):
        created = 0
        for data in self.DEFAULT_TAGS:
            obj, is_created = SurveyTag.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                },
            )
            if is_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Создано/обновлено тегов опросов: {len(self.DEFAULT_TAGS)} (новых: {created})."
            )
        )

