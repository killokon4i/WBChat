"""
Пакет демо-опросов ВБ Банк: удовлетворённость, вовлечённость, культура и т.д.
Используется management-командой и Django Admin.
"""
from datetime import timedelta

from django.utils import timezone

from surveys.models import Survey, SurveyQuestion, SurveyQuestionOption, SurveyTag


# Уникальный префикс в названии — не дублировать при повторном запуске
PACK_MARKER = "[ВБ Банк]"

WB_BANK_SURVEYS = [
    {
        "title": f"{PACK_MARKER} Удовлетворённость работой",
        "description": (
            "Пульс-опрос об удовлетворённости работой в ВБ Банке. "
            "Ответы анонимны и помогут HR улучшить условия для сотрудников."
        ),
        "tags": ["enps-engagement", "pulse"],
        "is_anonymous": True,
        "questions": [
            {
                "title": "Насколько вероятно, что вы порекомендуете ВБ Банк как работодателя друзьям или знакомым?",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 0,
                "scale_max": 10,
                "help_text": "0 — точно не порекомендую, 10 — обязательно порекомендую",
            },
            {
                "title": "Насколько вы удовлетворены своей текущей работой в банке?",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
            },
            {
                "title": "Что сильнее всего влияет на вашу удовлетворённость?",
                "question_type": SurveyQuestion.TYPE_SINGLE,
                "is_required": True,
                "options": [
                    "Зарплата и льготы",
                    "Карьерные возможности",
                    "Команда и атмосфера",
                    "Руководитель",
                    "Баланс работы и личной жизни",
                    "Миссия и ценности банка",
                ],
            },
            {
                "title": "Что, на ваш взгляд, ВБ Банк мог бы улучшить в первую очередь?",
                "question_type": SurveyQuestion.TYPE_TEXT,
                "is_required": False,
            },
        ],
    },
    {
        "title": f"{PACK_MARKER} Вовлечённость сотрудников",
        "description": (
            "Оцените, насколько вы чувствуете связь с целями банка и готовность "
            "вкладываться в общий результат."
        ),
        "tags": ["enps-engagement"],
        "is_anonymous": True,
        "questions": [
            {
                "title": "Я понимаю, как моя работа связана с целями подразделения и банка",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
            },
            {
                "title": "Я чувствую, что мой вклад действительно важен для ВБ Банка",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
            },
            {
                "title": "Мне интересно развиваться и оставаться в банке на долгий срок",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
            },
            {
                "title": "Что помогло бы вам быть более вовлечённым?",
                "question_type": SurveyQuestion.TYPE_TEXT,
                "is_required": False,
            },
        ],
    },
    {
        "title": f"{PACK_MARKER} Корпоративная культура",
        "description": (
            "Опрос о ценностях, этике и атмосфере в ВБ Банке. "
            "Помогает оценить, насколько культура банка соответствует ожиданиям сотрудников."
        ),
        "tags": ["culture"],
        "is_anonymous": True,
        "questions": [
            {
                "title": "Я разделяю ценности и принципы работы ВБ Банка",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
            },
            {
                "title": "В банке поддерживают взаимное уважение и открытый диалог",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
            },
            {
                "title": "Как часто вы участвуете в корпоративных активностях банка?",
                "question_type": SurveyQuestion.TYPE_SINGLE,
                "is_required": True,
                "options": [
                    "Регулярно",
                    "Иногда",
                    "Редко",
                    "Не участвую, но хотел(а) бы",
                    "Не интересно / не актуально",
                ],
            },
            {
                "title": "Что бы вы изменили в корпоративной культуре банка?",
                "question_type": SurveyQuestion.TYPE_TEXT,
                "is_required": False,
            },
        ],
    },
    {
        "title": f"{PACK_MARKER} Руководитель и команда",
        "description": (
            "Обратная связь о взаимодействии с руководителем и командой. "
            "Результаты агрегируются анонимно по подразделениям."
        ),
        "tags": ["pulse", "hr-processes"],
        "is_anonymous": True,
        "questions": [
            {
                "title": "Мой руководитель даёт понятную обратную связь и поддержку",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
            },
            {
                "title": "В моей команде комфортная и продуктивная атмосфера",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
            },
            {
                "title": "Рабочие вопросы в команде решаются в разумные сроки",
                "question_type": SurveyQuestion.TYPE_SINGLE,
                "is_required": True,
                "options": [
                    "Всегда быстро",
                    "Чаще быстро, чем медленно",
                    "Иногда затягивается",
                    "Часто возникают задержки",
                ],
            },
            {
                "title": "Комментарий о взаимодействии с руководителем или командой (необязательно)",
                "question_type": SurveyQuestion.TYPE_TEXT,
                "is_required": False,
            },
        ],
    },
    {
        "title": f"{PACK_MARKER} Условия труда и well-being",
        "description": (
            "Оценка организации работы, нагрузки, гибридного формата и HR-сервисов ВБ Банка."
        ),
        "tags": ["pulse", "services-satisfaction"],
        "is_anonymous": True,
        "questions": [
            {
                "title": "Меня устраивает организация офисной / гибридной / удалённой работы",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
            },
            {
                "title": "Текущая нагрузка позволяет сохранять баланс работы и личной жизни",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
            },
            {
                "title": "HR-сервисы и льготы банка доступны и понятны",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
            },
            {
                "title": "Что больше всего мешает комфортно работать в банке?",
                "question_type": SurveyQuestion.TYPE_MULTIPLE,
                "is_required": False,
                "options": [
                    "Высокая нагрузка",
                    "Недостаток гибкости графика",
                    "IT и рабочие инструменты",
                    "Коммуникации между подразделениями",
                    "Офис / рабочее место",
                    "Ничего из перечисленного",
                ],
            },
        ],
    },
]


