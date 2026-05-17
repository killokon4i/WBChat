"""
Пакет демо-опросов ВБ Банк: удовлетворённость, вовлечённость, культура и т.д.
Используется management-командой и Django Admin.
"""
from datetime import timedelta

from django.utils import timezone

from surveys.models import Survey, SurveyQuestion, SurveyQuestionOption, SurveyTag


# Уникальный префикс в названии — не дублировать при повторном запуске
PACK_MARKER = "[ВБ Банк]"
PACK_DEV_MARKER = "[ВБ Банк · Развитие]"

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

WB_DEVELOPMENT_SURVEYS = [
    {
        "title": f"{PACK_DEV_MARKER} Корпоративное обучение",
        "description": (
            "Опрос о тренингах, курсах и платформах обучения ВБ Банка. "
            "Если вы не участвовали в программе — уточняющие вопросы пропускаются автоматически."
        ),
        "tags": ["training-feedback", "hr-processes"],
        "is_anonymous": True,
        "questions": [
            {
                "client_id": "train-main",
                "title": (
                    "Участвовали ли вы в обучающих мероприятиях ВБ Банка "
                    "(тренинги, вебинары, курсы) за последние 12 месяцев?"
                ),
                "question_type": SurveyQuestion.TYPE_SINGLE,
                "is_required": True,
                "options": ["Да", "Нет"],
                "sub_questions": [
                    {
                        "title": "Как часто вы участвовали?",
                        "question_type": SurveyQuestion.TYPE_SINGLE,
                        "is_required": True,
                        "parent_triggers": ["Да"],
                        "options": [
                            "1–2 раза",
                            "3–5 раз",
                            "6 и более",
                        ],
                    },
                    {
                        "title": "Какой формат обучения был для вас наиболее полезным?",
                        "question_type": SurveyQuestion.TYPE_SINGLE,
                        "is_required": True,
                        "parent_triggers": ["Да"],
                        "options": [
                            "Очные тренинги",
                            "Онлайн-курсы",
                            "Вебинары",
                            "Обучение от наставника / коллег",
                        ],
                    },
                    {
                        "title": "Оцените качество обучения в банке",
                        "question_type": SurveyQuestion.TYPE_SCALE,
                        "is_required": True,
                        "parent_triggers": ["Да"],
                        "scale_min": 1,
                        "scale_max": 10,
                    },
                    {
                        "title": "Что бы вы улучшили в программе обучения?",
                        "question_type": SurveyQuestion.TYPE_TEXT,
                        "is_required": False,
                        "parent_triggers": ["Да"],
                    },
                ],
            },
            {
                "client_id": "platform-main",
                "title": "Пользуетесь ли вы внутренней платформой или библиотекой обучения ВБ Банка?",
                "question_type": SurveyQuestion.TYPE_SINGLE,
                "is_required": True,
                "options": ["Да", "Нет"],
                "sub_questions": [
                    {
                        "title": "Как часто вы заходите на платформу обучения?",
                        "question_type": SurveyQuestion.TYPE_SINGLE,
                        "is_required": True,
                        "parent_triggers": ["Да"],
                        "options": [
                            "Еженедельно",
                            "Несколько раз в месяц",
                            "Реже раза в месяц",
                        ],
                    },
                    {
                        "title": "Чего не хватает в обучающих материалах банка?",
                        "question_type": SurveyQuestion.TYPE_TEXT,
                        "is_required": False,
                        "parent_triggers": ["Да"],
                    },
                ],
            },
            {
                "title": "Что поможет вам развиваться профессиональнее в ВБ Банке?",
                "question_type": SurveyQuestion.TYPE_MULTIPLE,
                "is_required": False,
                "options": [
                    "Больше очных тренингов",
                    "Больше онлайн-курсов",
                    "Индивидуальный план развития",
                    "Наставник / карьерный партнёр",
                    "Время на обучение в рабочем графике",
                    "Другое",
                ],
            },
        ],
    },
    {
        "title": f"{PACK_DEV_MARKER} Наставничество и карьера",
        "description": (
            "Обратная связь о наставничестве, карьерных программах и понятности роста в банке. "
            "Подвопросы появляются только при ответе «Да»."
        ),
        "tags": ["training-feedback", "hr-processes"],
        "is_anonymous": True,
        "questions": [
            {
                "client_id": "mentor-main",
                "title": "Есть ли у вас наставник или карьерный партнёр в ВБ Банке?",
                "question_type": SurveyQuestion.TYPE_SINGLE,
                "is_required": True,
                "options": ["Да", "Нет"],
                "sub_questions": [
                    {
                        "title": "Насколько наставничество помогает вам в работе?",
                        "question_type": SurveyQuestion.TYPE_SCALE,
                        "is_required": True,
                        "parent_triggers": ["Да"],
                        "scale_min": 1,
                        "scale_max": 10,
                    },
                    {
                        "title": "Как часто вы встречаетесь с наставником?",
                        "question_type": SurveyQuestion.TYPE_SINGLE,
                        "is_required": True,
                        "parent_triggers": ["Да"],
                        "options": [
                            "Еженедельно",
                            "Раз в 2–4 недели",
                            "По необходимости",
                        ],
                    },
                ],
            },
            {
                "client_id": "career-main",
                "title": (
                    "Участвуете ли вы в программах карьерного развития "
                    "(ИПР, оценка компетенций, ротация, talent-программы)?"
                ),
                "question_type": SurveyQuestion.TYPE_SINGLE,
                "is_required": True,
                "options": ["Да", "Нет"],
                "sub_questions": [
                    {
                        "title": "Что из перечисленного было для вас наиболее полезным?",
                        "question_type": SurveyQuestion.TYPE_SINGLE,
                        "is_required": True,
                        "parent_triggers": ["Да"],
                        "options": [
                            "Индивидуальный план развития (ИПР)",
                            "Оценка компетенций",
                            "Ротация / смена роли",
                            "Talent / high-potential программа",
                        ],
                    },
                    {
                        "title": "Что можно улучшить в программах развития карьеры?",
                        "question_type": SurveyQuestion.TYPE_TEXT,
                        "is_required": False,
                        "parent_triggers": ["Да"],
                    },
                ],
            },
            {
                "title": "Насколько вам понятны возможности карьерного роста в ВБ Банке?",
                "question_type": SurveyQuestion.TYPE_SCALE,
                "is_required": True,
                "scale_min": 1,
                "scale_max": 10,
                "help_text": "1 — совсем непонятно, 10 — полностью понятно",
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
            "training-feedback": "Оценка обучения",
        }
        tag, _ = SurveyTag.objects.get_or_create(
            slug=slug,
            defaults={"name": defaults.get(slug, slug.replace("-", " ").title())},
        )
        tags.append(tag)
    return tags


def _create_question_row(survey, order, qd, parent=None, parent_triggers=None):
    q = SurveyQuestion.objects.create(
        survey=survey,
        order=order,
        title=qd["title"],
        help_text=qd.get("help_text", ""),
        question_type=qd["question_type"],
        is_required=qd.get("is_required", False),
        scale_min=qd.get("scale_min", 1),
        scale_max=qd.get("scale_max", 10),
        parent_question=parent,
        parent_option_values=list(parent_triggers or []),
    )
    if q.question_type in (
        SurveyQuestion.TYPE_SINGLE,
        SurveyQuestion.TYPE_MULTIPLE,
    ):
        for idx, text in enumerate(qd.get("options") or []):
            SurveyQuestionOption.objects.create(
                question=q, order=idx, text=text
            )
    return q


def _create_questions(survey, questions_data):
    survey.questions.all().delete()
    order = 0
    for qd in questions_data:
        parent = _create_question_row(survey, order, qd)
        order += 1
        for sub in qd.get("sub_questions") or []:
            triggers = sub.get("parent_triggers") or ["Да"]
            _create_question_row(survey, order, sub, parent=parent, parent_triggers=triggers)
            order += 1


def _seed_survey_catalog(catalog, author, *, publish=False, duration_days=14):
    """Создать/обновить опросы из каталога. Вернуть (создано, обновлено, опубликовано)."""
    if author is None:
        raise ValueError("Нужен автор опроса (пользователь).")

    created_count = 0
    updated_count = 0
    published_count = 0
    now = timezone.now()
    ends_at = now + timedelta(days=duration_days)

    for data in catalog:
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


def seed_wb_bank_surveys(author, *, publish=False, duration_days=14):
    return _seed_survey_catalog(
        WB_BANK_SURVEYS, author, publish=publish, duration_days=duration_days
    )


def seed_wb_development_surveys(author, *, publish=False, duration_days=14):
    return _seed_survey_catalog(
        WB_DEVELOPMENT_SURVEYS, author, publish=publish, duration_days=duration_days
    )


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
