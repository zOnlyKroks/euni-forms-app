# Generated to add performance indexes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('euniforms', '0003_form_introduction_text'),
    ]

    operations = [
        # Add indexes to Form model for better query performance
        migrations.AddIndex(
            model_name='form',
            index=models.Index(fields=['status'], name='form_status_idx'),
        ),
        migrations.AddIndex(
            model_name='form',
            index=models.Index(fields=['created_at'], name='form_created_at_idx'),
        ),
        migrations.AddIndex(
            model_name='form',
            index=models.Index(fields=['status', 'created_at'], name='form_status_created_idx'),
        ),

        # Add indexes to FormResponse model for better query performance
        migrations.AddIndex(
            model_name='formresponse',
            index=models.Index(fields=['submitted_at'], name='response_submitted_at_idx'),
        ),
        migrations.AddIndex(
            model_name='formresponse',
            index=models.Index(fields=['form', 'submitted_at'], name='response_form_submitted_idx'),
        ),
        migrations.AddIndex(
            model_name='formresponse',
            index=models.Index(fields=['user'], name='response_user_idx'),
        ),
        migrations.AddIndex(
            model_name='formresponse',
            index=models.Index(fields=['main_character_name'], name='response_character_name_idx'),
        ),

        # Add indexes to FormAnswer model for better query performance
        migrations.AddIndex(
            model_name='formanswer',
            index=models.Index(fields=['response'], name='answer_response_idx'),
        ),
        migrations.AddIndex(
            model_name='formanswer',
            index=models.Index(fields=['field'], name='answer_field_idx'),
        ),
        migrations.AddIndex(
            model_name='formanswer',
            index=models.Index(fields=['response', 'field'], name='answer_response_field_idx'),
        ),
    ]