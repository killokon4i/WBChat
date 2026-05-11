import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("surveys", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="surveyquestion",
            name="parent_question",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Если задан, вопрос является подвопросом и показывается только при "
                    "выборе одного из «триггерных» вариантов в родительском вопросе."
                ),
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="sub_questions",
                to="surveys.surveyquestion",
                verbose_name="Родительский вопрос",
            ),
        ),
        migrations.AddField(
            model_name="surveyquestion",
            name="parent_option_values",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    "Список значений (текстов вариантов или числа для шкалы), при выборе "
                    "которых подвопрос будет показан."
                ),
                verbose_name="Триггерные ответы родителя",
            ),
        ),
    ]
