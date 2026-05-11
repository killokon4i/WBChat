from django.core.management.base import BaseCommand

from news.models import NewsCategory


class Command(BaseCommand):
    help = "Создать стандартные рубрики новостей для портала"

    DEFAULT_CATEGORIES = [
        {
            "name": "Официальные документы",
            "slug": "official",
            "description": "Приказы, распоряжения, регламенты и иные официальные документы банка.",
            "color": "#7C3AED",
            "icon": "gavel",
            "is_official": True,
            "requires_moderation": True,
            "order": 10,
        },
        {
            "name": "Новости банка",
            "slug": "corporate-news",
            "description": "Ключевые события банка, продукты, проекты, результаты.",
            "color": "#CB11AB",
            "icon": "megaphone",
            "is_official": False,
            "requires_moderation": True,
            "order": 20,
        },
        {
            "name": "HR и корпоративная культура",
            "slug": "hr-culture",
            "description": "Команда, корпоративная жизнь, мероприятия, соцпакет и льготы.",
            "color": "#EC4899",
            "icon": "users",
            "is_official": False,
            "requires_moderation": True,
            "order": 30,
        },
        {
            "name": "Обучение и развитие",
            "slug": "learning",
            "description": "Обучающие программы, курсы, вебинары и полезные материалы.",
            "color": "#10B981",
            "icon": "graduation-cap",
            "is_official": False,
            "requires_moderation": False,
            "order": 40,
        },
        {
            "name": "IT и сервисы",
            "slug": "it-services",
            "description": "Плановые работы, инциденты, новые функции внутренних систем.",
            "color": "#0EA5E9",
            "icon": "cpu",
            "is_official": False,
            "requires_moderation": True,
            "order": 50,
        },
    ]

    def handle(self, *args, **options):
        created = 0
        for data in self.DEFAULT_CATEGORIES:
            obj, is_created = NewsCategory.objects.update_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "description": data["description"],
                    "color": data["color"],
                    "icon": data["icon"],
                    "is_official": data["is_official"],
                    "requires_moderation": data["requires_moderation"],
                    "order": data["order"],
                    "is_active": True,
                },
            )
            if is_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Создано/обновлено рубрик: {len(self.DEFAULT_CATEGORIES)} (новых: {created})."
            )
        )

