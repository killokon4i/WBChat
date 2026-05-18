from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='attachment',
            name='variant',
            field=models.CharField(
                choices=[
                    ('default', 'Default'),
                    ('voice', 'Voice message'),
                    ('video_note', 'Video note'),
                ],
                default='default',
                max_length=20,
            ),
        ),
    ]
