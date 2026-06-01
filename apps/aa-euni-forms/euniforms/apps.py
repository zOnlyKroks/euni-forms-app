"""App configuration."""

# Django
from django.apps import AppConfig

# AA EVE Uni Forms
from euniforms import __version__


class EuniFormsConfig(AppConfig):
    """Config for the EVE Uni Forms app."""

    name = "euniforms"
    label = "euniforms"
    default_auto_field = "django.db.models.BigAutoField"
    verbose_name = f"EVE Uni Forms v{__version__}"
