from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0002_attachment_variant'),
    ]

    operations = [
        migrations.AddField(
            model_name='userconversation',
            name='history_cleared_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
