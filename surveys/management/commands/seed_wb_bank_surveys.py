from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from surveys.seed_wb_pack import PACK_MARKER, seed_wb_bank_surveys
from surveys.services import send_survey_invitations


class Command(BaseCommand):
    help = (
        f"Создать 5 опросов ВБ Банк ({PACK_MARKER} …). "
        "С флагом --publish — сразу активировать и разослать приглашения."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--publish",
            action="store_true",
            help="Опубликовать опросы (status=active) и отправить приглашения",
        )
        parser.add_argument(
            "--username",
            type=str,
            default="",
            help="Логин автора опросов (по умолчанию — первый суперпользователь)",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=14,
            help="Срок проведения в днях от момента публикации",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        author = None
        if options["username"]:
            author = User.objects.filter(username=options["username"]).first()
            if not author:
                self.stderr.write(
                    self.style.ERROR(f"Пользователь «{options['username']}» не найден.")
                )
                return
        else:
            author = User.objects.filter(is_superuser=True).order_by("id").first()
            if not author:
                author = User.objects.filter(is_active=True).order_by("id").first()
        if not author:
            self.stderr.write(self.style.ERROR("Нет пользователей для автора опросов."))
            return

        created, updated, published = seed_wb_bank_surveys(
            author,
            publish=options["publish"],
            duration_days=options["days"],
        )

        invited = 0
        if options["publish"]:
            from surveys.models import Survey

            for survey in Survey.objects.filter(
                title__startswith=PACK_MARKER, status="active"
            ):
                invited += send_survey_invitations(survey)

        self.stdout.write(
            self.style.SUCCESS(
                f"Готово. Создано: {created}, обновлено: {updated}, "
                f"опубликовано: {published}, приглашений: {invited}. "
                f"Автор: {author.username}"
            )
        )