def _ensure_tags(slug_list):
    tags = []
    for slug in slug_list:
        defaults = {
            "enps-engagement": "eNPS / вовлечённость",
            "pulse": "Пульс-опрос",
            "culture": "Корпоративная культура",
            "hr-processes": "HR-процессы",
            "services-satisfaction": "Удовлетворённость сервисами",
        }
        tag, _ = SurveyTag.objects.get_or_create(
            slug=slug,
            defaults={"name": defaults.get(slug, slug.replace("-", " ").title())},
        )
        tags.append(tag)
    return tags


def _create_questions(survey, questions_data):
    survey.questions.all().delete()
    for order, qd in enumerate(questions_data):
        q = SurveyQuestion.objects.create(
            survey=survey,
            order=order,
            title=qd["title"],
            help_text=qd.get("help_text", ""),
            question_type=qd["question_type"],
            is_required=qd.get("is_required", False),
            scale_min=qd.get("scale_min", 1),
            scale_max=qd.get("scale_max", 10),
        )
        if q.question_type in (
            SurveyQuestion.TYPE_SINGLE,
            SurveyQuestion.TYPE_MULTIPLE,
        ):
            for idx, text in enumerate(qd.get("options") or []):
                SurveyQuestionOption.objects.create(
                    question=q, order=idx, text=text
                )


def seed_wb_bank_surveys(author, *, publish=False, duration_days=14):
    """
    Создать или обновить 5 опросов пакета. Вернуть (создано, обновлено, опубликовано).
    """
    if author is None:
        raise ValueError("Нужен автор опроса (пользователь).")

    created_count = 0
    updated_count = 0
    published_count = 0
    now = timezone.now()
    ends_at = now + timedelta(days=duration_days)

    for data in WB_BANK_SURVEYS:
        survey, created = Survey.objects.get_or_create(
            title=data["title"],
            defaults={
                "description": data["description"],
                "author": author,
                "status": "draft",
                "is_anonymous": data.get("is_anonymous", True),
                "allow_multiple": False,
                "allow_edit_until_end": True,
                "audience_type": "all",
                "ends_at": ends_at,
                "reminder_days": [3, 1],
            },
        )
        if created:
            created_count += 1
        else:
            updated_count += 1
            survey.description = data["description"]
            survey.is_anonymous = data.get("is_anonymous", True)
            survey.author = author
            survey.ends_at = ends_at
            survey.save(
                update_fields=[
                    "description",
                    "is_anonymous",
                    "author",
                    "ends_at",
                    "updated_at",
                ]
            )

        survey.tags.set(_ensure_tags(data.get("tags", [])))
        _create_questions(survey, data["questions"])

        if publish and survey.status != "active":
            survey.status = "active"
            if not survey.starts_at:
                survey.starts_at = now
            survey.save(update_fields=["status", "starts_at", "updated_at"])
            published_count += 1

    return created_count, updated_count, published_count


def publish_wb_pack_surveys(queryset=None):
    """Опубликовать опросы пакета (или переданный queryset)."""
    from surveys.services import send_survey_invitations

    now = timezone.now()
    qs = queryset if queryset is not None else Survey.objects.filter(
        title__startswith=PACK_MARKER
    )
    count = 0
    for survey in qs:
        if survey.status == "active":
            continue
        survey.status = "active"
        if not survey.starts_at:
            survey.starts_at = now
        survey.save(update_fields=["status", "starts_at", "updated_at"])
        send_survey_invitations(survey)
        count += 1
    return count
