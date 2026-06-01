# Generated migration for Discord webhook URL field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('euniforms', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='form',
            name='discord_webhook_url',
            field=models.URLField(blank=True, help_text='Optional Discord webhook URL to send form responses to. Format: https://discord.com/api/webhooks/{id}/{token}', max_length=500, null=True),
        ),
    ]