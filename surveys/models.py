from django.conf import settings
from django.db import models
from django.utils import timezone


class SurveyTag(models.Model):
    name = models.CharField("Название", max_length=100, unique=True)
    slug = models.SlugField("Slug", max_length=120, unique=True)

    class Meta:
        verbose_name = "Тег опроса"
        verbose_name_plural = "Теги опросов"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Survey(models.Model):
    STATUS_CHOICES = [
        ("draft", "Черновик"),
        ("active", "Активен"),
        ("closed", "Завершён"),
        ("archived", "В архиве"),
    ]

    AUDIENCE_CHOICES = [
        ("all", "Весь банк"),
        ("departments", "Подразделения"),
        ("users", "Список сотрудников"),
        ("roles", "Ролевые группы"),
    ]

    title = models.CharField("Название опроса", max_length=255)
    description = models.TextField("Описание / цель", blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_surveys",
        verbose_name="Автор",
    )
    status = models.CharField(
        "Статус",
        max_length=16,
        choices=STATUS_CHOICES,
        default="draft",
    )
    is_anonymous = models.BooleanField(
        "Анонимный опрос",
        default=False,
        help_text="При включении ответы не привязываются к сотруднику в интерфейсе.",
    )
    allow_multiple = models.BooleanField(
        "Разрешить повторное прохождение", default=False
    )
    allow_edit_until_end = models.BooleanField(
        "Разрешить изменять ответы до завершения", default=True
    )

    starts_at = models.DateTimeField("Начало проведения", null=True, blank=True)
    ends_at = models.DateTimeField("Окончание проведения", null=True, blank=True)
    closed_at = models.DateTimeField("Фактическое закрытие", null=True, blank=True)

    audience_type = models.CharField(
        "Целевая аудитория",
        max_length=16,
        choices=AUDIENCE_CHOICES,
        default="all",
    )
    audience_departments = models.ManyToManyField(
        "org.Department",
        verbose_name="Подразделения",
        blank=True,
        related_name="surveys",
    )
    audience_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="Сотрудники",
        blank=True,
        related_name="targeted_surveys",
    )
    audience_roles = models.JSONField(
        "Ролевые группы",
        blank=True,
        default=list,
        help_text="Список флагов пользователя, например: isModerator, is_hr.",
    )
    excluded_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="Исключить сотрудников",
        blank=True,
        related_name="excluded_from_surveys",
    )

    reminder_days = models.JSONField(
        "Напоминания (дни до окончания)",
        blank=True,
        default=list,
        help_text="Например: [2, 1] — напомнить за 2 дня и за 1 день до окончания.",
    )

    tags = models.ManyToManyField(
        SurveyTag,
        verbose_name="Теги",
        blank=True,
        related_name="surveys",
    )

    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        verbose_name = "Опрос"
        verbose_name_plural = "Опросы"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def is_active_now(self) -> bool:
        if self.status != "active":
            return False
        now = timezone.now()
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        return True

    def get_eligible_users(self):
        """
        Вернуть queryset сотрудников, попадающих в аудиторию опроса,
        с учётом исключений.
        """
        User = self.audience_users.model
        qs = User.objects.filter(is_active=True, is_archived=False)

        if self.audience_type == "departments":
            dept_ids = list(
                self.audience_departments.values_list("id", flat=True)
            )
            if dept_ids:
                qs = qs.filter(department_id__in=dept_ids)
            else:
                qs = qs.none()
        elif self.audience_type == "users":
            user_ids = list(self.audience_users.values_list("id", flat=True))
            if user_ids:
                qs = qs.filter(id__in=user_ids)
            else:
                qs = qs.none()
        elif self.audience_type == "roles":
            role_filters = models.Q()
            for flag in self.audience_roles or []:
                role_filters |= models.Q(**{flag: True})
            if role_filters:
                qs = qs.filter(role_filters)
            else:
                qs = qs.none()

        excluded_ids = list(self.excluded_users.values_list("id", flat=True))
        if excluded_ids:
            qs = qs.exclude(id__in=excluded_ids)
        return qs


