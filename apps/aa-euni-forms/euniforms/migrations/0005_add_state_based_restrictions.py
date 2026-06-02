# Generated to add state-based form restrictions

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('euniforms', '0004_add_performance_indexes'),
    ]

    operations = [
        # Create GroupStateMapping model
        migrations.CreateModel(
            name='GroupStateMapping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('state', models.CharField(max_length=50)),
                ('group', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='state_mapping', to='auth.group')),
            ],
            options={
                'default_permissions': (),
            },
        ),

        # Add state-based restriction fields to Form model
        migrations.AddField(
            model_name='form',
            name='restricted_states',
            field=models.JSONField(blank=True, default=list, help_text='User states that may fill out the form. Leave empty to allow any state. Common states: member, student, alumni, inactive'),
        ),
        migrations.AddField(
            model_name='form',
            name='restrict_by_group',
            field=models.BooleanField(default=True, help_text='Enable group-based restrictions'),
        ),
        migrations.AddField(
            model_name='form',
            name='restrict_by_state',
            field=models.BooleanField(default=False, help_text='Enable state-based restrictions'),
        ),
        migrations.AddField(
            model_name='form',
            name='restriction_logic',
            field=models.CharField(
                choices=[('OR', 'Either group OR state (less restrictive)'), ('AND', 'Both group AND state (more restrictive)')],
                default='OR',
                help_text='How to combine group and state restrictions when both are enabled',
                max_length=3
            ),
        ),
    ]