from django.contrib import admin, messages
from django.shortcuts import redirect
from django.urls import path
from django.utils import timezone

from surveys.models import (
    Survey,
    SurveyAnswer,
    SurveyQuestion,
    SurveyQuestionOption,
    SurveyResponse,
    SurveyTag,
)
from surveys.seed_wb_pack import PACK_MARKER, publish_wb_pack_surveys, seed_wb_bank_surveys
from surveys.services import send_survey_invitations


class SurveyQuestionOptionInline(admin.TabularInline):
    model = SurveyQuestionOption
    extra = 1
    ordering = ["order", "id"]


class SurveyQuestionInline(admin.StackedInline):
    model = SurveyQuestion
    extra = 0
    ordering = ["order", "id"]
    show_change_link = True
    fields = [
        "order",
        "title",
        "question_type",
        "is_required",
        "scale_min",
        "scale_max",
        "help_text",
    ]


@admin.register(SurveyTag)
class SurveyTagAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "status",
        "author",
        "is_anonymous",
        "audience_type",
        "starts_at",
        "ends_at",
        "created_at",
    ]
    list_filter = ["status", "is_anonymous", "audience_type", "tags"]
    search_fields = ["title", "description"]
    filter_horizontal = [
        "tags",
        "audience_departments",
        "audience_users",
        "excluded_users",
    ]
    readonly_fields = ["created_at", "updated_at", "closed_at"]
    inlines = [SurveyQuestionInline]
    actions = ["publish_selected_surveys", "publish_wb_pack_action"]
    change_list_template = "admin/surveys/survey/change_list.html"

    fieldsets = (
        (
            "Основное",
            {
                "fields": (
                    "title",
                    "description",
                    "author",
                    "status",
                    "tags",
                )
            },
        ),
        (
            "Настройки",
            {
                "fields": (
                    "is_anonymous",
                    "allow_multiple",
                    "allow_edit_until_end",
                    "starts_at",
                    "ends_at",
                    "closed_at",
                    "reminder_days",
                )
            },
        ),
        (
            "Аудитория",
            {
                "fields": (
                    "audience_type",
                    "audience_departments",
                    "audience_users",
                    "audience_roles",
                    "excluded_users",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Служебное",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "seed-wb-pack/",
                self.admin_site.admin_view(self.seed_wb_pack_view),
                name="surveys_survey_seed_wb_pack",
            ),
            path(
                "seed-wb-pack/publish/",
                self.admin_site.admin_view(self.seed_wb_pack_publish_view),
                name="surveys_survey_seed_wb_pack_publish",
            ),
        ]
        return custom + urls

    def seed_wb_pack_view(self, request):
        created, updated, _ = seed_wb_bank_surveys(
            author=request.user, publish=False
        )
        self.message_user(
            request,
            f"Пакет «ВБ Банк»: создано {created}, обновлено {updated} (статус — черновик). "
            f"Опубликуйте через действие «Опубликовать» или кнопку «Загрузить и опубликовать».",
            messages.SUCCESS,
        )
        return redirect("admin:surveys_survey_changelist")

    def seed_wb_pack_publish_view(self, request):
        created, updated, published = seed_wb_bank_surveys(
            author=request.user, publish=True
        )
        from surveys.models import Survey

        pack_qs = Survey.objects.filter(title__startswith=PACK_MARKER, status="active")
        invited = 0
        for survey in pack_qs:
            invited += send_survey_invitations(survey)
        self.message_user(
            request,
            f"Пакет «ВБ Банк»: создано {created}, обновлено {updated}, "
            f"опубликовано {published}. Отправлено приглашений: {invited}.",
            messages.SUCCESS,
        )
        return redirect("admin:surveys_survey_changelist")

    @admin.action(description="Опубликовать (активировать) и разослать приглашения")
    def publish_selected_surveys(self, request, queryset):
        now = timezone.now()
        total_invites = 0
        published = 0
        for survey in queryset:
            if survey.status == "active":
                continue
            survey.status = "active"
            if not survey.starts_at:
                survey.starts_at = now
            survey.save(update_fields=["status", "starts_at", "updated_at"])
            total_invites += send_survey_invitations(survey)
            published += 1
        self.message_user(
            request,
            f"Опубликовано опросов: {published}. Приглашений отправлено: {total_invites}.",
            messages.SUCCESS,
        )

    @admin.action(description=f"Опубликовать все опросы пакета {PACK_MARKER}")
    def publish_wb_pack_action(self, request, queryset):
        count = publish_wb_pack_surveys()
        self.message_user(
            request,
            f"Опубликовано опросов пакета ВБ Банк: {count}.",
            messages.SUCCESS,
        )


@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ["survey", "order", "title_short", "question_type", "is_required"]
    list_filter = ["question_type", "survey"]
    search_fields = ["title", "survey__title"]
    inlines = [SurveyQuestionOptionInline]
    ordering = ["survey", "order", "id"]

    @admin.display(description="Вопрос")
    def title_short(self, obj):
        t = obj.title or ""
        return t[:80] + ("…" if len(t) > 80 else "")


@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ["survey", "user", "started_at", "submitted_at"]
    list_filter = ["survey", "submitted_at"]
    raw_id_fields = ["user", "survey"]
    readonly_fields = ["started_at"]


@admin.register(SurveyAnswer)
class SurveyAnswerAdmin(admin.ModelAdmin):
    list_display = ["response", "question", "value_text", "value_number"]
    list_filter = ["question__survey"]
    raw_id_fields = ["response", "question"]