class SurveyQuestion(models.Model):
    TYPE_SINGLE = "single_choice"
    TYPE_MULTIPLE = "multiple_choice"
    TYPE_SCALE = "scale"
    TYPE_TEXT = "free_text"

    QUESTION_TYPES = [
        (TYPE_SINGLE, "Одиночный выбор"),
        (TYPE_MULTIPLE, "Множественный выбор"),
        (TYPE_SCALE, "Шкала (1–10)"),
        (TYPE_TEXT, "Свободный текст"),
    ]

    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="Опрос",
    )
    order = models.PositiveIntegerField("Порядок", default=0)
    title = models.TextField("Текст вопроса")
    help_text = models.TextField("Пояснение", blank=True)
    question_type = models.CharField(
        "Тип вопроса",
        max_length=32,
        choices=QUESTION_TYPES,
        default=TYPE_SINGLE,
    )
    is_required = models.BooleanField("Обязательный", default=False)
    scale_min = models.IntegerField("Минимальное значение шкалы", default=1)
    scale_max = models.IntegerField("Максимальное значение шкалы", default=10)

    parent_question = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sub_questions",
        verbose_name="Родительский вопрос",
        help_text=(
            "Если задан, вопрос является подвопросом и показывается только при "
            "выборе одного из «триггерных» вариантов в родительском вопросе."
        ),
    )
    parent_option_values = models.JSONField(
        "Триггерные ответы родителя",
        blank=True,
        default=list,
        help_text=(
            "Список значений (текстов вариантов или числа для шкалы), при выборе которых "
            "подвопрос будет показан."
        ),
    )

    class Meta:
        verbose_name = "Вопрос опроса"
        verbose_name_plural = "Вопросы опросов"
        ordering = ["survey", "order", "id"]

    def __str__(self) -> str:
        return f"{self.survey.title}: {self.title[:50]}"

    @property
    def is_sub_question(self) -> bool:
        return self.parent_question_id is not None

    def is_triggered_by(self, raw_value) -> bool:
        """
        Проверить, активен ли подвопрос при значениях, выбранных в родительском вопросе.
        raw_value — строка или список строк (как из POST).
        """
        if not self.parent_question_id:
            return True
        triggers = {str(x).strip().lower() for x in (self.parent_option_values or []) if str(x).strip()}
        if not triggers:
            return True
        if isinstance(raw_value, (list, tuple)):
            values = [str(x).strip().lower() for x in raw_value if str(x).strip()]
        else:
            text = str(raw_value or "").strip()
            if not text:
                return False
            values = [p.strip().lower() for p in text.split(",") if p.strip()]
        return any(v in triggers for v in values)


class SurveyQuestionOption(models.Model):
    question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name="Вопрос",
    )
    order = models.PositiveIntegerField("Порядок", default=0)
    text = models.CharField("Вариант ответа", max_length=255)

    class Meta:
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответов"
        ordering = ["question", "order", "id"]

    def __str__(self) -> str:
        return self.text


class SurveyResponse(models.Model):
    survey = models.ForeignKey(
        Survey,
        on_delete=models.CASCADE,
        related_name="responses",
        verbose_name="Опрос",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="survey_responses",
        verbose_name="Сотрудник",
    )
    started_at = models.DateTimeField("Начато", auto_now_add=True)
    submitted_at = models.DateTimeField("Завершено", null=True, blank=True)
    last_step = models.PositiveIntegerField(
        "Последний шаг", default=0, help_text="Для восстановления прогресса"
    )

    class Meta:
        verbose_name = "Ответ на опрос"
        verbose_name_plural = "Ответы на опросы"
        indexes = [
            models.Index(fields=["survey", "user"]),
        ]

    def __str__(self) -> str:
        return f"Ответ на «{self.survey}»"

    @property
    def is_submitted(self) -> bool:
        return self.submitted_at is not None


class SurveyAnswer(models.Model):
    response = models.ForeignKey(
        SurveyResponse,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Ответ",
    )
    question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Вопрос",
    )
    # Универсальное хранилище значения
    value_text = models.TextField("Текстовое значение", blank=True)
    value_number = models.FloatField("Числовое значение", null=True, blank=True)

    class Meta:
        verbose_name = "Ответ на вопрос"
        verbose_name_plural = "Ответы на вопросы"
        indexes = [
            models.Index(fields=["question"]),
        ]

    def __str__(self) -> str:
        return f"{self.question_id} / {self.response_id}"

