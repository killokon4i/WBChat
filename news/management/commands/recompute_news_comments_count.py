from django.core.management.base import BaseCommand

from news.models import News


class Command(BaseCommand):
    help = "Пересчитать поле comments_count для всех новостей с учётом мягко удалённых комментариев."

    def handle(self, *args, **options):
        total = 0
        for news in News.objects.all():
            news.recompute_comments_count()
            total += 1
        self.stdout.write(self.style.SUCCESS(f"Пересчитано новостей: {total}"))

