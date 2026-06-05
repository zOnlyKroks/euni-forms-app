# Losslessly migrate LONG_TEXT to FREE_TEXT and add new field types

from django.db import migrations, models


def migrate_long_text_to_free_text(apps, schema_editor):
    """Convert existing LONG_TEXT fields to FREE_TEXT."""
    FormField = apps.get_model('euniforms', 'FormField')
    FormAnswer = apps.get_model('euniforms', 'FormAnswer')

    # Convert LONG_TEXT to FREE_TEXT in both tables
    FormField.objects.filter(field_type='LONG_TEXT').update(field_type='FREE_TEXT')
    FormAnswer.objects.filter(field_type='LONG_TEXT').update(field_type='FREE_TEXT')


class Migration(migrations.Migration):

    dependencies = [
        ('euniforms', '0007_add_collaborators_and_answer_limits'),
    ]

    operations = [
        # Step 1: Add new field types while keeping LONG_TEXT temporarily
        migrations.AlterField(
            model_name='formfield',
            name='field_type',
            field=models.CharField(
                choices=[
                    ('SHORT_TEXT', 'Short text'),
                    ('LONG_TEXT', 'Paragraph text'),  # Keep temporarily for migration
                    ('FREE_TEXT', 'Free text (up to 1000 characters)'),
                    ('SINGLE_CHOICE', 'Single choice'),
                    ('MULTI_CHOICE', 'Multiple choice'),
                    ('NUMBER', 'Number'),
                    ('DATE_CURRENT', 'Date (always current date)'),
                    ('DATETIME', 'Date and time'),
                    ('BOOLEAN', 'Yes / No'),
                    ('EVE_CHARACTER', 'EVE character (verified)'),
                    ('USER_PICKER', 'User picker (search and select)')
                ],
                default='SHORT_TEXT',
                max_length=20
            ),
        ),

        # Step 2: Convert existing LONG_TEXT data to FREE_TEXT
        migrations.RunPython(migrate_long_text_to_free_text),

        # Step 3: Remove LONG_TEXT from choices (final field types)
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
                    ('USER_PICKER', 'User picker (search and select)')
                ],
                default='SHORT_TEXT',
                max_length=20
            ),
        ),
    ]