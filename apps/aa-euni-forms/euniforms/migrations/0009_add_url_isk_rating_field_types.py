# Add URL, ISK_AMOUNT, RATING_5, and RATING_10 field types

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('euniforms', '0008_add_new_field_types'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formfield',
            name='field_type',
            field=models.CharField(
                choices=[
                    ('SHORT_TEXT', 'Short text'),
                    ('FREE_TEXT', 'Free text (up to 1000 characters)'),
                    ('SINGLE_CHOICE', 'Single choice'),
                    ('MULTI_CHOICE', 'Multiple choice'),
                    ('NUMBER', 'Number'),
                    ('DATE_CURRENT', 'Date (always current date)'),
                    ('DATETIME', 'Date and time'),
                    ('BOOLEAN', 'Yes / No'),
                    ('EVE_CHARACTER', 'EVE character (verified)'),
                    ('USER_PICKER', 'User picker (search and select)'),
                    ('URL', 'URL / Link'),
                    ('ISK_AMOUNT', 'ISK Amount'),
                    ('RATING_5', 'Rating (1-5 stars)'),
                    ('RATING_10', 'Rating (1-10 scale)'),
                ],
                default='SHORT_TEXT',
                max_length=20
            ),
        ),
    ]