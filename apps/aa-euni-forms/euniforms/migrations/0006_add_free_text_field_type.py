# Add FREE_TEXT field type to FormField choices

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('euniforms', '0005_add_state_based_restrictions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formfield',
            name='field_type',
            field=models.CharField(
                choices=[
                    ('SHORT_TEXT', 'Short text'),
                    ('LONG_TEXT', 'Paragraph text'),
                    ('FREE_TEXT', 'Free text (up to 1000 characters)'),
                    ('SINGLE_CHOICE', 'Single choice'),
                    ('MULTI_CHOICE', 'Multiple choice'),
                    ('NUMBER', 'Number'),
                    ('DATE', 'Date'),
                    ('BOOLEAN', 'Yes / No'),
                    ('EVE_CHARACTER', 'EVE character (verified)')
                ],
                default='SHORT_TEXT',
                max_length=20
            ),
        ),
    ]