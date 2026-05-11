from django import forms

from .models import Survey, SurveyQuestion


def _parse_int_list(value):
    """'2, 1' -> [2, 1], пустая строка -> []."""
    if not value or not str(value).strip():
        return []
    return [int(x.strip()) for x in str(value).split(",") if x.strip().isdigit()]


def _parse_str_list(value):
    """'isModerator, is_hr' -> ['isModerator', 'is_hr']."""
    if not value or not str(value).strip():
        return []
    return [x.strip() for x in str(value).split(",") if x.strip()]


class SurveyForm(forms.ModelForm):
    class Meta:
        model = Survey
        fields = [
            "title",
            "description",
            "is_anonymous",
            "allow_multiple",
            "allow_edit_until_end",
            "starts_at",
            "ends_at",
            "audience_type",
            "audience_departments",
            "audience_users",
            "audience_roles",
            "excluded_users",
            "reminder_days",
            "tags",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Название опроса"}),
            "description": forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "Описание или цель опроса"}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
            "audience_type": forms.Select(attrs={"class": "form-control"}),
            "audience_departments": forms.SelectMultiple(attrs={"size": 6, "class": "form-control form-select-multi"}),
            "audience_users": forms.SelectMultiple(attrs={"size": 6, "class": "form-control form-select-multi"}),
            "excluded_users": forms.SelectMultiple(attrs={"size": 4, "class": "form-control form-select-multi"}),
        }
        help_texts = {
            "audience_departments": "Удерживайте Ctrl (Cmd на Mac) для выбора нескольких.",
            "audience_users": "Удерживайте Ctrl (Cmd на Mac) для выбора нескольких.",
            "excluded_users": "Удерживайте Ctrl для выбора нескольких.",
            "tags": "Удерживайте Ctrl для выбора нескольких.",
        }

    def clean_reminder_days(self):
        value = self.cleaned_data.get("reminder_days")
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return _parse_int_list(value) if isinstance(value, str) else list(value)

    def clean_audience_roles(self):
        value = self.cleaned_data.get("audience_roles")
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return _parse_str_list(value)
        return list(value)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # JSONField по умолчанию ожидает JSON; подменяем на CharField для ввода через запятую
        self.fields["reminder_days"] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={"placeholder": "2, 1 (дни до окончания)", "class": "form-control"}),
            label=self.fields["reminder_days"].label,
            help_text="Через запятую: за сколько дней до окончания напоминать (например 2, 1).",
        )
        self.fields["audience_roles"] = forms.CharField(
            required=False,
            widget=forms.TextInput(attrs={"placeholder": "isModerator, is_hr", "class": "form-control"}),
            label=self.fields["audience_roles"].label,
            help_text="Через запятую: имена флагов пользователя (например isModerator, is_hr).",
        )
        if self.instance and self.instance.pk:
            if isinstance(self.instance.reminder_days, list) and self.instance.reminder_days:
                self.initial.setdefault(
                    "reminder_days", ", ".join(str(x) for x in self.instance.reminder_days)
                )
            if isinstance(self.instance.audience_roles, list) and self.instance.audience_roles:
                self.initial.setdefault(
                    "audience_roles", ", ".join(self.instance.audience_roles)
                )


class QuestionInlineForm(forms.Form):
    """
    Упрощённая форма конструктора вопросов.
    Опции для single/multiple вводятся одной строкой, разделённой переводами строк.
    """

    id = forms.IntegerField(required=False, widget=forms.HiddenInput)
    title = forms.CharField(label="Текст вопроса")
    question_type = forms.ChoiceField(
        label="Тип",
        choices=SurveyQuestion.QUESTION_TYPES,
    )
    is_required = forms.BooleanField(label="Обязательный", required=False)
    options_raw = forms.CharField(
        label="Варианты (по одному на строку)",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

